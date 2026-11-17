/* Curriculum choice changes practice and teaching context, never a learner profile. */
(function () {
  'use strict';
  const KEY = 'math-practice.curriculum-path.v1';
  const PAGE_SIZE = 30;
  const language = window.MathPracticeLanguage;
  const topics = window.MathPracticeTopics;
  const t = (key, params) => language ? language.t(key, params) : key.replace(/\{(\w+)\}/g, (_, name) => params && params[name] !== undefined ? params[name] : '{' + name + '}');
  if (language) language.register({
    '{first} of {total}': '共 {total} 题，第 {first} 题',
    '{first} to {last} of {total}': '共 {total} 题，第 {first} 至 {last} 题',
    'Choose a concept or standard': '选择概念或课程标准',
    'No matching concepts or standards': '没有匹配的概念或课程标准',
    'Loading concepts…': '正在加载概念…',
    'Mathematical concept': '数学概念',
    'Chinese curriculum concept': '中国课程概念',
    'Common Core standard': '美国共同核心课程标准',
    'Practice paths are unavailable. Use the By source tab.': '练习路径暂时不可用。请使用“按来源”选项卡。',
    'Start the local launcher to browse practice paths. The By source tab still works.': '请启动本地应用以浏览练习路径。“按来源”选项卡仍可使用。',
    'This curriculum is not installed. Use another path or the By source tab.': '尚未安装此课程。请选择其他路径或使用“按来源”选项卡。',
    'Choose by mathematical idea, without a grade level.': '按数学概念选择，不限年级。',
    'Placements follow this curriculum. Related practice may include ideas beyond a standard.': '年级和教材安排沿用该课程。相关练习可能涉及课程标准以外的概念。',
    'Finding linked practice…': '正在查找关联练习…',
    'No questions on this page are installed. Choose another results page.': '尚未安装此页中的题目。请选择其他结果页。',
    'No practice is linked to this standard yet. Choose another concept or use the By source tab.': '此课程标准尚未关联练习。请选择其他概念或使用“按来源”选项卡。',
    'No linked questions are installed for this selection. Use the By source tab.': '尚未安装此选项的关联题目。请使用“按来源”选项卡。',
    'Question {range}. ': '{range}。',
    'Questions {range}. ': '{range}。',
    'Related practice; may include ideas beyond this standard. Choose any method the question allows.': '相关练习可能涉及此课程标准以外的概念。可使用题目允许的任何方法。',
    'These questions give you a chance to use this idea. Other methods may work too.': '这些题目可用于练习此概念，也可以使用其他适用的方法。',
    'Related practice': '相关练习'
  });
  function rangeLabel(start, total) {
    const first = start + 1, last = Math.min(start + PAGE_SIZE, total);
    return t(first === last ? '{first} of {total}' : '{first} to {last} of {total}', {first, last, total});
  }
  class CurriculumPath {
    constructor(options) {
      this.o = options; this.nodes = []; this.serial = 0; this.loadSerial = 0; this.state = {layer: 'ailleo', nodeId: ''};
      this.results = null; this.pageState = null; this.loading = false; this.loaded = false; this.finding = false; this.statusMessage = '';
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
      if (window.addEventListener) window.addEventListener('languagechange', () => this.renderLanguage());
      this.load();
    }
    layer() { return this.state.layer; }
    nodeId() { return this.state.nodeId || null; }
    persist() { try { localStorage.setItem(KEY, JSON.stringify(this.state)); } catch (_) {} }
    option(value, label) { const n = document.createElement('option'); n.value = value; n.textContent = label; return n; }
    status(message) { this.statusMessage = message; this.n.pathStatus.textContent = typeof message === 'function' ? message() : t(message); }
    clearResults() { this.serial += 1; this.results = null; this.pageState = null; this.finding = false; this.n.pathResults.replaceChildren(); this.n.pathPageField.hidden = true; this.status(''); }
    renderLanguage() {
      this.n.pathConceptLabel.textContent = t(this.layer() === 'ailleo' ? 'Mathematical concept' : this.layer() === 'CN' ? 'Chinese curriculum concept' : 'Common Core standard');
      if (this.loading) this.n.pathConcept.replaceChildren(this.option('', t('Loading concepts…')));
      else if (this.loaded) this.renderOptions();
      if (this.pageState) this.renderPages();
      if (this.results) this.renderResults();
      this.status(this.statusMessage);
    }
    placement(node) {
      if (this.layer() === 'ailleo') return '';
      const p = node.placement || {}, parts = [];
      if (p.grade !== undefined && p.grade !== null && p.grade !== '') parts.push(topics ? topics.grade(p.grade) : String(p.grade).match(/^(K|kindergarten)$/i) ? 'Kindergarten' : p.grade === 'HS' ? 'High school' : /grade/i.test(String(p.grade)) ? String(p.grade) : 'Grade ' + p.grade);
      for (const key of ['bookLabel', 'semester', 'book', 'category', 'domain']) {
        if (p[key] === undefined || p[key] === null || p[key] === '') continue;
        const text = topics ? topics.placementText(p[key]) : String(p[key]);
        if (!parts.includes(text)) parts.push(text);
      }
      return parts.join(' · ');
    }
    label(node) {
      const title = topics ? topics.name(node) : node.label || node.name || node.id;
      const placement = this.placement(node);
      return title + (placement ? ' · ' + placement : '');
    }
    describe() {
      const node = this.nodes.find(n => n.id === this.state.nodeId);
      const description = node ? topics ? topics.description(node) : node.description || '' : '';
      this.n.pathDescription.textContent = node ? this.label(node) + (description ? '\n' + description : '') : '';
      this.n.pathFind.disabled = !node || this.finding;
    }
    renderOptions() {
      const query = this.n.pathFilter.value.trim().toLocaleLowerCase();
      // Search both names so changing the display language cannot invalidate a filtered selection.
      const nodes = this.nodes.filter(n => (this.label(n) + ' ' + (topics ? topics.searchText(n) : n.description || '')).toLocaleLowerCase().includes(query))
        .sort((a,b) => this.label(a).localeCompare(this.label(b), language ? language.getLanguage() : undefined, {numeric: true}));
      this.n.pathConcept.replaceChildren(this.option('', t(nodes.length ? 'Choose a concept or standard' : 'No matching concepts or standards')));
      for (const node of nodes) this.n.pathConcept.appendChild(this.option(node.id, this.label(node)));
      this.n.pathConcept.value = nodes.some(n => n.id === this.state.nodeId) ? this.state.nodeId : '';
      if (!this.n.pathConcept.value) this.state.nodeId = '';
      this.n.pathConcept.disabled = !nodes.length; this.describe();
    }
    async get(url) {
      const response = await fetch(url);
      if (!response.ok) throw new Error('Practice paths are unavailable. Use the By source tab.');
      return response.json();
    }
    async load() {
      this.clearResults(); this.loading = true; this.loaded = false; const serial = ++this.loadSerial, layer = this.layer();
      const attribution = document.getElementById('pathAttribution');
      if (attribution) attribution.hidden = layer !== 'US';
      this.nodes = []; this.n.pathConcept.replaceChildren(this.option('', t('Loading concepts…')));
      this.n.pathConcept.disabled = true; this.n.pathFind.disabled = true; this.n.pathDescription.textContent = '';
      this.n.pathConceptLabel.textContent = t(layer === 'ailleo' ? 'Mathematical concept' : layer === 'CN' ? 'Chinese curriculum concept' : 'Common Core standard');
      if (location.protocol === 'file:') { this.loading = false; this.status('Start the local launcher to browse practice paths. The By source tab still works.'); return; }
      try {
        const data = window.MATH_PRACTICE_HOSTED
          ? await window.MathPracticeHosted.browse(layer)
          : await this.get('/api/knowledge/browse?layer=' + encodeURIComponent(layer));
        if (serial !== this.loadSerial || layer !== this.layer()) return;
        this.loading = false; this.loaded = true; this.nodes = (data.nodes || []).slice();
        const previous = this.state.nodeId;
        this.renderOptions();
        if (previous !== this.state.nodeId) { this.persist(); if (this.o.changed) this.o.changed(); }
        this.status(data.status === 'unavailable' ? 'This curriculum is not installed. Use another path or the By source tab.' : layer === 'ailleo' ? 'Choose by mathematical idea, without a grade level.' : 'Placements follow this curriculum. Related practice may include ideas beyond a standard.');
      } catch (error) { if (serial === this.loadSerial) { this.loading = false; this.status(error.message); } }
    }
    async find(offset = 0) {
      const id = this.n.pathConcept.value, layer = this.layer();
      if (!id) return;
      const serial = ++this.serial; this.results = null; this.finding = true; this.n.pathResults.replaceChildren(); this.n.pathFind.disabled = true; this.status('Finding linked practice…');
      try {
        const key = layer === 'ailleo' ? 'nodeId' : 'sourceNodeId';
        const data = window.MATH_PRACTICE_HOSTED
          ? await window.MathPracticeHosted.practice(layer, this.nodes.find(node => node.id === id), offset)
          : await this.get('/api/knowledge/practice?layer=' + encodeURIComponent(layer) + '&' + key + '=' + encodeURIComponent(id) + (offset ? '&offset=' + offset : ''));
        if (serial !== this.serial || layer !== this.layer()) return;
        if (offset && Number.isInteger(data.total) && offset >= data.total) return this.find(0);
        this.results = {data, offset}; this.renderResults();
      } catch (error) { if (serial === this.serial) this.status(error.message); }
      finally { if (serial === this.serial) { this.finding = false; this.n.pathFind.disabled = !this.state.nodeId; } }
    }
    renderResults() {
        const {data, offset} = this.results;
        this.n.pathResults.replaceChildren();
        const paged = data.total > PAGE_SIZE;
        this.n.pathPageField.hidden = !paged;
        this.pageState = paged ? {total: data.total, offset} : null;
        if (paged) this.renderPages();
        const candidates = (data.candidates || []).filter(candidate => this.o.question(candidate.questionId));
        if (!candidates.length) {
          this.status(paged ? 'No questions on this page are installed. Choose another results page.' : data.status === 'unmapped' ? 'No practice is linked to this standard yet. Choose another concept or use the By source tab.' : 'No linked questions are installed for this selection. Use the By source tab.');
          return;
        }
        this.status(() => {
          const range = paged ? t(offset + 1 === data.total ? 'Question {range}. ' : 'Questions {range}. ', {range: rangeLabel(offset, data.total)}) : '';
          return range + t(data.status === 'partial'
            ? 'Related practice; may include ideas beyond this standard. Choose any method the question allows.'
            : 'These questions give you a chance to use this idea. Other methods may work too.');
        });
        for (const candidate of candidates) {
          const question = this.o.question(candidate.questionId), button = document.createElement('button');
          button.type = 'button'; button.className = 'ghost path-question';
          button.textContent = this.o.title(question) + (candidate.coverage === 'partial' ? ' · ' + t('Related practice') : '');
          button.addEventListener('click', () => this.o.select(question)); this.n.pathResults.appendChild(button);
        }
    }
    renderPages() {
      const {total, offset} = this.pageState, options = [];
      for (let start = 0; start < total; start += PAGE_SIZE) options.push(this.option(String(start), rangeLabel(start, total)));
      this.n.pathPage.replaceChildren(...options); this.n.pathPage.value = String(offset);
    }
  }
  window.MathPracticeCurriculumPath = CurriculumPath;
})();
