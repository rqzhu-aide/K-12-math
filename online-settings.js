(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const language = window.MathPracticeLanguage;
  if (language) language.register({
    'Choose your own math tutor, then test the connection. You can browse questions, check answers and read included solutions without AI.': '选择你自己的数学辅导模型，然后测试连接。不使用 AI 也可以浏览题目、核对答案和阅读已有解答。',
    'Provider API URL': '服务商 API 网址',
    'Use an OpenAI-compatible API that permits requests from this website. Requests go directly from your browser to your chosen provider.': '使用允许本网站发送请求的 OpenAI 兼容 API。请求由浏览器直接发送给你选择的服务商。',
    'Your API key is kept only for this browser tab session. It is sent directly to the provider you choose. Provider charges and data-use policies apply.': 'API 密钥仅保留在当前浏览器标签页的会话中，并直接发送给你选择的服务商。费用和数据使用规则以服务商规定为准。',
    'ChatGPT sign-in needs a small helper running on the same computer as this browser. Your ChatGPT credentials stay on your device.': '使用 ChatGPT 登录需要在运行此浏览器的同一台电脑上启动一个小型辅助程序。ChatGPT 凭据保留在你的设备上。',
    'Download the tutor helper': '下载辅导连接助手', ' and extract the ZIP.': '，并解压 ZIP 文件。',
    'Start the helper on this computer and keep its terminal open.': '在这台电脑上启动连接助手，并保持终端窗口打开。',
    'Start instructions': '启动说明',
    'The helper uses your system Python installation. Install Python and its packages globally as described in the included README. No runtime is bundled.': '连接助手使用系统安装的 Python。请按随附 README 的说明，全局安装 Python 及所需的软件包。下载包不包含运行环境。',
    'Windows:': 'Windows：', 'macOS / Linux:': 'macOS / Linux：',
    'Paste the pairing key printed by the helper, then connect and sign in.': '粘贴连接助手显示的配对密钥，然后连接并登录。',
    'Helper pairing key': '连接助手配对密钥',
    'The pairing key is kept only for this tab session. Restarting the helper creates a new key. If your browser asks for local-network access, allow it for this site.': '配对密钥仅保留在当前标签页会话中。重启连接助手后会生成新密钥。如果浏览器询问是否允许访问本地网络，请允许本网站访问。',
    'Helper address': '连接助手地址', 'Local helper URL': '本地连接助手网址', 'ChatGPT connection': 'ChatGPT 连接',
    'Connect to the helper to check your ChatGPT sign-in.': '连接辅助程序后，即可检查 ChatGPT 登录状态。',
    'Connect helper': '连接辅助程序', 'Check status': '检查状态', 'Open ChatGPT sign-in': '打开 ChatGPT 登录页面', 'Sign out of helper': '在连接助手中退出登录',
    'Fetch models': '获取模型列表', 'Enter a model name, or fetch available models.': '输入模型名称，或获取可用模型列表。',
    'Tests may use API credits or ChatGPT plan usage. A successful text test does not verify image support.': '测试可能消耗 API 额度或 ChatGPT 套餐用量。文字测试成功并不代表模型支持图片。',
    'Optional Ailleo services are managed by the site operator. You do not need to enter an API key for them.': '可选的 Ailleo 服务由网站运营者管理。你无需为这些服务输入 API 密钥。',
    'Not connected': '尚未连接',
    'This service will appear when the site operator connects the desktop service to a public address. You can keep using the question bank and your own tutor.': '网站运营者将桌面服务连接到公网地址后，此服务才会开放。在此之前，你仍然可以使用题库和自己的辅导模型。',
    'API tutor requests go directly to your chosen provider. ChatGPT tutor requests pass through the helper on your computer. The site operator does not provide your math tutor.': 'API 辅导请求直接发送给你选择的服务商。ChatGPT 辅导请求通过你电脑上的连接助手发送。数学辅导模型由你自己连接。',
    'Opening or saving settings does not run a model. Keep personal information out of your work. Provider data-use policies apply.': '打开或保存设置不会调用模型。请勿在作答内容中包含个人信息。数据使用规则以服务商规定为准。',
    'Secrets last only for this tab session.': '密钥仅保留在当前标签页会话中。',
    'Connection settings loaded. Secrets last only for this tab session.': '已加载连接设置。密钥仅保留在当前标签页会话中。',
    'Connection settings saved. Secrets last only for this tab session.': '已保存连接设置。密钥仅保留在当前标签页会话中。',
    'Online tutor settings could not load. Reload this page to try again.': '在线辅导设置加载失败。请重新加载本页面后重试。',
    'You have unsaved connection settings.': '连接设置有未保存的修改。',
    'Test these settings before using them in practice.': '请先测试这些设置，再用于练习。',
    'Enter the provider API URL.': '请输入服务商 API 网址。', 'Enter a valid HTTP or HTTPS URL.': '请输入有效的 HTTP 或 HTTPS 网址。',
    'Enter the pairing key shown in the helper terminal.': '请输入连接助手终端显示的配对密钥。',
    'Enter a model name.': '请输入模型名称。', 'Connect the helper and sign in to ChatGPT before testing.': '请先连接辅助程序并登录 ChatGPT，然后测试。',
    'Saving…': '正在保存…', 'Settings saved for this tab. Run a connection test when ready.': '已为当前标签页保存设置。准备好后可以测试连接。',
    'Settings saved for this tab. The text tutor test passed.': '已为当前标签页保存设置。文字辅导测试已通过。',
    'Running a short connection test…': '正在运行简短的连接测试…', 'Text tutor test passed.': '文字辅导测试已通过。', 'Text test passed': '文字测试通过',
    'The connection did not pass the tutor test.': '此连接未通过辅导测试。', 'These settings are not saved yet.': '这些设置尚未保存。',
    'The ChatGPT connection changed during the test. Check status and test again.': '测试期间 ChatGPT 连接发生变化。请检查状态后重新测试。',
    'Fetching models…': '正在获取模型列表…', 'Models loaded. Choose a name from the list, or enter one.': '已加载模型列表。请从列表中选择或手动输入名称。',
    'No models were returned. You can enter a model name manually.': '未返回模型列表。你可以手动输入模型名称。',
    'Checking the helper…': '正在检查连接助手…', 'Connecting…': '正在连接…',
    'The helper is connected. Sign in to ChatGPT to continue.': '连接助手已连接。请登录 ChatGPT 后继续。',
    'ChatGPT is signed in. Choose a model and test the tutor.': '已登录 ChatGPT。请选择模型并测试辅导连接。',
    'ChatGPT is connected. The text tutor test passed.': 'ChatGPT 已连接，文字辅导测试已通过。',
    'Complete ChatGPT sign-in in the browser opened on this computer, then check status.': '请在这台电脑打开的浏览器窗口中完成 ChatGPT 登录，然后检查状态。',
    'Open the sign-in link to continue, then check status.': '请打开登录链接并完成登录，然后检查状态。',
    'The helper is connected, but ChatGPT is not ready.': '连接助手已连接，但 ChatGPT 尚未就绪。',
    'Updating ChatGPT sign-in…': '正在更新 ChatGPT 登录状态…',
    'Could not connect to the helper. Keep it running on this computer, use its current pairing key, and allow local-network access if your browser asks.': '无法连接辅助程序。请保持它在这台电脑上运行，使用当前配对密钥，并在浏览器询问时允许本地网络访问。',
    'The helper response was incomplete. Restart the helper and connect again.': '连接助手返回的信息不完整。请重启后重新连接。',
    'The request failed. Check the connection settings and try again.': '请求失败。请检查连接设置后重试。'
  });
  const api = window.MathPracticeOnline;
  const text = (node, value, state) => {
    if (language) language.bindText(node, value); else node.textContent = typeof value === 'function' ? value() : value;
    node.dataset.state = state || '';
  };
  const say = (id, value, state) => text($(id), value, state);
  const t = value => language ? language.t(value) : value;
  let method = 'api', working = false, accountState = null, accountTimer = null;
  let saved = '', passed = '', accountIdentity = '', accountVersion = 0;
  const modelDrafts = {api: '', chatgpt: ''};
  const formControls = [...$('inferenceForm').querySelectorAll('input, button')];
  const snapshot = () => ({method, baseUrl: $('inferenceBases').value.trim(), apiKey: $('inferenceKey').value,
    model: $('inferenceModel').value.trim(), companionUrl: $('companionUrl').value.trim(), companionToken: $('companionToken').value});
  const identity = value => JSON.stringify(value || snapshot());
  const safeMessage = error => {
    let message = String(error && error.message || error || t('The request failed. Check the connection settings and try again.'));
    for (const secret of [$('inferenceKey').value, $('companionToken').value]) {
      if (secret) message = message.split(secret).join('[redacted]');
    }
    return message;
  };
  const busy = value => {
    working = value;
    for (const node of formControls) node.disabled = value;
    $('inferenceForm').setAttribute('aria-busy', String(value));
    $('planLoginLink').setAttribute('aria-disabled', String(value));
  };
  function notify() {
    if (window.parent !== window) window.parent.postMessage({type: 'math-practice-settings-updated'}, window.location.origin);
  }
  function badge() {
    say('inferenceBadge', passed === identity() ? 'Text test passed' : snapshot().model ? 'Not tested' : 'Not configured', passed === identity() ? 'ok' : '');
  }
  function clearTimer() { clearTimeout(accountTimer); accountTimer = null; }
  function resetAccount() {
    ++accountVersion; clearTimer(); accountState = null;
    for (const id of ['planLogin', 'planLoginLink', 'planCancel', 'planDisconnect', 'managePlan']) $(id).hidden = true;
    $('planLoginLink').removeAttribute('href');
    say('connectCompanion', 'Connect helper');
    say('planAccountStatus', 'Connect to the helper to check your ChatGPT sign-in.');
  }
  function edited(event) {
    if (working) return;
    passed = ''; badge();
    if (event && ['companionToken', 'companionUrl'].includes(event.target.id)) resetAccount();
    refreshAccountStatus();
    if (event && event.target.id !== 'inferenceModel') $('inferenceModelNames').replaceChildren();
    say('pageStatus', identity() === saved ? '' : 'You have unsaved connection settings.');
    say('inferenceResult', 'Test these settings before using them in practice.');
    for (const input of formControls) input.removeAttribute('aria-invalid');
  }
  function switchMethod(next) {
    if (working || next === method) return;
    modelDrafts[method] = $('inferenceModel').value;
    method = next; $('inferenceModel').value = modelDrafts[next];
    $('inferenceApiFields').hidden = next !== 'api'; $('planAccountFields').hidden = next !== 'chatgpt';
    $('useCustomApi').setAttribute('aria-pressed', String(next === 'api'));
    $('useChatgptPlan').setAttribute('aria-pressed', String(next === 'chatgpt'));
    $('inferenceModelNames').replaceChildren();
    say('modelListStatus', 'Enter a model name, or fetch available models.');
    resetAccount(); edited();
    if (next === 'chatgpt' && $('companionToken').value) readAccount('status');
  }
  function invalid(id, message) {
    $(id).setAttribute('aria-invalid', 'true');
    if (id === 'companionUrl') $('helperAddressDetails').open = true;
    say('inferenceResult', message, 'error'); $(id).focus(); return false;
  }
  function validate(requireModel) {
    const value = snapshot(), urlId = method === 'api' ? 'inferenceBases' : 'companionUrl';
    if (!$(urlId).value.trim()) return invalid(urlId, method === 'api' ? 'Enter the provider API URL.' : 'Enter a valid HTTP or HTTPS URL.');
    try { const parsed = new URL($(urlId).value.trim()); if (!['https:', 'http:'].includes(parsed.protocol) || parsed.username || parsed.password) throw new Error(); }
    catch (_) { return invalid(urlId, 'Enter a valid HTTP or HTTPS URL.'); }
    if (method === 'chatgpt' && !value.companionToken.trim()) return invalid('companionToken', 'Enter the pairing key shown in the helper terminal.');
    if (requireModel && !value.model) return invalid('inferenceModel', 'Enter a model name.');
    return true;
  }
  function setModels(models) {
    const names = [...new Set((models || []).map(item => typeof item === 'string' ? item : item.id || item.model).filter(Boolean))];
    $('inferenceModelNames').replaceChildren(...names.map(name => { const option = document.createElement('option'); option.value = name; return option; }));
    return names.length;
  }
  function refreshAccountStatus() {
    if (method !== 'chatgpt' || !accountState) return;
    const info = accountState, signedIn = info.state === 'signed_in' && info.canTest === true;
    const description = signedIn ? 'ChatGPT is signed in. Choose a model and test the tutor.'
      : info.state === 'waiting' ? (!$('planLoginLink').hidden ? 'Open the sign-in link to continue, then check status.' : 'Complete ChatGPT sign-in in the browser opened on this computer, then check status.')
        : info.state === 'signed_out' ? 'The helper is connected. Sign in to ChatGPT to continue.'
          : 'The helper is connected, but ChatGPT is not ready.';
    const detail = info.message ? safeMessage({message: info.message}) : '';
    say('planAccountStatus', () => t(signedIn && passed === identity()
      ? 'ChatGPT is connected. The text tutor test passed.' : detail || description), info.state === 'failed' || info.state === 'unavailable' ? 'error' : '');
  }
  function renderAccount(envelope) {
    if (!envelope || envelope.paired !== true || !envelope.chatgpt) throw new Error(t('The helper response was incomplete. Restart the helper and connect again.'));
    const info = envelope.chatgpt, signedIn = info.state === 'signed_in' && info.canTest === true, waiting = info.state === 'waiting';
    const nextIdentity = JSON.stringify([info.state, info.canTest, info.account && info.account.id]);
    if (accountIdentity && accountIdentity !== nextIdentity || !signedIn || passed === saved && api.status().ready !== true) {
      if (passed) say('inferenceResult', 'Test these settings before using them in practice.');
      passed = ''; badge();
    }
    if (accountIdentity !== nextIdentity) notify();
    accountIdentity = nextIdentity; accountState = info;
    say('connectCompanion', 'Check status');
    let loginUrl = '';
    try { const parsed = new URL(info.loginUrl); if (parsed.protocol === 'https:') loginUrl = parsed.href; } catch (_) { /* Local helper may open the system browser itself. */ }
    $('planLoginLink').hidden = !loginUrl || signedIn;
    if (loginUrl) $('planLoginLink').href = loginUrl; else $('planLoginLink').removeAttribute('href');
    $('planLogin').hidden = signedIn || waiting || Boolean(loginUrl) || info.state === 'unavailable';
    $('planCancel').hidden = !waiting;
    $('planDisconnect').hidden = !info.account;
    $('managePlan').hidden = !info.account;
    refreshAccountStatus();
    if (info.modelSuggestions && info.modelSuggestions.length) {
      setModels(info.modelSuggestions);
      say('modelListStatus', 'Models loaded. Choose a name from the list, or enter one.');
    }
    if (info.modelMessage) say('modelListStatus', safeMessage({message: info.modelMessage}));
    clearTimer();
    if (method === 'chatgpt' && (waiting || info.modelsLoading)) accountTimer = setTimeout(() => { if (!working && !document.hidden) readAccount('status', true); }, 2000);
  }
  async function readAccount(action, quiet) {
    if (working || method !== 'chatgpt' || !validate(false)) return;
    clearTimer(); const version = ++accountVersion;
    if (!quiet) busy(true);
    if (!quiet) say('planAccountStatus', action === 'status' ? 'Checking the helper…' : 'Updating ChatGPT sign-in…');
    try {
      const response = await api.account(action, snapshot());
      if (version === accountVersion) renderAccount(response);
    } catch (error) {
      if (version === accountVersion) {
        resetAccount();
        if (passed) say('inferenceResult', 'Test these settings before using them in practice.');
        passed = ''; badge(); notify();
        const detail = safeMessage(error);
        say('planAccountStatus', () => t('Could not connect to the helper. Keep it running on this computer, use its current pairing key, and allow local-network access if your browser asks.') + ' ' + t(detail), 'error');
      }
    } finally { if (!quiet) busy(false); }
  }
  async function fetchModels() {
    if (working || !validate(false)) return;
    busy(true); say('fetchModels', 'Fetching models…'); say('modelListStatus', 'Fetching models…');
    try {
      const response = await api.models(snapshot(), {});
      if (method === 'chatgpt' && response.chatgpt) renderAccount(response);
      const count = setModels(response.models);
      say('modelListStatus', method === 'chatgpt' && response.chatgpt && response.chatgpt.modelMessage
        ? safeMessage({message: response.chatgpt.modelMessage})
        : count ? 'Models loaded. Choose a name from the list, or enter one.' : 'No models were returned. You can enter a model name manually.');
    } catch (error) { say('modelListStatus', safeMessage(error), 'error'); }
    finally { busy(false); say('fetchModels', 'Fetch models'); }
  }
  async function test() {
    if (working || !validate(true)) return;
    if (method === 'chatgpt' && (!accountState || accountState.canTest !== true)) {
      say('inferenceResult', 'Connect the helper and sign in to ChatGPT before testing.', 'error'); $('connectCompanion').focus(); return;
    }
    const value = snapshot(), current = identity(value), testAccount = accountIdentity;
    passed = ''; refreshAccountStatus(); busy(true); say('testInference', 'Testing…'); say('inferenceBadge', 'Testing'); say('inferenceResult', 'Running a short connection test…');
    try {
      const response = await api.test(value, {});
      if (method === 'chatgpt' && (testAccount !== accountIdentity || !accountState || !accountState.canTest)) throw new Error(t('The ChatGPT connection changed during the test. Check status and test again.'));
      if (!response || response.ready !== true) throw new Error(response && response.message || t('The connection did not pass the tutor test.'));
      passed = current; badge(); refreshAccountStatus();
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
  $('useCustomApi').addEventListener('click', () => switchMethod('api'));
  $('useChatgptPlan').addEventListener('click', () => switchMethod('chatgpt'));
  $('testInference').addEventListener('click', test);
  $('fetchModels').addEventListener('click', fetchModels);
  [['connectCompanion', 'status'], ['planLogin', 'login'], ['planCancel', 'cancel'], ['planDisconnect', 'logout']].forEach(([id, action]) => $(id).addEventListener('click', () => readAccount(action)));
  $('planLoginLink').addEventListener('click', event => { if (working) event.preventDefault(); });
  window.addEventListener('focus', () => { if (method === 'chatgpt' && accountState && !working) readAccount('status', true); });
  document.addEventListener('visibilitychange', () => { if (!document.hidden && method === 'chatgpt' && accountState && !working) readAccount('status', true); });
  window.addEventListener('pagehide', clearTimer);
  try {
    if (!api) throw new Error();
    const settings = api.getSettings();
    for (const [id, key] of [['inferenceBases', 'baseUrl'], ['inferenceKey', 'apiKey'], ['inferenceModel', 'model'], ['companionUrl', 'companionUrl'], ['companionToken', 'companionToken']]) {
      $(id).value = settings[key] || (key === 'companionUrl' ? 'http://127.0.0.1:8879' : '');
    }
    method = settings.method === 'chatgpt' ? 'chatgpt' : 'api';
    modelDrafts[method] = settings.model || '';
    $('inferenceApiFields').hidden = method !== 'api'; $('planAccountFields').hidden = method !== 'chatgpt';
    $('useCustomApi').setAttribute('aria-pressed', String(method === 'api')); $('useChatgptPlan').setAttribute('aria-pressed', String(method === 'chatgpt'));
    saved = identity(); passed = api.status().ready === true ? saved : ''; badge();
    if (passed) say('inferenceResult', 'Text tutor test passed.', 'ok');
    say('pageStatus', 'Connection settings loaded. Secrets last only for this tab session.');
    if (method === 'chatgpt' && settings.companionToken) readAccount('status');
  } catch (_) { busy(true); say('pageStatus', 'Online tutor settings could not load. Reload this page to try again.', 'error'); }
}());
