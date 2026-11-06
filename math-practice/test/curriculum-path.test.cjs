'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../curriculum-path.js'), 'utf8');
const settle = () => new Promise(resolve => setImmediate(resolve));
class Element {
  constructor() { this.value = ''; this.children = []; this.listeners = {}; this.disabled = false; this.textContent = ''; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren(...nodes) { this.children = nodes; }
  async emit(name) { if (this.listeners[name]) await this.listeners[name](); }
}
function harness(saved = null, options = {}) {
  const elements = new Map(), storage = new Map(), requests = [], chosen = [], changes = [];
  if (saved) storage.set('math-practice.curriculum-path.v1', JSON.stringify(saved));
  const node = id => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const context = vm.createContext({window: {}, document: {getElementById: node, createElement: () => new Element()},
    location: {protocol: 'http:'}, localStorage: {getItem: k => storage.get(k), setItem: (k,v) => storage.set(k,v)},
    fetch: async url => {
      requests.push(url);
      if (options.fetch) return options.fetch(url);
      const params = new URL(url, 'http://localhost').searchParams;
      const layer = params.get('layer');
      if (url.includes('/browse')) return {ok: true, json: async () => ({status: 'available', nodes: layer === 'ailleo'
        ? [{id: 'math:fraction', name: 'Fractions', description: 'A concept', original: {grade: 99}}]
        : [{id: '4.NF.4', label: '4.NF.4', description: 'Fraction multiplication', placement: {grade: 4}},
           {id: 'no-map', label: 'Unmapped topic', description: 'Scope', placement: {grade: 5}}]})};
      return {ok: true, json: async () => ({status: params.get('sourceNodeId') === 'no-map' ? 'unmapped' : 'partial',
        candidates: params.get('sourceNodeId') === 'no-map' ? [] : [{questionId: 'fraction-q', coverage: 'partial'}]})};
    }});
  vm.runInContext(source, context);
  const instance = new context.window.MathPracticeCurriculumPath({question: id => id === 'fraction-q' ? {id} : null,
    title: () => 'Fraction question', select: q => chosen.push(q.id), changed: () => changes.push(true)});
  return {instance, node, storage, requests, chosen, changes};
}

test('default ailleo offers gradeless concepts and keeps path storage separate', async () => {
  const h = harness(); await settle();
  assert.equal(h.instance.layer(), 'ailleo');
  assert.equal(h.node('pathConcept').children[1].textContent, 'Fractions');
  assert.doesNotMatch(h.node('pathConcept').children[1].textContent, /99|Grade/);
  h.node('practicePath').value = 'US'; await h.node('practicePath').emit('change'); await settle();
  assert.equal(h.changes.length, 1);
  assert.deepEqual([...h.storage.keys()], ['math-practice.curriculum-path.v1']);
  assert.match(h.node('pathConcept').children[1].textContent, /Grade 4.*4.NF.4/);
});

test('a native standard finds existing questions and visibly qualifies partial coverage', async () => {
  const h = harness({layer: 'US', nodeId: '4.NF.4'}); await settle();
  h.node('pathConcept').value = '4.NF.4'; await h.node('pathConcept').emit('change');
  await h.node('pathFind').emit('click');
  assert.match(h.requests.at(-1), /layer=US&sourceNodeId=4.NF.4/);
  assert.match(h.node('pathStatus').textContent, /Related practice; may include/);
  assert.match(h.node('pathResults').children[0].textContent, /Related practice/);
  await h.node('pathResults').children[0].emit('click');
  assert.deepEqual(h.chosen, ['fraction-q']);
});

test('unmapped native standards remain selectable and show an honest empty state', async () => {
  const h = harness({layer: 'CN'}); await settle();
  h.node('pathConcept').value = 'no-map'; await h.node('pathConcept').emit('change');
  await h.node('pathFind').emit('click');
  assert.match(h.node('pathStatus').textContent, /No practice is linked/);
  assert.equal(h.node('pathResults').children.length, 0);
  assert.equal(h.node('pathFind').disabled, false);
});

test('filtering while concepts load preserves the request and applies the filter on arrival', async () => {
  let finish;
  const h = harness({layer: 'US', nodeId: '4.NF.4'}, {fetch: () => new Promise(resolve => { finish = resolve; })});
  h.node('pathFilter').value = 'fraction'; await h.node('pathFilter').emit('input');
  finish({ok: true, json: async () => ({status: 'available', nodes: [
    {id: '4.NF.4', label: '4.NF.4', description: 'Fraction multiplication', placement: {grade: 4}},
    {id: 'other', label: 'Other topic'}]})});
  await settle();
  assert.equal(h.node('pathConcept').disabled, false);
  assert.equal(h.node('pathConcept').children.length, 2);
  assert.equal(h.instance.nodeId(), '4.NF.4');
  assert.equal(h.node('pathFind').disabled, false);
});

test('a saved selection removed from the installed graph is cleared in storage and feedback', async () => {
  const h = harness({layer: 'US', nodeId: 'removed-standard'}); await settle();
  assert.equal(h.instance.nodeId(), null);
  assert.equal(JSON.parse(h.storage.get('math-practice.curriculum-path.v1')).nodeId, '');
  assert.equal(h.changes.length, 1);
});

test('rapid path switches keep the latest browse response even after returning to the first path', async () => {
  const pending = [];
  const h = harness(null, {fetch: url => new Promise(resolve => pending.push({url, resolve}))});
  h.node('practicePath').value = 'CN'; await h.node('practicePath').emit('change');
  h.node('practicePath').value = 'ailleo'; await h.node('practicePath').emit('change');
  pending[2].resolve({ok: true, json: async () => ({nodes: [{id: 'new', name: 'Current concept'}]})});
  await settle();
  for (const request of pending.slice(0, 2)) request.resolve({ok: true, json: async () => ({nodes: [{id: 'old', name: 'Old concept'}]})});
  await settle();
  assert.equal(h.node('pathConcept').children[1].value, 'new');
  assert.equal(h.node('pathConceptLabel').textContent, 'Mathematical concept');
});

test('switching standards rejects an earlier find response and keeps the new selection usable', async () => {
  let finish;
  const h = harness({layer: 'US'}, {fetch: url => url.includes('/browse')
    ? {ok: true, json: async () => ({nodes: [{id: 'a', label: 'A'}, {id: 'b', label: 'B'}]})}
    : new Promise(resolve => { finish = resolve; })});
  await settle();
  h.node('pathConcept').value = 'a'; await h.node('pathConcept').emit('change');
  const finding = h.node('pathFind').emit('click');
  h.node('pathConcept').value = 'b'; await h.node('pathConcept').emit('change');
  finish({ok: true, json: async () => ({status: 'partial', candidates: [{questionId: 'fraction-q', coverage: 'partial'}]})});
  await finding;
  assert.equal(h.instance.nodeId(), 'b');
  assert.equal(h.node('pathResults').children.length, 0);
  assert.equal(h.node('pathStatus').textContent, '');
  assert.equal(h.node('pathFind').disabled, false);
});

test('filtering away the selected standard clears its frozen-selection source and result buttons', async () => {
  const h = harness({layer: 'US', nodeId: '4.NF.4'}); await settle();
  await h.node('pathFind').emit('click');
  h.node('pathFilter').value = 'unmapped'; await h.node('pathFilter').emit('input');
  assert.equal(h.instance.nodeId(), null);
  assert.equal(h.node('pathResults').children.length, 0);
  assert.equal(h.node('pathFind').disabled, true);
  assert.equal(h.changes.length, 1);
  assert.equal(JSON.parse(h.storage.get('math-practice.curriculum-path.v1')).nodeId, '');
});

