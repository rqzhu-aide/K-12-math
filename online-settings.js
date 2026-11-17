(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const language = window.MathPracticeLanguage;
  if (language) language.register({
    'Choose your own math tutor, then test the connection. You can browse questions, check answers and read included solutions without AI.': '选择你自己的数学辅导模型，然后测试连接。不使用 AI 也可以浏览题目、核对答案和阅读已有解答。',
    'Provider API URL': '服务商 API 网址',
    'Use an OpenAI-compatible API that permits requests from this website. Requests go directly from your browser to your chosen provider.': '使用允许本网站发送请求的 OpenAI 兼容 API。请求由浏览器直接发送给你选择的服务商。',
    'Your API key is kept only for this browser tab session. It is sent directly to the provider you choose. Provider charges and data-use policies apply.': 'API 密钥仅保留在当前浏览器标签页的会话中，并直接发送给你选择的服务商。费用和数据使用规则以服务商规定为准。',
    'ChatGPT login': 'ChatGPT 登录', 'Forthcoming': '即将推出',
    'Fetch models': '获取模型列表', 'Enter a model name, or fetch available models.': '输入模型名称，或获取可用模型列表。',
    'Tests may use API credits. A successful text test does not verify image support.': '测试可能消耗 API 额度。文字测试成功并不代表模型支持图片。',
    'Optional Ailleo services are managed by the site operator. You do not need to enter an API key for them.': '可选的 Ailleo 服务由网站运营者管理。你无需为这些服务输入 API 密钥。',
    'Not connected': '尚未连接',
    'This service will appear when the site operator connects the desktop service to a public address. You can keep using the question bank and your own tutor.': '网站运营者将桌面服务连接到公网地址后，此服务才会开放。在此之前，你仍然可以使用题库和自己的辅导模型。',
    'Tutor requests go directly to your chosen API provider. The site operator does not provide your math tutor.': '辅导请求直接发送给你选择的 API 服务商。数学辅导模型由你自己连接。',
    'Opening or saving settings does not run a model. Keep personal information out of your work. Provider data-use policies apply.': '打开或保存设置不会调用模型。请勿在作答内容中包含个人信息。数据使用规则以服务商规定为准。',
    'Secrets last only for this tab session.': '密钥仅保留在当前标签页会话中。',
    'Connection settings loaded. Secrets last only for this tab session.': '已加载连接设置。密钥仅保留在当前标签页会话中。',
    'Connection settings saved. Secrets last only for this tab session.': '已保存连接设置。密钥仅保留在当前标签页会话中。',
    'Online tutor settings could not load. Reload this page to try again.': '在线辅导设置加载失败。请重新加载本页面后重试。',
    'You have unsaved connection settings.': '连接设置有未保存的修改。',
    'Test these settings before using them in practice.': '请先测试这些设置，再用于练习。',
    'Enter the provider API URL.': '请输入服务商 API 网址。', 'Enter a valid HTTP or HTTPS URL.': '请输入有效的 HTTP 或 HTTPS 网址。',
    'Enter a model name.': '请输入模型名称。',
    'Saving…': '正在保存…', 'Settings saved for this tab. Run a connection test when ready.': '已为当前标签页保存设置。准备好后可以测试连接。',
    'Settings saved for this tab. The text tutor test passed.': '已为当前标签页保存设置。文字辅导测试已通过。',
    'Running a short connection test…': '正在运行简短的连接测试…', 'Text tutor test passed.': '文字辅导测试已通过。', 'Text test passed': '文字测试通过',
    'The connection did not pass the tutor test.': '此连接未通过辅导测试。', 'These settings are not saved yet.': '这些设置尚未保存。',
    'Fetching models…': '正在获取模型列表…', 'Models loaded. Choose a name from the list, or enter one.': '已加载模型列表。请从列表中选择或手动输入名称。',
    'No models were returned. You can enter a model name manually.': '未返回模型列表。你可以手动输入模型名称。',
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
    let message = String(error && error.message || error || t('The request failed. Check the connection settings and try again.'));
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
  function badge() {
    say('inferenceBadge', passed === identity() ? 'Text test passed' : snapshot().model ? 'Not tested' : 'Not configured', passed === identity() ? 'ok' : '');
  }
  function edited(event) {
    if (working) return;
    passed = ''; badge();
    if (event && event.target.id !== 'inferenceModel') $('inferenceModelNames').replaceChildren();
    say('pageStatus', identity() === saved ? '' : 'You have unsaved connection settings.');
    say('inferenceResult', 'Test these settings before using them in practice.');
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
    busy(true); say('fetchModels', 'Fetching models…'); say('modelListStatus', 'Fetching models…');
    try {
      const response = await api.models(snapshot(), {});
      const count = setModels(response.models);
      say('modelListStatus', count ? 'Models loaded. Choose a name from the list, or enter one.' : 'No models were returned. You can enter a model name manually.');
    } catch (error) { say('modelListStatus', safeMessage(error), 'error'); }
    finally { busy(false); say('fetchModels', 'Fetch models'); }
  }
  async function test() {
    if (working || !validate(true)) return;
    const value = snapshot(), current = identity(value);
    passed = ''; busy(true); say('testInference', 'Testing…'); say('inferenceBadge', 'Testing'); say('inferenceResult', 'Running a short connection test…');
    try {
      const response = await api.test(value, {});
      if (!response || response.ready !== true) throw new Error(response && response.message || t('The connection did not pass the tutor test.'));
      passed = current; badge();
      say('inferenceResult', () => t('Text tutor test passed.') + (current === saved ? '' : ' ' + t('These settings are not saved yet.')), 'ok');
    } catch (error) { say('inferenceBadge', 'Test failed', 'error'); say('inferenceResult', safeMessage(error), 'error'); $('inferenceResult').focus(); }
    finally { busy(false); say('testInference', 'Test Connection'); notify(); }
  }
  async function save(event) {
    event.preventDefault();
    if (working || !validate(true)) return;
    const value = snapshot(); busy(true); say('saveInference', 'Saving…');
    try {
      await api.saveSettings(value); saved = identity(value); notify();
      say('pageStatus', 'Connection settings saved. Secrets last only for this tab session.');
      say('inferenceResult', passed === saved ? 'Settings saved for this tab. The text tutor test passed.' : 'Settings saved for this tab. Run a connection test when ready.', 'ok');
      badge();
    } catch (error) { say('inferenceResult', safeMessage(error), 'error'); $('inferenceResult').focus(); }
    finally { busy(false); say('saveInference', 'Save Settings'); }
  }
  function selectTab(name, focus) {
    for (const role of ['speech', 'decision']) {
      const selected = role === name;
      $(role + 'Tab').setAttribute('aria-selected', String(selected)); $(role + 'Tab').tabIndex = selected ? 0 : -1;
      $(role + 'Panel').hidden = !selected;
    }
    if (focus) $(name + 'Tab').focus();
  }
  ['speech', 'decision'].forEach((name, index) => {
    $(name + 'Tab').addEventListener('click', () => selectTab(name));
    $(name + 'Tab').addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault(); selectTab(event.key === 'Home' ? 'speech' : event.key === 'End' ? 'decision' : ['speech', 'decision'][1 - index], true);
    });
  });
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
    saved = identity(); passed = api.status().ready === true ? saved : ''; badge();
    if (passed) say('inferenceResult', 'Text tutor test passed.', 'ok');
    say('pageStatus', 'Connection settings loaded. Secrets last only for this tab session.');
  } catch (_) { busy(true); say('pageStatus', 'Online tutor settings could not load. Reload this page to try again.', 'error'); }
}());
