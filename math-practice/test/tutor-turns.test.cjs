'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const answers = require('../answer-check.js');
const source = fs.readFileSync(path.join(__dirname, '../practice-feedback.js'), 'utf8');
const settle = () => new Promise(resolve => setImmediate(resolve));
const plain = value => JSON.parse(JSON.stringify(value));

class Element {
  constructor() { this.value = ''; this.textContent = ''; this.hidden = true; this.disabled = false; this.attributes = {}; this.dataset = {}; this.listeners = {}; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  setAttribute(name, value) { this.attributes[name] = value; }
  async click() { await this.listeners.click(); }
}
function harness(options = {}) {
  const nodes = new Map(), requests = [], graphs = [], saves = [], typeset = [];
  const node = id => { if (!nodes.has(id)) nodes.set(id, new Element()); return nodes.get(id); };
  const storage = options.storage || new Map();
  const current = {question: {id: 'square', bank: 'cn-math', responseType: 'numeric', answer: '9'},
    answer: '3', bank: 'cn-math', layer: 'ailleo', curriculumNodeId: null};
  const o = {question: () => current.question, answer: () => current.answer, bank: () => current.bank, layer: () => current.layer, curriculumNodeId: () => current.curriculumNodeId,
    draft: new Element(), note: new Element(), announce: new Element(),
    checkAnswer: answers.check, classifyAnswer: answers.classify,
    services: () => options.services || {decision: true, inference: true}, waitServices: async () => {},
    typeset: element => typeset.push(element), connection() {}, setRunning() {}, updated() {}, submitted() {},
    graphEvidence: value => graphs.push(plain(value)), save: () => saves.push(plain(instance.state()))};
  o.draft.value = 'Half of 6 is 3, so I added 3.';
  const context = vm.createContext({window: {MathPracticeAnswers: answers}, document: {getElementById: node},
    location: {protocol: 'http:'}, sessionStorage: {getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value)},
    AbortController, setTimeout, clearTimeout});
  vm.runInContext(source, context);
  const instance = new context.window.MathPracticeFeedback(o);
  instance.post = async (url, body) => {
    requests.push({url, body: plain(body)});
    return options.reply ? options.reply(url, body) : result(body, url === '/api/tutor');
  };
  return {instance, o, current, node, requests, graphs, saves, typeset, storage};
}
function result(body, tutor, fields = {}) {
  return {questionId: body.questionId, answer: body.answer, revisionId: body.turn.revisionId,
    answerCategory: 'wrong', answerCorrect: false, category: 'wrong',
    decisionConfigured: true, inferenceConfigured: true,
    ...(tutor ? {coach: 'You found half of 6. What constant appears when you expand \\( (x+3)^2 \\)?',
      hint: 'The constant term comes from multiplying 3 by itself.'} : {}),
    graphEvidence: {bank: body.bank, questionId: body.questionId, revisionId: body.turn.revisionId, source: tutor ? 'tutor' : 'assessment'}, ...fields};
}

test('wrong answer and thinking show coaching before the optional hint opens', async () => {
  const h = harness();
  await h.instance.submit(); await settle();
  assert.equal(h.node('coach').hidden, false);
  assert.match(h.node('coach').textContent, /What constant appears/);
  assert.equal(h.node('hintBody').hidden, true);
  assert.equal(h.node('hintBody').textContent, '');
  assert.equal(h.node('hintToggle').hidden, false);
  assert.equal(h.typeset.includes(h.node('coach')), true);
  assert.deepEqual(h.graphs.map(value => value.source), ['tutor']);
  assert.equal(h.instance.state().assistance, 'coach');
  assert.equal(h.instance.state().last.openedHint, null);
  assert.doesNotMatch(h.node('answerFeedback').textContent, /Check your final answer/);
});

test('required answer form preserves consistent coaching but corrects false full credit', async () => {
  const coach = 'You correctly identified one eighth. Write that value as a decimal.';
  for (const claimed of ['partial', 'correct']) {
    const h = harness({reply: (url, body) => result(body, url === '/api/tutor', {
      answerCategory: claimed, answerCorrect: claimed === 'correct' ? true : null,
      category: 'partial', ...(url === '/api/tutor' ? {coach, clarification: coach, hint: ''} : {})
    })});
    Object.assign(h.current.question, {responseType: 'numeric', answer: '0.125', answerForm: 'decimal'});
    h.current.answer = '1/8';
    h.o.draft.value = 'One of eight equal parts is one eighth of the whole.';
    await h.instance.submit(); await settle();
    assert.match(h.node('answerFeedback').textContent, /Partially correct/);
    if (claimed === 'partial') assert.equal(h.node('coach').textContent, coach);
    else assert.match(h.node('coach').textContent, /decimal numeral/);
    assert.equal(h.node('hintToggle').hidden, true);
    assert.equal(h.instance.state().last.coach, h.node('coach').textContent);
  }
});

test('a revision carries visible coaching and only the exact hint the student opened', async () => {
  const h = harness();
  await h.instance.submit(); await settle();
  const first = h.requests[0].body.turn.revisionId;
  const coach = h.node('coach').textContent;
  h.o.draft.value = 'I expanded the square but still think the constant is 3.';
  h.instance.revisionChanged();
  await h.instance.submit(); await settle();
  let request = h.requests[2].body;
  assert.equal(request.bank, 'cn-math');
  assert.equal(request.turn.action, 'revise');
  assert.equal(request.turn.assistance, 'coach');
  assert.equal(request.turn.previous.coach, coach);
  assert.equal(request.turn.previous.openedHint, null);
  assert.notEqual(request.turn.revisionId, first);
  assert.deepEqual(request.turn, h.requests[3].body.turn);
  for (let i = 0; i < 4; i++) await h.node('hintToggle').click();
  const hint = h.instance.hint;
  assert.equal(h.instance.state().last.openedHint, hint);
  assert.equal(h.instance.state().assistance, 'hint');
  assert.equal(h.graphs.length, 2);
  h.o.draft.value = 'The constant comes from 3 times 3.';
  h.instance.revisionChanged();
  await h.instance.submit(); await settle();
  request = h.requests[4].body;
  assert.equal(request.turn.assistance, 'hint');
  assert.equal(request.turn.previous.openedHint, hint);
});

test('opening or reopening a solution affects the next revision, not the frozen current turn', async () => {
  const h = harness();
  await h.instance.submit(); await settle();
  const first = plain(h.requests[0].body.turn);
  h.instance.solutionOpened(); h.instance.solutionOpened();
  assert.equal(h.instance.state().assistance, 'solution');
  assert.deepEqual(plain(h.instance.submitted.turn), first);
  h.o.draft.value = 'I now square the half coefficient.';
  await h.instance.submit(); await settle();
  assert.equal(h.requests[2].body.turn.assistance, 'solution');
  assert.equal(h.graphs.length, 2);
});

test('editing reasoning with the same answer rejects an in-flight assessment and its evidence', async () => {
  let finish;
  const h = harness({reply: (_url, body) => new Promise(resolve => { finish = () => resolve(result(body, false)); })});
  const pending = h.instance.submit(); await settle();
  h.o.draft.value = 'I have changed my reasoning.';
  h.instance.revisionChanged();
  finish(); await pending; await settle();
  assert.equal(h.requests.length, 1);
  assert.equal(h.graphs.length, 0);
  assert.match(h.node('reviewNote').textContent, /earlier try/);
  assert.equal(h.node('coach').hidden, true);
  assert.equal(h.node('hintToggle').disabled, true);
});

test('editing during tutor review rejects the late coach, hint and provisional graph', async () => {
  let finish;
  const h = harness({reply: (url, body) => url === '/api/tutor'
    ? new Promise(resolve => { finish = () => resolve(result(body, true)); }) : result(body, false)});
  await h.instance.submit(); await settle();
  h.o.draft.value = 'A different explanation for the same final answer.';
  h.instance.revisionChanged(); finish(); await settle();
  assert.equal(h.graphs.length, 0);
  assert.equal(h.node('coach').hidden, true);
  assert.equal(h.node('hintToggle').hidden, true);
});

test('retries reuse the revision, and a final result is recorded once', async () => {
  let fail = true;
  const h = harness({reply: (_url, body) => {
    if (fail) throw new TypeError('Offline');
    return result(body, false, {answerCategory: 'correct', answerCorrect: true, category: 'correct'});
  }});
  await h.instance.submit();
  const id = h.requests[0].body.turn.revisionId;
  fail = false;
  await h.instance.submit(); await settle();
  await h.instance.submit(); await settle();
  assert.deepEqual(h.requests.map(request => request.body.turn.revisionId), [id, id, id]);
  assert.equal(h.graphs.length, 1);
  assert.equal(h.requests.some(request => request.url === '/api/tutor'), false);
});

test('a failed tutor keeps one assessment observation and can replace it on retry', async () => {
  let fail = true;
  const h = harness({reply: (url, body) => {
    if (url === '/api/tutor' && fail) throw new TypeError('Offline');
    return result(body, url === '/api/tutor');
  }});
  await h.instance.submit(); await settle();
  assert.deepEqual(h.graphs.map(value => value.source), ['assessment']);
  fail = false;
  await h.node('tutorRetry').click(); await settle();
  assert.deepEqual(h.graphs.map(value => value.source), ['assessment', 'tutor']);
  assert.equal(h.requests[0].body.turn.revisionId, h.requests[2].body.turn.revisionId);
});

test('reload in the same tab retains help, while another session and legacy drafts are unknown', async () => {
  const h = harness();
  await h.instance.submit(); await settle();
  await h.node('hintToggle').click();
  const saved = plain(h.instance.state());
  const reloaded = harness({storage: h.storage});
  reloaded.instance.restoreTurn(saved, true);
  reloaded.o.draft.value = 'I multiplied the two constants.';
  await reloaded.instance.submit(); await settle();
  assert.equal(reloaded.requests[0].body.turn.assistance, 'hint');
  assert.equal(reloaded.requests[0].body.turn.previous.openedHint, h.instance.hint);
  for (const context of [saved, null, {last: null}]) {
    const other = harness();
    other.instance.restoreTurn(context, true);
    await other.instance.submit(); await settle();
    assert.equal(other.requests[0].body.turn.assistance, 'unknown');
    assert.equal(other.requests[0].body.turn.previous, null);
  }
});

test('same-tab rejudgment after reload retains its original revision and assistance', async () => {
  const h = harness();
  await h.instance.submit(); await settle();
  h.instance.solutionOpened();
  const reloaded = harness({storage: h.storage});
  reloaded.instance.restoreTurn(plain(h.instance.state()), true);
  await reloaded.instance.submit(); await settle();
  assert.deepEqual(reloaded.requests[0].body.turn, h.requests[0].body.turn);
  assert.equal(reloaded.instance.state().assistance, 'solution');
});

test('another item or bank never receives the previous learner context', async () => {
  const h = harness();
  await h.instance.submit(); await settle();
  const saved = plain(h.instance.state());
  for (const change of ['item', 'bank']) {
    const other = harness({storage: h.storage});
    if (change === 'item') other.current.question = {...other.current.question, id: 'other'};
    else other.current.bank = 'custom';
    other.instance.restoreTurn(saved, true);
    await other.instance.submit(); await settle();
    assert.equal(other.requests[0].body.turn.previous, null);
    assert.equal(other.requests[0].body.turn.assistance, 'unknown');
  }
});

test('graph records require an exact revision echo, even for an otherwise valid response', async () => {
  for (const revisionId of [undefined, 'old-revision']) {
    const h = harness({services: {decision: true, inference: false}, reply: (_url, body) => result(body, false, {revisionId})});
    await h.instance.submit(); await settle();
    assert.equal(h.graphs.length, 0);
  }
});

test('nested graph evidence must match the frozen bank, item and revision', async () => {
  for (const patch of [{bank: 'amc'}, {questionId: 'different'}, {revisionId: 'different'}]) {
    const h = harness({services: {decision: true, inference: false}, reply: (_url, body) => {
      const value = result(body, false);
      return {...value, graphEvidence: {...value.graphEvidence, ...patch}};
    }});
    await h.instance.submit(); await settle();
    assert.equal(h.graphs.length, 0);
  }
});

test('an explicitly opened solution resolves an unknown help history to solution exposure', async () => {
  const h = harness();
  h.instance.restoreTurn(null, true);
  h.instance.solutionOpened();
  await h.instance.submit(); await settle();
  assert.equal(h.requests[0].body.turn.assistance, 'solution');
});

test('blank work stays answer-only when Mathematics is not configured', async () => {
  const h = harness({services: {decision: true, inference: false},
    reply: (_url, body) => result(body, false, {category: 'cannot_judge', inferenceConfigured: false})});
  h.o.draft.value = '';
  await h.instance.submit(); await settle();
  assert.deepEqual(h.requests.map(request => request.url), ['/api/assessment']);
  assert.match(h.node('reasoningFeedback').textContent, /Add your thinking/);
  assert.equal(h.graphs.length, 1);
  assert.equal(h.node('coach').hidden, true);
});

test('a wrong selected answer without thinking gets one visible tutor cue and an opt-in hint', async () => {
  const coach = 'What calculation led you to this choice?';
  const hint = 'Start by writing the operation the question asks for.';
  const h = harness({reply: (url, body) => result(body, url === '/api/tutor', {
    category: url === '/api/tutor' ? 'partial' : 'cannot_judge',
    ...(url === '/api/tutor' ? {coach, hint} : {})})});
  h.current.question = {id: 'square', bank: 'cn-math', responseType: 'choice', answer: 'C',
    choices: {A: '3', B: '6', C: '9'}};
  h.current.answer = 'B'; h.o.draft.value = '   ';
  await h.instance.submit(); await settle();
  assert.deepEqual(h.requests.map(request => request.url), ['/api/assessment', '/api/tutor']);
  assert.equal(h.requests[1].body.answer, 'B');
  assert.equal(h.requests[1].body.thoughts, '');
  assert.equal(h.requests[1].body.turn.revisionId, h.requests[0].body.turn.revisionId);
  assert.match(h.node('answerFeedback').textContent, /Not quite yet/);
  assert.equal(h.node('reasoningFeedback').textContent, 'Thinking: Not provided yet.');
  assert.equal(h.node('coach').textContent, coach);
  assert.equal(h.node('coach').hidden, false);
  assert.equal(h.node('hintToggle').hidden, false);
  assert.equal(h.node('hintBody').hidden, true);
  assert.equal(h.node('hintBody').textContent, '');
  await h.node('hintToggle').click();
  assert.equal(h.node('hintBody').textContent, hint);
  assert.equal(h.requests.length, 2);
  assert.deepEqual(h.graphs.map(value => value.source), ['tutor']);
});

test('a correct answer without thinking still requests the missing reasoning once', async () => {
  const coach = 'Your answer matches. What calculation gives 9?';
  const h = harness({reply: (url, body) => result(body, url === '/api/tutor', {
    answerCategory: 'correct', answerCorrect: true,
    category: url === '/api/tutor' ? 'partial' : 'cannot_judge',
    ...(url === '/api/tutor' ? {coach, hint: ''} : {})})});
  h.current.answer = '9'; h.o.draft.value = '';
  await h.instance.submit(); await settle();
  assert.deepEqual(h.requests.map(request => request.url), ['/api/assessment', '/api/tutor']);
  assert.equal(h.requests[1].body.thoughts, '');
  assert.match(h.node('answerFeedback').textContent, /Correct\./);
  assert.equal(h.node('reasoningFeedback').textContent, 'Thinking: Not provided yet.');
  assert.equal(h.node('submissionMark').dataset.result, 'review');
  assert.equal(h.node('coach').textContent, coach);
  assert.equal(h.node('coach').hidden, false);
  assert.equal(h.node('hintToggle').hidden, true);
});

test('adding thinking while an answer-only review is pending rejects its late coaching', async () => {
  let release;
  const h = harness({reply: (url, body) => url === '/api/tutor'
    ? new Promise(resolve => { release = () => resolve(result(body, true, {category: 'partial'})); })
    : result(body, false, {category: 'cannot_judge'})});
  h.o.draft.value = '';
  await h.instance.submit(); await settle();
  assert.equal(h.node('tutorStatus').textContent, 'Reviewing your answer. You can keep working.');
  assert.doesNotMatch(h.node('reasoningFeedback').textContent, /Submit again|submit again/);
  h.o.draft.value = 'I am adding the calculation now.';
  h.instance.revisionChanged(); release(); await settle();
  assert.equal(h.node('coach').hidden, true);
  assert.equal(h.node('hintToggle').hidden, true);
  assert.equal(h.requests.length, 2);
  assert.equal(h.graphs.length, 0);
});

test('a failed answer-only review retains the missing-thinking state and offers a retry', async () => {
  const h = harness({reply: (url, body) => {
    if (url === '/api/tutor') throw new Error('Synthetic tutor unavailable.');
    return result(body, false, {category: 'cannot_judge'});
  }});
  h.o.draft.value = '';
  await h.instance.submit(); await settle();
  assert.equal(h.node('reasoningFeedback').textContent, 'Thinking: Not provided yet.');
  assert.equal(h.node('tutorStatus').textContent, 'Synthetic tutor unavailable.');
  assert.equal(h.node('tutorRetry').hidden, false);
  assert.equal(h.node('coach').hidden, true);
});

test('the local pilot can record a step when all optional models are turned off', async () => {
  const h = harness({services: {decision:false, inference:false, localEvidence:true},
    reply: (_url, body) => result(body, false, {category:'cannot_judge', decisionConfigured:false, inferenceConfigured:false})});
  await h.instance.submit(); await settle();
  assert.deepEqual(h.requests.map(request => request.url), ['/api/assessment']);
  assert.equal(h.graphs.length, 1);
  assert.match(h.node('reasoningFeedback').textContent, /Not checked/);
  assert.equal(h.node('coach').hidden, true);
});

test('Chinese coaching uses a character bound and model text is inserted as plain text', async () => {
  const h = harness({reply: (url, body) => result(body, url === '/api/tutor', url === '/api/tutor'
    ? {coach: '先展开平方，看看常数项。<img src=x> \\(3^2\\)', hint: '常数项来自两个常数相乘。'} : {})});
  await h.instance.submit(); await settle();
  assert.match(h.node('coach').textContent, /<img src=x>/);
  assert.equal(h.typeset.includes(h.node('coach')), true);
  const long = harness({reply: (url, body) => result(body, url === '/api/tutor', url === '/api/tutor'
    ? {coach: '常'.repeat(101), hint: ''} : {})});
  await long.instance.submit(); await settle();
  assert.equal(long.node('coach').hidden, true);
  assert.equal(long.node('tutorRetry').hidden, false);
  assert.deepEqual(long.graphs.map(value => value.source), ['assessment']);
});

test('the reviewed multiplication item shows its own solution and preserves the conflicting original', () => {
  const root = path.join(__dirname, '../..');
  const record = JSON.parse(fs.readFileSync(path.join(root, 'cn-math-bank/questions/cnm_p167_q1.json'), 'utf8'));
  const source = fs.readFileSync(path.join(root, 'cn-math-bank/bank.js'), 'utf8');
  const browser = JSON.parse(source.split('window.CN_MATH_BANK = ')[1].trim().replace(/;$/, ''));
  const item = browser.questions.find(value => value.id === record.ID);
  assert.equal(item.solution, 'Multiplying 1 by 3 gives 3.');
  assert.equal(item.solution, record.Solution);
  assert.equal(item.solutionSource, record.Meta.SolutionSource);
  assert.match(item.solutionSource, /not teacher reviewed/);
  assert.equal(record.Meta.Original.explanation, '1/2 的分子分母都乘 3，新的分子是 3。');
  assert.match(record.Meta.SolutionStatus, /displayed multiplication task/);
});


test('changing the path freezes a new revision and preserves assistance history', async () => {
  const h = harness();
  await h.instance.submit(); await settle();
  const previous = h.requests[0].body.turn.revisionId;
  const coach = h.node('coach').textContent;
  h.current.layer = 'US'; h.instance.revisionChanged();
  assert.equal(h.instance.edited(), true);
  await h.instance.submit(); await settle();
  assert.equal(h.requests[2].body.curriculumLayer, 'US');
  assert.equal(h.requests[3].body.curriculumLayer, 'US');
  assert.notEqual(h.requests[2].body.turn.revisionId, previous);
  assert.equal(h.requests[2].body.turn.previous.coach, coach);
  assert.equal(h.requests[2].body.turn.assistance, 'coach');
});

test('a path change rejects an outstanding reply even if the path switches back', async () => {
  let release;
  const h = harness({reply: (url, body) => new Promise(resolve => { release = () => resolve(result(body, false)); })});
  const pending = h.instance.submit(); await settle();
  h.current.layer = 'CN'; h.instance.revisionChanged();
  h.current.layer = 'ailleo'; h.instance.revisionChanged();
  release(); await pending; await settle();
  assert.equal(h.graphs.length, 0);
  assert.equal(h.requests.length, 1);
  assert.equal(h.node('coach').hidden, true);
});


test('a different standard within one path gets its own frozen revision', async () => {
  const h = harness(); h.current.layer = 'US'; h.current.curriculumNodeId = 'standard-a';
  await h.instance.submit(); await settle();
  const revision = h.requests[0].body.turn.revisionId;
  const coach = h.node('coach').textContent;
  assert.equal(h.requests[0].body.curriculumNodeId, 'standard-a');
  h.current.curriculumNodeId = 'standard-b'; h.instance.revisionChanged();
  assert.equal(h.instance.edited(), true);
  await h.instance.submit(); await settle();
  assert.equal(h.requests[2].body.curriculumNodeId, 'standard-b');
  assert.equal(h.requests[3].body.curriculumNodeId, 'standard-b');
  assert.notEqual(h.requests[2].body.turn.revisionId, revision);
  assert.equal(h.requests[2].body.turn.previous.coach, coach);
  assert.equal(h.requests[2].body.turn.assistance, 'coach');
});

test('a same-layer standard change cancels an outstanding assessment reply', async () => {
  let release;
  const h = harness({reply: (url, body) => new Promise(resolve => { release = () => resolve(result(body, false)); })});
  h.current.layer = 'US'; h.current.curriculumNodeId = 'standard-a';
  const pending = h.instance.submit(); await settle();
  h.current.curriculumNodeId = 'standard-b'; h.instance.revisionChanged();
  release(); await pending; await settle();
  assert.equal(h.graphs.length, 0);
  assert.equal(h.requests.length, 1);
});

for (const patch of [{curriculumLayer: 'CN'}, {curriculumNodeId: 'other-standard'}]) {
  test('an assessment echo for a different curriculum selection cannot replace current feedback: ' + JSON.stringify(patch), async () => {
    const h = harness({reply: (_url, body) => result(body, false, {...patch,
      category: 'correct', answerCategory: 'correct', answerCorrect: true})});
    h.current.layer = 'US'; h.current.curriculumNodeId = '4.NF.4';
    await h.instance.submit(); await settle();
    assert.equal(h.instance.mathState, 'error');
    assert.match(h.o.note.textContent, /different submission/);
    assert.doesNotMatch(h.node('answerFeedback').textContent, /Correct\./);
    assert.equal(h.graphs.length, 0);
  });

  test('a tutor echo for a different curriculum selection cannot replace current coaching: ' + JSON.stringify(patch), async () => {
    const h = harness({reply: (url, body) => result(body, url === '/api/tutor', url === '/api/tutor' ? patch : {})});
    h.current.layer = 'US'; h.current.curriculumNodeId = '4.NF.4';
    await h.instance.submit(); await settle();
    assert.equal(h.node('coach').hidden, true);
    assert.equal(h.node('hintToggle').hidden, true);
    assert.equal(h.node('tutorRetry').hidden, false);
    assert.match(h.node('tutorStatus').textContent, /different submission/);
    assert.equal(h.graphs.some(row => row.source === 'tutor'), false);
  });
}
