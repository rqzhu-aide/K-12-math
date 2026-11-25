/* Shared by the hosted settings and the standalone launcher. */
(function () {
  'use strict';
  if (window.parent !== window && window.name === 'math-practice-settings') {
    document.documentElement.classList.add('settings-embedded');
    document.querySelector('header').prepend(document.querySelector('main h1'));
  }
  const tabs = {
    tutor: document.getElementById('tutorTab'),
    service: document.getElementById('serviceTab')
  };
  const panels = {
    tutor: document.getElementById('inferencePanel'),
    service: document.getElementById('servicePanel')
  };

  function select(name) {
    for (const key of Object.keys(tabs)) {
      const active = key === name;
      tabs[key].setAttribute('aria-selected', String(active));
      tabs[key].tabIndex = active ? 0 : -1;
      panels[key].hidden = !active;
    }
  }
  function activate(name) {
    select(name);
    // Keep refresh and copied links on this tab without adding an entry for each click.
    try { window.history.replaceState(window.history.state, '', '#' + name); } catch (_) {}
  }
  function selectFragment() {
    const id = window.location.hash.slice(1);
    if (!id || id === 'tutor' || id === 'service') {
      select(id || 'tutor');
      return;
    }
    if (id === 'speechTab' || id === 'decisionTab') {
      select('service');
      return;
    }
    const target = document.getElementById(id);
    if (!target) return;
    for (const key of Object.keys(tabs)) {
      if (target === tabs[key] || panels[key].contains(target)) {
        select(key);
        target.scrollIntoView({block: 'nearest'});
        return;
      }
    }
  }
  for (const [name, tab] of Object.entries(tabs)) {
    tab.addEventListener('click', () => activate(name));
    tab.addEventListener('keydown', event => {
      const other = name === 'tutor' ? 'service' : 'tutor';
      const next = {ArrowLeft: other, ArrowRight: other, Home: 'tutor', End: 'service'}[event.key];
      if (!next) return;
      event.preventDefault();
      activate(next);
      tabs[next].focus();
    });
  }
  window.MathPracticeSettingsTabs = {select};
  window.addEventListener('hashchange', selectFragment);
  selectFragment();
})();
