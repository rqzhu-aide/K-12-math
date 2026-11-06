"""Small real connection probes for transcription and compatible inference APIs."""
import io
from http.client import HTTPException
import json
import re
import time
import urllib.error
import urllib.request
import uuid
import wave

from student_assessment import AssessmentError, OPENER


class _ModelListUnavailable(AssessmentError):
    pass


def request(config, route, data, content_type, timeout=60):
    if not config.configured:
        raise AssessmentError('This model is not configured. Enter its server address and model ID in Settings.', 503)
    headers = {'Content-Type': content_type, 'Accept': 'application/json'}
    if config.api_key:
        headers['Authorization'] = 'Bearer ' + config.api_key
    unauthorized = limited = unsupported = redirected = False
    statuses, transport_failed = [], False
    deadline = time.monotonic() + timeout
    for index, base in enumerate(config.bases):
        path = route[3:] if base.endswith('/v1') and route.startswith('/v1/') else route
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            # An unreachable address must leave time for the configured fallbacks.
            # A single (or last) address still receives the full remaining budget.
            attempt_timeout = remaining / (len(config.bases) - index)
            with OPENER.open(urllib.request.Request(base + path, data=data, headers=headers), timeout=attempt_timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            unauthorized |= exc.code in (401, 403)
            status = exc.code
            statuses.append(status)
            exc.close()
            limited |= status == 429
            unsupported |= status in (400, 404, 422)
            redirected |= status in (301, 302, 303, 307, 308)
        except (OSError, ValueError, HTTPException):
            transport_failed = True
    if route == '/v1/models' and not transport_failed and statuses and all(code in (404, 405, 501) for code in statuses):
        raise _ModelListUnavailable('This service does not provide a model list. Use Test Connection in Settings to check the configured model.', 502)
    if unauthorized:
        raise AssessmentError('The service rejected the credentials. Check its API key.', 503)
    if limited:
        raise AssessmentError('The provider rate limit or account quota was reached. Check your account and retry later.', 503)
    if redirected:
        raise AssessmentError('The service redirected the request. Enter its final API address in Settings and test again.', 502)
    if unsupported:
        raise AssessmentError('The service did not accept this model or request format. Check the model ID and API address, or choose another model.', 502)
    raise AssessmentError('The service could not complete the request. Check the address, model ID, API support, and connection in Settings.', 503)


def model_status(config):
    """Inspect model listings without treating them as a successful task test."""
    if not config.configured:
        return {'configured': False, 'ready': False, 'label': 'Not configured',
                'message': 'Enter a server address and model ID to enable this optional connection.'}
    try:
        reply = request(config, '/v1/models', None, 'application/json', timeout=8)
        models = reply.get('data') if isinstance(reply, dict) else None
        if not isinstance(models, list):
            return {'configured': True, 'ready': False, 'label': 'Not tested',
                    'message': 'The service returned an invalid model list. Use Test Connection in Settings to check the configured model.'}
        if not any(isinstance(item, dict) and item.get('id') == config.model for item in models):
            return {'configured': True, 'ready': False, 'label': 'Not tested',
                    'message': 'The service did not list this model ID. It may still accept requests for it. Use Test Connection in Settings to check it.'}
        return {'configured': True, 'ready': True, 'label': 'Model listed',
                'message': 'The service lists the configured model and accepted the connection. Use its test in Settings to check a real response.'}
    except _ModelListUnavailable as exc:
        return {'configured': True, 'ready': False, 'label': 'Not tested', 'message': str(exc)}
    except AssessmentError as exc:
        return {'configured': True, 'ready': False, 'label': 'Not tested',
                'message': 'The model-list check failed. ' + str(exc)
                           + ' Use Test Connection in Settings to check an actual request.'}


def test_speech(config):
    if not config.configured:
        return model_status(config)
    started = time.monotonic()
    audio = io.BytesIO()
    with wave.open(audio, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b'\0\0' * 16000)
    transcript = speech_reply(config, audio.getvalue())
    return {'ready': True, 'message': 'Speech service accepted a one-second silent WAV. This checks the connection, not speech accuracy.',
            'model': config.model, 'elapsedMs': round((time.monotonic() - started) * 1000), 'transcript': transcript}


def speech_reply(config, audio, timeout=60):
    boundary = 'math-practice-' + uuid.uuid4().hex
    parts = []
    for name, value in (('model', config.model),):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="thinking.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode()
                 + audio + f'\r\n--{boundary}--\r\n'.encode())
    reply = request(config, '/v1/audio/transcriptions', b''.join(parts), 'multipart/form-data; boundary=' + boundary, timeout)
    if not isinstance(reply, dict) or not isinstance(reply.get('text'), str):
        raise AssessmentError('The speech service did not return a text transcript. Check transcription API support.', 502)
    return re.sub(r'^\s*language\s+\S+\s*<asr_text>', '', reply['text'], flags=re.I).strip()


MAX_AUDIO_BYTES = 2_000_000
MAX_RECORDING_SECONDS = 60


def transcribe(config, audio):
    """Accept browser PCM WAV, split near pauses to respect the service's 26s limit."""
    started = time.monotonic()
    try:
        with wave.open(io.BytesIO(audio), 'rb') as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype()) != (1, 2, 16000, 'NONE'):
                raise ValueError()
            frames = wav.getnframes()
            if not 1600 <= frames <= 16000 * MAX_RECORDING_SECONDS:
                raise ValueError()
            pcm = wav.readframes(frames)
            if len(pcm) != frames * 2:
                raise ValueError()
    except (wave.Error, EOFError, ValueError, OSError):
        raise AssessmentError('Record between a moment and one minute of 16 kHz mono PCM WAV audio.', 400) from None
    # A short energy window chooses the quietest boundary in the last six seconds.
    # Every request remains <=26s even when the speaker never pauses.
    import struct
    words, start, chunks = [], 0, 0
    while start < frames:
        end = min(frames, start + 26 * 16000)
        if end < frames:
            candidates = range(end - 6 * 16000, end + 1, 4000)
            end = min(candidates, key=lambda boundary: sum(
                sample[0] ** 2 for sample in struct.iter_unpack('<h', pcm[(boundary - 4000) * 2:boundary * 2])))
        segment = io.BytesIO()
        with wave.open(segment, 'wb') as wav:
            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(16000)
            wav.writeframes(pcm[start * 2:end * 2])
        remaining = 120 - (time.monotonic() - started)
        if remaining <= 0:
            raise AssessmentError('Transcription took too long. Your recording is available to retry.', 504)
        words.append(speech_reply(config, segment.getvalue(), timeout=remaining))
        start = end
        chunks += 1
    text = ' '.join(word for word in words if word).strip()
    if len(text) > 12000:
        raise AssessmentError('This transcript is too long. Try a shorter explanation.', 502)
    return {'text': text, 'model': config.model, 'chunks': chunks,
            'elapsedMs': round((time.monotonic() - started) * 1000)}


def test_inference(config):
    if not config.configured:
        return model_status(config)
    from practice_tutor import test_tutor_connection
    return test_tutor_connection({'provider': 'api', 'model': config.model,
                                  'bases': config.bases, 'apiKey': config.api_key})
