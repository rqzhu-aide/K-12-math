"""Local model connections. Secret values never appear in public settings."""
from contextlib import contextmanager
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import threading
import time
import urllib.parse

from student_assessment import AssessmentError, ModelConfig, StudentAssessment

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / 'math-practice/config.json'
DEFAULT_OPENAI = {'model': '', 'effort': 'medium'}
EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max')
_REVISION_SECRET = secrets.token_bytes(32)
# Provider defaults, checked against official API documentation on 2026-11-01.
PRESETS = {
    'openai': {'label': 'OpenAI', 'base': 'https://api.openai.com/v1',
               'speechModel': 'gpt-transcribe', 'textModel': 'gpt-5.4-mini'},
    'mistral': {'label': 'Mistral', 'base': 'https://api.mistral.ai/v1',
                'speechModel': 'voxtral-mini-transcribe-3', 'textModel': 'mistral-small-latest'},
}


class SettingsError(ValueError):
    pass


def yaml_module():
    # JSON settings do not require an additional package.
    try:
        import yaml
    except ImportError:
        raise SettingsError('YAML settings require PyYAML. Install it for your user with: '
                            'python -m pip install --user PyYAML') from None
    return yaml


def read_document(path):
    yaml = yaml_module() if path.suffix.lower() in ('.yaml', '.yml') else None
    try:
        content = path.read_text(encoding='utf-8-sig')
        return yaml.safe_load(content) if yaml else json.loads(content)
    except (OSError, UnicodeError, ValueError):
        pass
    except Exception as exc:
        if yaml is None or not isinstance(exc, yaml.YAMLError):
            raise
    # Parser errors can contain credential values from the source document.
    raise SettingsError('Connection settings could not be read. Check the settings file '
                        'for valid YAML and model settings.' if yaml else
                        'Connection settings could not be read. Check the settings file '
                        'for valid JSON and model settings.') from None


def key_revision(role, key):
    """Compare masked keys within this engine without publishing a guessable key hash."""
    return hmac.digest(_REVISION_SECRET, (role + '\0' + key).encode(), 'sha256').hex() if key else ''


@contextmanager
def settings_write_lock(path):
    # Different launcher ports can use the same configuration file.
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.with_name(path.name + '.lock').open('a+b') as lock:
            if os.name == 'nt':
                import msvcrt
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            yield
    except OSError:
        raise SettingsError('Connection settings could not be saved. Check write access to the local settings folder.') from None


def model_id(value):
    if value == '':
        return value
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}', value):
        raise SettingsError('Enter a valid model ID.')
    return value


def server_bases(value):
    if not isinstance(value, list) or not 0 <= len(value) <= 5:
        raise SettingsError('Enter up to five server addresses, one per line. Leave empty to disable this connection.')
    result = []
    for address in value:
        if not isinstance(address, str) or len(address) > 800:
            raise SettingsError('Enter a valid HTTP or HTTPS server address.')
        address = address.strip().rstrip('/')
        try:
            parts = urllib.parse.urlsplit(address)
            parts.port
        except ValueError:
            raise SettingsError('Check the server address and port.') from None
        if (parts.scheme not in ('http', 'https') or not parts.hostname or parts.username
                or parts.password or parts.query or parts.fragment or any(c.isspace() for c in address)):
            raise SettingsError('Use an HTTP or HTTPS server address without credentials, a query, or a fragment.')
        if address not in result:
            result.append(address)
    return tuple(result)


def api_key(value, previous):
    if not isinstance(value, str) or len(value) > 4096 or '\n' in value or '\r' in value:
        raise SettingsError('Enter a valid API key.')
    return value.strip() or previous


def http_config(patch, previous):
    bases = server_bases(patch.get('bases', list(previous.bases)))
    protocol = patch.get('protocol', previous.protocol)
    if protocol not in ('systemone', 'chat'):
        raise SettingsError('Choose a compatible chat API or the custom decision API.')
    return ModelConfig(bases,
                       model_id(patch.get('model', previous.model)),
                       api_key(patch.get('apiKey', ''), previous.api_key if bases == previous.bases else ''),
                       protocol)


def public_http(config):
    return {'bases': list(config.bases), 'model': config.model, 'keyConfigured': bool(config.api_key),
            'configured': config.configured, 'protocol': config.protocol}


def saved_http(config):
    return {'bases': list(config.bases), 'model': config.model, 'apiKey': config.api_key, 'protocol': config.protocol}


class ConnectionSettings:
    def __init__(self, path=None, defaults=None):
        self.path = Path(path) if path is not None else DEFAULT_PATH
        self._lock = threading.RLock()
        self._decision = defaults or ModelConfig.from_environment()
        self._speech = ModelConfig(
            server_bases([os.environ['SPEECH_BASE_URL']]) if os.environ.get('SPEECH_BASE_URL') else (),
            os.environ.get('SPEECH_MODEL', '').strip(), os.environ.get('SPEECH_API_KEY', '').strip())
        self._inference = {'provider': 'api', **DEFAULT_OPENAI, 'bases': [], 'apiKey': ''}
        self._key_files = {}
        self._math_assessment = 'decision'
        self._setup = {'mode': 'separate' if self._decision.configured or self._speech.configured else 'single', 'provider': ''}
        self.notice = ''
        if self.path.is_file():
            try:
                saved = read_document(self.path)
                configs = self._merge(saved)
                self._key_files = self._key_references(saved, configs)
                self._decision, self._speech, self._inference = configs
                self._math_assessment = self.math_assessment_provider(saved)
                self._setup = self._setup_selection(saved)
            except SettingsError:
                raise
            except (OSError, ValueError, TypeError, AttributeError):
                raise SettingsError('Connection settings could not be read. Check the settings file and model settings.') from None

    def _resolve_key_files(self, patch):
        result = dict(patch)
        for role, alias in (('decision', 'jev'), ('speech', 'speech'), ('inference', 'openai')):
            name = role if role in patch else alias
            section = patch.get(name)
            if not isinstance(section, dict) or 'apiKeyFile' not in section:
                continue
            reference = section['apiKeyFile']
            if (not isinstance(reference, str) or not reference.strip() or len(reference) > 4096
                    or any(c in reference for c in ('\n', '\r', '\0'))):
                raise SettingsError(f'Enter a valid API key file for {role}.')
            if section.get('apiKey'):
                raise SettingsError(f'Use either an API key or an API key file for {role}.')
            try:
                key = (self.path.parent / reference).read_text(encoding='utf-8-sig').strip()
            except (OSError, UnicodeError, ValueError):
                raise SettingsError(f'The {role} API key file could not be read. Check apiKeyFile in the settings profile.') from None
            key = api_key(key, '')
            if not key:
                raise SettingsError(f'The {role} API key file is empty.')
            result[name] = {**section, 'apiKey': key}
        return result

    def _key_references(self, patch, configs):
        """Keep file references only while they supply the same destination's key."""
        expanded = self._expand_shared(patch)
        references = {}
        previous = (self._decision, self._speech, self._inference)
        for index, (role, alias) in enumerate((('decision', 'jev'), ('speech', 'speech'), ('inference', 'openai'))):
            section = expanded.get(role, expanded.get(alias, {}))
            if 'apiKeyFile' in section:
                references[role] = section['apiKeyFile']
                continue
            candidate = configs[index]
            old = previous[index]
            same = (candidate['apiKey'] == old['apiKey'] and candidate['bases'] == old['bases']) if role == 'inference' else (
                candidate.api_key == old.api_key and candidate.bases == old.bases)
            if role in self._key_files and same:
                references[role] = self._key_files[role]
        return references

    def _merge(self, patch):
        if not isinstance(patch, dict):
            raise SettingsError('Send settings as an object.')
        self.math_assessment_provider(patch)
        patch = self._resolve_key_files(self._expand_shared(patch))
        decision = patch.get('decision', patch.get('jev', {}))
        speech = patch.get('speech', {})
        inference = patch.get('inference', patch.get('openai', {}))
        if not all(isinstance(section, dict) for section in (decision, speech, inference)):
            raise SettingsError('Send connection settings as objects.')
        selection = {key: inference.get(key, value) for key, value in self._inference.items()}
        if selection['provider'] not in ('api', 'chatgpt', 'codex'):
            raise SettingsError('Choose a supported Mathematics connection.')
        selection['model'] = model_id(selection['model'])
        # Remember each method's model when switching between an API and a plan.
        models = inference.get('modelByProvider', self._inference.get('modelByProvider', {}))
        if not isinstance(models, dict) or any(key not in ('api', 'chatgpt', 'codex') for key in models):
            raise SettingsError('Check the saved Mathematics model names.')
        models = {key: model_id(name) for key, name in models.items()}
        if selection['provider'] != self._inference['provider'] and self._inference['model']:
            models[self._inference['provider']] = self._inference['model']
        if selection['model'] or models:
            models[selection['provider']] = selection['model']
            selection['modelByProvider'] = models
        if selection['effort'] not in EFFORTS:
            raise SettingsError('Choose a supported reasoning effort.')
        bases = selection['bases']
        selection['bases'] = list(server_bases(bases))
        selection['apiKey'] = api_key(inference.get('apiKey', ''),
                                      self._inference['apiKey'] if selection['bases'] == self._inference['bases'] else '')
        if inference.get('keyFrom') == 'decision':
            source = http_config(decision, self._decision)
            if source.protocol != 'chat' or selection['bases'] != list(source.bases) or selection['model'] != source.model:
                raise SettingsError('Use the same chat address and model as the learning-signals connection, or enter a separate key.')
            selection['apiKey'] = source.api_key
        return http_config(decision, self._decision), http_config(speech, self._speech), selection

    def _setup_selection(self, patch):
        selection = patch.get('setup')
        if selection is None:
            configured = self._decision.configured or self._speech.configured or self.inference_configured()
            return {'mode': 'separate' if configured else 'single', 'provider': ''}
        if (not isinstance(selection, dict) or selection.get('mode') not in ('single', 'separate')
                or selection.get('provider', '') not in ('', 'custom', *PRESETS)):
            raise SettingsError('Choose one provider or separate model connections.')
        return {'mode': selection['mode'], 'provider': selection.get('provider', '')}

    def _expand_shared(self, patch):
        if 'shared' not in patch:
            return patch
        shared = patch['shared']
        if not isinstance(shared, dict) or not isinstance(shared.get('useTutor', False), bool):
            raise SettingsError('Send valid shared connection settings.')
        bases = server_bases(shared.get('bases', []))
        # Reuse a saved key only for this same destination. Never return it to the browser.
        previous = self._speech.api_key if bases == self._speech.bases else ''
        key = api_key(shared.get('apiKey', ''), previous)
        if bases and self._setup_selection(patch)['provider'] in PRESETS and not key:
            raise SettingsError('Enter the API key for your selected provider.')
        common = {'bases': list(bases), 'apiKey': key}
        return {**patch,
                'speech': {**common, 'model': shared.get('speechModel', '')},
                'decision': {**common, 'model': shared.get('textModel', ''),
                             'protocol': 'chat' if shared.get('textModel') else self._decision.protocol},
                'inference': {**common, 'provider': 'api',
                              'model': shared.get('textModel', '') if shared.get('useTutor') else '',
                              'bases': list(bases) if shared.get('useTutor') else []}}

    def public(self):
        with self._lock:
            inference = {key: value for key, value in self._inference.items() if key != 'apiKey'}
            inference['bases'] = list(inference['bases'])
            inference['keyConfigured'] = bool(self._inference['apiKey'])
            inference['configured'] = self.inference_configured()
            inference['keyRevision'] = key_revision('inference', self._inference['apiKey'])
            return {'decision': {**public_http(self._decision), 'keyRevision': key_revision('decision', self._decision.api_key)},
                    'speech': {**public_http(self._speech), 'keyRevision': key_revision('speech', self._speech.api_key)},
                    'inference': inference, 'notice': self.notice, 'mathAssessment': self._math_assessment,
                    'setup': dict(self._setup), 'presets': PRESETS,
                    # Compatibility with an already-open older settings page.
                    'jev': public_http(self._decision), 'openai': self.openai_config()}

    def decision_config(self, patch=None):
        with self._lock:
            return self._merge(patch or {})[0]

    jev_config = decision_config

    def speech_config(self, patch=None):
        with self._lock:
            return self._merge(patch or {})[1]

    def inference_config(self, patch=None):
        with self._lock:
            return dict(self._merge(patch or {})[2])

    def inference_configured(self, patch=None):
        selection = self.inference_config(patch)
        return bool(selection['model'] and (selection['provider'] != 'api' or selection['bases']))

    def openai_config(self, patch=None):
        selection = self.inference_config(patch)
        return {key: selection[key] for key in ('model', 'effort')}

    def math_assessment_provider(self, patch=None):
        with self._lock:
            if patch is not None and not isinstance(patch, dict):
                raise SettingsError('Send settings as an object.')
            provider = (patch or {}).get('mathAssessment', self._math_assessment)
            if provider not in ('decision', 'inference'):
                raise SettingsError('Choose decision or inference for mathematical assessment.')
            return provider

    def on_disk(self):
        """Resolve a draft against the same saved keys and fallback URLs that Save will use."""
        return ConnectionSettings(self.path) if self.path.is_file() else self

    def reload(self):
        with self._lock:
            if not self.path.is_file():
                raise SettingsError('The settings file is missing. Start Math Practice again to create it.')
            saved = self.on_disk()
            self._decision, self._speech, self._inference = saved._merge({})
            self._setup, self.notice = saved._setup, saved.notice
            self._key_files = dict(saved._key_files)
            self._math_assessment = saved._math_assessment
            return self.public()

    def compare_file(self, patch):
        """Compare entered settings with disk without exposing keys or applying changes."""
        if not isinstance(patch, dict):
            raise SettingsError('Send settings as an object.')
        with self._lock:
            exists = self.path.is_file()
            saved = self.on_disk()
            previous = saved._merge({})
            active = self._merge({})
            revisions = {}
            expanded = saved._expand_shared(patch)
            changed = []
            for index, section in enumerate(('decision', 'speech', 'inference')):
                saved_key = previous[index]['apiKey'] if section == 'inference' else previous[index].api_key
                revisions[section] = key_revision(section, saved_key)
                if section not in expanded:
                    continue
                try:
                    candidates = saved._merge({section: expanded[section]})
                    candidate = candidates[index]
                    different = not exists or candidate != previous[index]
                    different = different or (saved._key_references({section: expanded[section]}, candidates).get(section)
                                              != saved._key_files.get(section))
                    # A blank field reuses the saved key. Detect an external rotation
                    # even when every visible input still matches the loaded settings.
                    if not different and not expanded[section].get('apiKey'):
                        active_key = active[index]['apiKey'] if section == 'inference' else active[index].api_key
                        uses_key = section != 'inference' or candidate['provider'] == 'api'
                        different = uses_key and saved_key != active_key
                except SettingsError:
                    different = True  # Incomplete edits still need saving or correction.
                if different:
                    changed.append(section)
            if 'setup' in patch and saved._setup_selection(patch) != saved._setup:
                changed.append('setup')
            if (saved.math_assessment_provider(patch) != saved._math_assessment
                    or ('mathAssessment' not in patch and saved._math_assessment != self._math_assessment)):
                changed.append('mathAssessment')
            return {'different': bool(changed), 'changedSections': changed, 'keyRevisions': revisions}

    def save(self, patch):
        with self._lock, settings_write_lock(self.path):
            # Preserve file edits and credentials in sections omitted by this save.
            saved = self.on_disk()
            decision, speech, inference = saved._merge(patch)
            references = saved._key_references(patch, (decision, speech, inference))
            math_assessment = saved.math_assessment_provider(patch)
            setup = saved._setup_selection(patch) if 'setup' in patch else (
                {'mode': 'separate', 'provider': ''} if any(role in patch for role in ('decision', 'speech', 'inference'))
                else dict(saved._setup))
            document = {'decision': saved_http(decision), 'speech': saved_http(speech), 'inference': dict(inference),
                        'setup': setup, 'mathAssessment': math_assessment}
            for role, reference in references.items():
                document[role].pop('apiKey')
                document[role]['apiKeyFile'] = reference
            yaml = yaml_module() if self.path.suffix.lower() in ('.yaml', '.yml') else None
            temporary = None
            try:
                fd, temporary = tempfile.mkstemp(prefix='.config-', suffix='.tmp', dir=self.path.parent)
                with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                    if yaml:
                        yaml.safe_dump(document, handle, allow_unicode=True, sort_keys=False)
                    else:
                        json.dump(document, handle, indent=2)
                        handle.write('\n')
                os.replace(temporary, self.path)
            finally:
                if temporary is not None:
                    Path(temporary).unlink(missing_ok=True)
            self._decision, self._speech, self._inference = decision, speech, inference
            self._setup = setup
            self._key_files = references
            self._math_assessment = math_assessment
            self.notice = ''
            return self.public()

    def test_decision(self, patch):
        assessor = StudentAssessment(self.decision_config(patch))
        if not assessor.config.configured:
            return {'configured': False, 'ready': False, 'label': 'Not configured',
                    'message': 'Enter a decision server address and model ID to test this connection.'}
        started = time.monotonic()
        from student_assessment import RUBRICS, CORRECTNESS, ANSWER_CORRECTNESS
        # Keep transcript observations separate from reference answers, as in practice.
        checks = (
            ('learning signals', 'Assess only the communication in this original speech transcript. '
             'Do not assess mathematical accuracy. Original transcript: "I am unsure how to begin."', RUBRICS),
            ('mathematical reasoning', 'Assess only this submitted mathematical reasoning. '
             'Problem: What is 2 + 2? Reference solution: Add two and two to get four. '
             'Student reasoning (quoted evidence): "I added two and two to get four."', CORRECTNESS),
            ('typed answer', 'Assess only this final typed answer. '
             'Problem: What is 2 + 2? Reference answer: 4. '
             'Student answer (quoted evidence): "4"', ANSWER_CORRECTNESS),
        )
        signals_only = self.math_assessment_provider(patch) == 'inference'
        if signals_only:
            checks = checks[:1]
        for name, context, rubrics in checks:
            try:
                assessor._decide(context, rubrics)
            except AssessmentError as exc:
                raise AssessmentError(f'The model could not complete the {name} connection test. '
                                      'Check the address, key, model ID, and selected API protocol.', exc.status) from None
        return {'configured': True, 'ready': True,
                'message': ('The model returned all three learning signals in the required format.' if signals_only else
                            'The model returned all three learning signals, a mathematical reasoning assessment, and a typed answer assessment in the required formats.'),
                'model': assessor.config.model, 'elapsedMs': round((time.monotonic() - started) * 1000)}

    test_jev = test_decision
