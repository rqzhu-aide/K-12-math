const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const source = readFileSync(join(__dirname, '../graph-evidence.js'), 'utf8');

class Element {
  constructor() { this.children = []; }
  appendChild(node) { this.children.push(node); }
  replaceChildren() { this.children = []; }
  all(className) {
    return [...(this.className === className ? [this] : []), ...this.children.flatMap(node => node.all(className))];
  }
}
function tab(stored = new Map()) {
  const panel = new Element(), body = new Element(), scope = new Element();
  const nodes = {graphEvidence: panel, graphEvidenceBody: body, graphEvidenceScope: scope};
  const context = {window: {}, document: {getElementById: id => nodes[id], createElement: () => new Element()},
    sessionStorage: {getItem: key => stored.get(key), setItem: (key,value) => stored.set(key,value)}};
  vm.runInNewContext(source, context);
  return {panel, body, record: context.window.MathPracticeGraph.record};
}
const initial = {shadow: true, bank: 'cn-math', questionId: 'item', revisionId: 'r1', topicId: 'topic',
  topicLabel: 'Completing the Square', criterionId: 'criterion-key', criterion: 'Justify the missing constant.',
  graphRevision: 'version-of-graph', mappingVersion: 'version-of-mapping', judgmentSource: 'rule',
  action: 'submit', status: 'needs_review', assistance: 'none', answerCategory: 'wrong', quote: 'My first try.'};

test('one graph row per revision survives reload only within this tab storage', () => {
  const saved = new Map(), first = tab(saved);
  assert.ok(first.panel.hidden);
  first.record(initial);
  first.record(initial);
  first.record({...initial, revisionId: 'r2', action:'revise', status: 'demonstrated', assistance:'hint',
    answerCategory:'correct', quote:'My second try.'});
  first.record({...initial, shadow:false, revisionId:'ignored'});
  const reloaded = tab(saved);
  assert.equal(reloaded.panel.hidden, false);
  assert.equal(reloaded.body.all('graph-observation').length, 2);
  assert.equal(reloaded.body.all('graph-quote')[1].textContent, 'My second try.');
  assert.match(reloaded.body.all('graph-summary')[0].textContent, /0 of 1/);
  assert.ok(tab().panel.hidden);
});

test('first arriving record can be a retry, an assisted attempt or unassessable work', () => {
  for (const change of [{action:'revise'}, {action:undefined}, {assistance:'unknown'}, {assistance:'solution'}, {status:'unobserved'}]) {
    const page = tab();
    page.record({...initial, ...change});
    assert.equal(page.body.all('graph-observation').length, 1);
    assert.equal(page.body.all('graph-summary').length, 0);
  }
});
