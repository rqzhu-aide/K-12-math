/* Run with the shared Node installation: node --test scripts/test_hosted_runtime.js */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const app = path.join(__dirname, '..', 'math-practice');
const source = fs.readFileSync(path.join(app, 'index.html'), 'utf8');
const transportSource = fs.readFileSync(path.join(app, 'hosted-data.js'), 'utf8');
const clone = value => JSON.parse(JSON.stringify(value));
const response = value => ({ok: true, json: async () => value});
function transport(fetch) {
  const window = {MATH_PRACTICE_HOSTED: {catalogs: ['../data/catalogs/cn-math.json', '../data/catalogs/amc.json'],
    browse: {ailleo: '../data/paths/ailleo.json', CN: '../data/paths/CN.json', US: '../data/paths/US.json'}}};
  vm.runInNewContext(transportSource, {window, fetch, URL,
    document: {baseURI: 'https://example.test/K-12-math/math-practice/'}, location: {origin: 'https://example.test'}});
  return window.MathPracticeHosted;
}
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return {promise, resolve, reject};
}
function selection() {
  const requests = [], rendered = [];
  const context = {
    hosted: true, questionLoadSerial: 0, selected: null,
    pool: {hint: {textContent: '', appendChild(child) { this.retry = child; }}},
    window: {MathPracticeHosted: {question(q) {
      const request = deferred(); requests.push({id: q.id, ...request}); return request.promise;
    }}},
    currentQ() { return context.selected; },
    clearQuestion() { context.questionLoadSerial += 1; },
    renderQuestion(q) { rendered.push(q.id); },
    el() { return {addEventListener(name, action) { this[name] = action; }}; }
  };
  const implementation = source.match(/  function loadQuestion\(\) \{[\s\S]*?(?=\n  function initPool\()/)[0];
  vm.runInNewContext(implementation, context);
  return {context, requests, rendered, choose(q) { context.selected = q; return context.loadQuestion(); }};
}

test('the application inline JavaScript parses', () => {
  for (const script of source.matchAll(/<script>([\s\S]*?)<\/script>/g)) new vm.Script(script[1]);
});

test('an optional literal answer example follows the active answer control', () => {
  function element(tagName, className, textContent) {
    return {tagName, className, textContent, children: [], hidden: true, value: '', attrs: {},
      setAttribute(name, value) { this.attrs[name] = value; },
      removeAttribute(name) { delete this.attrs[name]; },
      appendChild(child) { this.insertBefore(child, null); },
      insertBefore(child, reference) {
        this.children.splice(reference ? this.children.indexOf(reference) : this.children.length, 0, child);
        child.parentNode = this;
        child.remove = () => this.children.splice(this.children.indexOf(child), 1);
      }};
  }
  const freeAnswer = element('input'), openAnswer = element('textarea'), answerOpts = element('div');
  const writtenAnswer = element('div'), writtenAnswerCaption = element('div'), choices = element('div');
  writtenAnswer.appendChild(freeAnswer);
  writtenAnswer.appendChild(openAnswer);
  choices.appendChild(answerOpts);
  const notes = () => [...writtenAnswerCaption.children, ...choices.children].filter(node => node.id === 'answerExample');
  const controls = {freeAnswer, openAnswer, writtenAnswerCaption};
  const context = {els: {answerOpts}, $(id) { return controls[id] || notes()[0]; }, el: element,
    document: {createTextNode: textContent => ({textContent})}};
  const implementation = source.match(/  function answerExampleText\(q\) \{[\s\S]*?(?=\n  function buildAnswerButtons\()/)[0];
  vm.runInNewContext(implementation, context);

  for (const [control, parent, sample] of [[freeAnswer, writtenAnswerCaption, '5, 4'],
    [openAnswer, writtenAnswerCaption, '<literal>'], [answerOpts, choices, 'A, C']]) {
    for (const item of [freeAnswer, openAnswer, answerOpts]) item.hidden = item !== control;
    context.renderAnswerExample({answerExample: sample});
    const [note] = notes();
    assert.equal(notes().length, 1);
    assert.equal(parent.children[0], note);
    assert.equal(note.children[0].textContent, 'Example format');
    assert.equal(note.children[2].tagName, 'samp');
    assert.equal(note.children[2].textContent, sample);
    for (const item of [freeAnswer, openAnswer, answerOpts]) {
      assert.equal(item.attrs['aria-describedby'], item === control ? 'answerExample' : undefined);
      assert.equal(item.value, '');
    }
  }
  for (const missing of [{answerExample: '  '}, {answerExample: 7}, {}, null]) {
    context.renderAnswerExample(missing);
    assert.deepEqual(notes(), []);
    assert.equal(answerOpts.attrs['aria-describedby'], undefined);
  }
});

test('hosted startup fetches catalogs only and selected question preserves the full projection', async () => {
  const calls = [];
  const full = {id: 'item', question: 'Enter the number of groups and the number left over.', answerExample: '5, 4',
    acceptedResponses: ['3, 2'], responseType: 'numeric',
    solutionMethods: [{id: 'count', explanation: 'Count the full groups first.'}],
    provenance: {license: 'CC-BY-NC-SA-4.0'}, knowledgeGraph: {gradingStatus: 'disputed', gradingNote: 'Study only.'}};
  const runtime = transport(async (url, options) => {
    calls.push({url, options}); return response(url.includes('/questions/') ? full : {id: 'catalog', questions: []});
  });
  await runtime.ready;
  assert.equal(calls.length, 2);
  assert.ok(calls.every(call => call.url.includes('/data/catalogs/')));
  const stub = {id: 'item', questionURL: '../data/questions/amc/item.json'};
  assert.deepEqual(clone(await runtime.question(stub)), full);
  await runtime.question(stub);
  assert.equal(calls.length, 3);
  assert.equal(calls[2].url, 'https://example.test/K-12-math/data/questions/amc/item.json');
  assert.ok(calls.every(call => call.options.credentials === 'omit' && call.options.referrerPolicy === 'no-referrer'));
  assert.ok(calls.every(call => !call.options.body && !call.url.includes('/api/')));
});

test('each curriculum uses static browse data and practice pages retain every linked question', async () => {
  const calls = [], candidates = Array.from({length: 67}, (_, i) => ({questionId: 'q' + i}));
  const runtime = transport(async url => {
    calls.push(url);
    return response(url.includes('/practice/') ? {status: 'partial', candidates} : {nodes: []});
  });
  await runtime.ready;
  await Promise.all(['ailleo', 'CN', 'US'].map(layer => runtime.browse(layer)));
  const node = {practiceURL: '../data/practice/US/node.json'};
  const pages = await Promise.all([0, 30, 60].map(offset => runtime.practice('US', node, offset)));
  assert.deepEqual(pages.map(page => page.candidates.length), [30, 30, 7]);
  assert.deepEqual(pages.map(page => page.nextOffset), [30, 60, null]);
  assert.ok(pages.every(page => page.total === 67 && page.status === 'partial'));
  assert.deepEqual(clone(pages.flatMap(page => page.candidates)), candidates);
  assert.equal(calls.filter(url => url.includes('/practice/')).length, 1);
});

test('a failed question download can be retried', async () => {
  let failed = true;
  const runtime = transport(async url => {
    if (!url.includes('/questions/')) return response({questions: []});
    if (failed) { failed = false; return {ok: false}; }
    return response({id: 'item', question: 'Loaded on retry.'});
  });
  await runtime.ready;
  const stub = {id: 'item', questionURL: '../data/questions/amc/item.json'};
  await assert.rejects(runtime.question(stub), /could not load/);
  assert.equal((await runtime.question(stub)).question, 'Loaded on retry.');
});

test('hosted feedback and speech cannot use private services even with saved connection state', async () => {
  let requests = 0;
  const window = {MATH_PRACTICE_HOSTED: {}, MathPracticeAnswers: {}};
  const context = {window, fetch() { requests += 1; }};
  vm.runInNewContext(fs.readFileSync(path.join(app, 'practice-feedback.js'), 'utf8'), context);
  vm.runInNewContext(fs.readFileSync(path.join(app, 'speech-input.js'), 'utf8'), context);
  const feedback = Object.create(window.MathPracticeFeedback.prototype);
  feedback.o = {services: () => ({decision: true, inference: true, localEvidence: true})};
  feedback.serviceOverrides = {decision: true, inference: true};
  assert.deepEqual(clone(feedback.services()), {decision: false, inference: false, localEvidence: false});
  await assert.rejects(feedback.post('/api/assessment', {thoughts: 'Private student work'}), /local app/);
  const speech = Object.create(window.MathPracticeSpeech.prototype);
  speech.options = {isConfigured: () => true};
  assert.equal(speech.configured(), false);
  assert.equal(requests, 0);
});

test('switching questions while downloads overlap only displays the latest selection', async () => {
  const {choose, requests, rendered} = selection();
  const a = {id: 'a'}, b = {id: 'b'};
  const first = choose(a), second = choose(b);
  requests[1].resolve({id: 'b', question: 'Second question'}); await second;
  requests[0].resolve({id: 'a', question: 'First question'}); assert.equal(await first, undefined);
  assert.deepEqual(rendered, ['b']);
  assert.equal(b.question, 'Second question');
  assert.equal(a.question, undefined);
});

test('clearing a selection prevents an in-flight question from appearing', async () => {
  const {choose, context, requests, rendered} = selection();
  const loading = choose({id: 'a'});
  context.selected = null; await context.loadQuestion();
  requests[0].resolve({id: 'a', question: 'Now stale'}); assert.equal(await loading, undefined);
  assert.deepEqual(rendered, []);
});

test('the visible retry action reloads the selected question and reuses it after success', async () => {
  const {choose, context, requests, rendered} = selection();
  const stub = {id: 'a'};
  const failed = choose(stub); requests[0].reject(new Error('Connection interrupted.')); await failed;
  assert.match(context.pool.hint.textContent, /Connection interrupted/);
  const retry = context.pool.hint.retry.click();
  requests[1].resolve({id: 'a', question: 'Recovered'}); await retry;
  await choose(stub);
  assert.deepEqual(rendered, ['a', 'a']);
  assert.equal(requests.length, 2);
});
