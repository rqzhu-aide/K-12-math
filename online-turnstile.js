/* Public deployment verification. No challenge or service tokens are cached here. */
(function () {
  'use strict';
  const services = window.MATH_PRACTICE_HOSTED && window.MATH_PRACTICE_HOSTED.services;
  const config = services && services.turnstile;
  if (!config || typeof services.getChallengeToken === 'function'
      || typeof config.siteKey !== 'string' || !/^[A-Za-z0-9_-]{3,100}$/.test(config.siteKey)
      || typeof config.expectedHostname !== 'string' || !/^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$/i.test(config.expectedHostname)
      || typeof config.action !== 'string' || !/^[A-Za-z0-9_-]{1,32}$/.test(config.action)) return;

  const SCRIPT_URL = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
  const SCRIPT_TIMEOUT = 15000, CHALLENGE_TIMEOUT = 90000;
  const copy = {
    title: 'Verify your Ailleo connection',
    help: 'Complete this check to use speech input or learning feedback. You can cancel and continue practicing.',
    loading: 'Loading verification…',
    ready: 'Complete the verification below to continue.',
    failed: 'Verification could not finish. Check your connection and try again.',
    expired: 'Verification expired. Try again.',
    timeout: 'Verification took too long. Try again.',
    retry: 'Try again', cancel: 'Cancel'
  };
  const language = window.MathPracticeLanguage;
  if (language) language.register({
    [copy.title]: '验证 Ailleo 连接',
    [copy.help]: '完成验证后，即可使用语音输入或学习反馈。你也可以取消验证，继续练习。',
    [copy.loading]: '正在加载验证…',
    [copy.ready]: '请完成下方验证以继续。',
    [copy.failed]: '验证未能完成。请检查网络连接，然后重试。',
    [copy.expired]: '验证已过期，请重试。',
    [copy.timeout]: '验证用时过长，请重试。',
    [copy.retry]: '重试', [copy.cancel]: '取消'
  });
  const t = value => language ? language.t(value) : value;
  function failure(message = copy.failed) {
    const error = new Error(t(message)); error.name = 'OptionalServiceError'; error.code = 'challenge'; return error;
  }
  function aborted() { const error = new Error('Request cancelled.'); error.name = 'AbortError'; return error; }
  function apiReady() {
    return window.turnstile && typeof window.turnstile.render === 'function' && typeof window.turnstile.remove === 'function';
  }

  let scriptPromise = null, active = false;
  function loadApi() {
    if (apiReady()) return Promise.resolve(window.turnstile);
    if (scriptPromise) return scriptPromise;
    // A cancelled dialog may leave this shared load running, but it always settles.
    const pending = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = SCRIPT_URL; script.async = true; script.defer = true;
      let settled = false;
      function settle(error) {
        if (settled) return;
        settled = true; clearTimeout(timer);
        script.removeEventListener('load', loaded); script.removeEventListener('error', failed);
        if (error) { script.remove(); reject(error); } else resolve(window.turnstile);
      }
      const loaded = () => settle(apiReady() ? null : failure());
      const failed = () => settle(failure());
      const timer = setTimeout(failed, SCRIPT_TIMEOUT);
      script.addEventListener('load', loaded); script.addEventListener('error', failed);
      try { document.head.appendChild(script); } catch (_) { failed(); }
    });
    scriptPromise = pending;
    pending.catch(() => { if (scriptPromise === pending) scriptPromise = null; });
    return pending;
  }

  function styleDialog() {
    if (document.getElementById('mathPracticeVerificationStyle')) return;
    const style = document.createElement('style'); style.id = 'mathPracticeVerificationStyle';
    style.textContent = `
      .mp-verification { box-sizing: border-box; width: min(440px, calc(100vw - 32px)); max-height: calc(100dvh - 32px); margin: auto; padding: 24px; overflow: auto; border: 0; border-radius: 14px; background: var(--surface, #fff); color: var(--ink, #13294b); box-shadow: var(--modal-shadow, 0 24px 60px rgba(18,27,35,.25)); font: 16px/1.5 var(--font, sans-serif); }
      .mp-verification::backdrop { background: var(--backdrop, rgba(18,27,35,.5)); }
      .mp-verification h2 { margin: 0 0 10px; font-size: 1.125rem; line-height: 1.35; font-weight: 650; letter-spacing: -.015em; }
      .mp-verification p { margin: 0; overflow-wrap: anywhere; }
      .mp-verification-help { color: var(--ink-2, #4c5666); }
      .mp-verification-state { display: flex; gap: 10px; align-items: center; margin-block: 20px 16px; font-size: .875rem; }
      .mp-verification-state[data-error="true"] { color: var(--err, #a12828); }
      .mp-verification-spinner { flex: none; width: 16px; height: 16px; border: 2px solid var(--hairline, #ccd2dc); border-top-color: var(--accent, #13294b); border-radius: 50%; animation: mp-verification-spin .8s linear infinite; }
      .mp-verification-widget { display: flex; justify-content: center; min-width: 0; }
      .mp-verification-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 10px; margin-top: 24px; }
      .mp-verification button { min-height: 44px; padding: 9px 16px; border: 1px solid var(--field-line, #ccd2dc); border-radius: 8px; background: var(--surface, #fff); color: var(--ink, #13294b); font: 600 .875rem/1.4 var(--font, sans-serif); cursor: pointer; }
      .mp-verification button:hover { background: var(--surface-hover, #f1f3f5); border-color: var(--field-line-hover, #606b79); }
      .mp-verification button:focus-visible { outline: 2px solid var(--accent, #13294b); outline-offset: 3px; }
      .mp-verification [hidden] { display: none; }
      @keyframes mp-verification-spin { to { transform: rotate(360deg); } }
      @media (prefers-reduced-motion: reduce) { .mp-verification-spinner { animation: none; } }
    `;
    document.head.appendChild(style);
  }

  services.getChallengeToken = function (options = {}) {
    const signal = options.signal;
    if (signal && signal.aborted) return Promise.reject(aborted());
    let preferences;
    try { preferences = window.MathPracticeServices && window.MathPracticeServices.preferences(); } catch (_) {}
    if (!preferences || !preferences.acknowledged || !(preferences.speech || preferences.decision)
        || window.location.protocol !== 'https:' || window.location.hostname.toLowerCase() !== config.expectedHostname.toLowerCase()
        || active || !document.body) return Promise.reject(failure());
    active = true;

    return new Promise((resolve, reject) => {
      let done = false, attempt = null, state = copy.loading;
      const previousFocus = document.activeElement;
      const dialog = document.createElement('dialog'); dialog.className = 'mp-verification';
      dialog.setAttribute('aria-labelledby', 'mpVerificationTitle');
      dialog.setAttribute('aria-describedby', 'mpVerificationHelp');
      const title = document.createElement('h2'); title.id = 'mpVerificationTitle';
      const help = document.createElement('p'); help.id = 'mpVerificationHelp'; help.className = 'mp-verification-help';
      const statusRow = document.createElement('div'); statusRow.className = 'mp-verification-state';
      const spinner = document.createElement('span'); spinner.className = 'mp-verification-spinner'; spinner.setAttribute('aria-hidden', 'true');
      const status = document.createElement('p'); status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
      const widget = document.createElement('div'); widget.className = 'mp-verification-widget';
      const actions = document.createElement('div'); actions.className = 'mp-verification-actions';
      const cancel = document.createElement('button'); cancel.type = 'button';
      const retry = document.createElement('button'); retry.type = 'button'; retry.hidden = true;
      statusRow.append(spinner, status); actions.append(cancel, retry); dialog.append(title, help, statusRow, widget, actions);

      function translate() {
        title.textContent = t(copy.title); help.textContent = t(copy.help); status.textContent = t(state);
        cancel.textContent = t(copy.cancel); retry.textContent = t(copy.retry);
      }
      function removeWidget() {
        const old = attempt; attempt = null;
        if (old && old.id != null && apiReady()) try { window.turnstile.remove(old.id); } catch (_) {}
        widget.replaceChildren();
      }
      function finish(error, token) {
        if (done) return;
        done = true; clearTimeout(deadline); removeWidget();
        if (signal) signal.removeEventListener('abort', cancelled);
        window.removeEventListener('pagehide', cancelled); window.removeEventListener('languagechange', translate);
        if (dialog.open) dialog.close();
        dialog.remove(); active = false;
        if (previousFocus && previousFocus.isConnected && typeof previousFocus.focus === 'function') previousFocus.focus({preventScroll: true});
        if (error) reject(error); else resolve(token);
      }
      function cancelled() { finish(aborted()); }
      function showError(message) {
        if (done) return;
        removeWidget(); state = message; spinner.hidden = true; retry.hidden = false;
        statusRow.dataset.error = 'true'; translate(); retry.focus();
      }
      function start() {
        removeWidget(); state = copy.loading; spinner.hidden = false; retry.hidden = true;
        statusRow.dataset.error = 'false'; translate();
        const current = {id: null}; attempt = current;
        const currentAttempt = () => !done && attempt === current;
        loadApi().then(api => {
          if (!currentAttempt()) return;
          state = copy.ready; spinner.hidden = true; translate();
          const id = api.render(widget, {
            sitekey: config.siteKey, action: config.action,
            theme: document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light',
            language: language && language.getLanguage() === 'zh-CN' ? 'zh-cn' : 'en',
            size: window.innerWidth < 390 ? 'compact' : 'flexible',
            appearance: 'always', execution: 'render', retry: 'never',
            'refresh-expired': 'never', 'refresh-timeout': 'never', 'response-field': false,
            callback(token) {
              if (!currentAttempt()) return;
              if (typeof token !== 'string' || !token.trim() || token.length > 2048) showError(copy.failed);
              else finish(null, token);
            },
            'error-callback': () => { if (currentAttempt()) showError(copy.failed); return true; },
            'expired-callback': () => { if (currentAttempt()) showError(copy.expired); },
            'timeout-callback': () => { if (currentAttempt()) showError(copy.timeout); },
            'unsupported-callback': () => { if (currentAttempt()) showError(copy.failed); }
          });
          // Also clean up if an API callback settled synchronously during render.
          if (currentAttempt()) current.id = id;
          else if (id != null) try { api.remove(id); } catch (_) {}
        }).catch(() => { if (currentAttempt()) showError(copy.failed); });
      }

      const deadline = setTimeout(() => finish(failure(copy.timeout)), CHALLENGE_TIMEOUT);
      cancel.addEventListener('click', cancelled); retry.addEventListener('click', start);
      dialog.addEventListener('cancel', event => { event.preventDefault(); cancelled(); });
      dialog.addEventListener('close', cancelled);
      window.addEventListener('pagehide', cancelled); window.addEventListener('languagechange', translate);
      if (signal) signal.addEventListener('abort', cancelled, {once: true});
      try {
        styleDialog(); translate(); document.body.appendChild(dialog);
        dialog.showModal(); cancel.focus();
        if (signal && signal.aborted) cancelled(); else start();
      } catch (_) { finish(failure()); }
    });
  };
}());
