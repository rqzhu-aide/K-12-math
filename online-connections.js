/* Learner-owned tutor transport. Credentials belong to this browser tab. */
(function () {
  'use strict';
  const SETTINGS = 'math-practice.online-tutor.v1', SECRETS = 'math-practice.online-tutor.secrets.v1';
  const VERIFIED = 'math-practice.online-tutor.verified.v1', ACCOUNT = 'math-practice.online-tutor.account.v1', EPOCH = 'math-practice.online-tutor.epoch.v1';
  const defaults = {method: 'api', baseUrl: 'https://api.openai.com/v1', model: ''};
  const Language = window.MathPracticeLanguage;
  const messages = {
    unconfigured: 'Connect your own tutor in Settings for reasoning feedback.',
    untested: 'Your tutor is configured. Test the connection or submit your work.',
    ready: 'Your tutor completed a structured review.',
    url: 'Use an HTTPS API URL, or HTTP on this computer, separate from this website.',
    apiNetwork: 'The API could not be reached from this browser. Check its URL and browser access (CORS). For a local API, allow this site to access your computer when prompted.',
    forthcoming: 'ChatGPT login is forthcoming. Connect with your provider URL and API key for now.',
    auth: 'The API rejected this key. Check your key in Settings and test again.',
    denied: 'The API denied this request. Check access to the selected model.',
    missing: 'The API endpoint was not found. Check the API base URL in Settings.',
    limit: 'The API reached a usage or rate limit. Check your provider account and retry.',
    apiError: 'The API could not complete this request. Check the selected model and retry.',
    requestFormat: 'The selected model rejected the tutor request format. Refresh this page and test again, or choose another text model.',
    modelUnavailable: 'The selected model is unavailable for this API key. Choose another model or check your model access.',
    quota: 'The API account has no available quota. Check your provider billing or credits, then retry.',
    invalidRequest: 'The API rejected the request (HTTP 400). Check that the selected model supports text tutoring.',
    unavailable: 'The API service is temporarily unavailable. Try again shortly.',
    tokenLimit: 'The model reached the response limit before completing its review. Try again or choose another model.',
    refused: 'The model declined to review this submission. Rephrase your work or choose another model.',
    unreadable: 'The tutor returned an unreadable review. Try the review again.',
    incomplete: 'The tutor returned an incomplete review. Try the review again.',
    length: 'The tutor did not return a short visible review within 50 words or 100 script characters. Try the review again.',
    context: 'The tutor context could not load. Reload this website and retry.',
    selection: 'The selected topic context could not load. Reload this problem and retry.',
    figure: 'A problem figure could not be sent to the tutor. Reload the problem and retry.',
    storage: 'Browser storage is unavailable. Allow storage for this website to connect your tutor.',
    noText: 'The inference service returned no review text.'
  };
  if (Language) Language.register({
    [messages.unconfigured]: '在设置中连接你自己的辅导模型，以获取推理反馈。',
    [messages.untested]: '已配置你的辅导模型。请测试连接或提交作答。',
    [messages.ready]: '你的辅导模型已完成结构化点评。',
    [messages.url]: '请使用 HTTPS API 地址，或本机的 HTTP 地址，并与本站地址分开。',
    [messages.apiNetwork]: '浏览器无法连接 API。请检查地址与浏览器访问权限（CORS）。如果使用本机 API，请在浏览器提示时允许本站访问你的电脑。',
    [messages.forthcoming]: 'ChatGPT 登录即将推出。请先使用服务商网址和 API 密钥连接。',
    [messages.auth]: 'API 拒绝了此密钥。请在设置中检查密钥后重新测试。',
    [messages.denied]: 'API 拒绝了此请求。请检查所选模型的访问权限。',
    [messages.missing]: '未找到 API 端点。请检查设置中的 API 基础地址。',
    [messages.limit]: 'API 已达到用量或速率限制。请检查服务商账户后重试。',
    [messages.apiError]: 'API 未能完成请求。请检查所选模型后重试。',
    [messages.requestFormat]: '所选模型不接受当前的辅导请求格式。请刷新本页后重新测试，或选择其他文字模型。',
    [messages.modelUnavailable]: '此 API 密钥无法使用所选模型。请选择其他模型，或检查模型访问权限。',
    [messages.quota]: 'API 账户没有可用额度。请检查服务商的账单或余额后重试。',
    [messages.invalidRequest]: 'API 拒绝了请求（HTTP 400）。请确认所选模型支持文字辅导。',
    [messages.unavailable]: 'API 服务暂时不可用，请稍后重试。',
    [messages.tokenLimit]: '模型在完成点评前已达到回复额度上限。请重试或选择其他模型。',
    [messages.refused]: '模型拒绝点评此次作答。请换一种方式描述解题过程，或选择其他模型。',
    [messages.unreadable]: '辅导返回的点评无法读取，请重新点评。',
    [messages.incomplete]: '辅导返回的点评不完整，请重新点评。',
    [messages.length]: '辅导未返回限定长度的可见点评（最多 50 个英文词或 100 个汉字），请重新点评。',
    [messages.context]: '无法加载辅导所需的题目背景。请刷新本站后重试。',
    [messages.selection]: '无法加载所选主题的辅导背景。请重新加载此题后重试。',
    [messages.figure]: '无法向辅导模型发送题目图片。请重新加载题目后重试。',
    [messages.storage]: '浏览器存储不可用。请允许本站使用存储以连接辅导模型。',
    [messages.noText]: '推理服务未返回点评文字。'
  });
  let contractValue = null;
  const selectionBundles = new Map();
  const read = (storage, key) => { try { const value = JSON.parse(storage.getItem(key)); return value && typeof value === 'object' && !Array.isArray(value) ? value : {}; } catch (_) { return {}; } };
  const stored = (key, persistent = false) => { try { return read(persistent ? localStorage : sessionStorage, key); } catch (_) { return {}; } };
  const clean = value => typeof value === 'string' ? value.trim() : '';
  const identity = settings => JSON.stringify(settings);
  const epoch = () => stored(EPOCH).value || 0;
  function resetVerification() {
    try { sessionStorage.removeItem(VERIFIED); sessionStorage.setItem(EPOCH, JSON.stringify({value: epoch() + 1})); } catch (_) {}
  }
  function markVerified(settings, started) {
    if (started !== epoch()) return;
    try {
      sessionStorage.setItem(VERIFIED, JSON.stringify({key: identity(settings)}));
    } catch (_) {}
  }
  function getSettings() {
    const saved = stored(SETTINGS, true), secrets = stored(SECRETS);
    return {method: 'api', baseUrl: typeof saved.baseUrl === 'string' ? saved.baseUrl : defaults.baseUrl,
      model: saved.method === 'chatgpt' ? '' : clean(saved.model), apiKey: clean(secrets.apiKey)};
  }
  function normalized(value) {
    if (value && value.method === 'chatgpt') throw new Error(messages.forthcoming);
    const settings = {...getSettings(), ...value};
    return {method: 'api', baseUrl: clean(settings.baseUrl), model: clean(settings.model), apiKey: clean(settings.apiKey)};
  }
  function changed() {
    if (window.dispatchEvent && typeof CustomEvent !== 'undefined') window.dispatchEvent(new CustomEvent('math-practice-online-change'));
  }
  function saveSettings(value) {
    const settings = normalized(value);
    // URL userinfo and query strings can contain credentials; never persist them.
    if (settings.baseUrl) endpoint(settings);
    try {
      localStorage.setItem(SETTINGS, JSON.stringify({method: 'api', baseUrl: settings.baseUrl, model: settings.model}));
      sessionStorage.setItem(SECRETS, JSON.stringify({apiKey: settings.apiKey}));
    } catch (_) { throw new Error(messages.storage); }
    const verified = stored(VERIFIED);
    if (verified.key && verified.key !== identity(settings)) resetVerification();
    changed(); return getSettings();
  }
  function loopback(url) { return ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname); }
  function endpoint(settings) {
    let url;
    try { url = new URL(settings.baseUrl); } catch (_) { throw new Error(messages.url); }
    if (url.username || url.password || url.search || url.hash || url.origin === location.origin
        || (url.protocol !== 'https:' && !(url.protocol === 'http:' && loopback(url)))) throw new Error(messages.url);
    return url;
  }
  function apiEndpoint(settings, path) {
    const url = endpoint(settings);
    let prefix = url.pathname.replace(/\/+$/, '').replace(/\/chat\/completions$/, '').replace(/\/models$/, '');
    if (!prefix.endsWith('/v1')) prefix += '/v1';
    url.pathname = prefix + '/' + path;
    return url.href;
  }
  function status() {
    const settings = getSettings();
    let configured = false, message = messages.unconfigured;
    try {
      endpoint(settings);
      configured = !!settings.model;
      if (configured) message = messages.untested;
    } catch (_) {}
    const verified = stored(VERIFIED);
    const ready = configured && verified.key === identity(settings);
    if (ready) message = messages.ready;
    return {configured, ready, message, model: settings.model};
  }
  function abortError() { const error = new Error('Aborted'); error.name = 'AbortError'; return error; }
  function active(signal) { if (signal && signal.aborted) throw abortError(); }
  async function timed(signal, action, milliseconds = 145000) {
    const controller = new AbortController(), abort = () => controller.abort();
    if (signal) { active(signal); signal.addEventListener('abort', abort, {once: true}); }
    const timer = setTimeout(abort, milliseconds);
    try { const value = await action(controller.signal); active(controller.signal); return value; }
    finally { clearTimeout(timer); if (signal) signal.removeEventListener('abort', abort); }
  }
  async function json(url, options) {
    let response;
    try { response = await fetch(url, {...options, credentials: 'omit', referrerPolicy: 'no-referrer', cache: 'no-store', redirect: 'error'}); }
    catch (error) { if (error.name === 'AbortError') throw error; throw new Error(messages.apiNetwork); }
    if (!response.ok) {
      // Inspect structured error fields, but never show a provider's raw message,
      // which may echo credentials or the learner's submission.
      let failure;
      try { failure = (await response.json()).error; } catch (_) {}
      active(options.signal);
      const code = failure && failure.code, parameter = failure && failure.param;
      if (code === 'model_not_found') throw new Error(messages.modelUnavailable);
      if (response.status === 429 && code === 'insufficient_quota') throw new Error(messages.quota);
      if (response.status === 400 && ['unsupported_parameter', 'unsupported_value'].includes(code)
          && ['max_tokens', 'max_completion_tokens', 'reasoning_effort', 'response_format', 'messages', 'messages[0].role', 'model'].includes(parameter)) throw new Error(messages.requestFormat);
      if (response.status === 400) throw new Error(messages.invalidRequest);
      if (response.status >= 500) throw new Error(messages.unavailable);
      throw new Error(({401: messages.auth, 403: messages.denied, 404: messages.missing, 429: messages.limit})[response.status] || messages.apiError);
    }
    try { const value = await response.json(); active(options.signal); return value; }
    catch (error) { if (error.name === 'AbortError') throw error; throw new Error(messages.unreadable); }
  }
  async function account() { throw new Error(messages.forthcoming); }
  async function models(value, options = {}) {
    const settings = normalized(value);
    return timed(options.signal, async signal => {
      const result = await json(apiEndpoint(settings, 'models'), {method: 'GET', signal,
        headers: settings.apiKey ? {Authorization: 'Bearer ' + settings.apiKey} : {}});
      if (!result || !Array.isArray(result.data)) throw new Error(messages.apiError);
      return {models: result.data.filter(item => item && typeof item.id === 'string').map(item => ({id: item.id}))};
    }, 30000);
  }
  async function contract(signal) {
    active(signal);
    if (!contractValue) {
      const url = new URL('tutor-contract.json', document.baseURI);
      if (url.origin !== location.origin) throw new Error(messages.context);
      // Cache only completed static data. One cancelled review must not poison retries.
      try {
        const value = await json(url.href, {method: 'GET', signal});
        if (!value || typeof value.instructions !== 'string' || !value.schema) throw new Error(messages.context);
        active(signal); contractValue = value;
      } catch (error) { if (error.name === 'AbortError') throw error; throw new Error(messages.context); }
    }
    active(signal); return contractValue;
  }
  const object = value => !!value && typeof value === 'object' && !Array.isArray(value);
  const copy = value => JSON.parse(JSON.stringify(value));
  function selectedContext(base, delta) {
    if (!object(delta) || Object.keys(delta).some(key => !['set', 'remove'].includes(key))
        || delta.set !== undefined && !Array.isArray(delta.set) || delta.remove !== undefined && !Array.isArray(delta.remove)) throw new Error(messages.selection);
    let result = copy(base);
    const parent = path => {
      if (!Array.isArray(path) || !path.every(key => typeof key === 'string' && !['__proto__', 'prototype', 'constructor'].includes(key))) throw new Error(messages.selection);
      let node = result;
      for (const key of path.slice(0, -1)) {
        if (!object(node) || !Object.hasOwn(node, key) || !object(node[key])) throw new Error(messages.selection);
        node = node[key];
      }
      if (!object(node)) throw new Error(messages.selection);
      return node;
    };
    for (const path of delta.remove || []) {
      const node = parent(path);
      if (!path.length || !Object.hasOwn(node, path.at(-1))) throw new Error(messages.selection);
      delete node[path.at(-1)];
    }
    for (const entry of delta.set || []) {
      if (!Array.isArray(entry) || entry.length !== 2) throw new Error(messages.selection);
      const [path, value] = entry, node = parent(path);
      if (!path.length) result = copy(value); else node[path.at(-1)] = copy(value);
    }
    if (!object(result)) throw new Error(messages.selection);
    return result;
  }
  async function teachingContext(question, body, signal) {
    const context = question.tutorContext, layer = body.curriculumLayer || 'ailleo';
    const base = context && context.teachingContextByLayer && context.teachingContextByLayer[layer];
    if (!object(base)) throw new Error(messages.context);
    if (!body.curriculumNodeId) return base;
    if (typeof body.curriculumNodeId !== 'string' || !context.selectionsURL) throw new Error(messages.selection);
    let bundle, bundleURL;
    try {
      const url = new URL(context.selectionsURL, document.baseURI);
      if (url.origin !== location.origin || !['http:', 'https:'].includes(url.protocol)) throw new Error(messages.selection);
      bundleURL = url.href;
      bundle = selectionBundles.get(url.href);
      if (!bundle) { bundle = await json(url.href, {method: 'GET', signal}); active(signal); }
    } catch (error) { if (error.name === 'AbortError') throw error; throw new Error(messages.selection); }
    if (!bundle || bundle.schemaVersion !== 1 || bundle.questionId !== question.id || bundle.bank !== body.bank
        || !object(bundle.contexts) || !object(bundle.contexts[layer]) || !Object.hasOwn(bundle.contexts[layer], body.curriculumNodeId)) throw new Error(messages.selection);
    const result = selectedContext(base, bundle.contexts[layer][body.curriculumNodeId]);
    selectionBundles.set(bundleURL, bundle);
    return result;
  }
  const script = /[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]/g;
  function validateReview(text, known, form, language, reasoningProvided) {
    let value;
    try { value = JSON.parse(text); } catch (_) { throw new Error(messages.unreadable); }
    if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).sort().join(',') !== 'answerCategory,category,coach,hint'
        || !['correct', 'wrong', 'partial'].includes(value.category) || !['correct', 'wrong', 'partial', 'cannot_judge'].includes(value.answerCategory)
        || !['coach', 'hint'].every(key => typeof value[key] === 'string' && value[key].length <= 3000)) throw new Error(messages.incomplete);
    for (const key of Object.keys(value)) value[key] = value[key].trim();
    const raw = {category: value.category, answerCategory: value.answerCategory};
    const blankOverride = !reasoningProvided && value.category !== 'partial';
    if (!reasoningProvided) { value.category = 'partial'; value.hint = ''; }
    if (known !== null && known !== undefined) value.answerCategory = known;
    if (value.answerCategory === 'correct' && form) value.answerCategory = 'partial';
    const chinese = /^(zh|cn)/i.test(language || 'en');
    const subject = '\\b(?:(?:your|the|submitted)(?: final)?|final) answer (?:is|was|looks) ';
    const correct = subject + '(?:correct|right)\\b|你的答案(?:是)?正确|答案正确';
    const wrong = subject + '(?:wrong|incorrect|not correct)\\b|你的答案(?:是)?错误|答案错误|答案不正确';
    const conflict = ['correct', 'wrong', 'partial'].includes(value.answerCategory) && new RegExp(value.answerCategory === 'correct' ? wrong : correct, 'i').test(value.coach + ' ' + value.hint);
    if (blankOverride || value.answerCategory !== raw.answerCategory || conflict) {
      if (!reasoningProvided) value.coach = chinese ? '你会先做哪一步来解这道题？' : 'What first step would you try to solve this problem?';
      else if (form) value.coach = chinese ? '请按题目要求的形式写出最终答案。' : form;
      else if (value.category === 'correct' && value.answerCategory === 'correct') value.coach = chinese ? '你的解释正确。' : 'Your explanation is correct.';
      else if (value.category === 'correct') value.coach = chinese ? '你的推理正确。请检查最终答案是否与推理结果一致。' : 'Your reasoning is sound. Check that your final answer matches its result.';
      else if (value.answerCategory === 'correct') value.coach = chinese ? '答案符合要求。你能写出支持这个结果的计算步骤吗？' : 'Your answer matches. Which calculation supports the result?';
      else value.coach = chinese ? '请写出得到最终答案前的计算步骤。' : 'Write the calculation just before your final answer so we can check that step.';
      value.hint = '';
    }
    if (value.category === 'correct' && value.answerCategory === 'correct') value.hint = '';
    const textToCount = value.coach + ' ' + value.hint, characters = (textToCount.match(script) || []).length;
    const words = textToCount.replace(script, ' ').trim().split(/\s+/).filter(Boolean).length;
    if (!value.coach || characters + 2 * words > 100) throw new Error(messages.length);
    return {...value, clarification: value.coach, answerCorrect: value.answerCategory === 'correct' ? true : value.answerCategory === 'wrong' ? false : null,
      wordCount: words, scriptCharacterCount: characters, source: 'llm', modelJudgment: raw};
  }
  async function infer(settings, prompt, instructions, schema, images, signal) {
    if (!settings.model) throw new Error(messages.unconfigured);
    const url = apiEndpoint(settings, 'chat/completions');
    const officialOpenAI = url === 'https://api.openai.com/v1/chat/completions';
    const reasoningModel = /^(?:gpt-[56](?:[.-]|$)|o[1-9](?:-|$))/.test(settings.model);
    const lowEffort = /^gpt-[56](?:[.-]|$)/.test(settings.model) && !/(?:-pro|-chat-latest)(?:-|$)/.test(settings.model);
    const content = images.length ? [{type: 'text', text: prompt}, ...images.map(url => ({type: 'image_url', image_url: {url}}))] : prompt;
    // OpenAI's current limit includes reasoning tokens. Keep custom compatible
    // providers on the existing request contract instead of assuming their support.
    const payload = {model: settings.model,
      messages: [{role: officialOpenAI && reasoningModel ? 'developer' : 'system', content: instructions}, {role: 'user', content}],
      ...(officialOpenAI ? {max_completion_tokens: reasoningModel ? 4096 : 1000} : {max_tokens: 1000}),
      ...(officialOpenAI && lowEffort ? {reasoning_effort: 'low'} : {}), response_format: {type: 'json_object'}};
    const result = await json(url, {method: 'POST', signal,
      headers: {'Content-Type': 'application/json', ...(settings.apiKey ? {Authorization: 'Bearer ' + settings.apiKey} : {})},
      body: JSON.stringify(payload)});
    const choice = result && result.choices && result.choices[0];
    if (choice && choice.finish_reason === 'length') throw new Error(messages.tokenLimit);
    if (choice && (choice.finish_reason === 'content_filter' || choice.message && choice.message.refusal)) throw new Error(messages.refused);
    const text = choice && choice.message && choice.message.content;
    if (typeof text !== 'string') throw new Error(messages.noText);
    return text;
  }
  async function test(value, options = {}) {
    const settings = normalized(value);
    resetVerification(); changed(); const started = epoch();
    const result = await timed(options.signal, async signal => {
      const data = await contract(signal);
      if (typeof data.testPrompt !== 'string') throw new Error(messages.context);
      validateReview(await infer(settings, data.testPrompt, data.instructions, data.schema, [], signal), 'correct', '', 'en', true);
      return {ready: true, message: messages.ready, model: settings.model};
    });
    markVerified(settings, started); changed(); return result;
  }
  const figureNames = reference => {
    const names = [], texts = [reference.question, ...Object.values(reference.choices || {}), reference.solution];
    for (const text of texts) for (const match of String(text || '').matchAll(/\[Figure \d+\]\(([^)]+)\)/g)) if (!names.includes(match[1])) names.push(match[1]);
    return names;
  };
  async function imageData(url, signal) {
    active(signal);
    let response;
    try { response = await fetch(url.href, {signal, credentials: 'omit', referrerPolicy: 'no-referrer', redirect: 'error'}); }
    catch (error) { if (error.name === 'AbortError') throw error; throw new Error(messages.figure); }
    if (!response.ok) throw new Error(messages.figure);
    const blob = await response.blob(); active(signal);
    const objectUrl = URL.createObjectURL(blob);
    try {
      const image = new Image();
      await new Promise((resolve, reject) => {
        const abort = () => { image.src = ''; reject(abortError()); };
        const done = action => { if (signal) signal.removeEventListener('abort', abort); action(); };
        image.onload = () => done(resolve); image.onerror = () => done(() => reject(new Error(messages.figure)));
        if (signal) signal.addEventListener('abort', abort, {once: true});
        image.src = objectUrl;
      });
      active(signal);
      if (!image.naturalWidth || !image.naturalHeight) throw new Error(messages.figure);
      const edge = Math.max(image.naturalWidth, image.naturalHeight), scale = Math.min(Math.max(2, 900 / edge), 1600 / edge);
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(image.naturalWidth * scale) + 24; canvas.height = Math.round(image.naturalHeight * scale) + 24;
      const context = canvas.getContext('2d'); if (!context) throw new Error(messages.figure);
      context.fillStyle = 'white'; context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 12, 12, canvas.width - 24, canvas.height - 24);
      const data = canvas.toDataURL('image/png');
      if (!data.startsWith('data:image/png;base64,')) throw new Error(messages.figure);
      return data;
    } catch (error) { if (error.name === 'AbortError') throw error; throw new Error(messages.figure); }
    finally { URL.revokeObjectURL(objectUrl); }
  }
  async function figures(question, reference, signal) {
    const names = figureNames(reference), images = [];
    for (const name of names) {
      if (!/^figures\/[A-Za-z0-9][A-Za-z0-9_.-]*\.(svg|png|jpe?g|webp)$/i.test(name) || !question.figuresBase) throw new Error(messages.figure);
      const url = new URL(question.figuresBase + name.split('/').pop(), document.baseURI);
      if (url.origin !== location.origin || !['http:', 'https:'].includes(url.protocol)) throw new Error(messages.figure);
      images.push(await imageData(url, signal));
    }
    return {names, images};
  }
  function assessment(body, question) {
    const Answers = window.MathPracticeAnswers, known = Answers.classify(question, body.answer), note = Answers.gradingNotice(question);
    const common = {questionId: question.id, answer: Answers.copy(body.answer), revisionId: body.turn && body.turn.revisionId,
      curriculumLayer: body.curriculumLayer, curriculumNodeId: body.curriculumNodeId};
    if (note !== null) return {...common, gradingStatus: 'disputed', gradingNote: note, category: 'cannot_judge', answerCategory: 'not_graded', answerCorrect: null};
    return {...common, category: 'cannot_judge', answerCategory: known || 'cannot_judge', exactAnswerCategory: known,
      answerCorrect: known === 'correct' ? true : known === 'wrong' ? false : null,
      answerFormFeedback: Answers.formFeedback(question, body.answer), modelUsed: false, decisionConfigured: false, inferenceConfigured: status().configured, decisionRequests: 0};
  }
  async function post(path, body, controller, question) {
    if (!question || question.id !== body.questionId) throw new Error(messages.context);
    active(controller && controller.signal);
    const result = assessment(body, question);
    if (path === '/api/assessment' || result.gradingStatus === 'disputed') return result;
    if (path !== '/api/tutor') throw new Error(messages.unconfigured);
    // Read saved credentials for every request, including retries after a settings edit.
    const settings = getSettings();
    const started = epoch();
    if (!status().configured) throw new Error(messages.unconfigured);
    try {
      const value = await timed(controller && controller.signal, async signal => {
        const data = await contract(signal), context = question.tutorContext;
        if (!context || !context.reference) throw new Error(messages.context);
        const teaching = await teachingContext(question, body, signal);
        const {names, images} = await figures(question, context.reference, signal);
        const known = window.MathPracticeAnswers.classify(question, body.answer);
        const prompt = JSON.stringify({reference: {...context.reference, knownAnswerCorrect: known === 'correct' ? true : known === 'wrong' ? false : null, knownAnswerCategory: known},
          studentSubmission: {answer: body.answer, reasoning: body.thoughts}, initialDecision: {reasoning: body.category, answer: body.answerCategory},
          practiceLanguage: question.language || 'en', teachingContext: teaching,
          reviewedCriterion: context.reviewedCriterion, turn: body.turn || {action: 'submit', assistance: 'unknown', previous: null}, attachedFiguresInOrder: names});
        const text = await infer(settings, prompt, data.instructions, data.schema, images, signal);
        return {...result, ...validateReview(text, known, result.answerFormFeedback, question.language || 'en', !!body.thoughts), configured: true, inferenceConfigured: true};
      });
      markVerified(settings, started); changed(); return value;
    } catch (error) { if (stored(VERIFIED).key === identity(settings)) { resetVerification(); changed(); } throw error; }
  }
  // Retire saved helper connections without forwarding an account model to an API.
  const previous = stored(SETTINGS, true), previousSecrets = stored(SECRETS);
  if (previous.method === 'chatgpt' || 'companionUrl' in previous || 'companionToken' in previousSecrets) {
    try {
      const current = getSettings();
      localStorage.setItem(SETTINGS, JSON.stringify({method: 'api', baseUrl: current.baseUrl, model: current.model}));
      sessionStorage.setItem(SECRETS, JSON.stringify({apiKey: current.apiKey}));
      sessionStorage.removeItem(ACCOUNT);
    } catch (_) { /* Reading questions and exact answer checks still work without storage. */ }
    resetVerification();
  }
  window.MathPracticeOnline = {getSettings, saveSettings, status, test, models, account, post};
})();
