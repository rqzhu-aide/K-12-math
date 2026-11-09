/* Captures mono PCM on the audio thread. Outputs stay silent. */
class ThinkingRecorder extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = new Float32Array(4096);
    this.used = 0;
    this.frames = 0;
    this.done = false;
    this.port.onmessage = (event) => { if (event.data === 'stop') this.finish(); };
  }
  flush() {
    if (!this.used) return;
    const samples = this.buffer.slice(0, this.used);
    this.port.postMessage({samples}, [samples.buffer]);
    this.used = 0;
  }
  finish() {
    if (this.done) return;
    this.done = true;
    this.flush();
    this.port.postMessage({done: true});
  }
  process(inputs) {
    if (this.done) return false;
    const channels = inputs[0];
    if (!channels || !channels.length) return true;
    for (let i = 0; i < channels[0].length; i++) {
      let sample = 0;
      for (const channel of channels) sample += channel[i] || 0;
      this.buffer[this.used++] = sample / channels.length;
      this.frames++;
      if (this.used === this.buffer.length) this.flush();
      if (this.frames >= sampleRate * 60) { this.finish(); return false; }
    }
    return true;
  }
}
registerProcessor('thinking-recorder', ThinkingRecorder);
