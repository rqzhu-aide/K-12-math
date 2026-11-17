/* Learner-owned tutor transport. Credentials belong to this browser tab. */
(function () {
  'use strict';
  const SETTINGS = 'math-practice.online-tutor.v1', SECRETS = 'math-practice.online-tutor.secrets.v1';
  const VERIFIED = 'math-practice.online-tutor.verified.v1', ACCOUNT = 'math-practice.online-tutor.account.v1', EPOCH = 'math-practice.online-tutor.epoch.v1';
  const defaults = {method: 'api', baseUrl: 'https://api.openai.com/v1', model: '', companionUrl: 'http://127.0.0.1:8879'};
  const Language = window.MathPracticeLanguage;
  const messages = {
    unconfigured: 'Connect your own tutor in Settings for reasoning feedback.',
    untested: 'Your tutor is configured. Test the connection or submit your work.',
    ready: 'Your tutor completed a structured review.',
    url: 'Use an HTTPS API URL, or HTTP on this computer, separate from this website.',
    companion: 'Use the companion on this computer and enter its current pairing key.',
    apiNetwork: 'The API could not be reached from this browser. Check its URL and browser access (CORS), or use the ChatGPT companion.',
    companionNetwork: 'The companion could not be reached. Start it on this computer, check its pairing key and allow browser access.',
    auth: 'The API rejected this key. Check your key in Settings and test again.',
    denied: 'The API denied this request. Check access to the selected model.',
    missing: 'The API endpoint was not found. Check the API base URL in Settings.',
    limit: 'The API reached a usage or rate limit. Check your provider account and retry.',
    apiError: 'The API could not complete this request. Check the selected model and retry.',
    companionError: 'The companion could not complete this request. Check its account status and pairing key.',
    unreadable: 'The tutor returned an unreadable review. Try the review again.',
    incomplete: 'The tutor returned an incomplete review. Try the review again.',
    length: 'The tutor did not return a short visible review within 50 words or 100 script characters. Try the review again.',
    context: 'The tutor context could not load. Reload this website and retry.',
    selection: 'The selected topic context could not load. Reload this problem and retry.',
    figure: 'A problem figure could not be sent to the tutor. Reload the problem and retry.',
    storage: 'Browser storage is unavailable. Allow storage for this website to connect your tutor.',
    account: 'Sign in through the companion, then test your selected ChatGPT model.',
    noText: 'The inference service returned no review text.'
  };
  if (Language) Language.register({
    [messages.unconfigured]: '在设置中连接你自己的辅导模型，以获取推理反馈。',
    [messages.untested]: '已配置你的辅导模型。请测试连接或提交作答。',
    [messages.ready]: '你的辅导模型已完成结构化点评。',
    [messages.url]: '请使用 HTTPS API 地址，或本机的 HTTP 地址，并与本站地址分开。',
    [messages.companion]: '请使用本机上的连接助手，并输入它当前的配对密钥。',
    [messages.apiNetwork]: '浏览器无法连接 API。请检查地址与浏览器访问权限（CORS），或使用 ChatGPT 连接助手。',
    [messages.companionNetwork]: '无法连接本机助手。请启动助手，检查配对密钥，并允许浏览器访问。',
    [messages.auth]: 'API 拒绝了此密钥。请在设置中检查密钥后重新测试。',
    [messages.denied]: 'API 拒绝了此请求。请检查所选模型的访问权限。',
    [messages.missing]: '未找到 API 端点。请检查设置中的 API 基础地址。',
    [messages.limit]: 'API 已达到用量或速率限制。请检查服务商账户后重试。',
    [messages.apiError]: 'API 未能完成请求。请检查所选模型后重试。',
    [messages.companionError]: '本机助手未能完成请求。请检查账户状态和配对密钥。',
    [messages.unreadable]: '辅导返回的点评无法读取，请重新点评。',
    [messages.incomplete]: '辅导返回的点评不完整，请重新点评。',
    [messages.length]: '辅导未返回限定长度的可见点评（最多 50 个英文词或 100 个汉字），请重新点评。',
    [messages.context]: '无法加载辅导所需的题目背景。请刷新本站后重试。',
    [messages.selection]: '无法加载所选主题的辅导背景。请重新加载此题后重试。',
    [messages.figure]: '无法向辅导模型发送题目图片。请重新加载题目后重试。',
    [messages.storage]: '浏览器存储不可用。请允许本站使用存储以连接辅导模型。',
    [messages.account]: '请通过本机助手登录，然后测试所选的 ChatGPT 模型。',
    [messages.noText]: '推理服务未返回点评文字。',
    'Enter the current pairing key from the tutor companion window, then connect again.': '请输入本机助手窗口显示的当前配对密钥，然后重新连接。',
    'This website is not allowed to use the tutor companion.': '此网站未获准使用本机辅导助手。',
    'A ChatGPT request is already running. Wait for it to finish.': '已有 ChatGPT 请求正在运行，请等待完成。',
    'Your ChatGPT authorization expired. Continue with ChatGPT to sign in again.': '你的 ChatGPT 授权已过期。请继续使用 ChatGPT 重新登录。',
    'ChatGPT plan permission is disabled. Continue with ChatGPT and approve plan usage.': 'ChatGPT 套餐权限已关闭。请继续使用 ChatGPT 并允许使用套餐。',
    'The tutor connection was interrupted. Keep the companion running and try again.': '辅导连接已中断。请保持本机助手运行并重试。'
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
      const account = stored(ACCOUNT);
      if (settings.method === 'chatgpt' && account.key === companionIdentity(settings)) sessionStorage.setItem(ACCOUNT, JSON.stringify({...account, canTest: true}));
      sessionStorage.setItem(VERIFIED, JSON.stringify({key: identity(settings)}));
    } catch (_) {}
  }
  function setAccount(settings, value) {
    const previous = stored(ACCOUNT);
    const accountId = value.chatgpt.account && value.chatgpt.account.id;
    if (!value.chatgpt.canTest || previous.key === companionIdentity(settings) && previous.accountId !== accountId) resetVerification();
    try { sessionStorage.setItem(ACCOUNT, JSON.stringify({key: companionIdentity(settings), accountId, canTest: value.chatgpt.canTest === true})); } catch (_) {}
  }
  function getSettings() {
    const saved = stored(SETTINGS, true), secrets = stored(SECRETS);
    return {method: saved.method === 'chatgpt' ? 'chatgpt' : 'api', baseUrl: typeof saved.baseUrl === 'string' ? saved.baseUrl : defaults.baseUrl,
      model: clean(saved.model), companionUrl: typeof saved.companionUrl === 'string' ? saved.companionUrl : defaults.companionUrl,
      apiKey: clean(secrets.apiKey), companionToken: clean(secrets.companionToken)};
  }
  function normalized(value) {
    const settings = {...getSettings(), ...value};
    return {method: settings.method === 'chatgpt' ? 'chatgpt' : 'api', baseUrl: clean(settings.baseUrl), model: clean(settings.model),
      companionUrl: clean(settings.companionUrl), apiKey: clean(settings.apiKey), companionToken: clean(settings.companionToken)};
  }
  function changed() {
    if (window.dispatchEvent && typeof CustomEvent !== 'undefined') window.dispatchEvent(new CustomEvent('math-practice-online-change'));
  }
  function saveSettings(value) {
    const settings = normalized(value);
    // URL userinfo and query strings can contain credentials; never persist them.
    if (settings.baseUrl) endpoint(settings);
    if (settings.companionUrl) endpoint({...settings, companionToken: 'validate-url'}, true);
    try {
      localStorage.setItem(SETTINGS, JSON.stringify({method: settings.method, baseUrl: settings.baseUrl, model: settings.model, companionUrl: settings.companionUrl}));
      sessionStorage.setItem(SECRETS, JSON.stringify({apiKey: settings.apiKey, companionToken: settings.companionToken}));
    } catch (_) { throw new Error(messages.storage); }
    const verified = stored(VERIFIED);
    if (verified.key && verified.key !== identity(settings)) resetVerification();
    changed(); return getSettings();
  }
  function loopback(url) { return ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname); }
  function endpoint(settings, companion = false) {
    let url;
    try { url = new URL(companion ? settings.companionUrl : settings.baseUrl); } catch (_) { throw new Error(companion ? messages.companion : messages.url); }
    if (url.username || url.password || url.search || url.hash || url.origin === location.origin
        || (companion ? !loopback(url) || !['http:', 'https:'].includes(url.protocol)
          : url.protocol !== 'https:' && !(url.protocol === 'http:' && loopback(url)))) throw new Error(companion ? messages.companion : messages.url);
    if (companion && !settings.companionToken) throw new Error(messages.companion);
    return url;
  }
  function apiEndpoint(settings, path) {
    const url = endpoint(settings);
    let prefix = url.pathname.replace(/\/+$/, '').replace(/\/chat\/completions$/, '').replace(/\/models$/, '');
    if (!prefix.endsWith('/v1')) prefix += '/v1';
    url.pathname = prefix + '/' + path;
    return url.href;
  }
  function companionIdentity(settings) { return JSON.stringify([settings.companionUrl, settings.companionToken]); }
  function status() {
    const settings = getSettings();
    let configured = false, message = messages.unconfigured;
    try {
      endpoint(settings, settings.method === 'chatgpt');
      configured = !!settings.model && (settings.method !== 'chatgpt' || !!settings.companionToken);
      if (configured) message = settings.method === 'chatgpt' ? messages.account : messages.untested;
    } catch (_) {}
    const lastAccount = stored(ACCOUNT), verified = stored(VERIFIED);
    const accountAvailable = settings.method !== 'chatgpt' || lastAccount.key !== companionIdentity(settings) || lastAccount.canTest;
    const ready = configured && verified.key === identity(settings) && !!accountAvailable;
    if (ready) message = messages.ready;
    if (configured && lastAccount.key === companionIdentity(settings) && settings.method === 'chatgpt' && !lastAccount.canTest) message = messages.account;
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
  async function json(url, options, companion = false) {
    let response;
    try { response = await fetch(url, {...options, credentials: 'omit', referrerPolicy: 'no-referrer', cache: 'no-store', redirect: 'error'}); }
    catch (error) { if (error.name === 'AbortError') throw error; throw new Error(companion ? messages.companionNetwork : messages.apiNetwork); }
    if (!response.ok) {
      if (companion) {
        // The local helper exposes curated public errors, never raw provider diagnostics.
        let value;
        try { value = await response.json(); } catch (_) {}
        const secrets = getSettings(), header = options.headers && options.headers.Authorization;
        const privateValues = [secrets.apiKey, secrets.companionToken, header && header.replace(/^Bearer /, '')].filter(Boolean);
        const safe = value && typeof value.error === 'string' && value.error.length <= 600 && !privateValues.some(secret => value.error.includes(secret));
        throw new Error(safe ? value.error : response.status === 401 || response.status === 403 ? messages.companion : messages.companionError);
      }
      throw new Error(({401: messages.auth, 403: messages.denied, 404: messages.missing, 429: messages.limit})[response.status] || messages.apiError);
    }
    try { const value = await response.json(); active(options.signal); return value; }
    catch (error) { if (error.name === 'AbortError') throw error; throw new Error(messages.unreadable); }
  }
  async function companionCall(action, settings, body, signal) {
    const url = endpoint(settings, true);
    url.pathname = '/api/companion/' + (action === 'status' ? 'status' : 'chatgpt/' + action);
    return json(url.href, {method: action === 'status' ? 'GET' : 'POST', signal,
      headers: {'Authorization': 'Bearer ' + settings.companionToken, ...(action === 'status' ? {} : {'Content-Type': 'application/json'})},
      ...(action === 'status' ? {} : {body: JSON.stringify(body || {})})}, true);
  }
  async function account(action, value, options = {}) {
    if (!['status', 'login', 'cancel', 'logout'].includes(action)) throw new Error(messages.companionError);
    const settings = normalized(value), payload = {};
    if (action === 'login' || action === 'logout') resetVerification();
    if (action === 'login' && value) {
      if (value.clientId) payload.clientId = value.clientId;
      if (value.newAccount === true) payload.newAccount = true;
    }
    let result;
    try { result = await timed(options.signal, signal => companionCall(action, settings, payload, signal), 30000); }
    catch (error) { resetVerification(); changed(); throw error; }
    if (!result || result.application !== 'math-practice-tutor-companion' || result.version !== 1 || result.paired !== true || !result.chatgpt) { resetVerification(); changed(); throw new Error(messages.companionError); }
    setAccount(settings, result);
    changed(); return result;
  }
  async function models(value, options = {}) {
    const settings = normalized(value);
    return timed(options.signal, async signal => {
      if (settings.method === 'chatgpt') {
        let result;
        try {
          result = await companionCall('models', settings, {}, signal);
          if (!result || result.application !== 'math-practice-tutor-companion' || result.version !== 1 || result.paired !== true || !result.chatgpt || !Array.isArray(result.chatgpt.modelSuggestions)) throw new Error(messages.companionError);
        } catch (error) { resetVerification(); changed(); throw error; }
        setAccount(settings, result); changed();
        return {...result, models: result.chatgpt.modelSuggestions.filter(model => model && typeof model.model === 'string').map(model => ({...model, id: model.model}))};
      }
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
    if (settings.method === 'chatgpt') {
      const result = await companionCall('infer', settings, {selection: {model: settings.model}, prompt, instructions, schema, images}, signal);
      if (!result || typeof result.reply !== 'string') throw new Error(messages.noText);
      return result.reply;
    }
    const content = images.length ? [{type: 'text', text: prompt}, ...images.map(url => ({type: 'image_url', image_url: {url}}))] : prompt;
    const result = await json(apiEndpoint(settings, 'chat/completions'), {method: 'POST', signal,
      headers: {'Content-Type': 'application/json', ...(settings.apiKey ? {Authorization: 'Bearer ' + settings.apiKey} : {})},
      body: JSON.stringify({model: settings.model, messages: [{role: 'system', content: instructions}, {role: 'user', content}], max_tokens: 1000, response_format: {type: 'json_object'}})});
    const text = result && result.choices && result.choices[0] && result.choices[0].message && result.choices[0].message.content;
    if (typeof text !== 'string') throw new Error(messages.noText);
    return text;
  }
  async function test(value, options = {}) {
    const settings = normalized(value);
    resetVerification(); changed(); const started = epoch();
    const result = await timed(options.signal, async signal => {
      if (settings.method === 'chatgpt') {
        const result = await companionCall('test', settings, {model: settings.model}, signal);
        if (!result || result.ok !== true || result.ready !== true) throw new Error(messages.companionError);
      } else {
        const data = await contract(signal);
        if (typeof data.testPrompt !== 'string') throw new Error(messages.context);
        validateReview(await infer(settings, data.testPrompt, data.instructions, data.schema, [], signal), 'correct', '', 'en', true);
      }
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
  window.MathPracticeOnline = {getSettings, saveSettings, status, test, models, account, post};
})();
