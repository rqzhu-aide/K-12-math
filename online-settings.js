(function () {
  'use strict';
  if (!window.MathPracticeAgreement || !window.MathPracticeAgreement.accepted()) return;
  const $ = id => document.getElementById(id);
  const language = window.MathPracticeLanguage;
  window.MathPracticeAgreement.bindExperimentalSettings?.();
  if (language) language.register({
    'Provider API URL': '服务商 API 网址',
    'Use an OpenAI-compatible API that accepts requests from this website.': '请使用允许本网站发送请求的 OpenAI 兼容 API。',
    'Your browser sends requests directly to your provider and keeps your API key only for this tab session. A test sends a text-only sample and may use API credits. The provider’s data policy applies.': '浏览器会直接向你的服务商发送请求。API 密钥仅保留在当前标签页的会话中。连接测试只发送文字示例，可能消耗 API 额度。数据处理遵循服务商的政策。',
    'ChatGPT sign-in is coming to the website.': '网页版将支持 ChatGPT 登录。',
    'Fetch models': '获取模型列表',
    'Check connection': '检查连接', 'Checking…': '正在检查…',
    'Connection checks send no audio or practice data.': '检查连接时不会发送录音或练习数据。',
    'Server setup pending': '服务器尚未接入',
    'Reachable': '可连接', 'Unavailable': '暂不可用', 'Not checked': '尚未检查',
    'The service connection could not be checked. Try again.': '无法检查服务连接，请重试。',
    'Online tutor settings could not load. Reload this page to try again.': '在线辅导设置加载失败。请重新加载本页面后重试。',
    'Enter the provider API URL.': '请输入服务商 API 网址。', 'Enter a valid HTTP or HTTPS URL.': '请输入有效的 HTTP 或 HTTPS 网址。',
    'Enter a model name.': '请输入模型名称。',
    'Settings saved. Test the connection before practicing.': '设置已保存。开始练习前，请测试连接。',
    'The connection did not pass the tutor test.': '此连接未通过辅导测试。',
    'Fetching models…': '正在获取模型列表…', 'Models loaded. Choose one or type a name.': '模型列表已加载。请选择或输入模型名称。',
    'No models returned. Type a model name.': '未返回模型列表。请输入模型名称。',
    'The request failed. Check the connection settings and try again.': '请求失败。请检查连接设置后重试。'
  });
  const api = window.MathPracticeOnline;
  const text = (node, value, state) => {
    if (language) language.bindText(node, value); else node.textContent = typeof value === 'function' ? value() : value;
    node.dataset.state = state || '';
  };
  const say = (id, value, state) => text($(id), value, state);
  const t = value => language ? language.t(value) : value;
  let working = false;
  let saved = '', passed = '';
  const formControls = [...$('inferenceForm').querySelectorAll('input, button')];
  const snapshot = () => ({method: 'api', baseUrl: $('inferenceBases').value.trim(), apiKey: $('inferenceKey').value,
    model: $('inferenceModel').value.trim()});
  const identity = value => JSON.stringify(value || snapshot());
  const safeMessage = error => {
    let message = String(error && error.message || error || 'The request failed. Check the connection settings and try again.');
    const secret = $('inferenceKey').value;
    if (secret) message = message.split(secret).join('[redacted]');
    return message;
  };
  const busy = value => {
    working = value;
    for (const node of formControls) node.disabled = value;
    $('inferenceForm').setAttribute('aria-busy', String(value));
  };
  function notify() {
    if (window.parent !== window) window.parent.postMessage({type: 'math-practice-settings-updated'}, window.location.origin);
  }
  const services = window.MathPracticeServices;
  const serviceRoles = ['speech', 'decision'];
  const serviceChecking = {speech: false, decision: false};
  const serviceErrors = {speech: '', decision: ''};
  const serviceCheckButton = role => $(role === 'speech' ? 'checkSpeech' : 'checkDecision');
  function renderServices() {
    for (const role of serviceRoles) {
      const status = services.status(role);
      const check = serviceCheckButton(role);
      check.disabled = !status.configured || serviceChecking[role];
      check.setAttribute('aria-busy', String(serviceChecking[role]));
      let label = 'Not checked', state = '';
      if (!status.configured) label = 'Server setup pending';
      else if (serviceChecking[role]) label = 'Checking…';
      else if (status.available === false) label = 'Unavailable';
      else if (status.available === true) { label = 'Reachable'; state = 'ok'; }
      say(role + 'Badge', label, state);
      say(role + 'Status', serviceErrors[role], serviceErrors[role] ? 'error' : '');
    }
  }
  async function checkService(role) {
    if (serviceChecking[role] || !services.config().configured) return;
    serviceChecking[role] = true; serviceErrors[role] = ''; renderServices();
    try { await services.check(role); }
    catch (error) { serviceErrors[role] = safeMessage(error || 'The service connection could not be checked. Try again.'); }
    finally { serviceChecking[role] = false; renderServices(); notify(); }
  }
  if (services) {
    renderServices();
    for (const role of serviceRoles) {
      serviceCheckButton(role).addEventListener('click', () => checkService(role));
    }
    window.addEventListener('pageshow', renderServices);
  }
  function edited(event) {
    if (working) return;
    passed = '';
    if (event.target.id !== 'inferenceModel') {
      $('inferenceModelNames').replaceChildren();
      say('modelListStatus', '');
    }
    say('inferenceResult', identity() === saved ? '' : 'You have unsaved connection settings.');
    for (const input of formControls) input.removeAttribute('aria-invalid');
  }
  function invalid(id, message) {
    $(id).setAttribute('aria-invalid', 'true');
    say('inferenceResult', message, 'error'); $(id).focus(); return false;
  }
  function validate(requireModel) {
    const value = snapshot();
    if (!value.baseUrl) return invalid('inferenceBases', 'Enter the provider API URL.');
    try { const parsed = new URL(value.baseUrl); if (!['https:', 'http:'].includes(parsed.protocol) || parsed.username || parsed.password) throw new Error(); }
    catch (_) { return invalid('inferenceBases', 'Enter a valid HTTP or HTTPS URL.'); }
    if (requireModel && !value.model) return invalid('inferenceModel', 'Enter a model name.');
    return true;
  }
  function setModels(models) {
    const names = [...new Set((models || []).map(item => typeof item === 'string' ? item : item.id || item.model).filter(Boolean))];
    $('inferenceModelNames').replaceChildren(...names.map(name => { const option = document.createElement('option'); option.value = name; return option; }));
    return names.length;
  }
  async function fetchModels() {
    if (working || !validate(false)) return;
    busy(true); say('fetchModels', 'Fetching models…'); say('modelListStatus', '');
    try {
      const response = await api.models(snapshot(), {});
      const count = setModels(response.models);
      say('modelListStatus', count ? 'Models loaded. Choose one or type a name.' : 'No models returned. Type a model name.');
    } catch (error) { say('modelListStatus', safeMessage(error), 'error'); }
    finally { busy(false); say('fetchModels', 'Fetch models'); }
  }
  async function test() {
    if (working || !validate(true)) return;
    const value = snapshot(), current = identity(value);
    passed = ''; busy(true); say('testInference', 'Testing…'); say('inferenceResult', '');
    try {
      const response = await api.test(value, {});
      if (!response || response.ready !== true) throw new Error(response && response.message || t('The connection did not pass the tutor test.'));
      passed = current;
      say('inferenceResult', () => t('Text test passed.') + (current === saved ? '' : ' ' + t('These settings are not saved yet.')), 'ok');
    } catch (error) { say('inferenceResult', safeMessage(error), 'error'); $('inferenceResult').focus(); }
    finally { busy(false); say('testInference', 'Test Connection'); notify(); }
  }
  async function save(event) {
    event.preventDefault();
    if (working || !validate(true)) return;
    const value = snapshot(); busy(true); say('saveInference', 'Saving…');
    try {
      await api.saveSettings(value); saved = identity(value); notify();
      say('inferenceResult', passed === saved ? 'Settings saved. Text test passed.' : 'Settings saved. Test the connection before practicing.', 'ok');
    } catch (error) { say('inferenceResult', safeMessage(error), 'error'); $('inferenceResult').focus(); }
    finally { busy(false); say('saveInference', 'Save Settings'); }
  }
  $('inferenceForm').addEventListener('input', edited);
  $('inferenceForm').addEventListener('submit', save);
  $('testInference').addEventListener('click', test);
  $('fetchModels').addEventListener('click', fetchModels);
  try {
    if (!api) throw new Error();
    const settings = api.getSettings();
    for (const [id, key] of [['inferenceBases', 'baseUrl'], ['inferenceKey', 'apiKey'], ['inferenceModel', 'model']]) {
      $(id).value = settings[key] || '';
    }
    saved = identity(); passed = api.status().ready === true ? saved : '';
    if (passed) say('inferenceResult', 'Text test passed.', 'ok');
  } catch (_) { busy(true); say('inferenceResult', 'Online tutor settings could not load. Reload this page to try again.', 'error'); }
}());
