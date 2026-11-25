/* Browser-owned recommendation evidence contains only scored, submitted work. */
(function () {
  'use strict';
  const KEY = 'math-practice.practice-recommendations.history.v1';
  const PAUSE_KEY = 'math-practice.practice-recommendations.pause.v1';
  const MAX_ANSWERS = 128;
  const MAX_RETRIES = 4;
  const outcomes = {correct: 'correct', wrong: 'incorrect', partial: 'partial'};
  const banks = ['cn-math', 'amc'];
  const DAY = 86400000;

  function dayNumber(date) {
    return Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()) / DAY;
  }

  function readHistory(storage) {
    try {
      const rows = JSON.parse(storage.getItem(KEY));
      if (!Array.isArray(rows)) return [];
      return rows.filter(row => row && banks.includes(row.bank) && typeof row.questionId === 'string' &&
        /^[A-Za-z0-9_.:-]{1,200}$/.test(row.questionId) && Object.values(outcomes).includes(row.outcome) &&
        Number.isSafeInteger(row.day)).slice(-MAX_ANSWERS)
        .map(({bank, questionId, outcome, day}) => ({bank, questionId, outcome, day}));
    } catch (_) { return []; }
  }

  function scoreKey(row) {
    return `${row.bank}:${row.questionId}:${row.day}`;
  }

  function wireHistory(rows, today, retries = []) {
    const events = [];
    let previousDay, rowIndex = 0;
    function addGap(day) {
      if (previousDay !== undefined && day > previousDay) events.push({gapDays: Math.min(1826, day - previousDay)});
      previousDay = day;
    }
    function addScore(row) {
      addGap(Math.max(row.day, previousDay ?? row.day));
      events.push({questionId: row.questionId, outcome: row.outcome});
    }
    const positions = new Map(rows.map((row, index) => [scoreKey(row), index]));
    for (const {questionId, outcome, anchor} of retries) {
      if (!positions.has(anchor)) continue;
      const boundary = positions.get(anchor) + 1;
      while (rowIndex < boundary) addScore(rows[rowIndex++]);
      addGap(Math.max(today, previousDay ?? today));
      events.push({questionId, outcome, retry: true});
    }
    while (rowIndex < rows.length) addScore(rows[rowIndex++]);
    addGap(today);
    return events;
  }

  const domainLabels = {
    'domain:number-algebra': 'Number and algebra',
    'domain:geometry': 'Geometry',
    'domain:probability-statistics': 'Probability and statistics',
    'domain:modeling-practice': 'Modeling and mathematical practice',
    'domain:prealgebra': 'Prealgebra',
    'domain:algebra': 'Algebra',
    'domain:number-theory': 'Number theory',
    'domain:counting-probability': 'Counting and probability'
  };
  const copy = {
    'Practice recommendations': '练习推荐',
    'Suggest my next problem': '推荐下一题',
    'Start review problem': '开始做复习题',
    'Continue practice': '继续练习',
    'Finding a problem…': '正在选择题目…',
    'Try again': '重试',
    'Practice the same skill': '继续练习当前知识点',
    'Review a supporting skill': '复习相关的基础知识',
    'Review {topic}': '复习{topic}',
    'Try another problem on the skill you were working on.': '再做一道题，继续练习刚才的知识点。',
    'A building block for {topic}.': '这是学习「{topic}」的基础知识。',
    'This is a building block for the topic you were working on.': '这是学习刚才那个主题的基础知识。',
    'Pause suggestions for today': '今天暂停推荐',
    'Resume recommendations': '恢复题目推荐',
    'Recommendations are paused for today. You can still choose problems yourself.': '今天的题目推荐已暂停，你仍可自己选题练习。',
    'Practice {topic}': '练习{topic}',
    'Change topic to {topic}': '换个主题，练习{topic}',
    'Browse topics': '浏览练习主题',
    'Choose another topic': '换个主题',
    'Number and algebra': '数与代数',
    'Probability and statistics': '统计与概率',
    'Modeling and mathematical practice': '综合与实践',
    'There’s no follow-up suggestion for this topic right now.': '这个主题暂时没有合适的推荐题目。',
    'You’ve reached today’s limit for suggestions. You can still practice on your own.': '今天的题目推荐已达到上限，你仍可自主练习。',
    'You’re practicing on your own. You can choose more problems from the question bank.': '你正在自主练习，可以从题库继续选题。',
    'There is no suggestion for this problem yet. You can choose another from the question bank.': '这道题暂时没有推荐。你可以从题库里再选一道。',
    'The suggestion could not load. Try again or choose a problem from the bank.': '推荐未能加载。请重试，或自行从题库中选题。'
  };

  function setup(o) {
    const agreement = window.MathPracticeAgreement;
    const grant = () => agreement?.experimentalGrant?.() || '';
    const {panel, button, heading, reference, status, open, pause, alternate, resume} = o;
    const language = window.MathPracticeLanguage;
    language?.register(copy);
    let controller, suggestion, anchor, current, currentGrant, opening, pendingScore;
    let stop, manualDay, dayRefresh, pauseMarker = readPause(), message = '', failed = false;
    let renderedMessage, renderedChoice, renderedSuggestion, renderedButton;
    let retryDay, retryGrant;
    const retries = [], recordedRevisions = new Set();
    const today = () => dayNumber(new Date());
    const sameContext = (a, b) => a?.question.id === b?.question.id && a?.bank === b?.bank && a?.targetId === b?.targetId;
    function syncRetries(day, activeGrant) {
      if (day === retryDay && activeGrant === retryGrant) return;
      retryDay = day;
      retryGrant = activeGrant;
      retries.length = 0;
      recordedRevisions.clear();
    }
    const focused = element => window.document?.activeElement === element;
    function conceptName(id) {
      const title = id && window.MathPracticeTopics?.name(id, '');
      return title && title !== id ? title : '';
    }
    function storage() { return window.localStorage; }
    function readPause() {
      try { return JSON.parse(storage().getItem(PAUSE_KEY)); }
      catch (_) { return null; }
    }
    function grantId(value) {
      try { return JSON.parse(value).grantId || value; }
      catch (_) { return value; }
    }
    function isPaused() { return !!currentGrant && pauseMarker?.day === today() && pauseMarker.grant === grantId(currentGrant); }
    function setPause(value) {
      pauseMarker = value;
      try {
        if (value) storage().setItem(PAUSE_KEY, JSON.stringify(value));
        else storage().removeItem(PAUSE_KEY);
      } catch (_) { /* Keep the choice in this tab when storage is unavailable. */ }
    }
    function scheduleDayRefresh() {
      if (dayRefresh || !window.setTimeout) return;
      const next = new Date();
      next.setHours(24, 0, 0, 0);
      dayRefresh = window.setTimeout(() => { dayRefresh = null; refresh(); }, Math.max(1, next.getTime() - Date.now()));
    }
    function alternateQuestion() { return stop?.choice && o.lookup(stop.choice.problemId, current?.bank); }
    function render() {
      const paused = isPaused(), manual = manualDay === today();
      if (paused || manual || stop || retries.length) scheduleDayRefresh();
      button.hidden = paused || manual || !!stop || !!suggestion;
      button.setAttribute('aria-disabled', String(!!controller || !!opening));
      const buttonText = failed ? 'Try again' : 'Suggest my next problem';
      if (renderedButton !== buttonText) { o.text(button, buttonText); renderedButton = buttonText; }
      open.hidden = !suggestion || paused;
      open.setAttribute('aria-disabled', String(!!opening));
      pause.hidden = (!stop && !suggestion) || !!stop?.budgetReached || paused;
      const choice = alternateQuestion() ? stop.choice : null;
      alternate.hidden = paused || (!stop && !suggestion && !manual && !failed) || (!choice && !o.canBrowse());
      const label = alternate.hidden ? null : choice || (suggestion ? 'Choose another topic' : 'Browse topics');
      if (label && label !== renderedChoice) {
        o.text(alternate, choice ? () => ({key: 'Change topic to {topic}', params: {topic: choice.topicId ?
          window.MathPracticeTopics?.name(choice.topicId, choice.topic) || choice.topic :
          language?.t(choice.topic) || choice.topic}}) : label);
      }
      renderedChoice = label;
      resume.hidden = !paused;
      if (heading && reference && renderedSuggestion !== suggestion) {
        heading.hidden = reference.hidden = !suggestion;
        if (suggestion) {
          const {q, review, conceptId} = suggestion;
          o.text(heading, () => {
            const topic = conceptName(conceptId);
            return topic ? {key: review ? 'Review {topic}' : 'Practice {topic}', params: {topic}} :
              review ? 'Review a supporting skill' : 'Practice the same skill';
          });
          o.text(reference, () => o.title(q, conceptId));
          o.text(open, review ? 'Start review problem' : 'Continue practice');
        }
        renderedSuggestion = suggestion;
      }
      let text = message;
      if (paused) text = 'Recommendations are paused for today. You can still choose problems yourself.';
      else if (manual) text = 'You’re practicing on your own. You can choose more problems from the question bank.';
      else if (stop?.budgetReached) text = 'You’ve reached today’s limit for suggestions. You can still practice on your own.';
      else if (stop) text = 'There’s no follow-up suggestion for this topic right now.';
      else if (suggestion) text = suggestion.reason;
      if (text !== renderedMessage) { o.text(status, text); renderedMessage = text; }
    }
    function reset() {
      controller?.abort();
      controller = null;
      suggestion = null;
      stop = null;
      message = '';
      failed = false;
    }
    function refresh() {
      const ctx = o.context(), nextGrant = grant();
      syncRetries(today(), nextGrant);
      if (nextGrant !== currentGrant) {
        manualDay = null;
        if (currentGrant) {
          opening = null;
          if (pauseMarker?.grant !== grantId(nextGrant)) pauseMarker = null;
        }
      }
      if (nextGrant !== currentGrant || !sameContext(ctx, current)) {
        reset();
        anchor = null;
      }
      if (stop && stop.day !== today()) reset();
      current = ctx;
      currentGrant = nextGrant;
      panel.hidden = !ctx?.question || ctx.scored === false || !currentGrant || !banks.includes(ctx.bank) || location.protocol === 'file:';
      render();
    }
    function record(question, bank, answer, {answerChanged, revisionId} = {}) {
      const submissionGrant = grant();
      if (!submissionGrant || !banks.includes(bank)) return;
      const outcome = outcomes[o.classify(question, answer)];
      if (!outcome) return;
      const questionId = question.id, day = today();
      reset();
      render();
      function append() {
        if (grant() !== submissionGrant) return;
        const currentDay = today();
        syncRetries(currentDay, submissionGrant);
        const currentRevision = day === currentDay && revisionId;
        if (currentRevision && recordedRevisions.has(revisionId)) return;
        try {
          const store = storage(), rows = readHistory(store);
          if (rows.some(row => row.bank === bank && row.questionId === questionId)) {
            if (currentRevision && answerChanged && outcome !== 'partial') {
              retries.push({questionId, outcome, anchor: scoreKey(rows[rows.length - 1])});
              if (retries.length > MAX_RETRIES) retries.shift();
              recordedRevisions.add(revisionId);
              scheduleDayRefresh();
            }
            return;
          }
          rows.push({bank, questionId, outcome, day});
          const saved = JSON.stringify(rows.slice(-MAX_ANSWERS));
          store.setItem(KEY, saved);
          if (grant() !== submissionGrant && store.getItem(KEY) === saved) store.removeItem(KEY);
          else if (currentRevision) recordedRevisions.add(revisionId);
        } catch (_) { /* An unavailable browser store still permits a fresh recommendation. */ }
      }
      // Serialize simultaneous scored submissions from different practice tabs.
      if (window.navigator?.locks) pendingScore = window.navigator.locks.request(KEY, append).catch(append);
      else append();
    }
    async function recommend(payload, signal) {
      if (o.hosted) return window.MathPracticeServices.recommendation(payload, {signal});
      const reply = await fetch('/api/practice/recommendation', {method: 'POST', signal,
        cache: 'no-store', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
      if (!reply.ok) throw new Error('Recommendation unavailable.');
      return reply.json();
    }
    button.addEventListener('click', async function () {
      refresh();
      if (panel.hidden || button.hidden || controller || opening) return;
      const ctx = current, requestGrant = currentGrant;
      reset();
      controller = new AbortController();
      const request = controller;
      const requestCurrent = () => !request.signal.aborted && grant() === requestGrant && sameContext(ctx, o.context());
      message = 'Finding a problem…';
      render();
      try {
        await pendingScore;
        if (!requestCurrent()) return;
        let rows = [];
        try { rows = readHistory(storage()); } catch (_) {}
        const target = anchor?.target || (ctx.targetId ? {targetId: ctx.targetId} : {targetQuestionId: ctx.question.id});
        const targetQuestion = anchor?.question || ctx.question, day = today();
        syncRetries(day, requestGrant);
        const payload = {...target, bank: ctx.bank, excludeQuestionId: ctx.question.id, history: wireHistory(rows, day, retries)};
        if (targetQuestion.id !== ctx.question.id) payload.anchorQuestionId = targetQuestion.id;
        const reply = await recommend(payload, request.signal);
        if (!requestCurrent() || day !== today()) return;
        const item = reply.recommendation;
        const q = item && o.lookup(item.questionId, ctx.bank);
        if (q && q.id !== ctx.question.id && !reply.stopReason) {
          const review = item.prerequisiteDepth > 0;
          const assessed = targetQuestion.assessedIds || targetQuestion.knowledgeGraph?.assessedIds;
          const targetConceptId = target.targetId || (assessed?.length === 1 ? assessed[0] : null);
          const reason = review ? () => {
            const topic = conceptName(targetConceptId);
            return topic ? {key: 'A building block for {topic}.', params: {topic}} :
              'This is a building block for the topic you were working on.';
          } : 'Try another problem on the skill you were working on.';
          suggestion = {q, target, question: targetQuestion, review, reason,
            conceptId: Array.isArray(item.matchedConceptIds) ? item.matchedConceptIds[0] : null};
        } else if (!item && ['visit_budget', 'no_suitable_question'].includes(reply.stopReason)) {
          const id = reply.alternateQuestionId;
          const alt = id && id !== ctx.question.id && o.lookup(id, ctx.bank);
          const topic = alt && (ctx.bank === 'cn-math' ? alt.topic?.label :
            domainLabels[alt.domain?.find(domain => Object.hasOwn(domainLabels, domain))]);
          const choice = topic ? {problemId: id, topic, topicId: ctx.bank === 'cn-math' ? alt.topic.id : null} : null;
          stop = {day, budgetReached: reply.stopReason === 'visit_budget', choice};
        } else if (!item && reply.stopReason === 'unsupported_scope') {
          message = 'There is no suggestion for this problem yet. You can choose another from the question bank.';
        } else {
          throw new Error('Recommendation response unavailable.');
        }
      } catch (_) {
        if (requestCurrent()) {
          failed = true;
          message = 'The suggestion could not load. Try again or choose a problem from the bank.';
        }
      } finally {
        if (controller === request) {
          const moveFocus = focused(button);
          controller = null;
          if (message === 'Finding a problem…') message = '';
          refresh();
          if (moveFocus && !open.hidden) open.focus();
          else if (moveFocus && !pause.hidden) pause.focus();
          else if (moveFocus && !alternate.hidden) alternate.focus();
        }
      }
    });
    async function openProblem(q, nextAnchor, budgetDay) {
      const attempt = opening = {};
      const openingGrant = currentGrant;
      const actionFocused = focused(open) || focused(alternate);
      anchor = null;
      render();
      try {
        const loaded = await o.select(q);
        refresh();
        if (opening !== attempt || grant() !== openingGrant) return;
        if (loaded !== q) throw new Error('Suggested problem unavailable.');
        if (current?.question.id !== q.id) return;
        anchor = nextAnchor;
        manualDay = budgetDay;
      } catch (_) {
        if (opening === attempt && grant() === openingGrant) {
          reset();
          failed = true;
          message = 'The suggestion could not load. Try again or choose a problem from the bank.';
        }
      } finally {
        if (opening === attempt) {
          opening = null;
          refresh();
          if (failed && actionFocused && !panel.hidden && !button.hidden) button.focus();
        }
      }
    }
    open.addEventListener('click', function () {
      refresh();
      if (panel.hidden || open.hidden || opening) return;
      const {q, target, question} = suggestion;
      return openProblem(q, {target, question});
    });
    pause.addEventListener('click', function () {
      refresh();
      if (panel.hidden || pause.hidden || opening) return;
      const moveFocus = focused(pause);
      setPause({day: today(), grant: grantId(currentGrant)});
      reset();
      render();
      if (moveFocus) resume.focus();
    });
    alternate.addEventListener('click', function () {
      refresh();
      if (panel.hidden || alternate.hidden || opening) return;
      const q = alternateQuestion();
      if (q) return openProblem(q, null, stop.budgetReached ? stop.day : null);
      if (stop?.budgetReached) {
        manualDay = stop.day;
        reset();
        render();
      }
      o.browse();
    });
    resume.addEventListener('click', function () {
      refresh();
      if (panel.hidden || resume.hidden) return;
      const moveFocus = focused(resume);
      setPause(null);
      render();
      if (moveFocus) button.focus();
    });
    window.addEventListener(agreement?.experimentalEvent || 'math-practice-experimental-change', refresh);
    window.addEventListener('pageshow', refresh);
    window.addEventListener('focus', refresh);
    window.addEventListener('storage', event => {
      if (event.key === KEY || event.key === null) reset();
      if (event.key === PAUSE_KEY || event.key === null) {
        pauseMarker = readPause();
        reset();
      }
      refresh();
    });
    refresh();
    return {record, refresh};
  }
  if (typeof module === 'object' && module.exports) module.exports = {wireHistory, readHistory, dayNumber, setup};
  else window.MathPracticeRecommendations = {setup};
})();
