/* Apply before the page paints. Appearance is a browser preference, not model configuration. */
(function () {
  'use strict';
  const key = 'math-practice-appearance';
  const root = document.documentElement;
  const system = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
  const normalize = value => value === 'light' || value === 'dark' ? value : 'system';
  let preference = 'system';
  try { preference = normalize(window.localStorage.getItem(key)); } catch (_) { /* Private browser storage may be unavailable. */ }

  function apply() {
    root.dataset.theme = preference === 'system' ? (system && system.matches ? 'dark' : 'light') : preference;
    root.dataset.themePreference = preference;
    document.querySelectorAll('[data-theme-choice]').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.themeChoice === root.dataset.theme));
    });
  }

  apply();
  function connect() {
    document.querySelectorAll('[data-theme-choice]').forEach(button => {
      button.addEventListener('click', () => {
        preference = normalize(button.dataset.themeChoice);
        try { window.localStorage.setItem(key, preference); } catch (_) { /* Keep the choice for this page. */ }
        apply();
      });
    });
    apply();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', connect, {once: true});
  else connect();
  if (system) {
    const changed = () => { if (preference === 'system') apply(); };
    if (system.addEventListener) system.addEventListener('change', changed);
    else if (system.addListener) system.addListener(changed);
  }
  window.addEventListener('storage', event => {
    if (event.key !== key && event.key !== null) return;
    if (event.storageArea && event.storageArea !== window.localStorage) return;
    preference = normalize(event.newValue);
    apply();
  });
}());
