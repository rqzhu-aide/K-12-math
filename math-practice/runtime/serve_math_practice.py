"""Serve Math Practice locally with automatic decision-model assessment.

Run with a shared Python installation, then open http://127.0.0.1:8877/.
The backend owns credentials, question context and the assessment rubrics.
Decision and speech connections use the Python standard library. Codex tests use
the shared openai-codex Python package and installed Codex runtime.
"""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
import sqlite3
from pathlib import Path
from layout import database_root
import urllib.parse
import uuid
from student_assessment import AssessmentError, ModelConfig, StudentAssessment
from connection_settings import ConnectionSettings, SettingsError, key_revision
from openai_connection import OpenAIConnection
from chatgpt_plan import ChatGPTPlan
from model_connections import model_status, test_speech, test_inference, transcribe, MAX_AUDIO_BYTES
from practice_tutor import normalize_turn, review_submission, test_tutor_connection
from graph_evidence import PILOT_ITEM, observation_for
from question_banks import BankError, FIGURE_PATH, custom_asset_path
from knowledge_graph import GraphError, build_database, source_digest, validate_database
import curriculum_graph

ROOT = Path(__file__).resolve().parents[2]
ENGINE_VERSION = 'public-v' + (ROOT / 'math-practice/VERSION').read_text(encoding='utf-8').strip()


def prepare_knowledge_graph(root=ROOT):
    """Check the local derived index once; build it offline on a fresh checkout."""
    root = Path(root)
    database = database_root(root) / 'knowledge-graph/knowledge.sqlite3'
    source = database_root(root) / 'knowledge-graph/source'
    complete = all((source / name).is_file() for name in
                   ('metadata.json', 'nodes.json', 'relationships.json', 'mappings.jsonl'))
    invalid = False
    if database.is_file():
        try:
            report = validate_database(root, check_bindings=False)
            if not complete or report['sourceDigest'] == source_digest(root):
                return report
            invalid = True
        except GraphError:
            invalid = True
    try:
        if complete:
            return build_database(root)
    except (GraphError, OSError) as error:
        print('Knowledge graph could not be rebuilt: ' + str(error), flush=True)
    if invalid:
        # Preserve the invalid artifact, but do not let a partial index steer tutoring.
        database.rename(database.with_name('knowledge-invalid-' + uuid.uuid4().hex + '.sqlite3'))
    return {'valid': False, 'reason': 'database_unavailable' if invalid else 'sources_not_installed'}


def engine_instance(root=ROOT):
    return hashlib.sha256(str(root.resolve()).casefold().encode('utf-8')).hexdigest()


def knowledge_payload(route, query, root=ROOT):
    """Read-only local curriculum browsing, projecting only learner-facing fields."""
    params = urllib.parse.parse_qs(query, keep_blank_values=True, max_num_fields=8)
    if any(len(v) != 1 for v in params.values()):
        raise GraphError('Supply each curriculum parameter once.')
    params = {k: v[0] for k, v in params.items()}
    allowed = {'layers': set(), 'browse': {'layer'}, 'node': {'id', 'layer'},
               'practice': {'layer', 'nodeId', 'sourceNodeId', 'offset'}}
    if route not in allowed or set(params) - allowed[route]:
        raise GraphError('Unknown curriculum query.')
    layer = params.get('layer', 'ailleo')
    curriculum_graph._layer(layer)
    for key in ('id', 'nodeId', 'sourceNodeId'):
        if key in params and (not params[key].strip() or len(params[key]) > 200):
            raise GraphError('Choose a valid concept or standard.')
    if route == 'layers':
        return curriculum_graph.layer_catalog(root)
    if route == 'browse':
        result = curriculum_graph.browse_layer(layer, root)
        if layer == 'ailleo':
            result['nodes'] = [{k: n.get(k) for k in ('id', 'name', 'nameZh', 'description', 'kind')} for n in result['nodes']]
        else:
            result['nodes'] = [{**{k: n.get(k) for k in ('id', 'label', 'description', 'placement')},
                                'placement': {**n.get('placement', {}), **({'category': n['metadata']['domainName']} if layer == 'US' and n.get('metadata', {}).get('domainName') else {})}} for n in result['nodes']]
        result['relationships'] = [{k: e.get(k) for k in ('id', 'fromId', 'toId', 'nodeId', 'prerequisiteId', 'relation', 'directed')} for e in result['relationships']]
        result['alignments'] = [{k: a[k] for k in ('id', 'nodeId', 'layer', 'sourceNodeId', 'relation', 'status')} for a in result['alignments']]
        return result
    if route == 'node':
        if 'id' not in params:
            raise GraphError('Choose a concept.')
        return {'annotations': curriculum_graph.annotations_for_node(params['id'], root),
                'neighborhood': curriculum_graph.layer_neighborhood(params['id'], layer, root)}
    if ('nodeId' in params) == ('sourceNodeId' in params):
        raise GraphError('Choose one concept or standard.')
    offset = params.get('offset', '0')
    if not offset.isascii() or not offset.isdigit():
        raise GraphError('Practice offset must be a nonnegative integer.')
    offset = int(offset)
    if 'sourceNodeId' in params:
        return curriculum_graph.practice_for_source(params['sourceNodeId'], layer, root, limit=30, offset=offset)
    return curriculum_graph.practice_candidates(params['nodeId'], layer, root, limit=30, offset=offset)


class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, status, data, content_type, content_security_policy=None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        if content_security_policy:
            self.send_header('Content-Security-Policy', content_security_policy)
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # The student may have changed questions and canceled the request.

    def error_json(self, status, message):
        self.send_bytes(status, json.dumps({'error': {'message': message}}).encode(), 'application/json')

    def local_request(self, strict=True):
        # Reject cross-site proxy use, including DNS rebinding to this loopback server.
        host = self.headers.get('Host', '')
        allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        origin = self.headers.get('Origin')
        return (host in allowed and (not strict or (
                (origin is None or origin == 'http://' + host)
                and self.headers.get('Sec-Fetch-Site') != 'cross-site')))

    def assessment(self, kind='reasoning'):
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 100_000:
                return self.error_json(413, 'The submission is too large or empty.')
            raw = self.rfile.read(length)
            # Match the other POST routes: unread bytes can reset Windows
            # connections before a rejected request receives its error.
            if not self.local_request():
                return self.error_json(403, 'Use the app from its local HTTP address.')
            attempt = json.loads(raw)
            if not isinstance(attempt, dict):
                raise AssessmentError('Submit a valid answer and reasoning.', 400)
            layer = attempt.get('curriculumLayer', 'ailleo')
            if layer not in curriculum_graph.LAYERS:
                raise AssessmentError('Choose a valid practice path.', 400)
            attempt['curriculumLayer'] = layer
            assessor = self.current_assessor(for_math=kind != 'signals')
            selected_node_id = curriculum_graph.validate_selection(layer, attempt.get('curriculumNodeId'), assessor.root)
            attempt['curriculumNodeId'] = selected_node_id
            turn = normalize_turn(attempt) if kind != 'signals' else None
            if turn:
                attempt['turn'] = turn
                question = assessor._question(attempt.get('questionId'))
                if attempt.get('bank') != question.get('Bank'):
                    return self.error_json(400, 'The submission does not match this question bank.')
            if kind == 'signals':
                result = assessor.learning_signals(attempt)
            elif kind == 'tutor':
                result = review_submission(assessor, self.server.settings, self.server.openai, attempt,
                                           chatgpt=self.server.chatgpt)
            else:
                result = assessor.assess(attempt)
            if turn:
                result['revisionId'] = turn['revisionId']
                observation = observation_for(question, attempt, result)
                if observation is not None:
                    result['graphEvidence'] = observation
            result['curriculumLayer'] = layer
            result['curriculumNodeId'] = selected_node_id
            result['decisionConfigured'] = self.server.settings.decision_config().configured
            result['inferenceConfigured'] = self.server.settings.inference_configured()
            self.send_bytes(200, json.dumps(result).encode(), 'application/json')
        except AssessmentError as exc:
            self.error_json(exc.status, str(exc))
        except (ValueError, TypeError):
            self.error_json(400, 'Submit a valid answer and reasoning.')

    def current_assessor(self, *, for_math=False):
        current = self.server.assessor
        config = self.server.settings.decision_config()
        if config != current.config:
            current = StudentAssessment(config, current.cn_bank_root, current.root)
            self.server.assessor = current
        if for_math and self.server.settings.math_assessment_provider() == 'inference':
            # Keep exact answer checks local, then let Mathematics review the
            # unresolved reasoning. Sentiment remains on its own connection.
            return StudentAssessment(ModelConfig(), current.cn_bank_root, current.root)
        return current

    def connection_action(self, route):
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 30_000:
                return self.error_json(413, 'The connection settings are too large or empty.')
            # Consume the bounded body before rejecting headers. Closing with unread
            # POST bytes can reset Windows connections before the error arrives.
            raw = self.rfile.read(length)
            if not self.local_request():
                return self.error_json(403, 'Use the app from its local HTTP address.')
            if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                return self.error_json(415, 'Connection actions require application/json.')
            body = json.loads(raw)
            if not isinstance(body, dict):
                raise SettingsError('Send connection settings as an object.')
            if route == '/api/settings':
                result = self.server.settings.save(body)
            elif route == '/api/settings/compare':
                result = self.server.settings.compare_file(body)
            elif route == '/api/settings/reload':
                result = self.server.settings.reload()
            elif route in ('/api/settings/decision/test', '/api/settings/jev/test'):
                draft = self.server.settings.on_disk()
                result = draft.test_decision(body)
                result['keyRevision'] = key_revision('decision', draft.decision_config(body).api_key)
            elif route == '/api/settings/speech/test':
                selected = self.server.settings.on_disk().speech_config(body)
                result = test_speech(selected)
                result['keyRevision'] = key_revision('speech', selected.api_key)
            elif route == '/api/settings/inference/test':
                selected = self.server.settings.on_disk().inference_config(body)
                if not selected['model'] or (selected['provider'] == 'api' and not selected['bases']):
                    result = model_status(ModelConfig())
                elif selected['provider'] == 'codex':
                    result = self.server.openai.test({key: selected[key] for key in ('model', 'effort')})
                elif selected['provider'] == 'chatgpt':
                    result = test_tutor_connection(selected, self.server.chatgpt)
                else:
                    result = test_inference(ModelConfig(tuple(selected['bases']), selected['model'], selected['apiKey']))
                result['keyRevision'] = key_revision('inference', selected['apiKey']) if selected['provider'] == 'api' else ''
            elif route == '/api/settings/openai/test':
                result = self.server.openai.test(self.server.settings.openai_config(body))
            elif route == '/api/connections/openai/login':
                result = self.server.openai.start_login()
            elif route == '/api/connections/openai/cancel':
                result = self.server.openai.cancel_login()
            elif route == '/api/connections/chatgpt/login':
                if not body:
                    result = self.server.chatgpt.start_login()
                elif set(body) == {'clientId'} and isinstance(body['clientId'], str):
                    result = self.server.chatgpt.start_login(client_id=body['clientId'])
                elif body == {'newAccount': True} and body['newAccount'] is True:
                    result = self.server.chatgpt.start_login(new_account=True)
                else:
                    raise SettingsError('Choose a saved account or sign in with a new one.')
            elif route == '/api/connections/chatgpt/cancel':
                result = self.server.chatgpt.cancel_login()
            elif route == '/api/connections/chatgpt/models':
                result = self.server.chatgpt.refresh_models()
            elif route == '/api/connections/chatgpt/disconnect':
                result = self.server.chatgpt.sign_out()
            self.send_bytes(200, json.dumps(result).encode(), 'application/json')
        except SettingsError as exc:
            self.error_json(400, str(exc))
        except AssessmentError as exc:
            self.error_json(exc.status, str(exc))
        except (ValueError, TypeError):
            self.error_json(400, 'Send valid connection settings.')

    def transcription(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_AUDIO_BYTES:
                return self.error_json(413, 'Record up to one minute at a time.')
            audio = self.rfile.read(length)
            if not self.local_request():
                return self.error_json(403, 'Use the app from its local HTTP address.')
            if self.headers.get('Content-Type', '').split(';')[0].strip() != 'audio/wav':
                return self.error_json(415, 'Speech input requires PCM WAV audio.')
            result = transcribe(self.server.settings.speech_config(), audio)
            self.send_bytes(200, json.dumps(result).encode(), 'application/json')
        except AssessmentError as exc:
            self.error_json(exc.status, str(exc))
        except (ValueError, TypeError):
            self.error_json(400, 'Send a valid WAV recording.')

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path.startswith('/api/knowledge/'):
            if not self.local_request():
                return self.error_json(403, 'Use the local app address.')
            try:
                result = knowledge_payload(parsed.path[len('/api/knowledge/'):], parsed.query, self.server.assessor.root)
                return self.send_bytes(200, json.dumps(result, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8')
            except (GraphError, ValueError):
                return self.error_json(400, 'Choose a valid practice path, concept, or standard.')
            except (OSError, sqlite3.Error):
                return self.error_json(503, 'Practice paths are unavailable. Use the question bank below.')
        if parsed.path == '/api/engine':
            if not self.local_request():
                return self.error_json(403, 'Use the local app address.')
            return self.send_bytes(200, json.dumps({'application': 'math-practice', 'pid': os.getpid(),
                                                   'port': self.server.server_port, 'version': ENGINE_VERSION,
                                                   'instance': engine_instance(getattr(self.server, 'bank_root', ROOT)),
                                                   'settingsInstance': engine_instance(self.server.settings.path)}).encode(), 'application/json')
        if parsed.path in ('/api/status/decision', '/api/status/speech', '/api/status/inference'):
            if not self.local_request():
                return self.error_json(403, 'Use the local app address.')
            role = parsed.path.rsplit('/', 1)[1]
            if role == 'decision':
                result = model_status(self.server.settings.decision_config())
                result['localEvidenceItems'] = [PILOT_ITEM]
            elif role == 'speech':
                result = model_status(self.server.settings.speech_config())
            else:
                config = self.server.settings.inference_config()
                if not self.server.settings.inference_configured():
                    result = model_status(ModelConfig())
                elif config['provider'] == 'api':
                    result = model_status(ModelConfig(tuple(config['bases']), config['model'], config['apiKey']))
                else:
                    account = (self.server.chatgpt if config['provider'] == 'chatgpt' else self.server.openai).status()
                    result = {'configured': True, 'ready': account['canTest'],
                              'label': 'Signed in' if account['canTest'] else 'Sign in' if account['state'] == 'signed_out' else 'Setup needed',
                              'message': account['message'] + ' Use Test Connection in Mathematics to try a text tutor review.'}
            return self.send_bytes(200, json.dumps(result).encode(), 'application/json')
        if parsed.path == '/api/status':
            if not self.local_request():
                return self.error_json(403, 'Use the local app address.')
            return self.send_bytes(200, json.dumps(self.current_assessor().status()).encode(), 'application/json')
        if parsed.path in ('/api/settings', '/api/connections/openai', '/api/connections/chatgpt'):
            if not self.local_request():
                return self.error_json(403, 'Use the local app address.')
            if parsed.path == '/api/settings':
                result = self.server.settings.public()
            else:
                account = self.server.chatgpt if parsed.path.endswith('/chatgpt') else self.server.openai
                result = account.status()
            return self.send_bytes(200, json.dumps(result).encode(), 'application/json')
        if not self.local_request(strict=False):
            return self.error_json(403, 'Use the local app address.')
        relative = urllib.parse.unquote(parsed.path).lstrip('/')
        if not relative:
            self.send_response(302)
            self.send_header('Location', '/math-practice/')
            self.end_headers()
            return
        if relative in ('', 'math-practice', 'math-practice/'):
            relative = 'math-practice/index.html'
        if relative.startswith('custom-banks/'):
            try:
                asset = custom_asset_path(relative, getattr(self.server, 'bank_root', ROOT))
            except BankError:
                asset = None
            if asset is None:
                return self.error_json(404, 'File not found.')
            if relative == 'custom-banks/banks.js':
                data = asset.read_bytes() if asset.is_file() else b'window.CUSTOM_MATH_BANKS = [];\n'
                return self.send_bytes(200, data, 'text/javascript; charset=utf-8')
            if not asset.is_file():
                return self.error_json(404, 'File not found.')
            return self.send_bytes(200, asset.read_bytes(), mimetypes.guess_type(asset.name)[0] or 'application/octet-stream',
                                   content_security_policy="sandbox; default-src 'none'; style-src 'unsafe-inline'")
        # Published bundles retain their bank-relative asset references. Accept
        # those URLs as well as the explicit database/ URLs used by the UI.
        if relative.startswith('database/'):
            relative = relative[len('database/'):]
        allowed = (relative in ('math-practice/index.html', 'cn-math-bank/bank.js', 'amc-bank/bank.js',
                               'cn-math-bank/NOTICE.md', 'amc-bank/NOTICE.md',
                               'amc-bank/official-solutions/AMC8_2023_Solutions.pdf',
                               'amc-bank/official-solutions/AMC8_2022_Solutions.pdf',
                               'amc-bank/official-solutions/AMC8_2020_Solutions.pdf',
                               'amc-bank/official-solutions/AMC8_2019_Solutions.pdf',
                               'amc-bank/official-solutions/AMC8_2018_Solutions.pdf',
                               'amc-bank/official-solutions/AMC10A_2022_Solutions.pdf',
                               'amc-bank/official-solutions/AMC10A_2021_Spring_Solutions.pdf',
                               'amc-bank/official-solutions/AMC10A_2021_Fall_Solutions.pdf',
                               'math-practice/answer-check.js',
                               'math-practice/settings.html', 'math-practice/settings.css', 'math-practice/settings.js',
                               'math-practice/theme.css', 'math-practice/theme.js',
                               'math-practice/speech-input.js', 'math-practice/speech-worklet.js',
                               'math-practice/practice-feedback.js', 'math-practice/curriculum-path.js', 'math-practice/graph-evidence.js')
                   or relative.startswith('math-practice/vendor/')
                   or relative.startswith('cn-math-bank/figures/')
                   or (relative.startswith('amc-bank/') and FIGURE_PATH.fullmatch(relative[len('amc-bank/'):])))
        asset_root = ROOT if relative.startswith('math-practice/') else database_root(getattr(self.server, 'bank_root', ROOT))
        path = (asset_root / relative).resolve()
        if not allowed or not path.is_relative_to(asset_root) or not path.is_file() or any(p.startswith('.') for p in Path(relative).parts):
            return self.error_json(404, 'File not found.')
        # Vendor and figure roots cannot escape their allowlisted subtree via '..'.
        if '..' in Path(relative).parts:
            return self.error_json(404, 'File not found.')
        data = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
        if relative.endswith('.html'):
            content_type = 'text/html; charset=utf-8'
        self.send_bytes(200, data, content_type)

    def do_POST(self):
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == '/api/assessment':
            return self.assessment()
        if parsed.path == '/api/learning-signals':
            return self.assessment('signals')
        if parsed.path == '/api/tutor':
            return self.assessment('tutor')
        if parsed.path == '/api/transcription':
            return self.transcription()
        if parsed.path in ('/api/settings', '/api/settings/reload', '/api/settings/compare', '/api/settings/jev/test', '/api/settings/openai/test',
                           '/api/settings/decision/test', '/api/settings/speech/test', '/api/settings/inference/test',
                           '/api/connections/openai/login', '/api/connections/openai/cancel',
                           '/api/connections/chatgpt/login', '/api/connections/chatgpt/cancel',
                           '/api/connections/chatgpt/disconnect', '/api/connections/chatgpt/models'):
            return self.connection_action(parsed.path)
        self.error_json(405, 'Unsupported route.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8877)
    parser.add_argument('--settings', type=Path, help='Load a local JSON or YAML settings file.')
    parser.add_argument('--bank-root', type=Path, default=ROOT,
                        help='Read the banks and knowledge graph from this directory, using the installed practice UI.')
    args = parser.parse_args()
    if args.settings is not None and not args.settings.is_file():
        parser.error(f'The selected settings file does not exist: {args.settings}')
    bank_root = args.bank_root.resolve()
    if not bank_root.is_dir():
        parser.error('Choose an existing bank root.')
    prepare_knowledge_graph(bank_root)
    try:
        settings = ConnectionSettings(args.settings)
        if not settings.path.exists():
            settings.save({})
    except SettingsError as exc:
        parser.error(str(exc))
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.bank_root = bank_root
    server.settings = settings
    server.assessor = StudentAssessment(server.settings.decision_config(), root=bank_root)
    server.openai = OpenAIConnection(bank_root / '.local/codex-work')
    server.chatgpt = ChatGPTPlan()
    print(f'Math Practice: http://127.0.0.1:{server.server_port}/math-practice/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.openai.close()
        server.chatgpt.close()
        server.server_close()


if __name__ == '__main__':
    main()
