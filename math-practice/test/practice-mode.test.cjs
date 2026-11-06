'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const directory = path.resolve(__dirname, '..');
const answers = require('../answer-check.js');

class Element {
  constructor() {
    this.value = ''; this.textContent = ''; this.hidden = true; this.disabled = false;
    this.dataset = {}; this.attributes = {}; this.listeners = {}; this.children = []; this.style = {};
    const classes = new Set();
    this.classList = {add: (...values) => values.forEach(value => classes.add(value)), remove: value => classes.delete(value), toggle: (value, active) => active ? classes.add(value) : classes.delete(value)};
  }
  addEventListener(name, callback) { (this.listeners[name] ||= []).push(callback); }
  setAttribute(name, value) { this.attributes[name] = value; }
  removeAttribute(name) { delete this.attributes[name]; }
  appendChild(child) { this.children.push(child); child.parentElement = this; return child; }
  replaceChildren(...children) { this.children = []; children.forEach(child => this.appendChild(child)); }
  focus() {}
  scrollIntoView() {}
  checkValidity() { return true; }
  reportValidity() { return true; }
  querySelectorAll() { return []; }
  async emit(name, details = {}) {
    const event = {target: this, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; }, ...details};
    for (const callback of this.listeners[name] || []) await callback(event);
    return event;
  }
}
function environment(file, extras = {}) {
  const elements = new Map();
  const root = new Element();
  const node = id => { if (!elements.has(id)) { const value = new Element(); root.appendChild(value); elements.set(id, value); } return elements.get(id); };
  const window = Object.assign(new Element(), {MathPracticeAnswers: answers});
  const context = vm.createContext({window, document: {getElementById: node, addEventListener() {}, body: new Element(), createElement: () => new Element(), createTextNode: text => Object.assign(new Element(), {textContent: text, nodeType: 3})},
    location: {protocol: 'http:'}, AbortController, setTimeout, clearTimeout, setInterval, clearInterval,
    fetch: async () => { throw new Error('Unexpected network request'); }, ...extras});
  vm.runInContext(fs.readFileSync(path.join(directory, file), 'utf8'), context, {filename: file});
  return {node, window, context};
}
function feedback(options = {}) {
  const requests = [];
  const env = environment('practice-feedback.js', {location: {protocol: options.protocol || 'http:'}});
  const question = options.question || {id: 'sample', responseType: 'numeric', answer: '0.5'};
  const answer = options.answer || '1/2';
  const o = {
    question: () => question, answer: () => answer, draft: new Element(), note: new Element(),
    panel: new Element(), panelStatus: new Element(), results: new Element(), announce: new Element(),
    el: (_tag, _class, text) => Object.assign(new Element(), {textContent: text}), percent: String,
    typeset() {}, connection() {}, collapse() {}, setRunning(value) { o.running = value; }, save() {},
    submitted() {}, updated() {}, checkAnswer: answers.check, classifyAnswer: answers.classify,
    services: () => options.services || {decision: false, inference: false},
    waitServices: options.waitServices
  };
  o.draft.value = options.thoughts === undefined ? 'One half equals five tenths.' : options.thoughts;
  const instance = new env.window.MathPracticeFeedback(o);
  instance.post = async (url, body) => { requests.push({url, body}); return options.reply(url, body); };
  return {...env, instance, requests, o};
}

for (const protocol of ['file:', 'http:']) {
  test(`${protocol} practice checks a correct answer without models or thinking`, async () => {
    const f = feedback({protocol, thoughts: ''});
    await f.instance.submit();
    assert.match(f.node('answerFeedback').textContent, /Correct\./);
    assert.match(f.node('reasoningFeedback').textContent, /Thinking: Not checked\./);
    assert.equal(f.node('submissionMark').dataset.result, 'review');
    assert.equal(f.node('tutorRetry').hidden, true);
    assert.equal(f.node('hintToggle').hidden, true);
    assert.equal(f.o.running, false);
    assert.deepEqual(f.requests, []);
  });
}
test('wrong exact answers show a cross without attempting a tutor', async () => {
  const f = feedback({answer: '2'});
  await f.instance.submit();
  assert.equal(f.node('submissionMark').dataset.result, 'wrong');
  assert.match(f.node('reasoningFeedback').textContent, /Not checked/);
  assert.deepEqual(f.requests, []);
});
for (const protocol of ['file:', 'http:']) {
  test(`${protocol} controlled graph disputes preserve the question and skip grading and models`, async () => {
    const question = {id: 'ambiguous', responseType: 'choice', answer: 'D',
      choices: {A: 'The square root of 4 is 2.', D: 'The square root of 0 is 0.'},
      knowledgeGraph: {version: 'test-v1', contentHash: 'a'.repeat(64),
        gradingStatus: 'disputed', gradingNote: 'This wording has a confirmed ambiguity.'}};
    const original = JSON.stringify(question);
    const f = feedback({protocol, question, answer: 'A', services: {decision: true, inference: true}});
    await f.instance.submit();
    assert.equal(answers.classify(question, 'A'), 'not_graded');
    assert.equal(answers.check(question, 'A'), null);
    assert.match(f.node('answerFeedback').textContent, /Not graded/i);
    assert.match(f.node('coach').textContent, /confirmed ambiguity/);
    assert.deepEqual(f.requests, []);
    assert.equal(JSON.stringify(question), original);
    assert.equal(Object.hasOwn(question, 'gradingStatus'), false);
    await f.instance.requestTutor('partial', 'wrong', f.instance.serial);
    assert.deepEqual(f.requests, []);
  });
}
test('first-pass graph uncertainty does not suppress the ordinary answer check', async () => {
  const question = {id: 'review-flag', responseType: 'choice', answer: 'D',
    knowledgeGraph: {answerCheck: {status: 'ambiguous'}, flags: ['answer_key_disagreement']}};
  const f = feedback({protocol: 'file:', question, answer: 'A'});
  await f.instance.submit();
  assert.equal(answers.classify(question, 'A'), 'wrong');
  assert.equal(f.node('submissionMark').dataset.result, 'wrong');
  assert.deepEqual(f.requests, []);
});
test('answer forms remain partial and unsupported symbolic work remains unverified', async () => {
  const partial = feedback({question: {id: 'decimal', responseType: 'numeric', answer: '0.5', answerForm: 'decimal'}});
  await partial.instance.submit();
  assert.match(partial.node('answerFeedback').textContent, /Partially correct/);
  assert.match(partial.node('coach').textContent, /decimal numeral/);
  assert.equal(partial.node('submissionMark').dataset.result, 'review');
  const unknown = feedback({question: {id: 'symbolic', responseType: 'short', answer: 'x+x'}, answer: '2x'});
  await unknown.instance.submit();
  assert.match(unknown.node('answerFeedback').textContent, /Not checked automatically/);
  assert.equal(unknown.node('submissionMark').dataset.result, 'review');
});
test('speech learning signals are skipped without a decision model', async () => {
  const f = feedback();
  f.instance.evidence = {transcript: 'My original thinking.', signals: null};
  await f.instance.checkSignals();
  assert.equal(f.o.panelStatus.textContent, 'Decision model not configured');
  assert.equal(f.o.results.children.length, 1);
  assert.deepEqual(f.requests, []);
});
test('learning signals accept a decision connection disabled after the page loaded', async () => {
  const f = feedback({services: {decision: true, inference: false}, reply(_url, body) {
    return {...body, decisionConfigured: false, signals: []};
  }});
  f.instance.evidence = {transcript: 'My original thinking.', signals: null};
  await f.instance.checkSignals();
  assert.equal(f.requests.length, 1);
  assert.equal(f.o.panel.dataset.state, 'idle');
  assert.equal(f.o.panelStatus.textContent, 'Decision model not configured');
  assert.equal(f.o.results.children.length, 1);
  assert.equal(f.o.results.children[0].children.length, 0);
});

test('mathematical review uses edited thinking while learning signals retain the original transcript', async () => {
  const original = 'ORIGINAL_RECOGNITION_TEXT';
  const edited = 'I corrected the transcript: one half is five tenths.';
  const f = feedback({services: {decision: true, inference: true}, reply(url, body) {
    if (url === '/api/learning-signals') return {...body, signals: ['confidence', 'reasoning', 'engagement'].map(id => ({
      id, title: id, label: 'Unclear', evidence: 'Not enough communication evidence.'}))};
    return {...body, answerCategory: 'correct', answerCorrect: true,
      category: url === '/api/tutor' ? 'correct' : 'cannot_judge',
      ...(url === '/api/tutor' ? {coach: 'Your conversion correctly gives five tenths.', hint: ''} : {})};
  }});
  f.instance.evidence = {transcript: original, signals: null};
  await f.instance.checkSignals();
  f.o.draft.value = '  ' + edited + '  ';
  await f.instance.submit(); await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(f.requests.map(request => request.url), ['/api/learning-signals', '/api/assessment', '/api/tutor']);
  assert.equal(f.requests[0].body.transcript, original);
  assert.equal(Object.hasOwn(f.requests[0].body, 'thoughts'), false);
  for (const request of f.requests.slice(1)) {
    assert.equal(request.body.thoughts, edited);
    assert.equal(request.body.answer, '1/2');
    assert.doesNotMatch(JSON.stringify(request.body), /ORIGINAL_RECOGNITION_TEXT/);
  }
  assert.equal(f.instance.evidence.transcript, original);
});
test('configured inference reviews work when the decision model is absent', async () => {
  const f = feedback({services: {decision: false, inference: true}, reply(url, body) {
    if (url === '/api/assessment') return {...body, answerCategory: 'correct', answerCorrect: true,
      category: 'cannot_judge', modelUsed: false, decisionConfigured: false, inferenceConfigured: true};
    return {...body, answerCategory: 'correct', answerCorrect: true, category: 'correct', hint: '', coach: 'Your explanation checks out.'};
  }});
  await f.instance.submit();
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(f.requests.map(r => r.url), ['/api/assessment', '/api/tutor']);
  assert.equal(f.node('submissionMark').dataset.result, 'correct');
});
test('assessment flags prevent tutor requests after a connection is disabled', async () => {
  const f = feedback({services: {decision: true, inference: true}, reply(_url, body) {
    return {...body, answerCategory: 'correct', answerCorrect: true, category: 'cannot_judge',
      decisionConfigured: false, inferenceConfigured: false, modelUsed: false};
  }});
  await f.instance.submit();
  assert.equal(f.requests.length, 1);
  assert.match(f.node('reasoningFeedback').textContent, /Not checked/);
  assert.equal(f.node('tutorRetry').hidden, true);
  assert.equal(f.node('submissionMark').dataset.result, 'review');
});
test('an unconfigured tutor response does not create a failed review or retry', async () => {
  const f = feedback({services: {decision: false, inference: true}, reply(url, body) {
    if (url === '/api/tutor') return {configured: false, inferenceConfigured: false};
    return {...body, answerCategory: 'correct', answerCorrect: true, category: 'cannot_judge',
      decisionConfigured: false, inferenceConfigured: true};
  }});
  await f.instance.submit();
  await new Promise(resolve => setImmediate(resolve));
  assert.match(f.node('reasoningFeedback').textContent, /Not checked/);
  assert.equal(f.node('tutorRetry').hidden, true);
  assert.equal(f.node('tutorStatus').hidden, true);
});
test('submission waits for pending configuration and ignores a stale submission', async () => {
  let finish;
  const f = feedback({waitServices: () => new Promise(resolve => { finish = resolve; })});
  const submission = f.instance.submit();
  f.instance.clear(); finish(); await submission;
  assert.equal(f.instance.mathState, 'idle');
  assert.equal(f.node('workFeedback').hidden, true);
  assert.deepEqual(f.requests, []);
});
test('microphone capture cannot start without a configured speech service', async () => {
  let captures = 0;
  const env = environment('speech-input.js', {navigator: {mediaDevices: {getUserMedia() { captures++; }}}});
  const o = Object.fromEntries(['record', 'recordLabel', 'recordTime', 'recordProgress', 'cancel', 'retry', 'status', 'draft'].map(id => [id, new Element()]));
  Object.assign(o, {isConfigured: () => false, isEnabled: () => true, isAssessing: () => false, onState() {}});
  const speech = new env.window.MathPracticeSpeech(o);
  assert.equal(o.record.disabled, true);
  assert.match(o.status.textContent, /Speech is not configured/);
  await speech.start();
  assert.equal(captures, 0);
  assert.equal(speech.state, 'idle');
  o.isConfigured = () => true; speech.sync();
  assert.equal(o.record.disabled, false);
  assert.equal(o.status.textContent, '');
});

function settingsEnvironment(overrides = {}, testReplies = {}) {
  const requests = [];
  const section = () => ({bases: [], model: '', keyConfigured: false});
  const sections = ['decision', 'speech', 'inference'];
  const clone = value => JSON.parse(JSON.stringify(value));
  let saved = {decision: {...section(), protocol: 'chat'}, speech: section(), inference: {...section(), provider: 'api', effort: 'medium'}, ...clone(overrides)};
  if (saved.inference.model) saved.inference.modelByProvider = {...saved.inference.modelByProvider, [saved.inference.provider]: saved.inference.model};
  const keys = Object.fromEntries(sections.map(name => [name, saved[name].keyConfigured ? 'saved-fixture-key' : '']));
  const confirmations = [];
  const merge = (name, patch) => {
    const bases = patch.bases || saved[name].bases;
    const key = (patch.apiKey || '').trim() || (JSON.stringify(bases) === JSON.stringify(saved[name].bases) ? keys[name] : '');
    const value = {...saved[name], ...patch, bases: [...bases], keyConfigured: !!key};
    delete value.apiKey;
    if (name === 'inference') {
      const models = {...saved.inference.modelByProvider, ...patch.modelByProvider};
      if (value.provider !== saved.inference.provider && saved.inference.model) models[saved.inference.provider] = saved.inference.model;
      if (value.model || Object.keys(models).length) value.modelByProvider = {...models, [value.provider]: value.model};
    }
    return {value, key};
  };
  const write = patch => {
    for (const name of sections) if (patch[name]) {
      const merged = merge(name, patch[name]);
      saved = {...saved, [name]: merged.value}; keys[name] = merged.key;
    }
  };
  const env = environment('settings.js', {fetch: async (url, options) => {
    const body = options && options.body ? JSON.parse(options.body) : null;
    requests.push({url, body});
    if (url === '/api/settings' && body && !testReplies[url]) write(body);
    let value = saved;
    if (url === '/api/settings/compare') {
      const changedSections = sections.filter(name => {
        const merged = merge(name, body[name]);
        return JSON.stringify(merged.value) !== JSON.stringify(saved[name]) || merged.key !== keys[name];
      });
      value = {different: !!changedSections.length, changedSections};
    }
    if (url === '/api/connections/openai' || url === '/api/connections/chatgpt') value = {state: 'signed_out', message: 'Sign in when ready.', canTest: false, account: null, modelSuggestions: []};
    if (testReplies[url]) value = typeof testReplies[url] === 'function' ? await testReplies[url](body, clone(value)) : testReplies[url];
    value = clone(value);
    return {ok: !value.error, json: async () => value};
  }});
  env.window.confirm = text => { confirmations.push(text); return env.confirmLoad !== false; };
  Object.assign(env, {requests, confirmations, editSaved: write, saved: () => clone(saved)});
  return env;
}
test('blank settings load and save one model independently without a Codex probe', async () => {
  const s = settingsEnvironment();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(s.node('inferencePanel').hidden, false);
  assert.equal(s.node('decisionBadge').textContent, 'Not configured');
  assert.equal(s.node('decisionBases').disabled, false);
  s.node('decisionBases').value = 'http://localhost:8000';
  s.node('decisionModel').value = 'decision-test';
  await s.node('decisionForm').emit('submit');
  const writes = s.requests.filter(r => r.url === '/api/settings' && r.body);
  assert.equal(writes.length, 1);
  assert.deepEqual(Object.keys(writes[0].body), ['decision']);
  assert.equal(writes[0].body.decision.model, 'decision-test');
  assert.equal(s.node('speechBases').value, '');
  assert.equal(s.requests.some(r => r.url.includes('/connections/openai')), false);
});

test('saved shared connections load directly into tabs and retain independent drafts', async () => {
  const s = settingsEnvironment({setup: {mode: 'single', provider: 'custom'},
    decision: {bases: ['http://localhost:8000'], model: 'text-model', protocol: 'chat', keyConfigured: true},
    speech: {bases: ['http://localhost:8000'], model: 'speech-model', keyConfigured: true}});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(s.node('inferencePanel').hidden, false);
  assert.equal(s.node('speechModel').value, 'speech-model');
  assert.equal(s.node('decisionModel').value, 'text-model');
  assert.equal(s.node('saveConfiguration').disabled, true);
  s.node('speechModel').value = 'speech-draft';
  const count = s.requests.length;
  await s.node('decisionTab').emit('click');
  await s.node('speechTab').emit('click');
  assert.equal(s.node('speechModel').value, 'speech-draft');
  assert.equal(s.requests.length, count);
  await s.node('speechForm').emit('submit');
  const write = s.requests.find(r => r.url === '/api/settings' && r.body);
  assert.deepEqual(Object.keys(write.body), ['speech']);
  assert.equal(write.body.speech.model, 'speech-draft');
  assert.equal(s.node('decisionModel').value, 'text-model');
});

test('connection tests show per-model results and open the failed tab', async () => {
  const s = settingsEnvironment({
    decision: {bases: ['http://localhost:8000'], model: 'text-model', protocol: 'chat', keyConfigured: false},
    speech: {bases: ['http://localhost:8000'], model: 'speech-model', keyConfigured: false}}, {
    '/api/settings/speech/test': {ready: true, message: 'Speech accepted the sample.', model: 'speech-model', elapsedMs: 100},
    '/api/settings/decision/test': {error: {message: 'Choose a text model supporting JSON.'}}
  });
  await new Promise(resolve => setImmediate(resolve));
  await s.node('testConnections').emit('click');
  assert.equal(s.node('speechBadge').textContent, 'Test passed');
  assert.equal(s.node('decisionBadge').textContent, 'Test failed');
  assert.equal(s.node('decisionPanel').hidden, false);
  assert.match(s.node('decisionResult').textContent, /supporting JSON/);
  assert.match(s.node('pageStatus').textContent, /1 of 2/);
  assert.equal(s.node('speechDot').dataset.state, 'ok');
  assert.equal(s.node('decisionDot').dataset.state, 'idle');
  assert.equal(s.node('inferenceDot').dataset.state, 'idle');
  assert.match(s.node('testConnections').attributes['aria-label'], /Speech: Test passed; Sentiment: Test failed/);
  assert.equal(s.node('testConnectionsLabel').textContent, 'Test All Connections');
  assert.equal(s.requests.some(r => r.url === '/api/settings/inference/test'), false);
  s.node('decisionModel').value = 'another-model';
  await s.node('decisionForm').emit('input');
  assert.equal(s.node('decisionBadge').textContent, 'Not tested');
  s.node('speechModel').value = 'changed-speech-model';
  await s.node('speechForm').emit('input');
  assert.equal(s.node('speechDot').dataset.state, 'idle');
});

test('successful connection dots survive saving and reset when loading settings', async () => {
  const reply = {ready: true, message: 'Speech accepted the sample.', model: 'speech-model', elapsedMs: 100};
  const s = settingsEnvironment({speech: {bases: ['http://localhost:8000'], model: 'speech-model', keyConfigured: false}}, {
    '/api/settings/speech/test': reply
  });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(s.node('speechDot').dataset.state, 'idle');
  await s.node('testSpeech').emit('click');
  assert.equal(s.node('speechDot').dataset.state, 'ok');
  await s.node('speechForm').emit('submit');
  assert.equal(s.node('speechDot').dataset.state, 'ok');
  await s.node('saveConfiguration').emit('click');
  assert.equal(s.node('speechDot').dataset.state, 'ok');
  assert.equal(s.node('saveConfiguration').textContent, 'Save All Settings');
  await s.node('loadConfiguration').emit('click');
  assert.equal(s.node('speechDot').dataset.state, 'idle');
  assert.equal(s.node('loadConfiguration').textContent, 'Load Settings');
  await s.node('testSpeech').emit('click');
  assert.equal(s.node('speechDot').dataset.state, 'ok');
  reply.ready = false;
  await s.node('testSpeech').emit('click');
  assert.equal(s.node('speechDot').dataset.state, 'idle');
});

test('saved custom and account connections are preserved until a new URL is entered', async () => {
  const s = settingsEnvironment({
    decision: {bases: ['http://localhost:8000'], model: 'custom-model', protocol: 'systemone', keyConfigured: true},
    inference: {bases: [], model: 'saved-tutor', provider: 'codex', effort: 'high', keyConfigured: false}});
  await new Promise(resolve => setImmediate(resolve));
  const original = s.requests.find(r => r.url === '/api/settings/compare').body;
  assert.equal(original.decision.protocol, 'systemone');
  assert.equal(original.inference.provider, 'codex');
  assert.equal(original.inference.effort, 'high');
  assert.equal(s.requests.some(r => r.url.includes('/connections/openai')), false);
  s.node('decisionBases').value = 'http://localhost:9000/v1';
  await s.node('useCustomApi').emit('click');
  s.node('inferenceBases').value = 'http://localhost:9000/v1';
  await s.node('saveConfiguration').emit('click');
  const write = s.requests.find(r => r.url === '/api/settings' && r.body).body;
  assert.equal(write.decision.protocol, 'chat');
  assert.equal(write.inference.provider, 'api');
  assert.equal(write.inference.effort, 'high');
});

test('saving one connection clears its global draft state and does not prompt on load', async () => {
  const s = settingsEnvironment();
  await new Promise(resolve => setImmediate(resolve));
  s.node('speechBases').value = 'http://localhost:8000';
  s.node('speechModel').value = 'speech-model';
  s.node('speechKey').value = 'new-fixture-key';
  await s.node('speechForm').emit('input');
  assert.equal(s.node('saveConfiguration').disabled, false);
  await s.node('speechForm').emit('submit');
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(s.node('speechKey').value, '');
  assert.match(s.node('speechKey').placeholder, /Saved key/);
  assert.equal(s.saved().speech.keyConfigured, true);
  assert.equal(s.node('saveConfiguration').disabled, true);
  assert.equal((await s.window.emit('beforeunload')).defaultPrevented, false);
  await s.node('loadConfiguration').emit('click');
  assert.equal(s.confirmations.length, 0);
});

test('a fresh edit cannot use an older equal disk comparison to skip the leave warning', async () => {
  const replies = {}, s = settingsEnvironment({}, replies);
  await new Promise(resolve => setImmediate(resolve));
  s.node('speechModel').value = 'speech-draft';
  await s.node('speechForm').emit('input');
  const leaving = await s.window.emit('beforeunload');
  assert.equal(leaving.defaultPrevented, true);
  assert.equal(leaving.returnValue, '');
  // Once disk really matches the current draft, leaving is safe.
  s.editSaved({speech: {model: 'speech-draft'}});
  await s.window.emit('focus');
  assert.equal((await s.window.emit('beforeunload')).defaultPrevented, false);
  let finishComparison;
  replies['/api/settings/compare'] = (_body, result) => new Promise(resolve => { finishComparison = () => resolve(result); });
  const oldComparison = s.window.emit('focus');
  s.node('speechModel').value = 'newer-speech-draft';
  await s.node('speechForm').emit('input');
  finishComparison(); await oldComparison;
  delete replies['/api/settings/compare'];
  assert.equal((await s.window.emit('beforeunload')).defaultPrevented, true);
});

test('individual save preserves another tab draft and its leave and load protections', async () => {
  const replies = {}, s = settingsEnvironment({}, replies);
  await new Promise(resolve => setImmediate(resolve));
  await s.node('speechTab').emit('click');
  s.node('speechBases').value = 'http://localhost:8000';
  s.node('speechModel').value = 'speech-draft';
  s.node('speechKey').value = 'unsaved-speech-key';
  await s.node('speechForm').emit('input');
  await s.node('decisionTab').emit('click');
  s.node('decisionBases').value = 'http://localhost:9000';
  s.node('decisionModel').value = 'decision-model';
  await s.node('decisionForm').emit('input');
  let finishComparison;
  replies['/api/settings/compare'] = (_body, result) => new Promise(resolve => { finishComparison = () => resolve(result); });
  await s.node('decisionForm').emit('submit');
  // The post-save comparison has not returned yet.
  assert.equal((await s.window.emit('beforeunload')).defaultPrevented, true);
  assert.equal(s.node('saveConfiguration').disabled, false);
  assert.equal(s.node('speechModel').value, 'speech-draft');
  assert.equal(s.node('speechKey').value, 'unsaved-speech-key');
  assert.equal(s.saved().speech.model, '');
  delete replies['/api/settings/compare']; finishComparison();
  await new Promise(resolve => setImmediate(resolve));
  s.confirmLoad = false;
  await s.node('loadConfiguration').emit('click');
  assert.equal(s.confirmations.length, 1);
  assert.equal(s.node('speechModel').value, 'speech-draft');
  assert.equal(s.node('speechKey').value, 'unsaved-speech-key');
  s.confirmLoad = true;
  await s.node('loadConfiguration').emit('click');
  assert.equal(s.confirmations.length, 2);
  assert.equal(s.node('speechModel').value, '');
  assert.equal(s.node('speechKey').value, '');
  assert.equal(s.node('decisionModel').value, 'decision-model');
  assert.equal(s.node('saveConfiguration').disabled, true);
  assert.equal((await s.window.emit('beforeunload')).defaultPrevented, false);
});

test('saving one tab preserves other drafts and hidden settings across external file edits', async () => {
  const originalBases = ['http://localhost:8000', 'http://localhost:8001'];
  const s = settingsEnvironment({
    decision: {bases: originalBases, model: 'decision-original', protocol: 'systemone', keyConfigured: true},
    inference: {bases: [], model: 'account-tutor', provider: 'codex', effort: 'high', keyConfigured: false}
  });
  await new Promise(resolve => setImmediate(resolve));
  s.node('decisionModel').value = 'decision-draft';
  await s.node('decisionForm').emit('input');
  s.node('speechModel').value = 'speech-saved';
  await s.node('speechForm').emit('input');
  s.editSaved({decision: {bases: ['http://localhost:9000'], model: 'external-decision', protocol: 'chat'},
    inference: {bases: ['http://localhost:9001'], model: 'external-tutor', provider: 'api', effort: 'low'}});
  await s.node('speechForm').emit('submit');
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(s.saved().decision.model, 'external-decision');
  assert.equal(s.saved().inference.model, 'external-tutor');
  assert.equal(s.node('decisionModel').value, 'decision-draft');
  assert.equal(s.node('inferenceModel').value, 'account-tutor');
  const comparison = s.requests.filter(request => request.url === '/api/settings/compare').at(-1).body;
  assert.deepEqual(comparison.decision.bases, originalBases);
  assert.equal(comparison.decision.protocol, 'systemone');
  assert.equal(comparison.inference.provider, 'codex');
  assert.equal(comparison.inference.effort, 'high');
  assert.equal(s.node('saveConfiguration').disabled, false);
  assert.equal((await s.window.emit('beforeunload')).defaultPrevented, true);
});

test('external file edits enable save or load without being mistaken for local drafts', async () => {
  const s = settingsEnvironment();
  await new Promise(resolve => setImmediate(resolve));
  s.editSaved({speech: {bases: ['http://localhost:8000'], model: 'external-speech'}});
  await s.window.emit('focus');
  assert.equal(s.node('saveConfiguration').disabled, false);
  assert.match(s.node('pageStatus').textContent, /Saved settings have changed/);
  assert.equal((await s.window.emit('beforeunload')).defaultPrevented, false);
  await s.node('loadConfiguration').emit('click');
  assert.equal(s.confirmations.length, 0);
  assert.equal(s.node('speechModel').value, 'external-speech');
  assert.equal(s.node('saveConfiguration').disabled, true);
});

test('failed individual save retains the draft and key for retry', async () => {
  const replies = {}, s = settingsEnvironment({}, replies);
  await new Promise(resolve => setImmediate(resolve));
  replies['/api/settings'] = {error: {message: 'Could not write config.json.'}};
  s.node('speechBases').value = 'http://localhost:8000';
  s.node('speechModel').value = 'speech-draft';
  s.node('speechKey').value = 'unsaved-fixture-key';
  await s.node('speechForm').emit('input');
  await s.node('speechForm').emit('submit');
  assert.match(s.node('speechResult').textContent, /Could not write/);
  assert.equal(s.node('speechKey').value, 'unsaved-fixture-key');
  assert.equal(s.saved().speech.model, '');
  assert.equal(s.node('saveConfiguration').disabled, false);
  assert.equal((await s.window.emit('beforeunload')).defaultPrevented, true);
  delete replies['/api/settings'];
  await s.node('saveConfiguration').emit('click');
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(s.saved().speech.model, 'speech-draft');
  assert.equal(s.node('speechKey').value, '');
  assert.equal(s.node('saveConfiguration').disabled, true);
  assert.equal((await s.window.emit('beforeunload')).defaultPrevented, false);
});

test('switching API and ChatGPT plan methods retains their drafts without starting sign-in', async () => {
  const s = settingsEnvironment({inference: {bases: ['http://localhost:8000'], model: 'api-saved',
    provider: 'api', effort: 'high', keyConfigured: true}});
  await new Promise(resolve => setImmediate(resolve));
  s.node('inferenceBases').value = 'http://localhost:8001';
  s.node('inferenceModel').value = 'api-draft';
  s.node('inferenceKey').value = 'api-draft-key';
  await s.node('inferenceForm').emit('input');
  s.node('speechModel').value = 'speech-draft';
  await s.node('speechForm').emit('input');
  s.node('decisionModel').value = 'decision-draft';
  await s.node('decisionForm').emit('input');
  await s.node('useChatgptPlan').emit('click');
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(s.node('inferenceApiFields').hidden, true);
  assert.equal(s.node('planAccountFields').hidden, false);
  assert.equal(s.node('inferenceModel').value, '');
  assert.equal(s.node('inferenceDot').dataset.state, 'idle');
  assert.equal(s.requests.some(request => request.url.endsWith('/login')), false);
  assert.equal(s.requests.some(request => request.url === '/api/settings' && request.body), false);
  s.node('inferenceModel').value = 'plan-draft';
  await s.node('inferenceForm').emit('input');
  await s.node('useCustomApi').emit('click');
  assert.equal(s.node('inferenceApiFields').hidden, false);
  assert.equal(s.node('inferenceModel').value, 'api-draft');
  assert.equal(s.node('inferenceBases').value, 'http://localhost:8001');
  assert.equal(s.node('inferenceKey').value, 'api-draft-key');
  await s.node('useChatgptPlan').emit('click');
  assert.equal(s.node('inferenceModel').value, 'plan-draft');
  assert.equal(s.node('speechModel').value, 'speech-draft');
  assert.equal(s.node('decisionModel').value, 'decision-draft');
  assert.equal(s.node('saveConfiguration').disabled, false);
});

test('a saved plan exposes account identity and suggestions and tests through Mathematics', async () => {
  const s = settingsEnvironment({inference: {bases: ['http://localhost:8000'], model: 'saved-plan-model',
    provider: 'chatgpt', effort: 'high', keyConfigured: true,
    modelByProvider: {api: 'remembered-api-model', chatgpt: 'saved-plan-model'}}}, {
    '/api/connections/chatgpt': {state: 'signed_in', canTest: true, account: {id: 'fixture-account', label: 'Fixture account'},
      message: 'Signed in as Fixture account.', modelSuggestions: [{model: 'suggested-plan-model', label: 'Suggested plan model'}]},
    '/api/settings/inference/test': {ready: true, model: 'edited-plan-model', message: 'Mathematics returned a response.', elapsedMs: 100}
  });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(s.node('inferenceApiFields').hidden, true);
  assert.match(s.node('planAccountStatus').textContent, /Fixture account/);
  assert.equal(s.node('inferenceModel').value, 'saved-plan-model');
  assert.equal(s.node('inferenceModelNames').children.some(option => option.value === 'suggested-plan-model'), true);
  assert.equal(s.node('inferenceDot').dataset.state, 'idle');
  assert.equal(s.requests.some(request => request.url.endsWith('/test')), false);
  await s.node('useCustomApi').emit('click');
  assert.equal(s.node('inferenceModel').value, 'remembered-api-model');
  await s.node('useChatgptPlan').emit('click');
  assert.equal(s.node('inferenceModel').value, 'saved-plan-model');
  s.node('inferenceModel').value = 'edited-plan-model';
  await s.node('inferenceForm').emit('input');
  await s.node('testInference').emit('click');
  const probe = s.requests.find(request => request.url === '/api/settings/inference/test').body.inference;
  assert.equal(probe.provider, 'chatgpt');
  assert.equal(probe.model, 'edited-plan-model');
  assert.equal(Object.hasOwn(probe, 'bases'), false);
  assert.equal(Object.hasOwn(probe, 'apiKey'), false);
  assert.equal(s.node('inferenceDot').dataset.state, 'ok');
  await s.node('inferenceForm').emit('submit');
  const write = s.requests.find(request => request.url === '/api/settings' && request.body).body;
  assert.deepEqual(Object.keys(write), ['inference']);
  assert.equal(write.inference.provider, 'chatgpt');
  assert.equal(write.inference.model, 'edited-plan-model');
  assert.equal(Object.hasOwn(write.inference, 'bases'), false);
  assert.equal(Object.hasOwn(write.inference, 'apiKey'), false);
  assert.equal(s.node('inferenceDot').dataset.state, 'ok');
});

test('a saved legacy Codex plan stays selected when its model is edited', async () => {
  const s = settingsEnvironment({inference: {bases: ['http://localhost:8000'], model: 'legacy-model',
    provider: 'codex', effort: 'xhigh', keyConfigured: true}});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(s.node('inferenceApiFields').hidden, true);
  assert.equal(s.requests.some(request => request.url.startsWith('/api/connections/')), false);
  s.node('inferenceModel').value = 'legacy-model-edited';
  await s.node('inferenceForm').emit('input');
  await s.node('inferenceForm').emit('submit');
  const accountWrite = s.requests.find(request => request.url === '/api/settings' && request.body).body.inference;
  assert.equal(accountWrite.provider, 'codex');
  assert.equal(accountWrite.model, 'legacy-model-edited');
  assert.equal(Object.hasOwn(accountWrite, 'bases'), false);
  assert.equal(Object.hasOwn(accountWrite, 'apiKey'), false);
  await s.node('useCustomApi').emit('click');
  assert.equal(s.node('inferenceApiFields').hidden, false);
  s.node('inferenceBases').value = 'http://localhost:9000';
  s.node('inferenceModel').value = 'new-api-model';
  await s.node('inferenceForm').emit('input');
  await s.node('inferenceForm').emit('submit');
  const apiWrite = s.requests.filter(request => request.url === '/api/settings' && request.body).at(-1).body.inference;
  assert.equal(apiWrite.provider, 'api');
  assert.deepEqual(apiWrite.bases, ['http://localhost:9000']);
  assert.equal(apiWrite.model, 'new-api-model');
});

test('plan sign-in, cancellation, and disconnect use explicit actions and preserve settings drafts', async () => {
  const replies = {
    '/api/connections/chatgpt/login': {state: 'waiting', canTest: false, account: null,
      message: 'Complete the fixture sign-in.', modelSuggestions: []},
    '/api/connections/chatgpt/cancel': {state: 'signed_out', canTest: false, account: null,
      message: 'Fixture sign-in canceled.', modelSuggestions: []},
    '/api/connections/chatgpt/disconnect': {state: 'signed_out', canTest: false, account: null,
      message: 'Fixture account disconnected.', modelSuggestions: []}
  };
  const s = settingsEnvironment({}, replies);
  await new Promise(resolve => setImmediate(resolve));
  s.node('speechModel').value = 'speech-draft';
  await s.node('speechForm').emit('input');
  await s.node('useChatgptPlan').emit('click');
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(s.requests.some(request => request.url.endsWith('/login')), false);
  await s.node('planLogin').emit('click');
  assert.equal(s.requests.filter(request => request.url === '/api/connections/chatgpt/login').length, 1);
  assert.equal(s.node('planCancel').hidden, false);
  assert.equal(s.node('inferenceDot').dataset.state, 'idle');
  await s.node('planCancel').emit('click');
  assert.equal(s.node('planCancel').hidden, true);
  assert.equal(s.node('planLogin').hidden, false);
  replies['/api/connections/chatgpt/login'] = {state: 'signed_in', canTest: true,
    account: {id: 'fixture-account', label: 'Fixture account'}, message: 'Signed in as Fixture account.',
    modelSuggestions: [{model: 'suggested-plan-model', label: 'Suggested plan model'}]};
  await s.node('planLogin').emit('click');
  assert.match(s.node('planAccountStatus').textContent, /Fixture account/);
  assert.equal(s.node('inferenceModel').value, '');
  assert.equal(s.node('inferenceDot').dataset.state, 'idle');
  assert.equal(s.node('inferenceModelNames').children.some(option => option.value === 'suggested-plan-model'), true);
  s.node('inferenceModel').value = 'chosen-plan-model';
  await s.node('inferenceForm').emit('input');
  await s.node('planDisconnect').emit('click');
  assert.equal(s.node('planDisconnect').hidden, true);
  assert.equal(s.node('planLogin').hidden, false);
  assert.equal(s.node('inferenceModel').value, 'chosen-plan-model');
  assert.equal(s.node('speechModel').value, 'speech-draft');
  assert.equal(s.node('inferenceDot').dataset.state, 'idle');
  assert.equal(s.requests.some(request => request.url === '/api/settings' && request.body), false);
  assert.equal(s.requests.some(request => request.url.endsWith('/test')), false);
  for (const request of s.requests.filter(request => /\/(login|cancel|disconnect)$/.test(request.url))) assert.deepEqual(request.body, {});
});

test('chat learning signals render evidence without probability percentages', () => {
  const f = feedback({services: {decision: true, inference: false}});
  const signals = ['confidence', 'reasoning', 'engagement'].map(id => ({id, title: id, label: 'Not expressed', code: 'unclear', evidence: 'No explicit cue in the transcript.'}));
  assert.equal(f.instance.validSignals(signals), true);
  f.instance.evidence = {transcript: 'I tried adding.', signals};
  f.instance.renderSignals();
  const details = f.o.results.children[0].children[1];
  assert.equal(details.children[0].textContent, 'Evidence and original speech');
  assert.equal(details.children.some(node => node.textContent === 'No explicit cue in the transcript.'), true);
  assert.equal(f.o.results.children[0].children[0].children[0].children[1].children.length, 1);
});
test('a returning user can reconnect the same plan registration or start a different one', async () => {
  const account = '/api/connections/chatgpt';
  const status = {state: 'signed_out', canTest: false, registrations: [{id: 'saved-first', label: 'First account'},
    {id: 'saved-second', label: 'Second account'}]};
  const s = settingsEnvironment({}, {[account]: status, [account + '/login']: status});
  await new Promise(resolve => setImmediate(resolve));
  await s.node('useChatgptPlan').emit('click');
  await new Promise(resolve => setImmediate(resolve));
  assert.match(s.node('planAccountStatus').textContent, /Continue as First account/);
  await s.node('planLogin').emit('click');
  assert.deepEqual(s.requests.at(-1).body, {clientId: 'saved-first'});
  await s.node('planAlternatives').children[0].emit('click');
  assert.deepEqual(s.requests.at(-1).body, {clientId: 'saved-second'});
  await s.node('planAlternatives').children[1].emit('click');
  assert.deepEqual(s.requests.at(-1).body, {newAccount: true});
  assert.equal(s.node('inferenceDot').dataset.state, 'idle');
});

test('testing optional blank settings skips model and account calls', async () => {
  const s = settingsEnvironment();
  await new Promise(resolve => setImmediate(resolve));
  await s.node('testConnections').emit('click');
  assert.match(s.node('pageStatus').textContent, /No models are configured/);
  assert.equal(s.requests.some(r => r.url.endsWith('/test')), false);
  assert.equal(s.requests.some(r => r.url.includes('/connections/openai')), false);
  for (const section of ['inference', 'speech', 'decision']) assert.equal(s.node(section + 'Dot').dataset.state, 'idle');
});

for (const action of ['saveConfiguration', 'testConnections']) {
  test(`${action} reveals an invalid hidden tab before reporting its field`, async () => {
    const s = settingsEnvironment();
    await new Promise(resolve => setImmediate(resolve));
    s.node('speechForm').checkValidity = () => false;
    let reported = 0;
    s.node('speechForm').reportValidity = () => {
      reported++;
      assert.equal(s.node('speechPanel').hidden, false);
      return false;
    };
    await s.node(action).emit('click');
    assert.equal(reported, 1);
    assert.equal(s.node('speechTab').attributes['aria-selected'], 'true');
    assert.equal(s.requests.some(request => request.url.endsWith('/test') || request.url === '/api/settings' && request.body), false);
  });
}

test('connection tabs use arrow, Home, and End keys while retaining drafts', async () => {
  const s = settingsEnvironment();
  await new Promise(resolve => setImmediate(resolve));
  s.node('inferenceModel').value = 'tutor-draft';
  for (const [from, key, to] of [['inference', 'ArrowLeft', 'decision'], ['decision', 'ArrowRight', 'inference'],
    ['inference', 'End', 'decision'], ['decision', 'Home', 'inference'], ['inference', 'ArrowRight', 'speech']]) {
    const event = await s.node(from + 'Tab').emit('keydown', {key});
    assert.equal(event.defaultPrevented, true);
    assert.equal(s.node(to + 'Tab').tabIndex, 0);
    assert.equal(s.node(to + 'Panel').hidden, false);
  }
  assert.equal(s.node('inferenceModel').value, 'tutor-draft');
});

test('equivalent URL spelling preserves saved fallback addresses, protocol, and masked key', async () => {
  const bases = ['http://localhost:8000', 'http://localhost:8001'];
  const s = settingsEnvironment({decision: {bases, model: 'decision-model', protocol: 'systemone', keyConfigured: true}});
  await new Promise(resolve => setImmediate(resolve));
  s.node('decisionBases').value = '  http://localhost:8000///  ';
  s.node('decisionModel').value = '  revised-model  ';
  await s.node('decisionForm').emit('input');
  assert.match(s.node('decisionKey').placeholder, /Saved key/);
  await s.node('decisionForm').emit('submit');
  const write = s.requests.find(request => request.url === '/api/settings' && request.body).body.decision;
  assert.deepEqual(write.bases, bases);
  assert.equal(write.protocol, 'systemone');
  assert.equal(s.node('decisionBases').value, bases[0]);
  assert.equal(s.node('decisionModel').value, 'revised-model');
  assert.equal(s.saved().decision.keyConfigured, true);
});

for (const action of ['inferenceForm', 'saveConfiguration']) {
  test(`${action} saves the plan while retaining inactive API drafts until Load`, async () => {
    const s = settingsEnvironment({inference: {bases: ['http://localhost:8000'], model: 'saved-api',
      provider: 'api', effort: 'medium', keyConfigured: false}});
    await new Promise(resolve => setImmediate(resolve));
    s.node('inferenceBases').value = 'http://localhost:9000';
    s.node('inferenceModel').value = 'draft-api';
    s.node('inferenceKey').value = 'draft-api-key';
    await s.node('inferenceForm').emit('input');
    await s.node('useChatgptPlan').emit('click');
    s.node('inferenceModel').value = 'saved-plan';
    await s.node('inferenceForm').emit('input');
    await s.node(action).emit(action === 'inferenceForm' ? 'submit' : 'click');
    const write = s.requests.find(request => request.url === '/api/settings' && request.body).body.inference;
    assert.equal(write.provider, 'chatgpt');
    assert.equal(Object.hasOwn(write, 'apiKey'), false);
    assert.equal(Object.hasOwn(write, 'bases'), false);
    assert.equal(s.node('saveConfiguration').disabled, true);
    assert.equal((await s.window.emit('beforeunload')).defaultPrevented, true);
    s.confirmLoad = false;
    await s.node('loadConfiguration').emit('click');
    assert.equal(s.confirmations.length, 1);
    assert.equal(s.node('inferenceKey').value, 'draft-api-key');
    s.confirmLoad = true;
    await s.node('useCustomApi').emit('click');
    assert.equal(s.node('inferenceModel').value, 'draft-api');
    assert.equal(s.node('inferenceBases').value, 'http://localhost:9000');
    assert.equal(s.node('inferenceKey').value, 'draft-api-key');
    await s.node('loadConfiguration').emit('click');
    await s.node('useCustomApi').emit('click');
    assert.equal(s.node('inferenceModel').value, 'saved-api');
    assert.equal(s.node('inferenceBases').value, 'http://localhost:8000');
    assert.equal(s.node('inferenceKey').value, '');
  });
}

test('a changed account invalidates an in-flight tutor test and stale account reads stay hidden after switching', async () => {
  const account = '/api/connections/chatgpt';
  const signedIn = {state: 'signed_in', canTest: true, account: {id: 'first-account', label: 'First account'}};
  const replies = {[account]: signedIn};
  const s = settingsEnvironment({inference: {bases: [], model: 'plan-model', provider: 'chatgpt', keyConfigured: false}}, replies);
  await new Promise(resolve => setImmediate(resolve));
  let finishAccount, finishTest;
  replies[account] = () => new Promise(resolve => { finishAccount = resolve; });
  const polling = s.window.emit('focus');
  await new Promise(resolve => setImmediate(resolve));
  replies['/api/settings/inference/test'] = () => new Promise(resolve => { finishTest = resolve; });
  const testing = s.node('testInference').emit('click');
  finishAccount({state: 'signed_out', canTest: false});
  await polling;
  finishTest({ready: true, model: 'plan-model', message: 'Old account succeeded.', elapsedMs: 100});
  await testing;
  assert.equal(s.node('inferenceDot').dataset.state, 'idle');
  assert.doesNotMatch(s.node('inferenceResult').textContent, /Old account succeeded/);
  const oldPolling = s.window.emit('focus');
  await new Promise(resolve => setImmediate(resolve));
  await s.node('useCustomApi').emit('click');
  const apiPlaceholder = s.node('inferenceModel').placeholder;
  finishAccount(signedIn); await oldPolling;
  assert.equal(s.node('planAccountFields').hidden, true);
  assert.equal(s.node('inferenceModel').placeholder, apiPlaceholder);
  assert.equal(s.node('inferenceModel').attributes.list, undefined);
});

test('an inactive plan model draft also warns before discard without enabling Save All', async () => {
  const s = settingsEnvironment({inference: {bases: ['http://localhost:8000'], model: 'saved-api',
    provider: 'api', effort: 'medium', keyConfigured: false, modelByProvider: {api: 'saved-api', chatgpt: 'saved-plan'}}});
  await new Promise(resolve => setImmediate(resolve));
  await s.node('useChatgptPlan').emit('click');
  s.node('inferenceModel').value = 'draft-plan';
  await s.node('inferenceForm').emit('input');
  await s.node('useCustomApi').emit('click');
  assert.equal(s.node('saveConfiguration').disabled, true);
  assert.equal((await s.window.emit('beforeunload')).defaultPrevented, true);
  await s.node('loadConfiguration').emit('click');
  assert.equal(s.confirmations.length, 1);
  assert.equal((await s.window.emit('beforeunload')).defaultPrevented, false);
});

test('saving all settings does not forget the account behind a passed tutor test', async () => {
  const account = '/api/connections/chatgpt';
  const replies = {[account]: {state: 'signed_in', canTest: true, account: {id: 'first-account'}},
    '/api/settings/inference/test': {ready: true, model: 'draft-plan', message: 'Sample accepted.', elapsedMs: 100}};
  const s = settingsEnvironment({inference: {bases: [], model: 'saved-plan', provider: 'chatgpt', keyConfigured: false}}, replies);
  await new Promise(resolve => setImmediate(resolve));
  s.node('inferenceModel').value = 'draft-plan';
  await s.node('inferenceForm').emit('input');
  await s.node('testInference').emit('click');
  assert.equal(s.node('inferenceDot').dataset.state, 'ok');
  replies[account] = {state: 'signed_in', canTest: true, account: {id: 'different-account'}};
  await s.node('saveConfiguration').emit('click');
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(s.node('inferenceDot').dataset.state, 'idle');
});

test('Test All identifies incomplete optional roles and still tests a complete role', async () => {
  for (const partial of [{bases: ['http://localhost:8000'], model: ''}, {bases: [], model: 'draft-model'}]) {
    const s = settingsEnvironment({speech: {...partial, keyConfigured: false},
      decision: {bases: ['http://localhost:8001'], model: 'decision-model', keyConfigured: false, protocol: 'chat'}}, {
      '/api/settings/decision/test': {ready: true, model: 'decision-model', message: 'Sample accepted.', elapsedMs: 100}
    });
    await new Promise(resolve => setImmediate(resolve));
    await s.node('testConnections').emit('click');
    assert.equal(s.node('speechBadge').textContent, 'Incomplete');
    assert.equal(s.node('speechPanel').hidden, false);
    assert.equal(s.node('pageStatus').dataset.state, 'error');
    assert.match(s.node('pageStatus').textContent, /1 of 1 configured connections passed\. Complete the settings/);
    assert.match(s.node('speechResult').textContent, partial.model ? /Enter a URL/ : /Enter a model name/);
    assert.equal(s.requests.some(request => request.url === '/api/settings/speech/test'), false);
    await s.node('saveConfiguration').emit('click');
    assert.deepEqual(s.saved().speech.bases, partial.bases);
    assert.equal(s.saved().speech.model, partial.model);
  }
  const s = settingsEnvironment();
  await new Promise(resolve => setImmediate(resolve));
  await s.node('useChatgptPlan').emit('click');
  await s.node('testConnections').emit('click');
  assert.equal(s.node('inferenceBadge').textContent, 'Incomplete');
  assert.match(s.node('inferenceResult').textContent, /Choose a model name/);
  assert.doesNotMatch(s.node('pageStatus').textContent, /No models are configured/);
});

test('saved-key changes reset only tests using the masked key and rerunning binds the new key', async () => {
  let diskRevision = 'old-key';
  const replies = {
    '/api/settings/compare': (_body, result) => ({...result, keyRevisions: {speech: diskRevision}}),
    '/api/settings/speech/test': () => ({ready: true, model: 'speech-model', message: 'Sample accepted.', elapsedMs: 100, keyRevision: diskRevision})
  };
  const s = settingsEnvironment({speech: {bases: ['http://localhost:8000'], model: 'speech-model', keyConfigured: true, keyRevision: 'old-key'}}, replies);
  await new Promise(resolve => setImmediate(resolve));
  await s.node('testSpeech').emit('click');
  assert.equal(s.node('speechDot').dataset.state, 'ok');
  diskRevision = 'new-key';
  await s.window.emit('focus');
  assert.equal(s.node('speechDot').dataset.state, 'idle');
  assert.match(s.node('speechResult').textContent, /verify the saved API key/);
  await s.node('testSpeech').emit('click');
  await s.window.emit('focus');
  assert.equal(s.node('speechDot').dataset.state, 'ok');
  s.node('speechKey').value = 'explicit-draft-key';
  await s.node('speechForm').emit('input');
  await s.node('testSpeech').emit('click');
  diskRevision = 'unrelated-key';
  await s.window.emit('focus');
  assert.equal(s.node('speechDot').dataset.state, 'ok');
  s.node('speechKey').value = '';
  s.node('speechBases').value = 'http://localhost:9000';
  await s.node('speechForm').emit('input');
  await s.node('testSpeech').emit('click');
  diskRevision = 'another-unrelated-key';
  await s.window.emit('focus');
  assert.equal(s.node('speechDot').dataset.state, 'ok');
});

test('a failed reload retains every draft and failed startup can recover through Load Settings', async () => {
  const replies = {'/api/settings': {error: {message: 'Temporary settings error.'}}};
  const s = settingsEnvironment({}, replies);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(s.node('loadConfiguration').disabled, false);
  assert.equal(s.node('testConnections').disabled, true);
  delete replies['/api/settings'];
  await s.node('loadConfiguration').emit('click');
  s.node('speechModel').value = 'speech-draft';
  s.node('speechKey').value = 'key-draft';
  await s.node('speechForm').emit('input');
  replies['/api/settings/reload'] = {error: {message: 'Could not load saved settings.'}};
  await s.node('loadConfiguration').emit('click');
  assert.equal(s.node('speechModel').value, 'speech-draft');
  assert.equal(s.node('speechKey').value, 'key-draft');
  assert.equal(s.node('saveConfiguration').disabled, false);
  assert.equal(s.node('loadConfiguration').disabled, false);
  assert.match(s.node('pageStatus').textContent, /Could not load/);
});

test('a saved key changed during an in-flight test cannot leave a stale green dot', async () => {
  let diskRevision = 'first-key', finishTest;
  const replies = {
    '/api/settings/compare': (_body, result) => ({...result, keyRevisions: {speech: diskRevision}}),
    '/api/settings/speech/test': () => new Promise(resolve => { finishTest = resolve; })
  };
  const s = settingsEnvironment({speech: {bases: ['http://localhost:8000'], model: 'speech-model', keyConfigured: true, keyRevision: 'first-key'}}, replies);
  await new Promise(resolve => setImmediate(resolve));
  const testing = s.node('testSpeech').emit('click');
  diskRevision = 'second-key';
  await s.window.emit('focus');
  finishTest({ready: true, model: 'speech-model', message: 'Old key accepted.', elapsedMs: 100, keyRevision: 'first-key'});
  await testing;
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(s.node('speechDot').dataset.state, 'idle');
  assert.match(s.node('speechResult').textContent, /verify the saved API key/);
});
test('the shipped page loads the processed CN bank and permits blank connection fields', () => {
  const index = fs.readFileSync(path.join(directory, 'index.html'), 'utf8');
  const settings = fs.readFileSync(path.join(directory, 'settings.html'), 'utf8');
  assert.match(index, /<script src="\.\.\/cn-math-bank\/bank\.js"><\/script>/);
  assert.doesNotMatch(index, /<script src="amc-bank\.js"/);
  assert.doesNotMatch(settings, /\brequired\b/);
  assert.doesNotMatch(settings, /Use one provider|Advanced options|<select|<details|setupModes|singleConnection/);
  const inline = index.match(/<script>\s*([\s\S]*?)<\/script>/);
  assert.ok(inline, 'Practice bootstrap is present');
  new vm.Script(inline[1], {filename: 'index.html'});
  for (const match of settings.matchAll(/placeholder="(https?:\/\/[^\"]+)"/g)) assert.match(match[1], /^http:\/\/localhost:/);
});

for (const mode of ['file', 'backend without models', 'static HTTP']) {
  test(`full page supports browsing, answer checks, and solutions with ${mode}`, async () => {
    const requests = [], storage = new Map();
    const env = environment('practice-feedback.js', {location: {protocol: mode === 'file' ? 'file:' : 'http:'},
      localStorage: {getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value)},
      fetch: async url => {
        requests.push(url);
        if (mode === 'static HTTP') throw new TypeError('No API on a static server');
        assert.match(url, /^\/api\/status\/(decision|speech|inference)$/);
        return {ok: true, json: async () => ({configured: false, ready: false, label: 'Not configured'})};
      }
    });
    env.window.CN_MATH_BANK = {id: 'cn-math', label: 'Sample curriculum', questions: [{id: 'cn-sample',
      bank: 'cn-math', level: 'Primary', grade: 1, unit: 'Primary 1', batch: 'number', number: 1,
      topic: {label: 'Numbers'}, responseType: 'numeric', answer: '2', choices: {},
      question: 'What is 1 + 1?', solution: 'Add one to one.'}]};
    vm.runInContext(fs.readFileSync(path.join(directory, 'speech-input.js'), 'utf8'), env.context);
    const index = fs.readFileSync(path.join(directory, 'index.html'), 'utf8');
    vm.runInContext(index.match(/<script>\s*([\s\S]*?)<\/script>/)[1], env.context);
    await new Promise(resolve => setImmediate(resolve));
    await env.node('beginPractice').emit('click');
    assert.equal(env.node('poolDisplay').hidden, false);
    assert.equal(env.node('thoughtsCard').hidden, false);
    assert.equal(env.node('speechRecord').disabled, true);
    env.node('freeAnswer').value = '2';
    await env.node('freeAnswer').emit('input');
    await env.node('thoughtsSubmit').emit('click');
    await new Promise(resolve => setImmediate(resolve));
    assert.match(env.node('answerFeedback').textContent, /Correct\./);
    assert.match(env.node('reasoningFeedback').textContent, /Not checked/);
    assert.equal(env.node('submissionMark').dataset.result, 'review');
    const find = (node, className) => node.className === className ? node : node.children.map(child => find(child, className)).find(Boolean);
    await find(env.node('poolDisplay'), 'sol-btn').emit('click');
    assert.equal(env.node('solModal').hidden, false);
    assert.equal(env.node('solBody').children[0].children[0].textContent, 'Reference answer: 2');
    assert.equal(env.node('solBody').children[0].children[1].children[0].textContent, 'Add one to one.');
    assert.equal(requests.length, mode === 'file' ? 0 : 3);
  });
}
