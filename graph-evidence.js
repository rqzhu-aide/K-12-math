/* Per-tab observations attached to reviewed knowledge-graph criteria. */
(function () {
  'use strict';
  const Language = window.MathPracticeLanguage;
  const t = (source, params) => Language.t(source, params);
  const ui = (node, source, params) => Language.bindText(node, source, params);
  Language.register({
    'No in-app help observed': '未观察到应用内帮助', 'After coaching': '接受辅导后', 'After a hint': '查看提示后', 'After viewing the solution': '查看解答后', 'Help history unknown': '帮助记录未知',
    'Step demonstrated': '已展示该步骤', 'Step needs review': '该步骤需复查', 'Method unobserved': '未观察到解题方法', 'Mixed evidence': '观察结果不一致',
    'No reasoning submitted': '未提交推理', 'Checks disagree': '检查结果不一致', 'Answer and explanation differ': '答案与解释不一致', 'Step unverified': '步骤尚未验证',
    'Correct answer': '答案正确', 'Incorrect answer': '答案不正确', 'Partially correct answer': '答案部分正确', 'Answer unresolved': '答案尚未确定',
    'Record details': '记录详情', 'Item {question} · Topic {topic} · Graph {graph}': '题目 {question} · 知识点 {topic} · 图谱 {graph}',
    'The app checks the answer against the item key and looks for a supported calculation in the submitted explanation.': '应用会将答案与标准答案核对，并在提交的解释中查找可验证的计算。',
    'Step shown on {successes} of {attempts} first attempts with assessable work and no observed help.': '在可评估且未观察到帮助的 {attempts} 次首次作答中，{successes} 次展示了此步骤。',
    'Pilot observations for this practice tab.': '当前练习选项卡中的试点观察。', 'Observations are available until you leave this page.': '这些观察在离开此页面前可用。'
  });
  const key = 'math-practice.graph-evidence.v1';
  const panel = document.getElementById('graphEvidence');
  const content = document.getElementById('graphEvidenceBody');
  const assistance = {none: 'No in-app help observed', coach: 'After coaching', hint: 'After a hint',
    solution: 'After viewing the solution', unknown: 'Help history unknown'};
  const statuses = {demonstrated: 'Step demonstrated', needs_review: 'Step needs review',
    unobserved: 'Method unobserved', mixed: 'Mixed evidence'};
  const unresolved = {blank_reasoning: 'No reasoning submitted', assessment_disagreement: 'Checks disagree',
    answer_reasoning_conflict: 'Answer and explanation differ', unsupported_or_ambiguous_reasoning: 'Step unverified'};
  const answers = {correct: 'Correct answer', wrong: 'Incorrect answer', partial: 'Partially correct answer',
    cannot_judge: 'Answer unresolved'};
  function valid(row) {
    return row && row.shadow === true &&
      ['bank', 'questionId', 'revisionId', 'topicId', 'topicLabel', 'criterionId', 'criterion', 'graphRevision', 'mappingVersion', 'judgmentSource']
        .every(field => typeof row[field] === 'string' && row[field].length > 0) &&
      Object.hasOwn(statuses, row.status) && Object.hasOwn(assistance, row.assistance) &&
      Object.hasOwn(answers, row.answerCategory) && typeof row.quote === 'string';
  }
  let records = [];
  let saved = true;
  try {
    const stored = JSON.parse(sessionStorage.getItem(key) || '[]');
    if (Array.isArray(stored)) records = stored.filter(valid);
  } catch (_) { saved = false; }
  function element(tag, className, value) {
    const node = document.createElement(tag);
    node.className = className;
    node.textContent = value;
    return node;
  }
  function render() {
    panel.hidden = records.length === 0;
    content.replaceChildren();
    const groups = new Map();
    for (const row of records) {
      const group = JSON.stringify([row.bank, row.graphRevision, row.criterionId, row.mappingVersion]);
      if (!groups.has(group)) groups.set(group, []);
      groups.get(group).push(row);
    }
    for (const rows of groups.values()) {
      const topic = rows[0];
      const section = element('section', 'graph-criterion', '');
      section.appendChild(ui(element('h3', 'graph-topic', ''), () => window.MathPracticeTopics
        ? window.MathPracticeTopics.name(topic.topicId, topic.topicLabel) : topic.topicLabel));
      section.appendChild(element('p', 'graph-target', topic.criterion));
      const firstAttempts = new Map();
      const list = element('ol', 'graph-observations', '');
      for (const row of rows) {
        if (!firstAttempts.has(row.questionId)) firstAttempts.set(row.questionId, row);
        const item = element('li', 'graph-observation', '');
        item.appendChild(ui(element('strong', 'graph-outcome', ''), row.status === 'unobserved' && Object.hasOwn(unresolved, row.observationReason)
          ? unresolved[row.observationReason] : statuses[row.status]));
        item.appendChild(ui(element('span', 'graph-context', ''), () => t(answers[row.answerCategory]) + ' · ' + t(assistance[row.assistance])));
        if (row.quote) item.appendChild(element('q', 'graph-quote', row.quote));
        const source = element('details', 'graph-source', '');
        source.appendChild(ui(element('summary', '', ''), 'Record details'));
        source.appendChild(ui(element('p', '', ''), 'Item {question} · Topic {topic} · Graph {graph}',
          {question: row.questionId, topic: row.topicId, graph: row.graphRevision.slice(0, 8)}));
        if (row.judgmentSource === 'deterministic_bounded_math_parser') {
          source.appendChild(ui(element('p', '', ''), 'The app checks the answer against the item key and looks for a supported calculation in the submitted explanation.'));
        }
        item.appendChild(source);
        list.appendChild(item);
      }
      section.appendChild(list);
      const independent = [...firstAttempts.values()].filter(row => row.action === 'submit' && row.assistance === 'none' &&
        ['demonstrated', 'needs_review'].includes(row.status));
      if (independent.length) {
        const successes = independent.filter(row => row.status === 'demonstrated').length;
        section.appendChild(ui(element('p', 'graph-summary', ''), 'Step shown on {successes} of {attempts} first attempts with assessable work and no observed help.', {successes, attempts: independent.length}));
      }
      content.appendChild(section);
    }
    ui(document.getElementById('graphEvidenceScope'), saved
      ? 'Pilot observations for this practice tab.' : 'Observations are available until you leave this page.');
  }
  function record(row) {
    if (!valid(row)) return;
    const previous = records.findIndex(item => item.bank === row.bank && item.questionId === row.questionId &&
      item.revisionId === row.revisionId && item.criterionId === row.criterionId);
    if (previous === -1) records.push(row);
    else records[previous] = row;
    try { sessionStorage.setItem(key, JSON.stringify(records)); saved = true; }
    catch (_) { saved = false; }
    render();
  }
  window.MathPracticeGraph = {record};
  render();
})();
