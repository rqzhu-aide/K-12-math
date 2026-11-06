/* Per-tab observations attached to reviewed knowledge-graph criteria. */
(function () {
  'use strict';
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
      section.appendChild(element('h3', 'graph-topic', topic.topicLabel));
      section.appendChild(element('p', 'graph-target', topic.criterion));
      const firstAttempts = new Map();
      const list = element('ol', 'graph-observations', '');
      for (const row of rows) {
        if (!firstAttempts.has(row.questionId)) firstAttempts.set(row.questionId, row);
        const item = element('li', 'graph-observation', '');
        item.appendChild(element('strong', 'graph-outcome', row.status === 'unobserved' && Object.hasOwn(unresolved, row.observationReason)
          ? unresolved[row.observationReason] : statuses[row.status]));
        item.appendChild(element('span', 'graph-context', answers[row.answerCategory] + ' · ' + assistance[row.assistance]));
        if (row.quote) item.appendChild(element('q', 'graph-quote', row.quote));
        const source = element('details', 'graph-source', '');
        source.appendChild(element('summary', '', 'Record details'));
        source.appendChild(element('p', '', 'Item ' + row.questionId + ' · Topic ' + row.topicId +
          ' · Graph ' + row.graphRevision.slice(0, 8)));
        if (row.judgmentSource === 'deterministic_bounded_math_parser') {
          source.appendChild(element('p', '', 'The app checks the answer against the item key and looks for a supported calculation in the submitted explanation.'));
        }
        item.appendChild(source);
        list.appendChild(item);
      }
      section.appendChild(list);
      const independent = [...firstAttempts.values()].filter(row => row.action === 'submit' && row.assistance === 'none' &&
        ['demonstrated', 'needs_review'].includes(row.status));
      if (independent.length) {
        const successes = independent.filter(row => row.status === 'demonstrated').length;
        section.appendChild(element('p', 'graph-summary', 'Step shown on ' + successes + ' of ' +
          independent.length + ' first attempts with assessable work and no observed help.'));
      }
      content.appendChild(section);
    }
    document.getElementById('graphEvidenceScope').textContent = saved
      ? 'Pilot observations for this practice tab.' : 'Observations are available until you leave this page.';
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
