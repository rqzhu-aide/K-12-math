/* Optional owner services. Tutor credentials and raw audio are never persisted here. */
(function () {
  'use strict';
  const SESSION = 'math-practice.optional-services.session.v1';
  const NOTICE = '2026-11-16';
  const EVENT = 'math-practice-services-change';
  const ROLES = ['speech', 'decision'];
  const RECOMMENDATION_SCOPE = 'recommendation';
  const RECOMMENDATION_BANKS = ['cn-math', 'amc'];
  const RECOMMENDATION_OUTCOMES = ['correct', 'incorrect', 'partial'];
  const STOP_REASONS = ['visit_budget', 'no_suitable_question', 'unsupported_scope'];
  const MAX_HISTORY = 256;
  const MAX_RETRIES = 4;
  const MAX_GAP_DAYS = 1826.25;
  const messages = {
    unconfigured: 'Ailleo’s server connection is not ready yet.',
    permission: 'Review the agreement and enable experimental features in Settings first.',
    consent_required: 'Review the experimental features agreement in Settings before trying again.',
    notice_outdated: 'The service agreement changed. Review it in Settings before trying again.',
    unauthorized: 'Your Ailleo service session ended. Try again to start a new session.',
    token_expired: 'Your Ailleo service session expired. Try again to start a new session.',
    session_mismatch: 'Your Ailleo service session changed. Try again.',
    rate_limited: 'Ailleo has reached its current usage limit. Wait a moment and try again.',
    upstream_unavailable: 'The Ailleo service is temporarily unavailable. Try again later.',
    model_invalid: 'The Ailleo service returned an incomplete result. Try again.',
    payload_too_large: 'This recording is too large. Record up to one minute and try again.',
    bad_audio: 'The recording could not be read. Record again or type your thinking.',
    origin_not_allowed: 'This website is not connected to the Ailleo service yet.',
    challenge: 'The Ailleo connection check could not finish. Try again from Settings.',
    metadata: 'This problem’s service information is not ready. You can still type your thinking.',
    response: 'The Ailleo service returned an incomplete result. Try again.',
    network: 'Could not reach Ailleo. Check your connection and try again.',
    timeout: 'The Ailleo service took too long. Try again.',
    storage: 'Allow browser storage for this website to use Ailleo services.',
    failed: 'The Ailleo service could not finish this request. Try again.'
  };
  if (window.MathPracticeLanguage) window.MathPracticeLanguage.register({
    [messages.unconfigured]: 'Ailleo 的服务器连接尚未准备好。',
    [messages.permission]: '请先在设置中阅读协议，并开启实验性功能。',
    [messages.consent_required]: '请先在设置中阅读实验性功能协议，然后重试。',
    [messages.notice_outdated]: '服务协议已更新。请先在设置中查看，然后重试。',
    [messages.unauthorized]: 'Ailleo 服务会话已结束。请重试以开始新会话。',
    [messages.token_expired]: 'Ailleo 服务会话已过期。请重试以开始新会话。',
    [messages.session_mismatch]: 'Ailleo 服务会话已更改，请重试。',
    [messages.rate_limited]: 'Ailleo 已达到当前用量限制。请稍后重试。',
    [messages.upstream_unavailable]: 'Ailleo 服务暂时不可用，请稍后重试。',
    [messages.model_invalid]: 'Ailleo 服务返回的结果不完整，请重试。',
    [messages.payload_too_large]: '这段录音过大。请将录音控制在一分钟内，然后重试。',
    [messages.bad_audio]: '无法读取录音。请重新录音，或输入思路。',
    [messages.origin_not_allowed]: '本站尚未连接到 Ailleo 服务。',
    [messages.challenge]: 'Ailleo 连接验证未完成，请在设置中重试。',
    [messages.metadata]: '此题的服务信息尚未准备好。你仍可以输入思路。',
    [messages.network]: '无法连接 Ailleo。请检查网络后重试。',
    [messages.timeout]: 'Ailleo 服务超时，请重试。',
    [messages.storage]: '请允许本站使用浏览器存储，以使用 Ailleo 服务。',
    [messages.failed]: 'Ailleo 服务未能完成此请求，请重试。'
  });
  const clean = value => typeof value === 'string' ? value.trim() : '';
  function failure(code, message) {
    const error = new Error(message || messages[code] || messages.failed);
    error.name = 'OptionalServiceError'; error.code = code;
    return error;
  }
  function aborted() { const error = new Error('Request cancelled.'); error.name = 'AbortError'; return error; }
  function read(storage, key) {
    try { const value = JSON.parse(storage.getItem(key)); return value && typeof value === 'object' && !Array.isArray(value) ? value : {}; }
    catch (_) { return {}; }
  }
  function ownerWindow() {
    try { if (window.top && window.top.location.origin === location.origin) return window.top; } catch (_) {}
    return window;
  }
  function deployment() {
    const owner = ownerWindow();
    return owner.MATH_PRACTICE_HOSTED && owner.MATH_PRACTICE_HOSTED.services
      || window.MATH_PRACTICE_HOSTED && window.MATH_PRACTICE_HOSTED.services || {};
  }
  function configuration() {
    const value = deployment(); let baseUrl = '';
    try {
      const url = new URL(value.baseUrl);
      if (url.protocol === 'https:' && !url.username && !url.password && !url.search && !url.hash) baseUrl = url.href.replace(/\/+$/, '');
    } catch (_) {}
    // The hosted deployment installs the callback for its confirmed Turnstile key and action.
    const challengeConfigured = typeof value.getChallengeToken === 'function';
    return {configured: !!baseUrl && challengeConfigured, baseUrl, challengeConfigured};
  }
  function notice() { return clean(deployment().noticeVersion) || NOTICE; }
  const agreement = window.MathPracticeAgreement;
  function currentGrant() { return agreement?.experimentalGrant?.(notice()) || ''; }
  function changed() {
    const targets = new Set([window, ownerWindow()]);
    for (const target of targets) {
      try { target.dispatchEvent(new target.CustomEvent(EVENT)); } catch (_) {
        if (typeof CustomEvent !== 'undefined') target.dispatchEvent(new CustomEvent(EVENT));
      }
    }
  }
  function shared() {
    const owner = ownerWindow();
    if (!owner.__mathPracticeOptionalServices) owner.__mathPracticeOptionalServices = new Map();
    const key = configuration().baseUrl + '|' + notice();
    if (!owner.__mathPracticeOptionalServices.has(key)) owner.__mathPracticeOptionalServices.set(key, {tail: Promise.resolve(), health: {speech: null, decision: null}});
    return owner.__mathPracticeOptionalServices.get(key);
  }
  function roleName(role) { if (!ROLES.includes(role)) throw failure('bad_request'); return role; }
  function status(role) {
    roleName(role);
    const configured = configuration().configured, enabled = Boolean(currentGrant()), available = shared().health[role];
    return {configured, enabled, available,
      state: !configured ? 'unconfigured' : !enabled ? 'off' : available === null ? 'unchecked' : available ? 'ready' : 'unavailable'};
  }
  function route(path) {
    const config = configuration();
    if (!config.configured) throw failure('unconfigured');
    if (typeof path !== 'string' || !path.startsWith('/api/') || path.includes('..') || /[?#\\]/.test(path)) throw failure('unconfigured');
    return config.baseUrl + path;
  }
  async function request(url, options, externalSignal, milliseconds = 150000) {
    if (externalSignal && externalSignal.aborted) throw aborted();
    const controller = new AbortController(); let timedOut = false;
    const cancel = () => controller.abort();
    if (externalSignal) externalSignal.addEventListener('abort', cancel, {once: true});
    const timer = setTimeout(() => { timedOut = true; controller.abort(); }, milliseconds);
    try {
      const response = await fetch(url, {...options, credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer', signal: controller.signal});
      let value;
      try { value = await response.json(); } catch (_) { throw failure('response'); }
      if (!response.ok) {
        const rawCode = value && value.error && value.error.code;
        const code = typeof rawCode === 'string' && /^[a-z_]{1,60}$/.test(rawCode) ? rawCode : 'failed';
        const error = failure(code, code.includes('challenge') || code.startsWith('turnstile_') ? messages.challenge : undefined);
        const retry = response.headers && Number(response.headers.get('Retry-After'));
        if (Number.isFinite(retry) && retry > 0) error.retryAfter = retry;
        throw error;
      }
      if (externalSignal && externalSignal.aborted) throw aborted();
      return value;
    } catch (error) {
      if (externalSignal && externalSignal.aborted) throw aborted();
      if (timedOut) throw failure('timeout');
      if (error && error.name === 'OptionalServiceError') throw error;
      if (error && error.name === 'AbortError') throw error;
      throw failure('network');
    } finally {
      clearTimeout(timer);
      if (externalSignal) externalSignal.removeEventListener('abort', cancel);
    }
  }
  async function check(role) {
    roleName(role);
    const path = deployment().statusRoutes && deployment().statusRoutes[role] || '/api/status/' + role;
    // The public gateway exposes these health routes without a session token.
    try {
      const value = await request(route(path), {method: 'GET'}, null, 15000);
      if (!value || typeof value.available !== 'boolean') throw failure('response');
      shared().health[role] = value.available; changed();
      return {available: value.available, checked: clean(value.checked), model: clean(value.model)};
    } catch (error) { shared().health[role] = false; changed(); throw error; }
  }
  function loadSession() {
    let value = {};
    try { value = read(sessionStorage, SESSION); } catch (_) {}
    return value.baseUrl === configuration().baseUrl ? value : {};
  }
  function forgetSession(state) {
    state.session = null; state.consentKey = '';
    try { sessionStorage.removeItem(SESSION); } catch (_) {}
  }
  async function challengeToken(renewal, signal) {
    if (signal && signal.aborted) throw aborted();
    const controller = new AbortController(); let cancel, timer;
    const interrupted = new Promise((resolve, reject) => {
      cancel = () => { controller.abort(); reject(aborted()); };
      if (signal) signal.addEventListener('abort', cancel, {once: true});
      // The widget has its own visible timeout. This also releases the session queue
      // if a challenge callback stops responding or ignores cancellation.
      timer = setTimeout(() => { controller.abort(); reject(failure('challenge')); }, 95000);
    });
    try {
      const value = await Promise.race([interrupted, Promise.resolve().then(() => {
        if (controller.signal.aborted) throw aborted();
        return deployment().getChallengeToken({renewal, signal: controller.signal});
      })]);
      if (signal && signal.aborted) throw aborted();
      if (!clean(value)) throw failure('challenge');
      return clean(value);
    } catch (error) {
      if (signal && signal.aborted) throw aborted();
      throw failure('challenge');
    } finally {
      clearTimeout(timer);
      if (signal) signal.removeEventListener('abort', cancel);
    }
  }
  async function session(state, signal, grant, scope) {
    let current = state.session || loadSession();
    const now = Date.now(), expires = Date.parse(current.expires_at);
    // A token issued before a new service was added may still be within its lifetime.
    const valid = clean(current.token) && clean(current.session_id) && Array.isArray(current.scopes) && current.scopes.includes(scope);
    if (valid && expires > now && Number(current.renewAt) > now) { state.session = current; return current; }
    const renew = valid && expires > now;
    const body = {turnstile_token: await challengeToken(!!renew, signal)};
    assertPermission(grant);
    const headers = {'Content-Type': 'application/json'};
    if (renew) {
      headers.Authorization = 'Bearer ' + current.token;
      // A lost rotation response can still invalidate the old token on the server.
      forgetSession(state);
    }
    const value = await request(route('/api/session'), {method: 'POST', headers, body: JSON.stringify(body)}, signal);
    const issued = Date.parse(value && value.issued_at), expiry = Date.parse(value && value.expires_at);
    if (!value || !clean(value.token) || !clean(value.session_id) || !Array.isArray(value.scopes)
        || !Number.isFinite(issued) || !Number.isFinite(expiry) || expiry <= Date.now()
        || typeof value.renew_after_seconds !== 'number' || !Number.isFinite(value.renew_after_seconds) || value.renew_after_seconds <= 0
        || renew && value.session_id !== current.session_id) throw failure('response');
    current = {token: value.token, session_id: value.session_id, scopes: value.scopes,
      issued_at: value.issued_at, expires_at: value.expires_at, renew_after_seconds: value.renew_after_seconds,
      baseUrl: configuration().baseUrl, renewAt: Math.min(expiry, issued + value.renew_after_seconds * 1000)};
    try { sessionStorage.setItem(SESSION, JSON.stringify(current)); } catch (_) { forgetSession(state); throw failure('storage'); }
    state.session = current; state.consentKey = ''; return current;
  }
  function assertPermission(expectedGrant) {
    if (!configuration().configured) throw failure('unconfigured');
    const grant = currentGrant();
    if (!grant || expectedGrant && expectedGrant !== grant) throw failure('permission');
    return grant;
  }
  async function consent(state, token, grant, signal) {
    const body = {transcription: Boolean(grant), d3: Boolean(grant), collection: false,
      notice_version: notice(), site_release: deployment().siteRelease};
    const supportsRecommendation = Array.isArray(token.scopes) && token.scopes.includes(RECOMMENDATION_SCOPE);
    if (supportsRecommendation) body.recommendation = Boolean(grant);
    const key = token.token + '|' + grant + '|' + JSON.stringify(body);
    if (state.consentKey === key) return;
    const value = await request(route('/api/consent'), {method: 'POST', headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + token.token}, body: JSON.stringify(body)}, signal, grant ? 150000 : 15000);
    if (!value || value.session_id !== token.session_id || value.notice_version !== notice() || value.effective_collection !== false) throw failure('response');
    if (supportsRecommendation && value.effective_recommendation !== body.recommendation) throw failure('response');
    state.consentKey = key;
  }
  function withdraw() {
    if (currentGrant() || !configuration().configured) return;
    const state = shared();
    state.tail = state.tail.then(async () => {
      if (currentGrant()) return;
      const token = state.session || loadSession();
      try {
        if (clean(token.token) && Date.parse(token.expires_at) > Date.now()) await consent(state, token, '', null);
      } finally { forgetSession(state); }
    }).catch(() => {
      // Browser permission is already off. Never issue a new session to withdraw.
    });
  }
  if (agreement) window.addEventListener(agreement.experimentalEvent, withdraw);
  function authorized(scope, signal, action) {
    const grant = assertPermission();
    const state = shared();
    // Rotation invalidates old tokens. One shared tab queue also covers same-origin settings frames.
    const pending = state.tail.then(async () => {
      if (signal && signal.aborted) throw aborted();
      assertPermission(grant);
      try {
        const token = await session(state, signal, grant, scope);
        if (!token.scopes.includes(scope)) throw failure('unauthorized');
        assertPermission(grant);
        await consent(state, token, grant, signal);
        assertPermission(grant);
        const value = await action(token);
        assertPermission(grant);
        if (value && (value.session_id !== token.session_id || value.recorded !== false || value.record_id !== null)) throw failure('response');
        return value;
      } catch (error) {
        if (['unauthorized', 'token_expired', 'session_mismatch'].includes(error.code)) forgetSession(state);
        if (['consent_required', 'notice_outdated'].includes(error.code)) state.consentKey = '';
        if (error.code === 'notice_outdated' && grant === currentGrant()) agreement.setExperimentalEnabled(false);
        throw error;
      }
    });
    state.tail = pending.catch(() => {}); return pending;
  }
  function questionMetadata(question, bank) {
    const value = deployment(), release = value.bankReleases && value.bankReleases[bank];
    if (!question || !clean(question.id) || !clean(bank) || !clean(release) || !clean(value.siteRelease)) throw failure('metadata');
    const choices = {};
    if (question.choices && (typeof question.choices !== 'object' || Array.isArray(question.choices))) throw failure('metadata');
    if (question.choices) {
      for (const [key, text] of Object.entries(question.choices)) {
        if (typeof text !== 'string') throw failure('metadata');
        choices[key] = text;
      }
    }
    if (typeof question.question !== 'string') throw failure('metadata');
    return {id: question.id, bank, release, text: question.question, choices};
  }
  async function transcribe(audio, question, options = {}) {
    assertPermission();
    const context = questionMetadata(question, options.bank);
    if (!audio || audio.type !== 'audio/wav' || !Number.isFinite(audio.size) || audio.size > 2000000 || audio.size < 44) throw failure('bad_audio');
    const url = new URL(route('/api/transcription'));
    url.searchParams.set('question_id', context.id); url.searchParams.set('bank', context.bank); url.searchParams.set('release', context.release);
    url.searchParams.set('site_release', deployment().siteRelease);
    const value = await authorized('transcribe', options.signal, token => request(url.href, {method: 'POST', headers: {'Content-Type': 'audio/wav', Authorization: 'Bearer ' + token.token}, body: audio}, options.signal));
    if (!value || value.question_id !== context.id || typeof value.text !== 'string' || value.text.length > 12000) throw failure('response');
    return value;
  }
  function signals(value, expected) {
    if (!value || value.question_id !== expected.question.id || value.transcript !== expected.transcript || !clean(value.rubric_version)
        || !value.answers || !value.rubrics) throw failure('response');
    const counts = {confidence: 3, reasoning: 4, engagement: 3};
    return Object.keys(counts).map(id => {
      const rubric = value.rubrics[id], answer = value.answers[id];
      if (!rubric || rubric.version !== value.rubric_version || !clean(rubric.title) || !rubric.choices
          || !answer || answer.type !== 'choice' || !answer.probabilities || !clean(answer.choice)) throw failure('response');
      const letters = Object.keys(rubric.choices).sort();
      if (letters.length !== counts[id] || letters.some((letter, i) => letter !== String.fromCharCode(97 + i))
          || Object.keys(answer.probabilities).length !== letters.length || !letters.includes(answer.choice)) throw failure('response');
      let total = 0;
      const distribution = letters.map(letter => {
        const choice = rubric.choices[letter], probability = answer.probabilities[letter];
        if (!choice || !clean(choice.code) || !clean(choice.label) || typeof probability !== 'number'
            || !Number.isFinite(probability) || probability < 0 || probability > 1) throw failure('response');
        total += probability; return {label: choice.label, score: probability};
      });
      if (total < 0.98 || total > 1.02) throw failure('response');
      const selected = rubric.choices[answer.choice];
      return {id, title: rubric.title, code: selected.code, label: selected.label, score: answer.probabilities[answer.choice], distribution};
    });
  }
  async function learningSignals(input, options = {}) {
    assertPermission();
    const context = questionMetadata(input.question, input.bank), transcript = input.transcript;
    if (typeof transcript !== 'string' || !transcript.trim() || transcript.length > 12000) throw failure('bad_request');
    const body = {transcript, question: context, site_release: deployment().siteRelease};
    const value = await authorized('d3', options.signal, token => request(route('/api/learning-signals'), {method: 'POST',
      headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + token.token}, body: JSON.stringify(body)}, options.signal));
    return {questionId: context.id, transcript, signals: signals(value, input), decisionConfigured: true,
      rubricVersion: value.rubric_version, recorded: false, recordId: null};
  }
  const validId = value => typeof value === 'string' && value.length > 0 && value.length <= 200 && !/[^A-Za-z0-9_.:-]/u.test(value);
  function recommendationBody(input) {
    if (!input || !RECOMMENDATION_BANKS.includes(input.bank)) throw failure('bad_request');
    const {bank, targetId, targetQuestionId, excludeQuestionId, anchorQuestionId, history = []} = input;
    if ((targetId == null) === (targetQuestionId == null) ||
        [targetId, targetQuestionId, excludeQuestionId, anchorQuestionId].some(id => id != null && !validId(id)) ||
        !Array.isArray(history) || history.length > MAX_HISTORY + MAX_RETRIES) throw failure('bad_request');
    const body = {bank, history: []};
    if (targetId != null) body.targetId = targetId;
    if (targetQuestionId != null) body.targetQuestionId = targetQuestionId;
    if (excludeQuestionId != null) body.excludeQuestionId = excludeQuestionId;
    if (anchorQuestionId != null) body.anchorQuestionId = anchorQuestionId;
    let retries = 0;
    for (const event of history) {
      if (!event || typeof event !== 'object' || Array.isArray(event)) throw failure('bad_request');
      if (event.gapDays !== undefined) {
        if (!Number.isFinite(event.gapDays) || event.gapDays <= 0 || event.gapDays > MAX_GAP_DAYS) throw failure('bad_request');
        body.history.push({gapDays: event.gapDays});
        continue;
      }
      const {questionId, outcome, retry} = event;
      if (!validId(questionId) || !RECOMMENDATION_OUTCOMES.includes(outcome) || retry !== undefined && retry !== true) throw failure('bad_request');
      const score = {questionId, outcome};
      if (retry === true) { retries++; score.retry = true; }
      body.history.push(score);
    }
    if (retries > MAX_RETRIES || history.length - retries > MAX_HISTORY) throw failure('bad_request');
    return body;
  }
  async function recommendation(input, options = {}) {
    assertPermission();
    const body = recommendationBody(input);
    const value = await authorized(RECOMMENDATION_SCOPE, options.signal, token => request(route('/api/practice/recommendation'), {
      method: 'POST', headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + token.token},
      body: JSON.stringify(body)
    }, options.signal));
    if (!value) throw failure('response');
    const {recommendation: item, stopReason, alternateQuestionId} = value;
    if (stopReason === null) {
      if (!validId(item?.questionId) || !Number.isInteger(item.prerequisiteDepth) || item.prerequisiteDepth < 0 ||
          alternateQuestionId != null) throw failure('response');
    } else if (!STOP_REASONS.includes(stopReason) || item !== null ||
        alternateQuestionId != null && !validId(alternateQuestionId)) throw failure('response');
    return value;
  }
  window.MathPracticeServices = {config: configuration, status, check, transcribe, learningSignals, recommendation};
})();
