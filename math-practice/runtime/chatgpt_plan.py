"""App-owned Sign in with ChatGPT for the documented local-app plan route.

Contract checked 2026-11-04:
https://developers.openai.com/siwc/token-sharing-open-source/sign-in
https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions
https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference
https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations

No Codex credentials are used. Status never starts login or makes a network call.
"""
import base64
from contextlib import contextmanager
import ctypes
import hashlib
import hmac
from http.client import HTTPException
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import secrets
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser

from student_assessment import AssessmentError

ISSUER = 'https://auth.openai.com'
DISCOVERY = ISSUER + '/.well-known/openid-configuration'
AUTHORIZE = ISSUER + '/api/accounts/authorize'
TOKEN = ISSUER + '/api/accounts/oauth/token'
RESOURCE = 'https://api.openai.com/v1'
DIRECT_SCOPE = 'chatgpt.tokens.use.direct'
SCOPES = 'openid profile email offline_access resource.invoke ' + DIRECT_SCOPE
USAGE_URL = 'https://chatgpt.com/settings/usage'
CALLBACK_PATH = '/auth/callback'
DEPENDENCY_MESSAGE = 'Install PyJWT[crypto] in your shared Python installation, then restart Math Practice: python -m pip install --user "PyJWT[crypto]".'
TERMINAL_REFRESH = {'invalid_grant', 'invalid_refresh_token', 'token_expired',
                    'refresh_token_expired', 'refresh_token_invalidated', 'refresh_token_reused'}


class PlanError(AssessmentError):
    """Safe display message plus provider diagnostics, without request credentials."""
    def __init__(self, message, status=502, *, code=None, param=None, request_id=None, body=None):
        super().__init__(message, status)
        self.code, self.param, self.request_id, self.body = code, param, request_id, body


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


def _dependency_available():
    return importlib.util.find_spec('jwt') is not None and importlib.util.find_spec('cryptography') is not None


def _home():
    if os.name == 'nt':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'MathPractice' / 'chatgpt'
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'math-practice' / 'chatgpt'


def _dpapi(data, decrypt=False):
    """Windows user-bound encryption using the OS, with no extra storage library."""
    class Blob(ctypes.Structure):
        _fields_ = [('size', ctypes.c_ulong), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    source = ctypes.create_string_buffer(data)
    incoming = Blob(len(data), ctypes.cast(source, ctypes.POINTER(ctypes.c_ubyte)))
    outgoing = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(Blob)]
    function.restype = ctypes.c_int
    if not function(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing)):
        raise OSError('Windows could not protect the Math Practice account storage.')
    try:
        return ctypes.string_at(outgoing.data, outgoing.size)
    finally:
        kernel.LocalFree(outgoing.data)


class ChatGPTPlan:
    def __init__(self, home=None):
        self.home = Path(home) if home is not None else _home()
        self._lock = threading.RLock()
        self._inference_lock = threading.Lock()
        self._pending = None
        self._state = None
        self._message = None
        self._model_message = ''
        self._model_message_for = None
        self._discovering_for = None
        self._jwks = None
        self._jwks_saved = 0
        self._discovery = None
        self._closed = False
        self._retry_client_id = None
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())

    @contextmanager
    def _storage(self):
        """Serialize rotating refresh tokens across app processes as well as threads."""
        with self._lock:
            self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
            if self.home.is_symlink():
                raise PlanError('The Math Practice account folder must not be a symbolic link.', 503)
            path = self.home / 'account.lock'
            if path.is_symlink():
                raise PlanError('The Math Practice account lock must not be a symbolic link.', 503)
            descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
            locked = False
            try:
                if os.fstat(descriptor).st_size == 0:
                    os.write(descriptor, b'0')
                until = time.monotonic() + 10
                while not locked:
                    try:
                        os.lseek(descriptor, 0, os.SEEK_SET)
                        if os.name == 'nt':
                            import msvcrt
                            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                        else:
                            import fcntl
                            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        locked = True
                    except OSError:
                        if time.monotonic() >= until:
                            raise PlanError('Another Math Practice window is updating this account. Try again shortly.', 409) from None
                        time.sleep(0.05)
                yield
            finally:
                if locked:
                    if os.name == 'nt':
                        import msvcrt
                        os.lseek(descriptor, 0, os.SEEK_SET)
                        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(descriptor, fcntl.LOCK_UN)
                os.close(descriptor)

    def _read(self):
        path = self.home / 'account.dat'
        if path.is_symlink():
            raise PlanError('The Math Practice account file must not be a symbolic link.', 503)
        if not path.exists():
            return {'host_id': None, 'account': None}
        try:
            raw = path.read_bytes()
            if os.name == 'nt':
                raw = _dpapi(raw, decrypt=True)
            elif path.stat().st_mode & 0o077:
                raise ValueError('Account storage is not private')
            record = json.loads(raw)
            if not isinstance(record, dict) or not isinstance(record.get('host_id'), str):
                raise ValueError('Invalid account storage')
            return record
        except (OSError, ValueError, TypeError):
            raise PlanError('Math Practice could not read its protected ChatGPT account storage. Restore access to the local account folder.', 503) from None

    def _write(self, value):
        raw = json.dumps(value).encode('utf-8')
        if os.name == 'nt':
            raw = _dpapi(raw)
        descriptor, temporary = tempfile.mkstemp(prefix='.account-', dir=self.home)
        try:
            with os.fdopen(descriptor, 'wb') as target:
                target.write(raw)
                target.flush()
                os.fsync(target.fileno())
            os.replace(temporary, self.home / 'account.dat')
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _request(self, url, *, form=None, body=None, token=None, stream=False, timeout=25):
        headers = {'Accept': 'text/event-stream' if stream else 'application/json', 'User-Agent': 'MathPractice/1.0'}
        data = None
        if form is not None:
            data = urllib.parse.urlencode(form).encode('utf-8')
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        elif body is not None:
            data = json.dumps(body).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        if token:
            headers['Authorization'] = 'Bearer ' + token
        try:
            response = self._opener.open(urllib.request.Request(url, data, headers), timeout=timeout)
            if stream:
                return response
            with response:
                raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise ValueError('Oversized response')
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as error:
            with error:
                request_id = error.headers.get('x-request-id') or error.headers.get('openai-request-id')
                try:
                    raw = error.read(64_000).decode('utf-8', errors='replace')
                except (OSError, HTTPException):
                    detail = {}
                else:
                    try:
                        detail = json.loads(raw)
                    except ValueError:
                        detail = {'detail': raw}
            raise self._provider_error(error.code, detail, request_id) from None
        except (OSError, ValueError, urllib.error.URLError, HTTPException):
            raise PlanError('OpenAI could not be reached or returned an unreadable response. Try again later.', 503) from None

    def _provider_error(self, status, body, request_id=None):
        error = (body.get('error') or (body if body.get('type') == 'error' else None)) if isinstance(body, dict) else None
        code = error.get('code') if isinstance(error, dict) else error if isinstance(error, str) else None
        param = error.get('param') if isinstance(error, dict) else None
        code = code if isinstance(code, str) else None
        param = param if isinstance(param, str) else None
        messages = {
            'server_is_overloaded': 'OpenAI\'s model service is busy. Try again later.',
            'subscription_sharing_user_not_eligible': 'ChatGPT plan usage is unavailable for this account, workspace, or policy. Choose an eligible account or use a custom API.',
            'subscription_sharing_usage_limit_exceeded': 'This app or ChatGPT plan has reached a usage limit. Review the app limit in ChatGPT Settings > Usage.',
            'invalid_client': 'OpenAI did not accept this app registration. Check the Sign in with ChatGPT registration guidance before trying again.',
        }
        fallback = {401: 'OpenAI did not accept this account authorization. Sign in again to check its permissions.',
                    403: 'OpenAI restricted this request. Check account eligibility, app permission, and serving-region policy.',
                    429: 'OpenAI has limited requests for this account. Check ChatGPT Settings > Usage and try later.',
                    503: 'ChatGPT plan routing is unavailable or not enabled for this integration. Keep the connection and try later.'}
        message = messages.get(code, fallback.get(status, 'OpenAI could not complete this request. Check the selected model and account permissions.'))
        # Provider text can echo submitted content. Keep it in diagnostics, not UI text.
        return PlanError(message, status, code=code, param=param, request_id=request_id, body=body)

    def _openid(self):
        if self._discovery is None:
            value = self._request(DISCOVERY)
            if (not isinstance(value, dict) or value.get('issuer') != ISSUER
                    or value.get('authorization_endpoint') != AUTHORIZE or value.get('token_endpoint') != TOKEN):
                raise PlanError('OpenAI sign-in discovery returned an unexpected configuration.', 502)
            for key in ('jwks_uri', 'revocation_endpoint'):
                endpoint = value.get(key)
                if not isinstance(endpoint, str):
                    raise PlanError('OpenAI sign-in discovery returned an unexpected endpoint.', 502)
                try:
                    parts = urllib.parse.urlsplit(endpoint)
                except ValueError:
                    raise PlanError('OpenAI sign-in discovery returned an unexpected endpoint.', 502) from None
                if parts.scheme != 'https' or parts.netloc != 'auth.openai.com' or parts.query or parts.fragment:
                    raise PlanError('OpenAI sign-in discovery returned an unexpected endpoint.', 502)
            self._discovery = value
        return self._discovery

    def _validate_identity(self, encoded, client_id, nonce=None, previous=None):
        if not _dependency_available():
            raise PlanError(DEPENDENCY_MESSAGE, 503)
        import jwt
        try:
            header = jwt.get_unverified_header(encoded)
            if header.get('alg') != 'RS256' or not isinstance(header.get('kid'), str):
                raise ValueError('Unsupported signing key')
            if self._jwks is None or time.time() - self._jwks_saved > 3600:
                self._jwks = self._request(self._openid()['jwks_uri'])
                self._jwks_saved = time.time()
            key = next((key for key in self._jwks.get('keys', []) if key.get('kid') == header['kid']), None)
            if key is None:
                self._jwks = self._request(self._openid()['jwks_uri'])
                self._jwks_saved = time.time()
                key = next((key for key in self._jwks.get('keys', []) if key.get('kid') == header['kid']), None)
            if not key or key.get('kty') != 'RSA' or key.get('use', 'sig') != 'sig' or key.get('alg', 'RS256') != 'RS256':
                raise ValueError('Unrecognized signing key')
            claims = jwt.decode(encoded, jwt.PyJWK.from_dict(key, algorithm='RS256').key,
                                algorithms=['RS256'], audience=client_id, issuer=ISSUER, leeway=5,
                                options={'require': ['sub', 'exp', 'iat', 'aud', 'iss']})
            if not isinstance(claims.get('sub'), str) or not claims['sub']:
                raise ValueError('Missing subject')
            if nonce is not None and (not isinstance(claims.get('nonce'), str) or not hmac.compare_digest(claims['nonce'], nonce)):
                raise ValueError('Invalid nonce')
            if previous and (claims['sub'] != previous['subject'] or claims['iss'] != previous['issuer']):
                raise ValueError('Account changed')
            if isinstance(claims.get('aud'), list) and len(claims['aud']) > 1 and claims.get('azp') != client_id:
                raise ValueError('Invalid authorized party')
            return claims
        except PlanError:
            raise
        except (ValueError, TypeError, KeyError, AttributeError, jwt.PyJWTError):
            raise PlanError('OpenAI account identity could not be verified. Sign in again.', 401) from None

    def _tokens(self, result, client_id, *, nonce=None, previous=None):
        if not isinstance(result, dict):
            raise PlanError('OpenAI returned an incomplete account authorization.', 502)
        scopes = result.get('scope', ' '.join(previous.get('scopes', [])) if previous else '')
        expiry = result.get('expires_in')
        if not isinstance(scopes, str):
            raise PlanError('OpenAI returned an incomplete account authorization.', 502)
        direct = DIRECT_SCOPE in scopes.split()
        if direct and (not isinstance(expiry, (int, float)) or isinstance(expiry, bool)
                       or not math.isfinite(expiry) or not 0 < expiry <= 86400):
            raise PlanError('OpenAI returned an incomplete account authorization.', 502)
        if direct and (str(result.get('token_type', '')).lower() != 'bearer'
                       or not isinstance(result.get('access_token'), str) or not result['access_token']):
            raise PlanError('OpenAI did not return a usable account access token.', 502)
        if nonce is not None and not result.get('id_token'):
            raise PlanError('OpenAI did not return an account identity token.', 502)
        claims = self._validate_identity(result['id_token'], client_id, nonce, previous) if result.get('id_token') else None
        if not claims and not previous:
            raise PlanError('OpenAI did not return a verified account identity.', 502)
        refresh_token = result.get('refresh_token')
        if direct and 'offline_access' in scopes.split() and (not isinstance(refresh_token, str) or not refresh_token):
            raise PlanError('OpenAI did not return the renewable session required for this connection.', 502)
        now = time.time()
        return {**(previous or {}), 'client_id': client_id, 'issuer': ISSUER,
                'subject': claims['sub'] if claims else previous['subject'],
                'email': claims.get('email', '') if claims else previous.get('email', ''),
                'name': claims.get('name', '') if claims else previous.get('name', ''),
                'id_token': result.get('id_token') or (previous.get('id_token') if previous else None),
                'access_token': result.get('access_token') if direct else None, 'refresh_token': refresh_token,
                'scopes': scopes.split(), 'expires_at': now + expiry if direct else 0, 'saved_at': now,
                'earliest_refresh_at': result.get('earliest_refresh_at')}

    def status(self):
        with self._lock:
            available = _dependency_available()
            try:
                # Reading an existing app-owned file does not inspect other apps' credentials.
                record = self._read() if self.home.exists() else {}
                account = record.get('account')
                granted = bool(account and DIRECT_SCOPE in account.get('scopes', []))
                renewable = bool(account and (not granted or account.get('refresh_token') or account.get('expires_at', 0) > time.time()))
                permission = bool(granted and renewable)
                state = 'signed_in' if renewable else 'signed_out'
                message = ('ChatGPT is connected. Test the selected model before using it.' if permission
                           else 'ChatGPT is signed in. Enable permission to use your ChatGPT plan.' if renewable
                           else 'Continue with ChatGPT to request access to an eligible plan.')
                if account and not renewable:
                    message = 'Your ChatGPT connection ended. Continue with ChatGPT to sign in again.'
                if self._pending:
                    state, message = 'waiting', 'Complete sign-in in your browser, then return here.'
                elif self._state:
                    state, message = self._state, self._message
                if not available:
                    state, message = 'unavailable', DEPENDENCY_MESSAGE
                public_account = None
                if account:
                    label = account.get('email') or account.get('name') or 'ChatGPT account'
                    public_account = {'id': account['client_id'], 'label': label,
                                      'email': account.get('email', ''), 'name': account.get('name', '')}
                registrations = [{'id': item['client_id'],
                                  'label': item.get('email') or item.get('name') or 'ChatGPT account'}
                                 for item in reversed(list(record.get('registrations', {}).values()))]
                return {'state': state, 'message': message, 'canTest': bool(available and renewable and permission and not self._pending),
                        'sdkAvailable': available, 'planEnabled': permission, 'account': public_account,
                        'registrations': registrations,
                        'modelsLoading': bool(account and self._discovering_for == account.get('client_id')),
                        'loginUrl': None, 'userCode': None, 'modelSuggestions': list(record.get('model_suggestions', [])),
                        'modelMessage': self._model_message if self._model_message_for == (account or {}).get('client_id') else '',
                        'usageUrl': USAGE_URL}
            except PlanError as error:
                return {'state': 'unavailable', 'message': str(error), 'canTest': False,
                        'sdkAvailable': available, 'planEnabled': False, 'account': None,
                        'registrations': [],
                        'loginUrl': None, 'userCode': None, 'modelSuggestions': [],
                        'modelMessage': '', 'usageUrl': USAGE_URL}

    def start_login(self, client_id=None, new_account=False):
        with self._lock:
            if (not isinstance(new_account, bool) or (client_id is not None and not isinstance(client_id, str))
                    or (new_account and client_id is not None)):
                raise PlanError('Choose one saved ChatGPT account or use another account.', 400)
            if self._closed:
                raise PlanError('The Math Practice account connection is closed. Restart the app.', 503)
            if self._pending:
                return self.status()
            if not _dependency_available():
                raise PlanError(DEPENDENCY_MESSAGE, 503)
            with self._storage():
                record = self._read()
                if not record.get('host_id'):
                    record['host_id'] = 'urn:uuid:' + str(uuid.uuid4())
                    self._write(record)
                account = record.get('account')
                if new_account:
                    account = None
                elif client_id is not None:
                    account = record.get('registrations', {}).get(client_id)
                    if not account:
                        raise PlanError('That saved ChatGPT registration is unavailable. Continue with a new account.', 400)
            owner = self

            class Callback(BaseHTTPRequestHandler):
                def do_GET(self):
                    expected = '127.0.0.1:' + str(self.server.server_port)
                    if self.client_address[0] != '127.0.0.1' or self.headers.get('Host') != expected:
                        self.send_error(400)
                        return
                    parts = urllib.parse.urlsplit(self.path)
                    if parts.path != CALLBACK_PATH or parts.scheme or parts.netloc:
                        self.send_error(404)
                        return
                    status, message = owner._callback(parts.query)
                    body = message.encode('utf-8')
                    self.send_response(status)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Referrer-Policy', 'no-referrer')
                    self.send_header('Content-Security-Policy', "default-src 'none'; frame-ancestors 'none'")
                    self.end_headers()
                    self.wfile.write(body)

                def log_message(self, *args):
                    pass

            try:
                server = ThreadingHTTPServer(('127.0.0.1', 0), Callback)
                server.daemon_threads = True
                server.timeout = 1
            except OSError:
                raise PlanError('Math Practice could not open its local sign-in callback. Allow a loopback listener and try again.', 503) from None
            client_id = (account['client_id'] if account else
                         'dynamic_agent_client' if new_account else self._retry_client_id or 'dynamic_agent_client')
            attempt = {'state': secrets.token_urlsafe(32), 'nonce': secrets.token_urlsafe(32), 'client_id': client_id,
                       'verifier': secrets.token_urlsafe(64), 'server': server, 'account': account,
                       'redirect_uri': f'http://127.0.0.1:{server.server_port}{CALLBACK_PATH}',
                       'expires_at': time.monotonic() + 600, 'used': False}
            self._pending = attempt
            self._state, self._message = None, None
            threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.1}, daemon=True).start()
            timer = threading.Timer(600, self._expire, args=(attempt,))
            timer.daemon = True
            attempt['timer'] = timer
            timer.start()
            params = {'client_id': client_id,
                      'ext_agent_host_id': record['host_id'], 'response_type': 'code',
                      'redirect_uri': attempt['redirect_uri'], 'scope': SCOPES, 'resource': RESOURCE,
                      'state': attempt['state'], 'nonce': attempt['nonce'], 'code_challenge_method': 'S256',
                      'code_challenge': base64.urlsafe_b64encode(hashlib.sha256(attempt['verifier'].encode('ascii')).digest()).rstrip(b'=').decode('ascii')}
            if account:
                if account.get('id_token'):
                    params['id_token_hint'] = account['id_token']
                if account.get('email'):
                    params['login_hint'] = account['email']
                if DIRECT_SCOPE not in account.get('scopes', []):
                    params['prompt'] = 'consent'
            elif client_id == 'dynamic_agent_client':
                params['agent_name_hint'] = 'Math Practice'
            try:
                if not webbrowser.open(AUTHORIZE + '?' + urllib.parse.urlencode(params), new=1):
                    raise OSError('No system browser')
            except Exception:
                self._end_attempt(attempt)
                raise PlanError('Math Practice could not open your system browser. Set a default browser, then try again.', 503) from None
            return self.status()

    def _end_attempt(self, attempt):
        if self._pending is attempt:
            self._pending = None
        attempt['timer'].cancel()
        # shutdown waits for serve_forever, so do it outside the current request.
        def stop():
            attempt['server'].shutdown()
            attempt['server'].server_close()
        threading.Thread(target=stop, daemon=True).start()

    def _expire(self, attempt):
        with self._lock:
            if self._pending is attempt:
                self._state, self._message = 'failed', 'ChatGPT sign-in expired. Continue with ChatGPT to try again.'
                self._end_attempt(attempt)

    def _callback(self, query):
        with self._lock:
            attempt = self._pending
            try:
                values = urllib.parse.parse_qs(query, keep_blank_values=True, strict_parsing=True, max_num_fields=16)
                if any(len(value) != 1 for value in values.values()):
                    raise ValueError('Repeated callback parameter')
                value = {key: values[0] for key, values in values.items()}
                if (not attempt or attempt['used'] or attempt['expires_at'] <= time.monotonic()
                        or not hmac.compare_digest(value.get('state', ''), attempt['state'])):
                    raise ValueError('Unverified callback')
                attempt['used'] = True
            except (ValueError, TypeError):
                return 400, 'This sign-in callback could not be verified. Return to Math Practice.'
            if value.get('error'):
                self._state, self._message = 'failed', 'ChatGPT sign-in was declined or could not finish. Continue with ChatGPT to try again.'
                self._end_attempt(attempt)
                return 400, self._message
            account = attempt['account']
            registered = attempt['client_id'] if attempt['client_id'] != 'dynamic_agent_client' else None
            client_id = value.get('client_id') or registered
            if (not isinstance(client_id, str) or not re.fullmatch(r'oaiapp_[A-Za-z0-9_-]+', client_id)
                    or (registered and client_id != registered) or not value.get('code')):
                self._state, self._message = 'failed', 'OpenAI registration was incomplete. Continue with ChatGPT to start a fresh sign-in.'
                self._end_attempt(attempt)
                return 400, self._message
            self._retry_client_id = client_id
        # Network requests do not hold the state lock, so Cancel remains responsive.
        try:
            result = self._request(TOKEN, form={'grant_type': 'authorization_code', 'client_id': client_id,
                                   'code': value['code'], 'code_verifier': attempt['verifier'],
                                   'redirect_uri': attempt['redirect_uri'], 'resource': RESOURCE})
            updated = self._tokens(result, client_id, nonce=attempt['nonce'], previous=account)
            with self._lock:
                if self._pending is not attempt:
                    return 400, 'Sign-in was cancelled. Return to Math Practice.'
                with self._storage():
                    record = self._read()
                    record['account'] = updated
                    record['model_suggestions'] = []
                    registrations = record.setdefault('registrations', {})
                    registrations.pop(client_id, None)
                    registrations[client_id] = {
                        key: updated[key] for key in ('client_id', 'issuer', 'subject', 'email', 'name')}
                    self._write(record)
                self._model_message, self._model_message_for = '', None
                self._retry_client_id = None
                self._state, self._message = None, None
                self._discovering_for = client_id if DIRECT_SCOPE in updated['scopes'] else None
                self._end_attempt(attempt)
            if DIRECT_SCOPE in updated['scopes']:
                try:
                    self.refresh_models()
                finally:
                    with self._lock:
                        if self._discovering_for == client_id:
                            self._discovering_for = None
            return 200, 'ChatGPT sign-in finished. You can close this tab and return to Math Practice.'
        except (PlanError, OSError) as error:
            with self._lock:
                if self._pending is attempt:
                    self._state = 'failed'
                    self._message = str(error) if isinstance(error, PlanError) else 'Math Practice could not save its protected account connection.'
                    self._end_attempt(attempt)
            return 400, 'ChatGPT sign-in did not finish. Return to Math Practice for details.'

    def cancel_login(self):
        with self._lock:
            if self._pending:
                self._end_attempt(self._pending)
            self._state, self._message = None, None
            return self.status()

    def _access(self):
        with self._storage():
            record = self._read()
            account = record.get('account')
            if not account:
                raise PlanError('Continue with ChatGPT to connect your account again.', 401)
            if DIRECT_SCOPE not in account.get('scopes', []):
                raise PlanError('ChatGPT plan permission is disabled. Continue with ChatGPT and approve plan usage.', 403)
            if not account.get('access_token'):
                raise PlanError('Continue with ChatGPT to connect your account again.', 401)
            now = time.time()
            if account.get('expires_at', 0) > now + (60 if account.get('refresh_token') else 0):
                return dict(account)
            if not account.get('refresh_token'):
                raise PlanError('Your ChatGPT authorization expired. Continue with ChatGPT to sign in again.', 401)
            try:
                result = self._request(TOKEN, form={'grant_type': 'refresh_token', 'client_id': account['client_id'],
                                       'refresh_token': account['refresh_token'], 'resource': RESOURCE})
                updated = self._tokens(result, account['client_id'], previous=account)
            except PlanError as error:
                if error.code in TERMINAL_REFRESH:
                    for key in ('access_token', 'refresh_token', 'id_token'):
                        account.pop(key, None)
                    account['expires_at'] = 0
                    self._write(record)
                    raise PlanError('Your ChatGPT connection ended. Continue with ChatGPT to sign in again.', 401,
                                    code=error.code, param=error.param, request_id=error.request_id, body=error.body) from None
                raise
            record['account'] = updated
            self._write(record)
            if DIRECT_SCOPE not in updated['scopes']:
                raise PlanError('ChatGPT plan permission is disabled. Continue with ChatGPT and approve plan usage.', 403)
            return dict(updated)

    def refresh_models(self):
        account = None
        try:
            account = self._access()
            result = self._request(RESOURCE + '/models', token=account['access_token'])
            if not isinstance(result, dict) or not isinstance(result.get('models'), list):
                raise PlanError('OpenAI returned an unreadable model list.', 502)
            models = [{'model': item['slug'], 'label': item['display_name']
                       if isinstance(item.get('display_name'), str) and item['display_name'] else item['slug']}
                      for item in result['models'] if isinstance(item, dict) and item.get('visibility') == 'list'
                      and isinstance(item.get('slug'), str) and item['slug']]
            with self._lock:
                current = self._read().get('account')
                if current and current['client_id'] == account['client_id']:
                    self._model_message = '' if models else 'No models are currently listed for this ChatGPT account.'
                    self._model_message_for = account['client_id']
                    with self._storage():
                        record = self._read()
                        if (record.get('account') or {}).get('client_id') == account['client_id']:
                            record['model_suggestions'] = models
                            self._write(record)
        except PlanError as error:
            with self._lock:
                current = self.status().get('account') or {}
                if account is None or current.get('id') == account['client_id']:
                    self._model_message = str(error)
                    self._model_message_for = current.get('id')
        return self.status()

    def infer(self, selection, prompt, instructions, schema, images=()):
        if not self._inference_lock.acquire(blocking=False):
            raise PlanError('A ChatGPT request is already running. Wait for it to finish.', 409)
        try:
            if not _dependency_available():
                raise PlanError(DEPENDENCY_MESSAGE, 503)
            if self._closed:
                raise PlanError('The ChatGPT connection is closed. Restart Math Practice.', 503)
            account = self._access()
            model = selection.get('model', '')
            if not isinstance(model, str) or not model:
                raise PlanError('Choose a model for your ChatGPT plan.', 400)
            content = [{'type': 'input_text', 'text': prompt}]
            content.extend({'type': 'input_image', 'image_url': url} for url in images)
            body = {'model': model, 'instructions': instructions, 'input': [{'role': 'user', 'content': content}],
                    'store': False, 'stream': True}
            if selection.get('effort'):
                body['reasoning'] = {'effort': selection['effort']}
            if schema is not None:
                body['text'] = {'format': {'type': 'json_schema', 'name': 'math_practice_review', 'schema': schema, 'strict': True}}
            try:
                with self._request(RESOURCE + '/responses', body=body, token=account['access_token'], stream=True, timeout=120) as response:
                    # The plan endpoint can return valid SSE without a Content-Type header.
                    # In that case let the event parser verify completion and extract the review.
                    media_type = response.headers.get('Content-Type', '').partition(';')[0].strip().lower()
                    if media_type and media_type != 'text/event-stream':
                        raise PlanError('OpenAI did not return the required streaming response.', 502,
                                        request_id=response.headers.get('x-request-id') or response.headers.get('openai-request-id'))
                    return self._stream(response)
            except (OSError, UnicodeError, HTTPException):
                raise PlanError('The ChatGPT response was interrupted. Try the review again.', 502) from None
        finally:
            self._inference_lock.release()

    def _stream(self, response):
        request_id = response.headers.get('x-request-id') or response.headers.get('openai-request-id')
        try:
            return self._read_stream(response, request_id)
        except PlanError as error:
            if not error.request_id:
                error.request_id = request_id
            raise
        except (OSError, UnicodeError, HTTPException):
            raise PlanError('The ChatGPT response was interrupted. Try the review again.', 502, request_id=request_id) from None

    def _read_stream(self, response, request_id=None):
        data, pieces, size = [], [], 0
        started = time.monotonic()
        for raw in response:
            if time.monotonic() - started > 180:
                raise PlanError('The ChatGPT response took too long. Try the review again.', 504)
            size += len(raw)
            if size > 4_000_000:
                raise PlanError('The ChatGPT response exceeded the review size limit.', 502)
            line = raw.decode('utf-8').rstrip('\r\n')
            if line.startswith('data:'):
                data.append(line[5:].lstrip(' '))
                continue
            if line or not data:
                continue
            try:
                event = json.loads('\n'.join(data))
            except ValueError:
                raise PlanError('OpenAI returned an unreadable response event.', 502) from None
            data = []
            if not isinstance(event, dict):
                raise PlanError('OpenAI returned an unreadable response event.', 502)
            kind = event.get('type')
            if kind == 'response.output_text.delta':
                if isinstance(event.get('delta'), str):
                    pieces.append(event['delta'])
            elif kind in ('response.failed', 'error'):
                detail = event.get('response', event)
                raise self._provider_error(502, detail, request_id)
            elif kind == 'response.incomplete':
                raise PlanError('ChatGPT did not complete the review. Try again.', 502)
            elif kind == 'response.completed':
                completed = event.get('response', {})
                if not isinstance(completed, dict) or completed.get('status', 'completed') != 'completed':
                    raise PlanError('ChatGPT did not complete the review. Try again.', 502)
                output = completed.get('output') or []
                if not isinstance(output, list):
                    raise PlanError('OpenAI returned an unreadable completed response.', 502)
                texts = []
                for item in output:
                    if not isinstance(item, dict) or item.get('type') != 'message':
                        continue
                    content = item.get('content') or []
                    if not isinstance(content, list):
                        raise PlanError('OpenAI returned an unreadable completed response.', 502)
                    texts.extend(part['text'] for part in content if isinstance(part, dict)
                                 and part.get('type') == 'output_text' and isinstance(part.get('text'), str))
                final = ''.join(texts)
                text = (final or ''.join(pieces)).strip()
                if not text:
                    raise PlanError('ChatGPT completed without a text review. Try again.', 502)
                return text
        raise PlanError('The ChatGPT stream ended before response.completed. Try the review again.', 502)

    def sign_out(self):
        self.cancel_login()
        revoked = True
        with self._storage():
            record = self._read()
            account = record.get('account')
            if account and account.get('refresh_token'):
                try:
                    self._request(self._openid()['revocation_endpoint'], form={'client_id': account['client_id'],
                                  'token': account['refresh_token'], 'token_type_hint': 'refresh_token'})
                except PlanError:
                    revoked = False
            if account:
                registrations = record.setdefault('registrations', {})
                registrations.pop(account['client_id'], None)
                registrations[account['client_id']] = {
                    key: account.get(key, '') for key in ('client_id', 'issuer', 'subject', 'email', 'name')}
                record['account'] = None
                record['model_suggestions'] = []
                self._write(record)
            self._retry_client_id = None
            self._model_message, self._model_message_for = '', None
            self._state, self._message = 'signed_out', ('Signed out of ChatGPT in Math Practice.' if revoked else
                'Signed out locally. Remote revocation was not confirmed; disconnect Math Practice in ChatGPT Settings > Security and login > Sign in with ChatGPT.')
        return self.status()

    def close(self):
        self.cancel_login()
        self._closed = True
