/* Public, read-only data transport for the GitHub Pages build. */
(function () {
  'use strict';
  const config = window.MATH_PRACTICE_HOSTED;
  if (!config) return;
  const pending = new Map();
  const PAGE_SIZE = 30;
  function read(path) {
    const url = new URL(path, document.baseURI);
    if (url.origin !== location.origin || !['http:', 'https:'].includes(url.protocol)) {
      return Promise.reject(new Error('The public practice data location is invalid.'));
    }
    if (!pending.has(url.href)) {
      const request = fetch(url.href, {credentials: 'omit', referrerPolicy: 'no-referrer'})
        .then(response => {
          if (!response.ok) throw new Error('Practice data could not load. Check your connection and try again.');
          return response.json();
        }).catch(error => { pending.delete(url.href); throw error; });
      pending.set(url.href, request);
    }
    return pending.get(url.href);
  }
  const runtime = {
    ready: Promise.all(config.catalogs.map(read)),
    async question(stub) {
      const question = await read(stub.questionURL);
      if (!question || question.id !== stub.id || typeof question.question !== 'string') {
        throw new Error('This problem could not load. Try choosing it again.');
      }
      return question;
    },
    browse(layer) { return read(config.browse[layer]); },
    async practice(layer, node, offset) {
      const data = await read(node.practiceURL);
      const candidates = Array.isArray(data.candidates) ? data.candidates : [];
      return Object.assign({}, data, {candidates: candidates.slice(offset, offset + PAGE_SIZE),
        total: candidates.length, nextOffset: offset + PAGE_SIZE < candidates.length ? offset + PAGE_SIZE : null});
    }
  };
  window.MathPracticeHosted = runtime;
})();
