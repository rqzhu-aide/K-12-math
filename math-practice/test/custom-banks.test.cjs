'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const directory = path.resolve(__dirname, '..');
const index = fs.readFileSync(path.join(directory, 'index.html'), 'utf8');
const bootstrap = index.match(/<script>\s*([\s\S]*?)<\/script>/)[1];

class Element {
  constructor(tag = 'div') {
    this.tagName = tag.toUpperCase(); this._value = ''; this._text = ''; this.hidden = true;
    this.disabled = false; this.dataset = {}; this.attributes = {}; this.listeners = {};
    this.children = []; this.style = {};
    const classes = new Set();
    this.classList = {add: (...values) => values.forEach(value => classes.add(value)),
      remove: value => classes.delete(value), toggle: (value, active) => active ? classes.add(value) : classes.delete(value)};
  }
  get childNodes() { return this.children; }
  get value() { return this._value; }
  set value(value) { this._value = String(value); }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
  set textContent(value) { this._text = String(value); this.children = []; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  setAttribute(name, value) { this.attributes[name] = value; }
  removeAttribute(name) { delete this.attributes[name]; }
  appendChild(child) { this.children.push(child); child.parentElement = this; return child; }
  replaceChildren(...children) { this._text = ''; this.children = []; children.forEach(child => this.appendChild(child)); }
  focus() {}
  scrollIntoView() {}
  querySelectorAll() { return []; }
  async emit(name) { if (this.listeners[name]) await this.listeners[name]({target: this, preventDefault() {}}); }
}
function question(id, fields = {}) {
  return {id, bank: 'garden_math', level: 'Primary', grade: 2, unit: 'Grade 2', batch: 'fractions', number: 1,
    topic: {id: 'fractions', label: 'Fractions'}, responseType: 'numeric', answer: '0.5', choices: {},
    question: 'What is one half as a decimal?', solution: 'One half equals five tenths.', ...fields};
}
function customBank(fields = {}) {
  return {id: 'garden_math', label: 'Garden mathematics', figuresBase: '../custom-banks/garden_math/figures/',
    sourceURL: 'https://example.org/garden-math', license: 'CC0-1.0', attribution: 'Written by <em>our team</em>',
    questions: [question('garden_math_q1'), question('garden_math_q2', {number: 2, responseType: 'choice',
      question: 'Which is one half?', choices: {A: 'One third', B: 'Two quarters'}, answer: 'B'}),
    question('garden_math_shape', {batch: 'shapes', topic: {id: 'shapes', label: 'Shapes'}}),
    question('garden_math_grade4', {grade: 4, unit: 'Grade 4'})], ...fields};
}
function amcBank() {
  const sample = {bank: 'amc', level: 'AMC 8', year: 2026, batch: 'NA', number: 1,
    responseType: 'choice', question: 'What is 2 + 2?', choices: {A: '2', B: '4'}, answer: 'B',
    solution: 'Adding two and two gives four.', solutionSource: 'Adapted from MAA official solutions',
    sourceURL: 'https://live.poshenloh.com/past-contests/amc8/2026/1'};
  return {id: 'amc', label: 'AMC contests', figuresBase: '../amc-bank/figures/', questions: [
    {id: 'amc8_2026_1', ...sample, officialSolution: {url: '../amc-bank/official-solutions/AMC8_2023_Solutions.pdf', page: 2}},
    {id: 'amc8_2026_2', ...sample, number: 2, solution: '', solutionSource: ''}]};
}
function environment(customBanks, amc, options = {}) {
  const elements = new Map(), storage = new Map(), requests = [], root = new Element();
  const node = id => {
    if (!elements.has(id)) { const value = new Element(); root.appendChild(value); elements.set(id, value); }
    return elements.get(id);
  };
  const text = value => Object.assign(new Element(), {textContent: value, nodeType: 3});
  node('sourceNotice').replaceChildren(text('English machine translations of AI-generated questions from '),
    Object.assign(new Element('a'), {textContent: 'cn-math-taxonomy', href: 'https://github.com/xiaoyang111222/cn-math-taxonomy'}),
    text(', adapted under CC BY-NC 4.0. Not teacher reviewed.'));
  const cnNotice = node('sourceNotice').textContent;
  const window = {MathPracticeAnswers: require('../answer-check.js'), addEventListener() {},
    CN_MATH_BANK: {id: 'cn-math', label: 'Chinese curriculum (English)', questions: [question('cn-sample', {
      bank: 'cn-math', grade: 1, unit: 'Grade 1', batch: 'numbers', topic: {id: 'numbers', label: 'Numbers'}})]}};
  if (customBanks !== undefined) window.CUSTOM_MATH_BANKS = customBanks;
  if (amc) window.AMC_BANK = amc;
  const context = vm.createContext({window, document: {getElementById: node, addEventListener() {},
    body: new Element(), createElement: tag => new Element(tag), createTextNode: text},
    location: {protocol: options.paths ? 'http:' : 'file:'}, localStorage: {getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value)},
    URL, AbortController, setTimeout, clearTimeout, setInterval, clearInterval,
    fetch: async (url, request) => { requests.push({url, request}); if (options.fetch) return options.fetch(url, request); throw new Error('Practice must not need a network request'); }});
  for (const file of ['speech-input.js', 'practice-feedback.js'].concat(options.paths ? ['curriculum-path.js'] : [])) {
    vm.runInContext(fs.readFileSync(path.join(directory, file), 'utf8'), context, {filename: file});
  }
  vm.runInContext(bootstrap, context, {filename: 'index.html'});
  return {node, storage, cnNotice, requests};
}
async function select(env, id, value) { env.node(id).value = value; await env.node(id).emit('change'); }
function options(node) { return node.children.map(option => [option.value, option.textContent]); }
function find(node, className) { return node.className === className ? node : node.children.map(child => find(child, className)).find(Boolean); }

test('the optional custom bundle loads before practice starts', () => {
  const custom = index.indexOf('<script src="../custom-banks/banks.js"></script>');
  assert.ok(custom > 0);
  assert.ok(custom < index.indexOf('<script>'));
});

test('the AMC snapshot loads before practice starts and source credits stay visible', () => {
  const amc = index.indexOf('<script src="../amc-bank/bank.js"></script>');
  assert.ok(amc > 0);
  assert.ok(amc < index.indexOf('<script>'));
  const footer = index.match(/<footer>[\s\S]*?<\/footer>/)[0];
  assert.match(footer, /href="https:\/\/maa\.org\/student-programs\/amc\/"[^>]*>Mathematical Association of America \(MAA\)<\/a>/);
  assert.match(footer, /href="https:\/\/creativecommons\.org\/licenses\/by-nc-sa\/4\.0\/"/);
  assert.match(footer, /href="https:\/\/github\.com\/xiaoyang111222\/cn-math-taxonomy"/);
  assert.match(footer, /href="https:\/\/creativecommons\.org\/licenses\/by-nc\/4\.0\/"/);
  assert.match(footer, /Developed by Ruoqing Zhu/);
  assert.match(footer, /Original app:/);
});

test('AMC navigation, answer checks, solution provenance, and CN return work without models', async () => {
  const env = environment([], amcBank());
  assert.deepEqual(options(env.node('selBank')), [
    ['cn-math', 'Chinese curriculum (English)'], ['amc', 'AMC contests']]);
  assert.equal(env.node('selBank').value, 'cn-math');
  await select(env, 'selBank', 'amc');
  assert.equal(env.node('poolSelectors').dataset.navigation, 'contest');
  assert.equal(env.node('yearLabel').textContent, 'Year');
  assert.equal(env.node('batchLabel').textContent, 'Batch');
  assert.equal(env.node('poolCount').textContent, '2 problems banked');
  assert.equal(env.node('sourceNotice').hidden, false);
  assert.match(env.node('sourceNotice').textContent, /AMC questions by Mathematical Association of America/);
  assert.match(env.node('sourceNotice').textContent, /CC BY-NC-SA 4\.0/);
  assert.match(env.node('sourceNotice').textContent, /Formatting and selected corrections applied\. No MAA endorsement\./);
  assert.deepEqual(env.node('sourceNotice').children.filter(child => child.tagName === 'A').map(link => link.href), [
    'https://maa.org/student-programs/amc/',
    'https://creativecommons.org/licenses/by-nc-sa/4.0/',
    'https://github.com/rqzhu-aide/math-practice/blob/main/amc-bank/NOTICE.md']);
  await select(env, 'selYear', 2026);
  assert.equal(env.node('selBatch').value, 'NA');
  assert.equal(env.node('selBatch').disabled, true);
  await select(env, 'selNum', 1);
  assert.equal(env.node('pickerTitle').textContent, 'AMC 8 2026 · Problem 1');
  const choice = env.node('answerOpts').children.find(button => button.dataset.answer === 'B');
  await choice.emit('click');
  await env.node('thoughtsSubmit').emit('click');
  assert.match(env.node('answerFeedback').textContent, /Correct\./);
  await find(env.node('poolDisplay'), 'sol-btn').emit('click');
  assert.match(env.node('solBody').textContent, /Adding two and two gives four\./);
  assert.match(env.node('solBody').textContent, /Adapted by Math Practice from MAA official solutions\./);
  const officialLink = find(env.node('solBody'), 'pool-hint').children.find(child => child.tagName === 'A');
  assert.equal(officialLink.href, '../amc-bank/official-solutions/AMC8_2023_Solutions.pdf#page=2');
  assert.doesNotMatch(env.node('solBody').textContent, /LIVE by Po-Shen Loh/);
  await env.node('solClose').emit('click');
  await env.node('nextProblem').emit('click');
  await find(env.node('poolDisplay'), 'sol-btn').emit('click');
  assert.match(env.node('solBody').textContent, /Correct answer: \(B\)/);
  assert.match(env.node('solBody').textContent, /A worked solution for this problem is not included\./);
  assert.doesNotMatch(env.node('solBody').textContent, /LIVE|source page|Solution source:|Which idea made this solution work/);
  await env.node('solClose').emit('click');
  await select(env, 'selBank', 'cn-math');
  assert.equal(env.node('sourceNotice').textContent, env.cnNotice);
  assert.equal(env.node('yearLabel').textContent, 'Grade / unit');
});

test('disputed AMC solutions retain the historical key and explain why the problem is not graded', async () => {
  const amc = amcBank();
  const gradingNote = 'The printed choices do not provide a unique correct answer.';
  amc.questions = [{...amc.questions[1], gradingStatus: 'disputed', gradingNote}];
  const env = environment([], amc);
  await select(env, 'selBank', 'amc');
  await env.node('beginPractice').emit('click');
  await find(env.node('poolDisplay'), 'sol-btn').emit('click');
  assert.match(env.node('solBody').textContent, /Not graded\. Historical printed key: \(B\)\./);
  assert.ok(env.node('solBody').textContent.includes(gradingNote));
  assert.match(env.node('solBody').textContent, /A worked solution for this problem is not included\./);
  assert.doesNotMatch(env.node('solBody').textContent, /Correct answer:|See the explanation below/);
});

  for (const booklet of ['AMC8_2023_Solutions.pdf', 'AMC8_2022_Solutions.pdf',
    'AMC8_2020_Solutions.pdf', 'AMC8_2019_Solutions.pdf', 'AMC8_2018_Solutions.pdf',
    'AMC10A_2022_Solutions.pdf', 'AMC10A_2021_Spring_Solutions.pdf', 'AMC10A_2021_Fall_Solutions.pdf']) {
  test(`AMC questions open the bundled official MAA booklet ${booklet}`, async () => {
    const amc = amcBank();
    const url = '../amc-bank/official-solutions/' + booklet;
    amc.questions = [{...amc.questions[1], officialSolution: {url}}];
    const env = environment([], amc);
    await select(env, 'selBank', 'amc');
    await env.node('beginPractice').emit('click');
    await find(env.node('poolDisplay'), 'sol-btn').emit('click');
    assert.match(env.node('solBody').textContent, /Correct answer: \(B\)/);
    assert.match(env.node('solBody').textContent, /Official MAA solutions are available in the original booklet\./);
    const link = find(env.node('solBody'), 'pool-hint').children.find(child => child.tagName === 'A');
    assert.equal(link.href, url);
    assert.equal(link.textContent, 'Read official MAA solutions (PDF)');
    assert.equal(link.target, '_blank');
    assert.equal(link.rel, 'noopener noreferrer');
    assert.doesNotMatch(env.node('solBody').textContent, /not included|LIVE by Po-Shen Loh|Which idea made/);
  });
}

test('unrecognized official booklet metadata shows an honest unavailable notice without a third-party solution link', async () => {
  for (const url of ['javascript:alert(1)', '../amc-bank/official-solutions/unknown.pdf', 'https://example.org/solutions.pdf']) {
    const amc = amcBank();
    amc.questions = [{...amc.questions[1], officialSolution: {url}}];
    const env = environment([], amc);
    await select(env, 'selBank', 'amc');
    await env.node('beginPractice').emit('click');
    await find(env.node('poolDisplay'), 'sol-btn').emit('click');
    assert.match(env.node('solBody').textContent, /A worked solution for this problem is not included\./);
    assert.doesNotMatch(env.node('solBody').textContent, /Official MAA solutions|Read official/);
    assert.doesNotMatch(env.node('solBody').textContent, /LIVE|source page/);
  }
});

for (const customBanks of [undefined, []]) {
  test(`CN practice remains available with ${customBanks ? 'an empty' : 'a missing'} custom bundle`, async () => {
    const env = environment(customBanks);
    assert.deepEqual(options(env.node('selBank')), [['cn-math', 'Chinese curriculum (English)']]);
    assert.equal(env.node('poolCount').textContent, '1 English questions');
    assert.equal(env.node('yearLabel').textContent, 'Grade / unit');
    assert.equal(env.node('batchLabel').textContent, 'Topic');
    assert.equal(env.node('sourceNotice').textContent, env.cnNotice);
    assert.equal(env.node('sourceNotice').hidden, false);
    await env.node('beginPractice').emit('click');
    assert.equal(env.node('pickerTitle').textContent, 'Grade 1 · Numbers · Problem 1');
    assert.equal(env.node('poolDisplay').hidden, false);
  });
}

test('custom banks use grade and topic controls and safely display their own attribution', async () => {
  const env = environment([customBank()]);
  await select(env, 'selBank', 'garden_math');
  assert.equal(env.node('poolCount').textContent, '4 questions');
  assert.equal(env.node('yearLabel').textContent, 'Grade / unit');
  assert.equal(env.node('batchLabel').textContent, 'Topic');
  assert.equal(env.node('poolSelectors').dataset.navigation, 'curriculum');
  assert.deepEqual(options(env.node('selYear')), [['', 'Choose grade / unit'], ['2', 'Grade 2'], ['4', 'Grade 4']]);
  assert.doesNotMatch(env.node('poolHint').textContent, /AMC/);
  assert.equal(env.node('sourceNotice').textContent,
    'Written by <em>our team</em> · Source: Garden mathematics · License: CC0-1.0');
  assert.equal(env.node('sourceNotice').children.filter(child => child.tagName === 'A').length, 1);
  const source = env.node('sourceNotice').children.find(child => child.tagName === 'A');
  assert.equal(source.href, 'https://example.org/garden-math');
  assert.equal(source.rel, 'noopener noreferrer');
  await select(env, 'selYear', 2);
  assert.deepEqual(options(env.node('selBatch')), [['', 'Choose topic'], ['fractions', 'Fractions'], ['shapes', 'Shapes']]);
  await select(env, 'selBatch', 'shapes');
  await select(env, 'selNum', 1);
  assert.equal(env.node('pickerTitle').textContent, 'Grade 2 · Shapes · Problem 1');
  await select(env, 'selYear', 4);
  assert.equal(env.node('selBatch').value, 'fractions');
  assert.equal(env.node('selBatch').disabled, true);
  await select(env, 'selNum', 1);
  assert.equal(env.node('pickerTitle').textContent, 'Grade 4 · Fractions · Problem 1');
  await select(env, 'selBank', 'cn-math');
  assert.equal(env.node('sourceNotice').textContent, env.cnNotice);
  assert.equal(env.node('poolCount').textContent, '1 English questions');
});

test('custom source URLs only become links for HTTP or HTTPS', async () => {
  for (const sourceURL of ['javascript:alert(1)', 'data:text/html,hello', 'file:///C:/bank.html', '/relative-source']) {
    const env = environment([customBank({sourceURL})]);
    await select(env, 'selBank', 'garden_math');
    assert.equal(env.node('sourceNotice').children.some(child => child.tagName === 'A'), false);
    assert.match(env.node('sourceNotice').textContent, /Source: Garden mathematics/);
    assert.doesNotMatch(env.node('sourceNotice').textContent, /cn-math-taxonomy/);
  }
});

async function solutionSource(fields) {
  const env = environment([customBank({questions: [question('garden_math__source', {
    solutionSource: 'Garden author <b>notes</b>', ...fields})]})]);
  await select(env, 'selBank', 'garden_math');
  await env.node('beginPractice').emit('click');
  await find(env.node('poolDisplay'), 'sol-btn').emit('click');
  return env.node('solBody').children[0].children.find(child => child.className === 'pool-hint');
}

test('custom solution attribution without a URL stays plain text', async () => {
  const source = await solutionSource({});
  assert.equal(source.textContent, 'Solution source: Garden author <b>notes</b>');
  assert.equal(source.children.some(child => child.tagName === 'A'), false);
});

test('custom solution attribution with an invalid URL stays plain text', async () => {
  for (const sourceURL of ['javascript:alert(1)', 'data:text/html,hello', 'file:///C:/bank.html', '/relative-source']) {
    const source = await solutionSource({sourceURL});
    assert.equal(source.textContent, 'Solution source: Garden author <b>notes</b>');
    assert.equal(source.children.some(child => child.tagName === 'A'), false);
  }
});

test('custom solution attribution links to its own HTTP or HTTPS URL', async () => {
  for (const sourceURL of ['http://example.org/solution', 'https://example.org/solution']) {
    const source = await solutionSource({sourceURL});
    const link = source.children.find(child => child.tagName === 'A');
    assert.ok(link);
    assert.equal(link.href, sourceURL);
    assert.equal(link.textContent, 'Garden author <b>notes</b>');
    assert.equal(link.rel, 'noopener noreferrer');
  }
});

test('custom level and topic names can match JavaScript property names', async () => {
  const env = environment([customBank({questions: [question('garden_math__reserved', {
    level: '__proto__', batch: 'toString', topic: {id: 'toString', label: 'Property names'}})]})]);
  await select(env, 'selBank', 'garden_math');
  assert.deepEqual(options(env.node('selLevel')), [['__proto__', '__proto__']]);
  await select(env, 'selYear', 2);
  assert.deepEqual(options(env.node('selBatch')), [['toString', 'Property names']]);
  await select(env, 'selNum', 1);
  assert.equal(env.node('pickerTitle').textContent, 'Grade 2 · Property names · Problem 1');
  assert.equal(env.node('poolDisplay').hidden, false);
});

test('custom question answers, sequential navigation, solutions, and notebook return work together', async () => {
  const env = environment([customBank()]);
  await select(env, 'selBank', 'garden_math');
  await env.node('beginPractice').emit('click');
  assert.equal(env.node('pickerTitle').textContent, 'Grade 2 · Fractions · Problem 1');
  assert.equal(env.node('previousProblem').disabled, true);
  assert.equal(env.node('nextProblem').disabled, false);
  env.node('freeAnswer').value = '1/2';
  await env.node('freeAnswer').emit('input');
  await env.node('thoughtsSubmit').emit('click');
  assert.match(env.node('answerFeedback').textContent, /Correct\./);
  await env.node('bookmarkProblem').emit('click');
  await env.node('nextProblem').emit('click');
  assert.equal(env.node('pickerTitle').textContent, 'Grade 2 · Fractions · Problem 2');
  assert.equal(env.node('nextProblem').disabled, true);
  assert.equal(env.node('freeAnswer').hidden, true);
  const choice = env.node('answerOpts').children.find(button => button.dataset.answer === 'B');
  await choice.emit('click');
  await env.node('thoughtsSubmit').emit('click');
  assert.match(env.node('answerFeedback').textContent, /Correct\./);
  await find(env.node('poolDisplay'), 'sol-btn').emit('click');
  assert.equal(env.node('solTitle').textContent, 'Grade 2 · Fractions · Problem 2. Solution');
  assert.match(env.node('solBody').textContent, /Correct answer: \(B\)/);
  await env.node('solClose').emit('click');
  await env.node('previousProblem').emit('click');
  assert.equal(env.node('freeAnswer').value, '1/2');
  await select(env, 'selBank', 'cn-math');
  const saved = env.node('notebookList').children.find(row => row.dataset.questionId === 'garden_math_q1');
  assert.match(saved.children[0].textContent, /^Grade 2 · Fractions · Problem 1/);
  await saved.children[0].emit('click');
  assert.equal(env.node('selBank').value, 'garden_math');
  assert.equal(env.node('selYear').value, '2');
  assert.equal(env.node('selBatch').value, 'fractions');
  assert.equal(env.node('pickerTitle').textContent, 'Grade 2 · Fractions · Problem 1');
  assert.equal(env.node('freeAnswer').value, '1/2');
  assert.doesNotMatch(env.node('sourceNotice').textContent, /cn-math-taxonomy/);
  const attempts = JSON.parse(env.storage.get('math-practice.attempts.v1'));
  assert.equal(attempts.garden_math_q1.answer, '1/2');
});

for (const layer of ['ailleo', 'CN', 'US']) {
  test(layer + ' practice selection captures the standard while manual custom, AMC and CN browsing still works', async () => {
    const submissions = [];
    const response = value => ({ok: true, json: async () => value, text: async () => JSON.stringify(value)});
    const selectedId = layer === 'ailleo' ? 'math:fraction' : 'native-standard';
    const env = environment([customBank()], amcBank(), {paths: true, fetch: (url, request) => {
      if (url.includes('/api/status/')) return response({configured: false, ready: false,
        localEvidenceItems: ['garden_math_q1', 'amc8_2026_1', 'cn-sample']});
      if (url.includes('/browse')) return response({status: 'available', nodes: [
        {id: selectedId, name: 'Fractions', label: 'Fraction standard', placement: {grade: 4}}]});
      if (url.includes('/practice')) return response({status: layer === 'US' ? 'partial' : 'mapped', candidates: [
        {questionId: 'not-installed'}, {questionId: 'garden_math_q1'}, {questionId: 'amc8_2026_1'}]});
      assert.equal(url, '/api/assessment');
      const body = JSON.parse(request.body); submissions.push(body);
      return response({questionId: body.questionId, answer: body.answer, revisionId: body.turn.revisionId,
        curriculumLayer: body.curriculumLayer, curriculumNodeId: body.curriculumNodeId,
        category: 'cannot_judge', answerCategory: 'correct', answerCorrect: true,
        decisionConfigured: false, inferenceConfigured: false});
    }});
    await new Promise(resolve => setImmediate(resolve));
    if (layer !== 'ailleo') {
      await select(env, 'practicePath', layer);
      await new Promise(resolve => setImmediate(resolve));
    }
    await select(env, 'pathConcept', selectedId);
    await env.node('pathFind').emit('click');
    assert.equal(env.node('pathResults').children.length, 2);
    await env.node('pathResults').children[0].emit('click');
    assert.equal(env.node('selBank').value, 'garden_math');
    env.node('freeAnswer').value = '1/2'; await env.node('freeAnswer').emit('input');
    await env.node('thoughtsSubmit').emit('click');
    await new Promise(resolve => setImmediate(resolve));
    await select(env, 'selBank', 'amc'); await env.node('beginPractice').emit('click');
    await env.node('answerOpts').children.find(button => button.dataset.answer === 'B').emit('click');
    await env.node('thoughtsSubmit').emit('click');
    await new Promise(resolve => setImmediate(resolve));
    await select(env, 'selBank', 'cn-math'); await env.node('beginPractice').emit('click');
    env.node('freeAnswer').value = '1/2'; await env.node('freeAnswer').emit('input');
    await env.node('thoughtsSubmit').emit('click');
    await new Promise(resolve => setImmediate(resolve));
    assert.deepEqual(submissions.map(body => [body.bank, body.questionId, body.curriculumLayer, body.curriculumNodeId]), [
      ['garden_math', 'garden_math_q1', layer, selectedId], ['amc', 'amc8_2026_1', layer, selectedId],
      ['cn-math', 'cn-sample', layer, selectedId]]);
    assert.equal(env.node('practicePath').value, layer);
    assert.equal(env.node('pathConcept').value, selectedId);
    assert.match(env.node('answerFeedback').textContent, /Correct\./);
  });
}
