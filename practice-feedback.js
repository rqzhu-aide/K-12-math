/* Original speech observations and submitted mathematical work stay separate. */
(function () {
  'use strict';
  const Language = window.MathPracticeLanguage;
  const t = (source, params) => Language.t(source, params);
  const ui = (node, source, params) => Language.bindText(node, source, params);
  const attribute = (node, name, source, params) => Language.bindAttribute(node, name, source, params);
  Language.register({
    'Show a hint': '显示提示', 'Hide hint': '隐藏提示', 'Hint: ': '提示：',
    'The decision model is off': '决策模型已关闭',
    'Enable the decision model in Model settings to analyze your original speech transcript.': '请在模型设置中开启决策模型，以分析原始语音转录文字。',
    'Ailleo speech and learning signals are not connected yet.': 'Ailleo 语音与学习信号服务尚未接入。',
    'Waiting for server connection': '等待服务器接入',
    'From original speech, before edits': '来自未经编辑的语音转录', 'Reading the original transcript for learning signals...': '正在从原始转录中分析学习信号…',
    'Your original transcript is ready to check. Review its learning signals when ready.': '原始转录已可检查。准备好后可查看学习信号。',
    'Learning signals returned an incomplete result. Try the check again.': '学习信号返回的结果不完整，请重新检查。',
    'Learning signals took too long. Retry when ready.': '学习信号分析超时，准备好后请重试。',
    'Could not reach learning signals. Check the backend connection.': '无法连接学习信号服务。请检查后台连接。',
    'Original speech signals unavailable': '原始语音信号不可用', 'Retry speech signals': '重试语音信号分析', 'Local app only': '仅限本地应用',
    'Learning signals are available in the local app. Your work stays in this browser.': '本地应用支持学习信号分析。你的作答保存在此浏览器中。',
    'Decision model not configured': '未配置决策模型', 'Your transcript is saved. Add a decision model in Connections to check original speech for learning signals.': '转录文字已保存。在连接设置中添加决策模型后，即可从原始语音文字中分析学习信号。',
    'The decision model assessed the original transcript.': '决策模型已分析原始语音转录文字。',
    'The decision model checked the submitted work.': '决策模型已检查提交的作答。',
    'Confidence': '自信程度', 'Clarity of reasoning': '思路表达清晰度', 'Engagement': '投入程度', 'Unsure': '不确定', 'Confident': '有信心', 'Not expressed': '未表达',
    'Clearly explained': '表达清楚', 'Some steps unclear': '部分步骤不清楚', 'Hard to follow': '难以理解', 'No explanation': '未解释',
    'Interested or persistent': '有兴趣或愿意坚持', 'Frustrated or discouraged': '感到受挫或灰心',
    'Model probability {score}': '模型概率 {score}', 'All probabilities and original speech': '所有概率与原始语音文字', 'Evidence and original speech': '依据与原始语音文字',
    'These observations describe the original transcript, not mathematical accuracy or measured certainty about you.': '这些观察描述的是原始转录文字，不代表数学正确性，也不是对你个人确定程度的测量。',
    'Original speech transcript: {transcript}': '原始语音转录：{transcript}', 'Learning signals ready from your original speech.': '原始语音的学习信号已准备好。',
    'This feedback belongs to your earlier try. Submit your changes for a fresh check.': '此反馈对应上一次作答。提交修改后可重新检查。',
    'Thinking: Submit your changes for a fresh check.': '思路：请提交修改以重新检查。', 'Choose a problem first.': '请先选择题目。', 'Choose or enter an answer before submitting.': '提交前请选择或输入答案。',
    'Thinking: Checking your reasoning...': '思路：正在检查推理…', 'Complete or clarify your answer above, then submit again.': '请补全或澄清上方答案，然后重新提交。',
    'AI reasoning feedback is available in the local app. Your work stays in this browser.': '本地应用支持 AI 推理反馈。你的作答保存在此浏览器中。',
    'Connect your own tutor in Settings for reasoning feedback.': '在设置中连接你自己的辅导模型，以获取推理反馈。',
    'Start the local launcher and add a model in Connections for reasoning feedback.': '请启动本地启动器，并在连接设置中添加模型，以获取推理反馈。',
    'Add a decision or inference model in Connections for reasoning feedback.': '在连接设置中添加分析或推理模型，即可获取推理反馈。',
    'Add an inference model in Connections for reasoning feedback.': '在连接设置中添加推理模型，即可获取推理反馈。',
    'Add your thinking and submit again for a reasoning review.': '请补充思路并重新提交，以获取推理点评。',
    'Thinking: Not checked. The model check is unavailable. Your answer check above still applies.': '思路：尚未检查。模型检查当前不可用，上方答案检查结果仍然适用。',
    'The check took too long. Submit again to retry.': '检查超时，请重新提交以重试。',
    'Could not reach the backend. Start the local launcher and submit again.': '无法连接后台。请启动本地启动器后重新提交。',
    'Thinking: Not checked.': '思路：尚未检查。', 'Correct answer; thinking not checked': '答案正确，思路尚未检查',
    'Not graded: Disputed problem.': '不评分：此题存在争议。', 'No score is assigned. You can still explore this problem.': '此题不计分，你仍可以探索解法。',
    'Correct answer and thinking': '答案和思路正确', 'Incorrect answer': '答案不正确', 'Correct answer; thinking needs review': '答案正确，思路需复查', 'Answer needs review': '答案需复查',
    'Answers {answer}: ': '答案 {answer}：', 'Answer {answer}: ': '答案 {answer}：', 'Answer: ': '答案：',
    'Correct.': '正确。', 'Not quite yet.': '还不正确。', 'Not quite yet. Check your final answer against your working.': '还不正确。请对照解题过程检查最终答案。',
    'Partially correct.': '部分正确。', 'Partially correct. Complete your answer or use the requested form.': '部分正确。请补全答案，或按要求的形式作答。',
    'Not checked automatically.': '未自动检查。', 'Not checked automatically. Compare with the reference solution.': '未自动检查，请对照参考解答。',
    'A step needs another look.': '有一步需要重新检查。', 'Partly explained.': '解释尚不完整。', 'Not checked.': '尚未检查。', 'Thinking: ': '思路：', 'Not provided yet.': '尚未提供。',
    'Generating response...': '正在生成回应…', 'Thinking: Your explanation still needs a closer review. Retry when ready.': '思路：你的解释仍需进一步检查，准备好后请重试。',
    'Thinking: Not provided yet.': '思路：尚未提供。', 'The tutor took too long. Retry when ready.': '辅导响应超时，准备好后请重试。',
    'The tutor could not connect. Check inference settings and retry.': '辅导模型无法连接。请检查推理设置后重试。', 'Retry review': '重试点评', 'Retry hint': '重试提示',
    'AI feedback is available in the local app.': '本地应用支持 AI 反馈。', 'The service returned an unreadable response. Try again.': '服务返回的响应无法读取，请重试。',
    'The check could not finish. Try again.': '检查未能完成，请重试。', 'The check returned a different submission. Submit again to retry.': '检查返回的内容对应其他提交，请重新提交以重试。',
    'The answer and reasoning check returned an incomplete result. Try submitting again.': '答案与推理检查返回的结果不完整，请重新提交。',
    'The tutor returned a different submission. Retry the review.': '辅导返回的内容对应其他提交，请重试点评。', 'The tutor returned an incomplete or overlong review. Retry the review.': '辅导返回的点评不完整或过长，请重试。',
    'Write your final answer as a decimal numeral rather than a fraction or expression.': '请将最终答案写成小数，而不是分数或表达式。',
    'Write the numerical coefficient first and omit multiplication signs between the coefficient and letters.': '请将数字系数写在前面，并省略系数与字母之间的乘号。',
    'Write the values in the order requested in the problem.': '请按题目要求的顺序写出各个数值。'
  });
  const Answers = window.MathPracticeAnswers;
  class PracticeFeedback {
    constructor(options) {
      this.o = options; this.serial = 0; this.signalSerial = 0;
      this.mathRequest = null; this.tutorRequest = null; this.signalRequest = null;
      this.evidence = null; this.submitted = null; this.hint = ''; this.initialCategory = null; this.initialAnswerCategory = null; this.mathState = 'idle';
      this.sessionId = this.practiceSession(); this.context = null; this.finalGraphs = new Set(); this.assessment = null;
      this.serviceOverrides = {};
      this.n = {};
      for (const id of ['workFeedback', 'submissionMark', 'answerFeedback', 'reasoningFeedback', 'coach', 'tutorStatus', 'hintToggle', 'hintBody', 'tutorRetry', 'reviewNote']) this.n[id] = document.getElementById(id);
      this.n.hintToggle.addEventListener('click', () => {
        if (!this.hint || this.edited()) return;
        const open = this.n.hintBody.hidden;
        this.n.hintBody.hidden = !open;
        this.showFeedbackText(this.n.hintBody, open ? this.hint : '', open);
        ui(this.n.hintToggle, open ? 'Hide hint' : 'Show a hint');
        this.n.hintToggle.setAttribute('aria-expanded', String(open));
        if (open) {
          this.context.last.openedHint = this.hint;
          this.noteAssistance('hint'); this.o.save(); this.o.typeset(this.n.hintBody);
        }
      });
      this.n.tutorRetry.addEventListener('click', () => {
        if (!this.edited() && this.initialCategory) this.requestTutor(this.initialCategory, this.initialAnswerCategory, this.serial);
      });
    }
    id() {
      return typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function' ? crypto.randomUUID()
        : Date.now().toString(36) + '-' + Math.random().toString(36).slice(2) + '-' + Math.random().toString(36).slice(2);
    }
    practiceSession() {
      try {
        const key = 'math-practice.practice-session.v1', previous = sessionStorage.getItem(key);
        if (previous) return previous;
        const id = this.id(); sessionStorage.setItem(key, id); return id;
      } catch (_) { return this.id(); }
    }
    bank() { return this.o.bank ? this.o.bank() : this.o.question() && this.o.question().bank || ''; }
    layer() { return this.o.layer ? this.o.layer() : 'ailleo'; }
    curriculumNodeId() { return this.o.curriculumNodeId ? this.o.curriculumNodeId() : null; }
    state() { return this.context; }
    previous(value) {
      const validAnswer = value && (typeof value.answer === 'string' && value.answer.length <= 2000
        || Array.isArray(value.answer) && value.answer.length <= 100 && new Set(value.answer).size === value.answer.length
          && value.answer.every(id => typeof id === 'string' && id.length > 0 && id.length <= 2000));
      if (!value || !validAnswer || typeof value.thoughts !== 'string' || value.thoughts.length > 12000
          || typeof value.coach !== 'string' || value.coach.length > 3000 || !(value.openedHint === null || typeof value.openedHint === 'string' && value.openedHint.length <= 3000)) return null;
      return {answer: Answers.copy(value.answer), thoughts: value.thoughts, coach: value.coach, openedHint: value.openedHint};
    }
    restoreTurn(value, hasHistory) {
      const q = this.o.question();
      if (!q) return;
      const compatible = value && value.version === 1 && value.sessionId === this.sessionId && value.questionId === q.id && value.bank === this.bank();
      const help = ['none', 'coach', 'hint', 'solution', 'unknown'];
      this.context = {version: 1, sessionId: this.sessionId, questionId: q.id, bank: this.bank(),
        assistance: compatible && help.includes(value.assistance) ? value.assistance : hasHistory || value ? 'unknown' : 'none', last: null};
      const last = compatible && value.last;
      if (last && typeof last.revisionId === 'string' && last.revisionId && last.revisionId.length <= 128 && this.previous(last)
          && last.turn && last.turn.revisionId === last.revisionId && help.includes(last.turn.assistance)
          && (last.turn.action === 'submit' && last.turn.previous === null || last.turn.action === 'revise' && this.previous(last.turn.previous))) {
        this.context.last = {...this.previous(last), revisionId: last.revisionId, curriculumNodeId: typeof last.curriculumNodeId === 'string' ? last.curriculumNodeId : null, curriculumLayer: ['ailleo', 'CN', 'US'].includes(last.curriculumLayer) ? last.curriculumLayer : 'ailleo', turn: {revisionId: last.revisionId,
          action: last.turn.action, assistance: last.turn.assistance, previous: this.previous(last.turn.previous)}};
      }
      else if (last) this.context.assistance = 'unknown';
    }
    ensureContext() {
      const q = this.o.question();
      if (q && (!this.context || this.context.questionId !== q.id || this.context.bank !== this.bank())) this.restoreTurn(null, false);
    }
    noteAssistance(kind) {
      this.ensureContext();
      if (!this.context) return;
      const levels = ['none', 'coach', 'hint', 'solution', 'unknown'];
      if (kind === 'solution' || levels.indexOf(kind) > levels.indexOf(this.context.assistance)) this.context.assistance = kind;
    }
    solutionOpened() { this.noteAssistance('solution'); this.o.save(); }
    freeze(question, answer, thoughts) {
      this.ensureContext();
      answer = Answers.copy(answer);
      const last = this.context.last;
      if (last && Answers.same(last.answer, answer) && last.thoughts === thoughts && (last.curriculumLayer || 'ailleo') === this.layer() && (last.curriculumNodeId || null) === this.curriculumNodeId()) return {question, bank: this.bank(), curriculumLayer: this.layer(), curriculumNodeId: this.curriculumNodeId(), answer, thoughts, turn: last.turn};
      const revisionId = this.id();
      const previous = last ? {answer: Answers.copy(last.answer), thoughts: last.thoughts, coach: last.coach, openedHint: last.openedHint} : null;
      const turn = {revisionId, action: last ? 'revise' : 'submit', assistance: this.context.assistance, previous};
      this.context.last = {revisionId, curriculumLayer: this.layer(), curriculumNodeId: this.curriculumNodeId(), answer: Answers.copy(answer), thoughts, coach: '', openedHint: null, turn};
      return {question, bank: this.bank(), curriculumLayer: this.layer(), curriculumNodeId: this.curriculumNodeId(), answer, thoughts, turn};
    }
    current(serial, submitted, value) {
      return serial === this.serial && this.submitted === submitted && !this.edited()
        && (!value || value.revisionId === undefined || value.revisionId === submitted.turn.revisionId)
        && (!value || value.curriculumLayer === undefined || value.curriculumLayer === submitted.curriculumLayer)
        && (!value || value.curriculumNodeId === undefined || value.curriculumNodeId === submitted.curriculumNodeId);
    }
    finishGraph(value, serial, submitted) {
      if (!value || !value.graphEvidence || !this.current(serial, submitted, value) || value.revisionId !== submitted.turn.revisionId) return;
      const evidence = value.graphEvidence;
      if (evidence.revisionId !== submitted.turn.revisionId || evidence.bank !== submitted.bank || evidence.questionId !== submitted.question.id) return;
      const key = submitted.turn.revisionId + ':' + JSON.stringify(value.graphEvidence);
      if (this.finalGraphs.has(key)) return;
      this.finalGraphs.add(key);
      if (this.o.graphEvidence) this.o.graphEvidence(value.graphEvidence);
    }
    async post(url, body, controller) {
      if (window.MATH_PRACTICE_HOSTED) {
        if (window.MathPracticeOnline && ['/api/assessment', '/api/tutor'].includes(url)) return window.MathPracticeOnline.post(url, body, controller, this.submitted && this.submitted.question);
        if (window.MathPracticeServices && url === '/api/learning-signals') return window.MathPracticeServices.learningSignals({question: this.o.question(), bank: this.bank(), transcript: body.transcript}, {signal: controller.signal});
        throw new Error('AI feedback is available in the local app.');
      }
      const timer = setTimeout(() => controller.abort(), 155000);
      try {
        const response = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body), signal: controller.signal});
        let value;
        try { value = JSON.parse(await response.text()); } catch (_) { throw new Error('The service returned an unreadable response. Try again.'); }
        if (!response.ok) throw new Error(value && value.error && value.error.message || 'The check could not finish. Try again.');
        return value;
      } finally { clearTimeout(timer); }
    }
    services() {
      if (window.MATH_PRACTICE_HOSTED) return {decision: false, inference: !!window.MathPracticeOnline && window.MathPracticeOnline.status().configured, localEvidence: false};
      return Object.assign({decision: false, inference: false}, this.o.services ? this.o.services() : {}, this.serviceOverrides);
    }
    signalsConfigured() {
      if (!window.MATH_PRACTICE_HOSTED) return this.services().decision;
      const service = window.MathPracticeServices && window.MathPracticeServices.status('decision');
      return !!service && service.configured && service.enabled;
    }
    async waitServices() { if (!window.MATH_PRACTICE_HOSTED && this.o.waitServices) await this.o.waitServices(); }
    updateServices(value) {
      for (const role of ['decision', 'inference']) {
        if (typeof value[role + 'Configured'] === 'boolean') this.serviceOverrides[role] = value[role + 'Configured'];
      }
    }
    cancelMath() {
      this.serial++;
      if (this.mathRequest) this.mathRequest.abort();
      if (this.tutorRequest) this.tutorRequest.abort();
      this.mathRequest = null; this.tutorRequest = null;
      this.o.setRunning(false);
    }
    clear() {
      this.cancelMath(); this.signalSerial++;
      if (this.signalRequest) this.signalRequest.abort();
      this.signalRequest = null; this.evidence = null; this.submitted = null; this.hint = '';
      this.context = null; this.assessment = null;
      this.mathState = 'idle';
      this.showSubmissionMark();
      this.n.workFeedback.hidden = true;
    }
    restore(evidence) {
      if (!evidence || typeof evidence.transcript !== 'string' || !evidence.transcript.trim()) return;
      this.evidence = evidence;
      if (this.validSignals(evidence.signals)) this.renderSignals();
      else if (this.signalsConfigured()) this.signalError('Your original transcript is ready to check. Review its learning signals when ready.');
      else this.skipSignals();
    }
    recorded(transcript) {
      if (!transcript || !this.o.question()) return;
      this.evidence = {transcript, signals: null};
      this.o.save();
      this.checkSignals();
    }
    validSignals(signals) {
      return Array.isArray(signals) && signals.length === 3 && ['confidence', 'reasoning', 'engagement'].every((id, i) => {
        const s = signals[i];
        return s && s.id === id && typeof s.title === 'string' && typeof s.label === 'string'
          && (typeof s.evidence === 'string' && s.evidence.trim().length > 0
            || typeof s.score === 'number' && Number.isFinite(s.score) && s.score >= 0 && s.score <= 1
            && Array.isArray(s.distribution) && s.distribution.every(d => typeof d.label === 'string' && typeof d.score === 'number' && Number.isFinite(d.score) && d.score >= 0 && d.score <= 1));
      });
    }
    async checkSignals() {
      const q = this.o.question(), evidence = this.evidence;
      if (!q || !evidence) return;
      await this.waitServices();
      if (this.evidence !== evidence || !this.o.question() || this.o.question().id !== q.id) return;
      if (!this.signalsConfigured()) { this.skipSignals(); return; }
      if (this.signalRequest) this.signalRequest.abort();
      const serial = ++this.signalSerial, controller = new AbortController(); this.signalRequest = controller;
      this.o.panel.dataset.state = 'loading'; ui(this.o.panelStatus, 'From original speech, before edits');
      this.o.results.replaceChildren(ui(this.o.el('p', 'signals-loading'), 'Reading the original transcript for learning signals...'));
      this.o.collapse(false);
      try {
        const reply = await this.post('/api/learning-signals', {questionId: q.id, transcript: evidence.transcript}, controller);
        if (serial !== this.signalSerial) return;
        this.updateServices(reply);
        if (reply.decisionConfigured === false) { this.skipSignals(); return; }
        if (reply.questionId !== q.id || reply.transcript !== evidence.transcript || !this.validSignals(reply.signals)) throw new Error('Learning signals returned an incomplete result. Try the check again.');
        this.evidence = {transcript: evidence.transcript, signals: reply.signals}; this.o.save(); this.renderSignals();
        this.o.connection('decision', 'ok', 'Ready', 'The decision model assessed the original transcript.');
      } catch (error) {
        if (serial === this.signalSerial) this.signalError(error.name === 'AbortError' ? 'Learning signals took too long. Retry when ready.' : error instanceof TypeError ? 'Could not reach learning signals. Check the backend connection.' : error.message);
      } finally { if (serial === this.signalSerial) this.signalRequest = null; }
    }
    signalError(message) {
      if (!this.signalsConfigured()) { this.skipSignals(); return; }
      this.o.panel.dataset.state = 'error'; ui(this.o.panelStatus, 'Original speech signals unavailable');
      const box = this.o.el('div', 'signals-error'); box.appendChild(ui(this.o.el('p'), message));
      const retry = ui(this.o.el('button', 'ghost'), 'Retry speech signals'); retry.type = 'button'; retry.addEventListener('click', () => this.checkSignals()); box.appendChild(retry);
      this.o.results.replaceChildren(box);
    }
    skipSignals() {
      if (window.MATH_PRACTICE_HOSTED) {
        const connected = window.MathPracticeServices && window.MathPracticeServices.config().configured;
        this.o.panel.dataset.state = 'idle'; ui(this.o.panelStatus, connected ? 'The decision model is off' : 'Waiting for server connection');
        this.o.results.replaceChildren(ui(this.o.el('p', 'signals-empty'), connected ? 'Enable the decision model in Model settings to analyze your original speech transcript.' : 'Ailleo speech and learning signals are not connected yet.'));
        return;
      }
      this.o.panel.dataset.state = 'idle'; ui(this.o.panelStatus, 'Decision model not configured');
      this.o.results.replaceChildren(ui(this.o.el('p', 'signals-empty'), 'Your transcript is saved. Add a decision model in Connections to check original speech for learning signals.'));
    }
    renderSignals() {
      const raw = this.o.el, el = (tag, className, value) => { const node = raw(tag, className); if (value !== undefined) ui(node, value); return node; };
      const wrap = el('div', 'signals-result'), list = el('dl', 'signal-list');
      for (const signal of this.evidence.signals) {
        const row = el('div', 'signal-row'), value = el('dd'); row.appendChild(el('dt', null, signal.title));
        value.appendChild(el('span', null, signal.label));
        if (typeof signal.score === 'number') {
          const score = el('span', 'signal-probability', this.o.percent(signal.score));
          attribute(score, 'aria-label', 'Model probability {score}', {score: this.o.percent(signal.score)}); value.appendChild(score);
        }
        row.appendChild(value); list.appendChild(row);
      }
      wrap.appendChild(list);
      const hasScores = this.evidence.signals.some(signal => Array.isArray(signal.distribution));
      const details = el('details', 'signal-details'); details.appendChild(el('summary', null, hasScores ? 'All probabilities and original speech' : 'Evidence and original speech'));
      details.appendChild(el('p', null, 'These observations describe the original transcript, not mathematical accuracy or measured certainty about you.'));
      for (const signal of this.evidence.signals) {
        details.appendChild(el('strong', null, signal.title));
        if (signal.evidence) details.appendChild(raw('p', null, signal.evidence));
        for (const item of signal.distribution || []) { const row = el('div', 'signal-score'); row.appendChild(el('span', null, item.label)); row.appendChild(el('span', 'num', this.o.percent(item.score))); details.appendChild(row); }
      }
      details.appendChild(el('p', 'submitted-work', {key: 'Original speech transcript: {transcript}', params: {transcript: this.evidence.transcript}})); wrap.appendChild(details);
      this.o.results.replaceChildren(wrap); this.o.panel.dataset.state = 'ready'; ui(this.o.panelStatus, 'From original speech, before edits');
      ui(this.o.announce, 'Learning signals ready from your original speech.');
    }
    edited() {
      return !this.submitted || !this.o.question() || this.o.question().id !== this.submitted.question.id || this.bank() !== this.submitted.bank || this.layer() !== this.submitted.curriculumLayer || this.curriculumNodeId() !== this.submitted.curriculumNodeId || !Answers.same(this.o.answer(), this.submitted.answer) || this.o.draft.value.trim() !== this.submitted.thoughts;
    }
    revisionChanged() {
      const edited = this.edited();
      this.n.reviewNote.hidden = !this.submitted || !edited;
      ui(this.n.reviewNote, this.submitted && edited ? 'This feedback belongs to your earlier try. Submit your changes for a fresh check.' : '');
      this.n.hintToggle.disabled = edited; this.n.tutorRetry.disabled = edited;
      if (edited) {
        if (this.mathRequest || this.tutorRequest) {
          this.cancelMath(); this.mathState = 'idle'; this.n.tutorStatus.hidden = true; this.n.tutorRetry.hidden = true;
          ui(this.n.reasoningFeedback, 'Thinking: Submit your changes for a fresh check.');
        }
        this.n.hintBody.hidden = true; ui(this.n.hintBody, ''); this.n.hintToggle.setAttribute('aria-expanded', 'false'); ui(this.n.hintToggle, 'Show a hint');
      }
    }
    async submit() {
      const question = this.o.question(), answer = Answers.copy(this.o.answer()), thoughts = this.o.draft.value.trim();
      const gradingNote = question ? window.MathPracticeAnswers.gradingNotice(question) : null;
      if (gradingNote !== null) {
        this.cancelMath(); this.submitted = this.freeze(question, answer || '', thoughts); this.mathState = 'ready';
        this.o.submitted(this.submitted); this.showNotGraded(gradingNote); this.o.updated();
        return;
      }
      if (!question || !Answers.hasAnswer(answer)) {
        ui(this.o.note, !question ? 'Choose a problem first.' : 'Choose or enter an answer before submitting.');
        return;
      }
      this.cancelMath(); this.submitted = this.freeze(question, answer, thoughts); this.initialCategory = null; this.initialAnswerCategory = null; this.hint = ''; this.assessment = null;
      this.serviceOverrides = {};
      this.mathState = 'loading';
      this.o.submitted(this.submitted); this.o.setRunning(true);
      const n = this.n; n.workFeedback.hidden = false;
      const exactCategory = this.o.classifyAnswer(question, answer);
      this.showAnswer(answer, this.o.checkAnswer(question, answer), exactCategory);
      this.showSubmissionMark('cannot_judge', exactCategory);
      n.reasoningFeedback.className = 'reasoning-feedback'; ui(n.reasoningFeedback, 'Thinking: Checking your reasoning...');
      n.coach.hidden = true; n.hintToggle.hidden = true; n.hintBody.hidden = true; ui(n.hintBody, ''); n.tutorRetry.hidden = true; n.tutorStatus.hidden = true;
      if (exactCategory === 'partial') {
        this.showCoach(window.MathPracticeAnswers.formFeedback(question, answer) || 'Complete or clarify your answer above, then submit again.', true, true);
      }
      n.hintToggle.setAttribute('aria-expanded', 'false'); ui(n.hintToggle, 'Show a hint');
      this.revisionChanged();
      const serial = this.serial, submitted = this.submitted, controller = new AbortController(); this.mathRequest = controller;
      try {
        if (location.protocol !== 'file:') await this.waitServices();
        if (!this.current(serial, submitted)) return;
        const services = this.services();
        if (location.protocol === 'file:' || (!services.decision && !services.inference && !services.localEvidence)) {
          this.mathState = 'ready';
          const message = window.MATH_PRACTICE_HOSTED ? 'Connect your own tutor in Settings for reasoning feedback.'
            : location.protocol === 'file:' ? 'Start the local launcher and add a model in Connections for reasoning feedback.'
            : 'Add a decision or inference model in Connections for reasoning feedback.';
          this.showUnchecked(message, exactCategory);
          return;
        }
        const value = await this.post('/api/assessment', {bank: submitted.bank, curriculumLayer: submitted.curriculumLayer, curriculumNodeId: submitted.curriculumNodeId, questionId: question.id, answer, thoughts, turn: submitted.turn}, controller);
        if (!this.current(serial, submitted)) return;
        if (!this.current(serial, submitted, value)) throw new Error('The check returned a different submission. Submit again to retry.');
        if (value.questionId === question.id && Answers.same(value.answer, answer) && value.gradingStatus === 'disputed' && value.answerCategory === 'not_graded' && value.answerCorrect === null) {
          this.mathState = 'ready'; this.showNotGraded(value.gradingNote); return;
        }
        this.reconcileForm(value);
        if (value.questionId !== question.id || !Answers.same(value.answer, answer) || !this.validAnswer(value) || !['correct', 'wrong', 'partial', 'cannot_judge'].includes(value.category)) throw new Error('The answer and reasoning check returned an incomplete result. Try submitting again.');
        this.updateServices(value);
        this.showAnswer(answer, value.answerCorrect, value.answerCategory);
        if (!this.services().decision && !this.services().inference) this.showUnchecked('Add a decision or inference model in Connections for reasoning feedback.', value.answerCategory);
        else if (!thoughts && !this.services().inference) this.showUnchecked('Add your thinking and submit again for a reasoning review.', value.answerCategory);
        else this.showVerdict(value.category, '', value.answerCategory, value.answerFormFeedback);
        this.mathState = 'ready';
        this.assessment = value;
        if (value.modelUsed) this.o.connection('decision', 'ok', 'Ready', 'The decision model checked the submitted work.');
        if (this.services().inference && (value.category !== 'correct' || value.answerCategory !== 'correct')) {
          this.initialCategory = value.category; this.initialAnswerCategory = value.answerCategory;
          this.requestTutor(value.category, value.answerCategory, serial);
        } else this.finishGraph(value, serial, submitted);
        this.revisionChanged();
      } catch (error) {
        if (!this.current(serial, submitted)) return;
        this.mathState = 'error';
        if (!thoughts) this.showUnchecked('Add your thinking and submit again for a reasoning review.', exactCategory);
        else ui(n.reasoningFeedback, 'Thinking: Not checked. The model check is unavailable. Your answer check above still applies.');
        ui(this.o.note, error.name === 'AbortError' ? 'The check took too long. Submit again to retry.' : error instanceof TypeError ? 'Could not reach the backend. Start the local launcher and submit again.' : error.message);
      } finally {
        if (serial === this.serial) { this.mathRequest = null; this.o.setRunning(false); this.o.updated(); }
      }
    }
    showUnchecked(message, answerCategory) {
      const n = this.n;
      this.showSubmissionMark('cannot_judge', answerCategory);
      if (answerCategory === 'correct') attribute(n.submissionMark, 'aria-label', 'Correct answer; thinking not checked');
      ui(n.reasoningFeedback, () => t('Thinking: Not checked.') + ' ' + t(message));
      n.reasoningFeedback.className = 'reasoning-feedback verdict-cannot_judge';
      n.hintToggle.hidden = true; n.hintBody.hidden = true; n.tutorRetry.hidden = true; n.tutorStatus.hidden = true;
      ui(this.o.announce, () => n.answerFeedback.textContent + ' ' + n.reasoningFeedback.textContent);
    }
    validAnswer(value) {
      return ['correct', 'wrong', 'partial', 'cannot_judge'].includes(value.answerCategory)
        && value.answerCorrect === (value.answerCategory === 'correct' ? true : value.answerCategory === 'wrong' ? false : null);
    }
    reconcileForm(value) {
      const submitted = this.submitted;
      const message = window.MathPracticeAnswers.formFeedback(submitted.question, submitted.answer);
      const corrected = message && value.answerCategory === 'correct';
      if (corrected) { value.answerCategory = 'partial'; value.answerCorrect = null; }
      if (message && value.answerCategory === 'partial') {
        value.answerFormFeedback = message;
        if (corrected && Object.prototype.hasOwnProperty.call(value, 'clarification')) {
          value.clarification = message;
          value.hint = '';
        }
        if (corrected && Object.prototype.hasOwnProperty.call(value, 'coach')) {
          value.coach = message;
          value.hint = '';
        }
      }
    }
    showNotGraded(note) {
      const n = this.n;
      this.showSubmissionMark();
      n.workFeedback.hidden = false;
      ui(n.answerFeedback, 'Not graded: Disputed problem.'); n.answerFeedback.className = 'answer-feedback';
      ui(n.reasoningFeedback, 'No score is assigned. You can still explore this problem.'); n.reasoningFeedback.className = 'reasoning-feedback';
      n.coach.hidden = false; this.showFeedbackText(n.coach, note || 'None of the printed choices answers this problem as written.');
      n.hintToggle.hidden = true; n.hintBody.hidden = true; ui(n.hintBody, ''); n.tutorRetry.hidden = true; n.tutorStatus.hidden = true;
      ui(this.o.announce, () => n.answerFeedback.textContent + ' ' + n.coach.textContent);
    }
    showSubmissionMark(category, answerCategory) {
      const mark = this.n.submissionMark;
      const result = answerCategory === 'wrong' ? 'wrong' : !category ? '' : answerCategory === 'correct' && category === 'correct' ? 'correct' : 'review';
      const labels = {correct: 'Correct answer and thinking', wrong: 'Incorrect answer', review: answerCategory === 'correct' ? 'Correct answer; thinking needs review' : 'Answer needs review'};
      mark.dataset.result = result; mark.hidden = !result;
      attribute(mark, 'aria-label', labels[result] || '');
    }
    showAnswer(answer, correct, category, hasCoach) {
      category = category || (correct === null ? 'cannot_judge' : correct ? 'correct' : 'wrong');
      const kind = this.submitted.question.responseType || 'choice';
      const label = () => kind === 'multiSelect' ? t('Answers {answer}: ', {answer: Answers.format(answer)}) : kind !== 'choice' ? t('Answer: ') : t('Answer {answer}: ', {answer});
      const labels = {correct: 'Correct.', wrong: hasCoach ? 'Not quite yet.' : 'Not quite yet. Check your final answer against your working.', partial: hasCoach ? 'Partially correct.' : 'Partially correct. Complete your answer or use the requested form.', cannot_judge: hasCoach ? 'Not checked automatically.' : 'Not checked automatically. Compare with the reference solution.'};
      ui(this.n.answerFeedback, () => label() + t(labels[category]));
      this.n.answerFeedback.className = 'answer-feedback' + (category === 'correct' ? ' correct' : ' verdict-' + category);
    }
    showFeedbackText(node, text, hint = false, translateText = false) {
      Language.unbindText(node);
      node.textContent = text || '';
      node.dataset.hint = String(hint && Boolean(text));
      if (translateText && text) {
        node.textContent = '';
        node.appendChild(ui(document.createElement('span'), text));
      }
      if (hint && text) {
        const label = document.createElement('strong');
        ui(label, 'Hint: ');
        node.prepend(label);
      }
    }
    showCoach(coach, assistance, translateText = false) {
      this.n.coach.hidden = !coach;
      this.showFeedbackText(this.n.coach, coach, assistance, translateText);
      if (coach) {
        this.o.typeset(this.n.coach);
        if (this.context && this.context.last) {
          this.context.last.coach = coach;
          if (assistance) this.noteAssistance('coach');
          this.o.save();
        }
      }
    }
    showVerdict(category, coach, answerCategory, formFeedback) {
      this.showSubmissionMark(category, answerCategory);
      const n = this.n, labels = {correct: 'Correct.', wrong: 'A step needs another look.', partial: 'Partly explained.', cannot_judge: 'Not checked.'};
      ui(n.reasoningFeedback, () => t('Thinking: ') + t(category === 'partial' && !this.submitted.thoughts ? 'Not provided yet.' : labels[category])); n.reasoningFeedback.className = 'reasoning-feedback verdict-' + category;
      const text = coach || (answerCategory === 'partial' ? formFeedback || 'Complete or clarify your answer above, then submit again.' : '');
      this.showCoach(text, category !== 'correct' || answerCategory !== 'correct', !coach);
      ui(this.o.announce, () => n.answerFeedback.textContent + ' ' + n.reasoningFeedback.textContent + (text ? ' ' + text : ''));
    }
    validTutor(value) {
      if (!['correct', 'wrong', 'partial'].includes(value.category) || !this.validAnswer(value)
          || typeof value.coach !== 'string' || !value.coach.trim() || typeof value.hint !== 'string'
          || value.coach.length > 3000 || value.hint.length > 3000) return false;
      const text = value.coach + ' ' + value.hint;
      const script = /[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]/g;
      const characters = (text.match(script) || []).length;
      const words = text.replace(script, ' ').trim().split(/\s+/).filter(Boolean).length;
      return characters + 2 * words <= 100;
    }
    async requestTutor(category, answerCategory, serial) {
      if (this.tutorRequest || !this.services().inference || location.protocol === 'file:' || window.MathPracticeAnswers.gradingNotice(this.submitted.question) !== null) return;
      const submitted = this.submitted, controller = new AbortController(), n = this.n;
      this.tutorRequest = controller; n.tutorRetry.hidden = true; n.tutorStatus.hidden = false;
      const reviewing = [category, answerCategory].some(value => value === 'partial' || value === 'cannot_judge');
      n.tutorStatus.dataset.state = 'loading';
      ui(n.tutorStatus, 'Generating response...');
      try {
        const value = await this.post('/api/tutor', {bank: submitted.bank, curriculumLayer: submitted.curriculumLayer, curriculumNodeId: submitted.curriculumNodeId, questionId: submitted.question.id, answer: submitted.answer, thoughts: submitted.thoughts, category, answerCategory, turn: submitted.turn}, controller);
        if (!this.current(serial, submitted)) return;
        if (!this.current(serial, submitted, value)) throw new Error('The tutor returned a different submission. Retry the review.');
        this.updateServices(value);
        if (value.configured === false || value.inferenceConfigured === false) {
          this.serviceOverrides.inference = false; n.tutorStatus.hidden = true; n.tutorRetry.hidden = true;
          if (!this.services().decision) this.showUnchecked('Add an inference model in Connections for reasoning feedback.', answerCategory);
          else if (category === 'cannot_judge') this.showVerdict(category, '', answerCategory);
          this.finishGraph(this.assessment, serial, submitted);
          return;
        }
        if (value.questionId === submitted.question.id && Answers.same(value.answer, submitted.answer) && value.gradingStatus === 'disputed' && value.answerCategory === 'not_graded' && value.answerCorrect === null) { this.showNotGraded(value.gradingNote); return; }
        this.reconcileForm(value);
        if (value.questionId !== submitted.question.id || !Answers.same(value.answer, submitted.answer) || !this.validTutor(value)
          || value.category === 'correct' && value.answerCategory === 'correct' && value.hint.trim()) throw new Error('The tutor returned an incomplete or overlong review. Retry the review.');
        this.showAnswer(submitted.answer, value.answerCorrect, value.answerCategory, true);
        this.showVerdict(value.category, value.coach.trim(), value.answerCategory, value.answerFormFeedback); this.hint = value.hint.trim();
        n.hintBody.hidden = true; ui(n.hintBody, ''); n.hintToggle.setAttribute('aria-expanded', 'false'); ui(n.hintToggle, 'Show a hint');
        n.hintToggle.hidden = !this.hint; n.tutorStatus.hidden = true;
        this.finishGraph(value, serial, submitted);
        this.o.connection('inference', 'ok', 'Ready', 'The inference model returned a mathematical review.'); this.revisionChanged();
      } catch (error) {
        if (!this.current(serial, submitted)) return;
        if (category === 'cannot_judge') ui(n.reasoningFeedback, submitted.thoughts ? 'Thinking: Your explanation still needs a closer review. Retry when ready.' : 'Thinking: Not provided yet.');
        ui(n.tutorStatus, error.name === 'AbortError' ? 'The tutor took too long. Retry when ready.' : error instanceof TypeError ? 'The tutor could not connect. Check inference settings and retry.' : error.message);
        n.tutorRetry.hidden = false; ui(n.tutorRetry, reviewing ? 'Retry review' : 'Retry hint'); this.revisionChanged();
        this.finishGraph(this.assessment, serial, submitted);
      } finally {
        if (serial === this.serial) {
          this.tutorRequest = null;
          n.tutorStatus.dataset.state = '';
        }
      }
    }
  }
  window.MathPracticeFeedback = PracticeFeedback;
})();
