/* Curriculum choice changes practice and teaching context, never a learner profile. */
(function () {
  'use strict';
  const KEY = 'math-practice.curriculum-path.v1';
  const PAGE_SIZE = 30;
  function rangeLabel(start, total) {
    const first = start + 1, last = Math.min(start + PAGE_SIZE, total);
    return (first === last ? first : first + ' to ' + last) + ' of ' + total;
  }
  class CurriculumPath {
    constructor(options) {
      this.o = options; this.nodes = []; this.serial = 0; this.loadSerial = 0; this.state = {layer: 'ailleo', nodeId: ''};
      this.n = {};
      for (const id of ['practicePath', 'pathFilter', 'pathConcept', 'pathConceptLabel', 'pathFind', 'pathStatus', 'pathResults', 'pathDescription', 'pathPageField', 'pathPage']) this.n[id] = document.getElementById(id);
      try {
        const saved = JSON.parse(localStorage.getItem(KEY) || 'null');
        if (saved && ['ailleo', 'CN', 'US'].includes(saved.layer)) this.state = {layer: saved.layer, nodeId: typeof saved.nodeId === 'string' ? saved.nodeId : ''};
      } catch (_) {}
      this.n.practicePath.value = this.state.layer;
      this.n.practicePath.addEventListener('change', () => {
        this.state = {layer: this.n.practicePath.value, nodeId: ''}; this.n.pathFilter.value = '';
        this.persist(); if (this.o.changed) this.o.changed(); this.load();
      });
      this.n.pathFilter.addEventListener('input', () => { const previous = this.state.nodeId; this.clearResults(); if (this.nodes.length) this.renderOptions(); this.persist(); if (previous !== this.state.nodeId && this.o.changed) this.o.changed(); });
      this.n.pathConcept.addEventListener('change', () => {
        this.state.nodeId = this.n.pathConcept.value; this.persist(); this.clearResults(); this.describe();
        if (this.o.changed) this.o.changed();
      });
      this.n.pathFind.addEventListener('click', () => this.find());
      this.n.pathPage.addEventListener('change', () => this.find(Number(this.n.pathPage.value)));
      this.load();
    }
    layer() { return this.state.layer; }
    nodeId() { return this.state.nodeId || null; }
    persist() { try { localStorage.setItem(KEY, JSON.stringify(this.state)); } catch (_) {} }
    option(value, label) { const n = document.createElement('option'); n.value = value; n.textContent = label; return n; }
    status(message) { this.n.pathStatus.textContent = message; }
    clearResults() { this.serial += 1; this.n.pathResults.replaceChildren(); this.n.pathPageField.hidden = true; this.status(''); }
    placement(node) {
      if (this.layer() === 'ailleo') return '';
      const p = node.placement || {}, parts = [];
      if (p.grade !== undefined && p.grade !== null && p.grade !== '') parts.push(String(p.grade).match(/^(K|kindergarten)$/i) ? 'Kindergarten' : p.grade === 'HS' ? 'High school' : /grade/i.test(String(p.grade)) ? String(p.grade) : 'Grade ' + p.grade);
      for (const key of ['bookLabel', 'semester', 'book', 'category', 'domain']) if (p[key] !== undefined && p[key] !== null && p[key] !== '' && !parts.includes(String(p[key]))) parts.push(String(p[key]));
      return parts.join(' · ');
    }
    label(node) {
      const title = node.label || node.name || node.id;
      const placement = this.placement(node);
      return (placement ? placement + ' · ' : '') + title;
    }
    describe() {
      const node = this.nodes.find(n => n.id === this.state.nodeId);
      this.n.pathDescription.textContent = node ? node.description || '' : '';
      this.n.pathFind.disabled = !node;
    }
    renderOptions() {
      const query = this.n.pathFilter.value.trim().toLocaleLowerCase();
      const nodes = this.nodes.filter(n => (this.label(n) + ' ' + (n.description || '')).toLocaleLowerCase().includes(query));
      this.n.pathConcept.replaceChildren(this.option('', nodes.length ? 'Choose a concept or standard' : 'No matching concepts or standards'));
      for (const node of nodes) this.n.pathConcept.appendChild(this.option(node.id, this.label(node)));
      this.n.pathConcept.value = nodes.some(n => n.id === this.state.nodeId) ? this.state.nodeId : '';
      if (!this.n.pathConcept.value) this.state.nodeId = '';
      this.n.pathConcept.disabled = !nodes.length; this.describe();
    }
    async get(url) {
      const response = await fetch(url);
      if (!response.ok) throw new Error('Practice paths are unavailable. Use the question bank below.');
      return response.json();
    }
    async load() {
      this.clearResults(); const serial = ++this.loadSerial, layer = this.layer();
      const attribution = document.getElementById('pathAttribution');
      if (attribution) attribution.hidden = layer !== 'US';
      this.nodes = []; this.n.pathConcept.replaceChildren(this.option('', 'Loading concepts…'));
      this.n.pathConcept.disabled = true; this.n.pathFind.disabled = true; this.n.pathDescription.textContent = '';
      this.n.pathConceptLabel.textContent = layer === 'ailleo' ? 'Mathematical concept' : layer === 'CN' ? 'Chinese curriculum concept' : 'Common Core standard';
      if (location.protocol === 'file:') { this.status('Start the local launcher to browse practice paths. The question bank below still works.'); return; }
      try {
        const data = window.MATH_PRACTICE_HOSTED
          ? await window.MathPracticeHosted.browse(layer)
          : await this.get('/api/knowledge/browse?layer=' + encodeURIComponent(layer));
        if (serial !== this.loadSerial || layer !== this.layer()) return;
        this.nodes = (data.nodes || []).slice().sort((a,b) => this.label(a).localeCompare(this.label(b), undefined, {numeric: true}));
        const previous = this.state.nodeId;
        this.renderOptions();
        if (previous !== this.state.nodeId) { this.persist(); if (this.o.changed) this.o.changed(); }
        this.status(data.status === 'unavailable' ? 'This curriculum is not installed. Use another path or the question bank below.' : layer === 'ailleo' ? 'Choose by mathematical idea, without a grade level.' : 'Placements follow this curriculum. Related practice may include ideas beyond a standard.');
      } catch (error) { if (serial === this.loadSerial) this.status(error.message); }
    }
    async find(offset = 0) {
      const id = this.n.pathConcept.value, layer = this.layer();
      if (!id) return;
      const serial = ++this.serial; this.n.pathResults.replaceChildren(); this.n.pathFind.disabled = true; this.status('Finding linked practice…');
      try {
        const key = layer === 'ailleo' ? 'nodeId' : 'sourceNodeId';
        const data = window.MATH_PRACTICE_HOSTED
          ? await window.MathPracticeHosted.practice(layer, this.nodes.find(node => node.id === id), offset)
          : await this.get('/api/knowledge/practice?layer=' + encodeURIComponent(layer) + '&' + key + '=' + encodeURIComponent(id) + (offset ? '&offset=' + offset : ''));
        if (serial !== this.serial || layer !== this.layer()) return;
        if (offset && Number.isInteger(data.total) && offset >= data.total) return this.find(0);
        const paged = data.total > PAGE_SIZE;
        this.n.pathPageField.hidden = !paged;
        if (paged) {
          const options = [];
          for (let start = 0; start < data.total; start += PAGE_SIZE) {
            options.push(this.option(String(start), rangeLabel(start, data.total)));
          }
          this.n.pathPage.replaceChildren(...options);
          this.n.pathPage.value = String(offset);
        }
        const candidates = (data.candidates || []).filter(candidate => this.o.question(candidate.questionId));
        if (!candidates.length) {
          this.status(paged ? 'No questions on this page are installed. Choose another results page.' : data.status === 'unmapped' ? 'No practice is linked to this standard yet. Choose another concept or use the question bank below.' : 'No linked questions are installed for this selection. Use the question bank below.');
          return;
        }
        const range = paged ? (offset + 1 === data.total ? 'Question ' : 'Questions ') + rangeLabel(offset, data.total) + '. ' : '';
        this.status(range + (data.status === 'partial'
          ? 'Related practice; may include ideas beyond this standard. Choose any method the question allows.'
          : 'These questions give you a chance to use this idea. Other methods may work too.'));
        for (const candidate of candidates) {
          const question = this.o.question(candidate.questionId), button = document.createElement('button');
          button.type = 'button'; button.className = 'ghost path-question';
          button.textContent = this.o.title(question) + (candidate.coverage === 'partial' ? ' · Related practice' : '');
          button.addEventListener('click', () => this.o.select(question)); this.n.pathResults.appendChild(button);
        }
      } catch (error) { if (serial === this.serial) this.status(error.message); }
      finally { if (serial === this.serial) this.n.pathFind.disabled = false; }
    }
  }
  window.MathPracticeCurriculumPath = CurriculumPath;
})();
