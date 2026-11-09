/* Microphone capture and reviewed text input. Audio is held only in memory. */
(function () {
  'use strict';
  function encodeWav(chunks, rate) {
    const count = chunks.reduce((n, chunk) => n + chunk.length, 0);
    const samples = new Float32Array(count);
    let offset = 0;
    for (const chunk of chunks) { samples.set(chunk, offset); offset += chunk.length; }
    const length = Math.min(16000 * 60, Math.floor(count * 16000 / rate));
    const buffer = new ArrayBuffer(44 + length * 2), view = new DataView(buffer);
    function text(at, value) { for (let i = 0; i < value.length; i++) view.setUint8(at + i, value.charCodeAt(i)); }
    text(0, 'RIFF'); view.setUint32(4, 36 + length * 2, true); text(8, 'WAVE');
    text(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
    view.setUint16(22, 1, true); view.setUint32(24, 16000, true); view.setUint32(28, 32000, true);
    view.setUint16(32, 2, true); view.setUint16(34, 16, true); text(36, 'data'); view.setUint32(40, length * 2, true);
    // Average each source interval when downsampling, including fractional edges.
    const step = rate / 16000;
    for (let i = 0; i < length; i++) {
      const start = i * step, end = (i + 1) * step;
      let value = 0;
      for (let j = Math.floor(start); j < Math.ceil(end); j++) {
        value += samples[j] * (Math.min(j + 1, end) - Math.max(j, start));
      }
      value = Math.max(-1, Math.min(1, value / step));
      view.setInt16(44 + i * 2, Math.round(value * (value < 0 ? 32768 : 32767)), true);
    }
    return new Blob([buffer], {type: 'audio/wav'});
  }

  class SpeechInput {
    constructor(options) {
      this.options = options;
      this.state = 'idle'; this.serial = 0; this.capture = null;
      this.request = null; this.audio = null; this.transcript = '';
      options.record.addEventListener('click', () => this.state === 'recording' ? this.stop() : this.start());
      options.cancel.addEventListener('click', () => this.reset('Recording discarded. Your written draft is unchanged.'));
      options.retry.addEventListener('click', () => this.transcript ? this.appendTranscript() : this.upload(this.serial));
      window.addEventListener('pagehide', () => this.reset());
      this.sync();
    }
    busy() { return ['preparing', 'recording', 'stopping', 'transcribing'].includes(this.state) || !!this.transcript; }
    configured() { return !window.MATH_PRACTICE_HOSTED && !!(this.options.isConfigured && this.options.isConfigured()); }
    sync(message) {
      const o = this.options;
      o.record.disabled = !this.configured() || !o.isEnabled() || o.isAssessing() || !['idle', 'recording', 'error', 'ready'].includes(this.state) || !!this.transcript;
      o.recordLabel.textContent = this.state === 'recording' ? 'Stop and transcribe' : this.state === 'preparing' ? 'Opening microphone…' : this.state === 'transcribing' ? 'Transcribing…' : 'Record thinking';
      o.record.title = this.configured() ? o.recordLabel.textContent : 'Add a speech connection in Settings to record your thinking.';
      o.record.setAttribute('aria-pressed', this.state === 'recording' ? 'true' : 'false');
      o.record.setAttribute('aria-busy', ['preparing', 'stopping', 'transcribing'].includes(this.state) ? 'true' : 'false');
      o.recordTime.hidden = o.recordProgress.hidden = this.state !== 'recording';
      if (this.state !== 'recording') this.updateProgress(0);
      o.cancel.hidden = !this.busy() && !this.audio;
      o.cancel.textContent = this.state === 'transcribing' ? 'Cancel transcription' : 'Discard recording';
      o.retry.hidden = !(this.state === 'error' && (this.audio || this.transcript));
      o.retry.textContent = this.transcript ? 'Add transcript' : 'Retry transcription';
      o.status.dataset.state = this.state;
      o.status.setAttribute('aria-live', this.state === 'recording' ? 'off' : 'polite');
      if (message !== undefined) o.status.textContent = message;
      else if (!o.isEnabled()) o.status.textContent = '';
      else if (this.connectionMissing && this.configured()) o.status.textContent = '';
      if (o.isEnabled() && !this.configured()) o.status.textContent = 'Speech is not configured. You can type your thinking or add a speech connection in Settings.';
      if (window.MATH_PRACTICE_HOSTED) {
        o.recordLabel.textContent = 'Recording: local app only';
        o.record.title = 'Recording is available in the local app. You can type your thinking here.';
        o.status.textContent = '';
      }
      this.connectionMissing = !this.configured();
      o.onState();
    }
    updateProgress(elapsed) {
      const remaining = Math.ceil((60000 - elapsed) / 1000);
      this.options.recordTime.textContent = Math.floor(remaining / 60) + ':' + String(remaining % 60).padStart(2, '0') + ' left';
      this.options.recordProgress.style.transform = 'scaleX(' + elapsed / 60000 + ')';
    }
    release(capture) {
      if (!capture) return;
      clearInterval(capture.timer);
      if (capture.stream) capture.stream.getTracks().forEach(track => track.stop());
      if (capture.node) { capture.node.port.onmessage = null; capture.node.onprocessorerror = null; capture.node.disconnect(); }
      if (capture.source) capture.source.disconnect();
      if (capture.context) capture.context.close().catch(() => {});
      if (this.capture === capture) this.capture = null;
    }
    reset(message) {
      this.serial++;
      this.release(this.capture);
      if (this.request) this.request.abort();
      this.request = null; this.audio = null; this.transcript = ''; this.state = 'idle';
      this.sync(message || '');
    }
    async start() {
      if (!this.configured() || !this.options.isEnabled() || this.options.isAssessing() || this.busy()) return;
      this.reset();
      const serial = this.serial;
      const Audio = window.AudioContext || window.webkitAudioContext;
      if (location.protocol === 'file:' || !window.isSecureContext) {
        this.state = 'error'; this.sync('Open practice through the local launcher to record. You can still type your thinking.'); return;
      }
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !Audio || !window.AudioWorkletNode) {
        this.state = 'error'; this.sync('This browser does not support recording here. Try current Chrome, Edge, Firefox, or Safari, or type your thinking.'); return;
      }
      const capture = {chunks: []}; this.capture = capture;
      this.state = 'preparing'; this.sync('Allow microphone access in your browser. You can cancel while waiting.');
      try {
        capture.context = new Audio();
        await capture.context.resume();
        await capture.context.audioWorklet.addModule('speech-worklet.js');
        if (serial !== this.serial) return;
        const stream = await navigator.mediaDevices.getUserMedia({audio: {channelCount: 1, echoCancellation: true, noiseSuppression: true}, video: false});
        if (serial !== this.serial) { stream.getTracks().forEach(track => track.stop()); return; }
        capture.stream = stream;
        capture.node = new window.AudioWorkletNode(capture.context, 'thinking-recorder', {outputChannelCount: [1]});
        capture.node.port.onmessage = event => {
          if (serial !== this.serial) return;
          if (event.data.samples) capture.chunks.push(event.data.samples);
          if (event.data.done) {
            const rate = capture.context.sampleRate;
            this.release(capture);
            this.audio = encodeWav(capture.chunks, rate);
            this.upload(serial);
          }
        };
        capture.node.onprocessorerror = () => {
          if (serial !== this.serial) return;
          this.release(capture); this.state = 'error'; this.sync('Recording stopped unexpectedly. Please record again or type your thinking.');
        };
        stream.getAudioTracks().forEach(track => track.addEventListener('ended', () => {
          if (serial === this.serial && this.state === 'recording') this.stop();
        }));
        capture.source = capture.context.createMediaStreamSource(stream);
        capture.source.connect(capture.node); capture.node.connect(capture.context.destination);
        capture.started = Date.now();
        this.state = 'recording';
        const tick = () => {
          if (serial !== this.serial || this.state !== 'recording' || this.capture !== capture) return;
          const elapsed = Math.max(0, Math.min(60000, Date.now() - capture.started));
          const seconds = Math.floor(elapsed / 1000);
          this.updateProgress(elapsed);
          if (capture.seconds !== seconds) {
            capture.seconds = seconds;
            this.sync('Recording ' + Math.floor(seconds / 60) + ':' + String(seconds % 60).padStart(2, '0') + ' / 1:00. Stop when you finish your thought.');
          }
          if (seconds >= 60) this.stop();
        };
        tick(); capture.timer = setInterval(tick, 250);
      } catch (error) {
        this.release(capture);
        if (serial !== this.serial) return;
        this.state = 'error';
        const message = error.name === 'NotAllowedError' ? 'Microphone access was not allowed. Enable it for this page in your browser, or type your thinking.' : error.name === 'NotFoundError' ? 'No microphone was found. Connect one, or type your thinking.' : 'The microphone could not start. Check your browser and microphone, or type your thinking.';
        this.sync(message);
      }
    }
    stop() {
      if (this.state !== 'recording' || !this.capture) return;
      const capture = this.capture;
      this.state = 'stopping';
      clearInterval(capture.timer);
      capture.stream.getTracks().forEach(track => track.stop());
      this.sync('Recording stopped. Preparing your words…');
      capture.node.port.postMessage('stop');
    }
    async upload(serial) {
      if (!this.configured() || !this.audio || serial !== this.serial || this.state === 'transcribing') return;
      if (this.audio.size < 3244) { this.audio = null; this.state = 'error'; this.sync('That recording was too short. Speak for a moment, then stop.'); return; }
      const controller = new AbortController(); this.request = controller;
      this.state = 'transcribing'; this.sync('Transcribing your recording. Your draft stays editable; review the added text before submitting.');
      const timeout = setTimeout(() => controller.abort(), 135000);
      try {
        const response = await fetch('/api/transcription', {method: 'POST', headers: {'Content-Type': 'audio/wav'}, body: this.audio, signal: controller.signal});
        let reply;
        try { reply = JSON.parse(await response.text()); } catch (_) { throw new Error('Transcription returned an unreadable response. Check the local launcher and try again.'); }
        if (!response.ok) throw new Error(reply && reply.error && reply.error.message || 'Transcription failed. Check the speech connection in Settings, then retry.');
        if (!reply || typeof reply.text !== 'string') throw new Error('The speech service returned no transcript field. Check its API support in Settings.');
        if (serial !== this.serial) return;
        this.transcript = reply.text.trim();
        if (!this.transcript) { this.audio = null; this.state = 'ready'; this.sync('No speech was detected. Your draft is unchanged. Try recording again or type your thinking.'); return; }
        if (this.options.onTranscript) this.options.onTranscript(this.transcript);
        this.appendTranscript();
      } catch (error) {
        if (serial !== this.serial) return;
        this.state = 'error';
        this.sync(error.name === 'AbortError' ? 'Transcription took too long. Retry this recording, record again, or type your thinking.' : error instanceof TypeError ? 'Could not reach transcription. Check the local launcher and speech settings, then retry.' : error.message);
      } finally {
        clearTimeout(timeout);
        if (serial === this.serial) this.request = null;
      }
    }
    appendTranscript() {
      const draft = this.options.draft;
      const value = draft.value + (draft.value && !/\n$/.test(draft.value) ? '\n\n' : '') + this.transcript;
      if (value.length > 12000) {
        this.state = 'error'; this.sync('The combined draft exceeds 12,000 characters. Shorten your writing, then choose Add transcript, or discard the recording.'); return;
      }
      draft.value = value;
      this.transcript = ''; this.audio = null; this.state = 'ready';
      this.options.onDraft();
      this.sync('Transcript added. Review and correct the text below, then choose Submit answer.');
      draft.focus();
    }
  }
  SpeechInput.encodeWav = encodeWav;
  window.MathPracticeSpeech = SpeechInput;
})();
