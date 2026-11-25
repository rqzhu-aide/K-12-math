/* First-visit acknowledgement, stored only in this browser. This is not an account or age check. */
(function () {
  'use strict';
  const version = '2026-11-23.1';
  const localServiceVersion = '2026-11-23.2';
  const hostedServiceVersion = '2026-11-23.3';
  const key = 'math-practice.agreement.v1';
  const experimentalKey = 'math-practice.experimental-agreement.v1';
  const legacyServicePreferences = 'math-practice.optional-services.preferences.v1';
  const recommendationHistory = 'math-practice.practice-recommendations.history.v1';
  const recommendationPause = 'math-practice.practice-recommendations.pause.v1';
  const experimentalEvent = 'math-practice-experimental-change';
  const defaultNotice = '2026-11-16';
  const current = new URL(window.location.href);
  const script = document.currentScript && document.currentScript.src;
  const base = new URL('.', script || current.href);
  const agreement = new URL('agreement.html', base);
  const release = script && new URL(script, base).searchParams.get('v');
  if (release) agreement.searchParams.set('v', release);
  const onAgreement = current.pathname === agreement.pathname;
  let hiddenState = null;

  function valid(raw, expectedVersion = version) {
    try {
      const value = JSON.parse(raw);
      return Boolean(value && value.version === expectedVersion && value.affirmative === true
        && typeof value.acceptedAt === 'string'
        && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/.test(value.acceptedAt)
        && new Date(value.acceptedAt).toISOString() === value.acceptedAt);
    } catch (_) { return false; }
  }
  function read(storageName) {
    try { return valid(window[storageName].getItem(key)); }
    catch (_) { return false; }
  }
  function accepted() {
    // A session record can carry an explicit acceptance across navigation when
    // the browser permits local reads but refuses local writes.
    return read('localStorage') || read('sessionStorage');
  }
  function accept() {
    const record = JSON.stringify({version, acceptedAt: new Date().toISOString(), affirmative: true});
    for (const storageName of ['localStorage', 'sessionStorage']) {
      try {
        const storage = window[storageName];
        storage.setItem(key, record);
        if (storage.getItem(key) === record) return true;
      } catch (_) { /* The next browser store may still be available. */ }
    }
    return false;
  }
  function noticeVersion() {
    let owner = window;
    try {
      if (window.top?.location.origin === current.origin) owner = window.top;
    } catch (_) { /* The iframe can still read its own configuration. */ }
    const value = (owner.MATH_PRACTICE_HOSTED?.services || window.MATH_PRACTICE_HOSTED?.services)?.noticeVersion;
    return typeof value === 'string' && value.trim() ? value.trim() : defaultNotice;
  }
  function storedGrant(notice, expectedVersion) {
    if (!accepted()) return '';
    try {
      const raw = window.localStorage.getItem(experimentalKey), value = JSON.parse(raw);
      return valid(raw, expectedVersion) && value.noticeVersion === notice && typeof value.grantId === 'string' && value.grantId ? raw : '';
    } catch (_) { return ''; }
  }
  function serviceVersion() { return window.MATH_PRACTICE_HOSTED ? hostedServiceVersion : localServiceVersion; }
  function experimentalGrant(notice = noticeVersion()) { return storedGrant(notice, serviceVersion()); }
  function priorGrant(notice) {
    return (window.MATH_PRACTICE_HOSTED && storedGrant(notice, localServiceVersion)) || storedGrant(notice, version);
  }
  function experimentalEnabled() { return Boolean(experimentalGrant()); }
  function dispatchExperimentalChange(target) {
    target.dispatchEvent(new target.Event(experimentalEvent));
  }
  function setExperimentalEnabled(enabled, notice = noticeVersion()) {
    if (typeof enabled !== 'boolean' || (enabled && !accepted())) return false;
    try {
      const storage = window.localStorage;
      if (enabled) {
        if (experimentalGrant(notice)) return true;
        const prior = priorGrant(notice);
        if (!prior) {
          storage.removeItem(recommendationHistory);
          storage.removeItem(recommendationPause);
        }
        const next = JSON.stringify({version: serviceVersion(), noticeVersion: notice, affirmative: true,
          acceptedAt: new Date().toISOString(), grantId: prior ? JSON.parse(prior).grantId : Math.random().toString(36)});
        storage.setItem(experimentalKey, next);
        if (storage.getItem(experimentalKey) !== next) return false;
      } else {
        // Open 2.2.1 tabs still check their independent speech and feedback preferences.
        for (const storageKey of [legacyServicePreferences, experimentalKey, recommendationHistory, recommendationPause]) {
          if (storage.getItem(storageKey) === null) continue;
          storage.removeItem(storageKey);
          if (storage.getItem(storageKey) !== null) return false;
        }
      }
    } catch (_) { return false; }
    dispatchExperimentalChange(window);
    try {
      if (window.top !== window && window.top.location.origin === current.origin) dispatchExperimentalChange(window.top);
    } catch (_) { /* Other origins do not share this choice. */ }
    return true;
  }
  function bindExperimentalSettings() {
    const action = document.getElementById('experimentalConsent');
    const decline = document.getElementById('experimentalDecline');
    const assent = document.getElementById('experimentalConsentAssent');
    const state = document.getElementById('experimentalConsentState');
    const header = document.getElementById('experimentalConsentHeader');
    const controls = document.getElementById('experimentalConsentControls');
    const withdrawal = document.getElementById('experimentalConsentWithdrawal');
    const notice = document.getElementById('experimentalConsentNotice');
    const result = document.getElementById('experimentalConsentResult');
    const language = window.MathPracticeLanguage;
    const embedded = window.parent !== window;
    const enableDescription = action.getAttribute('aria-describedby');
    let enabled = false;
    language.register({
      'Ailleo Math Practice Service': 'Ailleo 数学练习服务',
      'One setting controls all three features, independently of your tutor. Recommendations use your practice history whether you type or speak.': '一个设置同时控制这三项功能，与你的数学辅导模型相互独立。无论用文字还是语音作答，练习推荐都会使用你的练习记录。',
      'Speech-to-text': '语音转文字',
      'Sentiment feedback': '情绪反馈',
      'When you stop recording, Ailleo receives the audio and returns text you can edit before submitting.': '你停止录音时，Ailleo 会接收音频并返回文字，供你在提交前编辑。',
      'When you stop recording, the model you configure receives the audio and returns text you can edit before submitting.': '你停止录音时，你配置的模型会接收音频并返回文字，供你在提交前编辑。',
      'When available, Ailleo automatically reads the question and original transcript before you edit or submit it. It comments on clarity and confidence or frustration expressed in words.': '服务可用时，Ailleo 会在你编辑或提交前自动读取题目和原始转录文字，就表达是否清楚，以及你在文字中表达出的信心或挫败感提供反馈。',
      'When configured, the model automatically reads the question and original transcript before you edit or submit it. It comments on clarity and confidence or frustration expressed in words.': '配置后，模型会在你编辑或提交前自动读取题目和原始转录文字，就表达是否清楚，以及你在文字中表达出的信心或挫败感提供反馈。',
      'Practice recommendations': '练习推荐',
      'For suggestions, your browser sends Ailleo’s server the question bank, current question ID, topic or target question, and a limited history of scored question IDs, outcomes (which can include changed-answer retries) and time between visits.': '当你请求推荐时，浏览器会向 Ailleo 服务器发送当前题库、当前题号、练习主题或目标题目，以及少量历史记录，包括已评分的题号、作答结果（可能包括修改答案后再次提交的结果）和练习间隔。',
      'For suggestions, your browser sends the local launcher the question bank, current question ID, topic or target question, and a limited history of scored question IDs, outcomes (which can include changed-answer retries) and time between visits.': '当你请求推荐时，浏览器会向本地启动器发送当前题库、当前题号、练习主题或目标题目，以及少量历史记录，包括已评分的题号、作答结果（可能包括修改答案后再次提交的结果）和练习间隔。',
      'Ailleo temporarily processes recommendation requests, audio, original transcripts and sentiment feedback. Your browser keeps a limited recommendation history. Practice data collection for model training is off. Please do not include any confidential information.': 'Ailleo 会临时处理推荐请求、录音、原始转录文字和情绪反馈。浏览器只保存少量推荐所需的历史记录。目前未开启用于模型训练的练习数据收集。请勿提供任何保密信息。',
      'Speech and sentiment use the services you configure, which may be remote. Their privacy policies and charges apply. Please do not include any confidential information.': '语音转文字和情绪反馈通过你配置的服务处理，这些服务可能位于远程服务器。隐私和收费以各服务的规则为准。请勿提供任何保密信息。',
      'If you configure the sentiment model for math assessment, it can also review the answers and explanations you submit.': '如果将情绪分析模型配置为数学评估模型，它还可以检查你提交的答案和解释。',
      'Read the full agreement': '阅读完整协议',
      'I agree to this processing for myself or as the parent or legal guardian supervising my child’s use.': '我同意按上述方式处理我本人的数据，或我作为家长或法定监护人监督使用的孩子的数据。',
      'Agree and enable': '同意并开启',
      'Continue without these features': '不开启这些功能，继续练习',
      'Turn off these features': '关闭这些功能',
      'Features off': '功能已关闭',
      'Features on': '功能已开启',
      'Turning these features off clears this browser’s recommendation history.': '关闭这些功能会清除本浏览器保存的推荐历史记录。',
      'Recommendations now use Ailleo’s server. Review the change below before enabling these features again.': '题目推荐现在由 Ailleo 服务器处理。重新开启这些功能前，请先查看下方的变更说明。',
      'Speech and sentiment connections': '语音转文字和情绪反馈连接',
      'Your choice could not be saved. Allow site storage in your browser settings, then try again.': '无法保存你的选择。请在浏览器设置中允许此网站存储数据，然后重试。'
    });
    function render() {
      enabled = experimentalEnabled();
      const renewal = !enabled && window.MATH_PRACTICE_HOSTED && priorGrant(noticeVersion());
      language.bindText(action, enabled ? 'Turn off these features' : 'Agree and enable');
      language.bindText(state, enabled ? 'Features on' : 'Features off');
      state.dataset.state = enabled ? 'on' : 'off';
      if (notice) language.bindText(notice, renewal ? 'Recommendations now use Ailleo’s server. Review the change below before enabling these features again.' : '');
      action.setAttribute('aria-describedby', enabled ? 'experimentalConsentState experimentalConsentWithdrawal' : enableDescription);
      action.classList.toggle('primary', !enabled);
      action.classList.toggle('secondary', enabled);
      decline.hidden = enabled;
      assent.hidden = enabled;
      withdrawal.hidden = !enabled;
      const anchor = enabled ? header : assent;
      if (anchor.nextElementSibling !== controls) {
        const restoreFocus = document.activeElement === action;
        anchor.after(controls);
        if (restoreFocus) action.focus();
      }
    }
    function saveChoice(nextEnabled) {
      const saved = setExperimentalEnabled(nextEnabled);
      language.bindText(result, saved ? '' : 'Your choice could not be saved. Allow site storage in your browser settings, then try again.');
      result.dataset.state = saved ? '' : 'error';
      render();
      return saved;
    }
    function returnToPractice() {
      if (embedded) {
        const targetOrigin = current.protocol === 'file:' ? '*' : current.origin;
        window.parent.postMessage('math-practice:close-settings', targetOrigin);
      } else {
        window.location.assign(new URL('index.html', base).href);
      }
    }
    action.addEventListener('click', () => saveChoice(!enabled));
    decline.addEventListener('click', () => {
      if (saveChoice(false)) returnToPractice();
    });
    if (embedded) {
      document.querySelector('.back-link').addEventListener('click', event => {
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        returnToPractice();
      });
      document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && !event.defaultPrevented && !document.querySelector('dialog[open]')) {
          event.preventDefault();
          returnToPractice();
        }
      });
    }
    window.addEventListener(experimentalEvent, render);
    window.addEventListener('pageshow', render);
    action.disabled = false;
    decline.disabled = false;
    render();
  }
  function safeReturn(value) {
    if (typeof value !== 'string' || !value || /^[a-z][a-z\d+.-]*:/i.test(value)
        || value.startsWith('//') || /[\\\u0000-\u0020\u007f]/.test(value)) return 'index.html';
    try {
      const path = decodeURIComponent(value.split(/[?#]/, 1)[0]);
      if (/[\\\u0000-\u001f\u007f]/.test(path) || /(^|\/)\.\.(\/|$)/.test(path)) return 'index.html';
      const target = new URL(value, base);
      if (target.origin !== base.origin || target.protocol !== base.protocol
          || target.username || target.password
          || ![base.pathname, base.pathname + 'index.html', base.pathname + 'settings.html', base.pathname + 'online-settings.html'].includes(target.pathname)) return 'index.html';
      return (target.pathname === base.pathname ? './' : target.pathname.slice(base.pathname.length)) + target.search + target.hash;
    } catch (_) { return 'index.html'; }
  }
  function destination() {
    return safeReturn(new URL(window.location.href).searchParams.get('return'));
  }
  function hide() {
    const root = document.documentElement;
    if (!hiddenState) hiddenState = {hidden: root.hidden, inert: root.inert,
      display: root.style.getPropertyValue('display'), priority: root.style.getPropertyPriority('display')};
    root.hidden = true;
    root.inert = true;
    root.style.setProperty('display', 'none', 'important');
  }
  function reveal() {
    if (!hiddenState) return;
    const root = document.documentElement;
    root.hidden = hiddenState.hidden;
    root.inert = hiddenState.inert;
    if (hiddenState.display) root.style.setProperty('display', hiddenState.display, hiddenState.priority);
    else root.style.removeProperty('display');
    hiddenState = null;
  }
  function guard() {
    if (onAgreement) return;
    if (accepted()) { reveal(); return; }
    hide();
    const page = new URL(window.location.href);
    const target = new URL(agreement.href);
    target.searchParams.set('return', safeReturn(page.pathname + page.search + page.hash));
    window.location.replace(target.href);
  }
  window.MathPracticeAgreement = {version, accepted, accept, destination, noticeVersion, experimentalGrant, experimentalEnabled,
    setExperimentalEnabled, experimentalEvent, bindExperimentalSettings};
  guard();
  window.addEventListener('pageshow', guard);
  window.addEventListener('storage', event => {
    if (event.key === experimentalKey || event.key === key || event.key === null) dispatchExperimentalChange(window);
  });
}());
