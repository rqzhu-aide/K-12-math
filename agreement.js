/* First-visit acknowledgement, stored only in this browser. This is not an account or age check. */
(function () {
  'use strict';
  const version = '2026-11-17.2';
  const key = 'math-practice.agreement.v1';
  const current = new URL(window.location.href);
  const script = document.currentScript && document.currentScript.src;
  const base = new URL('.', script || current.href);
  const agreement = new URL('agreement.html', base);
  const onAgreement = current.pathname === agreement.pathname;
  let hiddenState = null;

  function valid(raw) {
    try {
      const value = JSON.parse(raw);
      return Boolean(value && value.version === version && value.affirmative === true
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
  function safeReturn(value) {
    if (typeof value !== 'string' || !value || /^[a-z][a-z\d+.-]*:/i.test(value)
        || value.startsWith('//') || /[\\\u0000-\u0020\u007f]/.test(value)) return 'index.html';
    try {
      const path = decodeURIComponent(value.split(/[?#]/, 1)[0]);
      if (/[\\\u0000-\u001f\u007f]/.test(path) || /(^|\/)\.\.(\/|$)/.test(path)) return 'index.html';
      const target = new URL(value, base);
      if (target.origin !== base.origin || target.protocol !== base.protocol
          || target.username || target.password
          || ![base.pathname, base.pathname + 'index.html', base.pathname + 'settings.html'].includes(target.pathname)) return 'index.html';
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
  window.MathPracticeAgreement = {version, accepted, accept, destination};
  guard();
  window.addEventListener('pageshow', guard);
}());
