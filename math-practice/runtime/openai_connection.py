"""Local Codex device sign-in and a small account-backed SDK inference test."""
import asyncio
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import tomllib

from student_assessment import AssessmentError

DEVICE_URL = 'https://auth.openai.com/codex/device'
CODE = re.compile(r'^(?:(?:enter|code|your code|one-time code)\s*:?\s*)?([A-Z0-9]{4}-[A-Z0-9]{4,6})$', re.I)
ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')


def find_codex():
    executable = shutil.which('codex')
    if executable and Path(executable).suffix.lower() not in ('.cmd', '.bat', '.ps1'):
        return executable
    try:
        from codex_cli_bin import bundled_codex_path
        candidate = Path(bundled_codex_path())
        return str(candidate) if candidate.is_file() else None
    except (ImportError, OSError, RuntimeError):
        return None


class OpenAIConnection:
    def __init__(self, work_root, home=None):
        self.work_root = Path(work_root)
        self.home = Path(home or os.environ.get('CODEX_HOME', Path.home() / '.codex'))
        self._lock = threading.RLock()
        self._test_lock = threading.Lock()
        self._process = None
        self._state = None
        self._code = None
        self._url = None
        self._cancelled = False

    def _environment(self):
        environment = dict(os.environ)
        environment['CODEX_HOME'] = str(self.home)
        for name in ('OPENAI_API_KEY', 'CODEX_API_KEY', 'CODEX_ACCESS_TOKEN'):
            environment.pop(name, None)
        return environment

    def _command(self, *args):
        executable = find_codex()
        if not executable:
            raise AssessmentError('Install Codex for this user, then refresh the connection status.', 503)
        return [executable, '-c', 'cli_auth_credentials_store="file"', *args]

    def _status(self):
        try:
            result = subprocess.run(self._command('login', 'status'), env=self._environment(),
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    timeout=8, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            output = ANSI.sub('', result.stdout.decode('utf-8', errors='replace')).lower()
            if result.returncode == 0 and 'logged in using chatgpt' in output:
                return 'signed_in', 'Signed in with this computer’s OpenAI account.'
            if 'not logged in' in output or 'api key' in output:
                return 'signed_out', 'Sign in with OpenAI to connect the tutor model.'
            return 'unavailable', 'Codex could not confirm the account. Check the sign-in in Codex, then refresh.'
        except (OSError, subprocess.TimeoutExpired, AssessmentError):
            return 'unavailable', 'Codex is unavailable. Check its user-wide installation, then refresh.'

    def status(self):
        with self._lock:
            sdk = importlib.util.find_spec('openai_codex') is not None
            if self._process and self._process.poll() is None:
                state, message = 'waiting', 'Complete sign-in on OpenAI’s website, then return here.'
            else:
                state, message = self._status()
                if self._state == 'failed' and state != 'signed_in':
                    state, message = 'failed', 'Sign-in did not finish. Try again; device-code login may need enabling in your ChatGPT security settings.'
                elif state == 'signed_in':
                    self._state = None
            if not sdk:
                message += ' Install the openai-codex package in your shared Python installation to test inference.'
            return {'state': state, 'message': message, 'sdkAvailable': sdk,
                    'canTest': state == 'signed_in' and sdk,
                    'loginUrl': self._url if state == 'waiting' else None,
                    'userCode': self._code if state == 'waiting' else None}

    def start_login(self):
        with self._lock:
            if self._process and self._process.poll() is None:
                return self.status()
            # Preserve an existing host account, as in Model Forge.
            state, _ = self._status()
            if state == 'signed_in':
                self._state = None
                return self.status()
            if (self.home / 'auth.json').exists() or (self.home / 'auth.json').is_symlink():
                raise AssessmentError('An existing Codex sign-in could not be confirmed. Resolve it in Codex before starting another sign-in.', 409)
            self.home.mkdir(parents=True, exist_ok=True)
            self._cancelled = False
            self._code, self._url, self._state = None, None, None
            try:
                self._process = subprocess.Popen(self._command('login', '--device-auth'), env=self._environment(),
                                                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            except OSError:
                raise AssessmentError('Codex could not start sign-in. Check its local installation.', 503) from None
            threading.Thread(target=self._watch, args=(self._process,), daemon=True).start()
            return self.status()

    def _watch(self, process):
        def expire():
            if process.poll() is None:
                process.kill()
        timer = threading.Timer(900, expire)
        timer.daemon = True
        timer.start()
        try:
            for line in process.stdout:
                clean = ANSI.sub('', line.decode('utf-8', errors='replace')).strip()
                with self._lock:
                    if DEVICE_URL in clean:
                        self._url = DEVICE_URL
                    match = CODE.fullmatch(clean)
                    if match:
                        self._code = match.group(1).upper()
            process.wait()
            with self._lock:
                if self._process is process:
                    self._state = 'failed' if process.returncode and not self._cancelled else None
                    self._code, self._url = None, None
        finally:
            timer.cancel()
            process.stdout.close()

    def cancel_login(self):
        with self._lock:
            self._cancelled = True
            if self._process and self._process.poll() is None:
                self._process.kill()
                self._process.wait(timeout=5)
            self._state, self._code, self._url = None, None, None
            return self.status()

    def close(self):
        self.cancel_login()

    async def _generate(self, selection, prompt, instructions, schema=None, images=()):
        from openai_codex import AsyncCodex, CodexConfig, Sandbox, ApprovalMode, TextInput, ImageInput
        self.work_root.mkdir(parents=True, exist_ok=True)
        overrides = ['cli_auth_credentials_store="file"', 'web_search="disabled"',
                     'project_doc_max_bytes=0', 'features.memories=false']
        # A connection check needs no desktop integrations or project skills.
        config_file = self.home / 'config.toml'
        try:
            config = tomllib.loads(config_file.read_text(encoding='utf-8')) if config_file.is_file() else {}
            for name in config.get('mcp_servers', {}):
                if not re.fullmatch(r'[A-Za-z0-9_-]+', name):
                    raise ValueError('Invalid tool name')
                overrides.append(f'mcp_servers.{name}.enabled=false')
        except (OSError, ValueError, TypeError):
            raise AssessmentError('Codex configuration could not be read for the connection test.', 503) from None
        client = AsyncCodex(CodexConfig(codex_bin=find_codex(), env=self._environment(),
                                       config_overrides=tuple(overrides), cwd=str(self.work_root),
                                       client_name='math_practice', client_title='Math Practice'))
        try:
            async with asyncio.timeout(125):
                thread = await client.thread_start(model=selection['model'], model_provider='openai', sandbox=Sandbox.read_only,
                    approval_mode=ApprovalMode.deny_all, ephemeral=True,
                    developer_instructions=instructions)
                content = [TextInput(prompt), *[ImageInput(url) for url in images]] if images else prompt
                result = await thread.run(content, model=selection['model'], output_schema=schema,
                    effort=selection['effort'], sandbox=Sandbox.read_only, approval_mode=ApprovalMode.deny_all)
                if getattr(result.status, 'value', result.status) != 'completed' or not (result.final_response or '').strip():
                    raise AssessmentError('The selected model did not complete its response. Check its availability in Codex.', 502)
                return result.final_response.strip()
        finally:
            await client.close()

    def infer(self, selection, prompt, instructions, schema, images=()):
        status = self.status()
        if not status['canTest']:
            raise AssessmentError(status['message'], 503)
        try:
            return asyncio.run(self._generate(selection, prompt, instructions, schema, images))
        except AssessmentError:
            raise
        except Exception:
            raise AssessmentError('The inference model could not finish the review. Check its connection and try again.', 502) from None

    def test(self, selection):
        if not self._test_lock.acquire(blocking=False):
            raise AssessmentError('An OpenAI test is already running. Wait for it to finish.', 409)
        try:
            from practice_tutor import test_tutor_connection
            try:
                result = test_tutor_connection({**selection, 'provider': 'codex'}, self)
            except AssessmentError:
                raise
            except Exception:
                # SDK exceptions may contain local configuration or transport data.
                raise AssessmentError('OpenAI did not complete the test inference. Check the selected model, account limits, and Codex connection.', 502) from None
            return {**result, **selection}
        finally:
            self._test_lock.release()
