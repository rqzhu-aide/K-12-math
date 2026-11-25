(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const language = window.MathPracticeLanguage;
  if (language) language.register({
    'Choose your own Math Tutor LLM, then test the connection. You can browse questions, check answers and read included solutions without AI.': '选择你自己的数学辅导大语言模型，然后测试连接。不使用 AI 也可以浏览题目、核对答案和阅读已有解答。',
    'Provider API URL': '服务商 API 网址',
    'Use an OpenAI-compatible API that permits requests from this website. Requests go directly from your browser to your chosen provider.': '使用允许本网站发送请求的 OpenAI 兼容 API。请求由浏览器直接发送给你选择的服务商。',
    'Your API key is kept only for this browser tab session. It is sent directly to the provider you choose. Provider charges and data-use policies apply.': 'API 密钥仅保留在当前浏览器标签页的会话中，并直接发送给你选择的服务商。费用和数据使用规则以服务商规定为准。',
    'ChatGPT login': 'ChatGPT 登录', 'Forthcoming': '即将推出',
    'Fetch models': '获取模型列表', 'Enter a model name, or fetch available models.': '输入模型名称，或获取可用模型列表。',
    'Tests may use API credits. A successful text test does not verify image support.': '测试可能消耗 API 额度。文字测试成功并不代表模型支持图片。',
    'Ailleo Math Practice Service': 'Ailleo 数学练习服务',
    'This optional service includes Speech-to-Text LLM and Sentiment Check LLM. Ailleo provides both without an API key from you.': '这项可选服务包括语音转文字和情绪分析大语言模型。两项功能均由 Ailleo 提供，无需你输入 API 密钥。',
    'If you enable both features, stopping a recording sends the audio to Ailleo for transcription. The app then automatically sends the original transcript and question for Sentiment Check before you edit the text or press Submit. Ailleo uses the audio, original transcript and sentiment results only for temporary processing.': '开启两项功能后，结束录音时，音频会发送给 Ailleo 并转成文字。应用随后会在你编辑文字或点击“提交”之前，自动发送原始转录文字和题目进行情绪分析。Ailleo 仅将音频、原始转录文字和情绪分析结果用于临时处理。',
    'You can practice by typing and turn off this service at any time.': '你可以用文字输入进行练习，也可以随时关闭这项服务。',
    'Improving question recommendations': '改进题目推荐',
    'If sharing becomes available and you separately opt in, Ailleo will keep only the final text you explicitly submit in ‘Your thinking’ for up to 90 days to improve its internal question recommendations. This can include typed text or speech-to-text output that you submit with or without edits.': '如果将来开放共享，且你另行选择同意，Ailleo 只会保留你在“你的思路”中主动提交的最终文字，最长保留 90 天，用于改进 Ailleo 内部的题目推荐。你可以提交手动输入的文字，也可以提交编辑过或未编辑的语音转录文字。',
    'Ailleo’s collection for question recommendations is off. Enabling a feature gives permission only for processing.': 'Ailleo 目前未开启用于题目推荐的数据收集。开启功能仅表示你同意数据处理。',
    'Data use and deletion': '数据使用与删除',
    'Sentiment Check LLM': '情绪分析大语言模型',
    'Agree and enable both features': '同意并开启两项功能',
    'Turn off Ailleo Math Practice Service': '关闭 Ailleo 数学练习服务',
    'Only Speech-to-Text LLM is enabled from your previous settings.': '根据你之前的设置，目前仅开启了语音转文字大语言模型。',
    'Only Sentiment Check LLM is enabled from your previous settings.': '根据你之前的设置，目前仅开启了情绪分析大语言模型。',
    'Waiting for server connection': '等待服务器连接',
    'Ailleo’s server is not connected to this website yet. You can save your choice for later.': 'Ailleo 的服务器尚未连接到本网站。你可以先保存选择，待连接后使用。',
    'Your choice is saved. Ailleo’s server is not connected to this website yet.': '已保存你的选择。Ailleo 的服务器尚未连接到本网站。',
    'Check connection': '检查连接', 'Checking…': '正在检查…',
    'Checks service availability without sending your audio or thinking.': '仅检查服务是否可用，不发送你的音频或思考内容。',
    'Off': '已关闭', 'Service reachable': '服务可连接', 'Unavailable': '暂不可用', 'Connection not checked': '尚未检查连接',
    'Checking Ailleo’s server. No audio or thinking is sent.': '正在检查 Ailleo 的服务器，不会发送音频或思考内容。',
    'This feature is off. You can enable both features above.': '此功能已关闭。你可以在上方开启两项功能。',
    'The server is reachable. This feature is off.': '服务器可连接。此功能已关闭。',
    'Ailleo’s server is unavailable. This feature is off. Check connection to try again.': 'Ailleo 的服务器暂不可用。此功能已关闭。请检查连接以重试。',
    'Your choice is saved. Check the connection before using this feature.': '已保存你的选择。使用此功能前，请先检查连接。',
    'The server is reachable. This check does not run the Speech-to-Text LLM or Sentiment Check LLM.': '服务器可连接。此检查不会运行语音转文字大语言模型或情绪分析大语言模型。',
    'Your choice is saved, but Ailleo’s server is unavailable. Check connection to try again.': '已保存你的选择，但 Ailleo 的服务器暂不可用。请检查连接以重试。',
    'Both features are enabled.': '两项功能均已开启。',
    'Processing permission removed. Both optional features are off.': '已撤回数据处理许可。两项可选功能均已关闭。',
    'Optional service settings could not load. Reload this page to try again.': '无法加载可选服务设置。请重新加载页面后重试。',
    'Your choice could not be saved. Try again.': '无法保存你的选择，请重试。',
    'The service connection could not be checked. Try again.': '无法检查服务连接，请重试。',
    'Not connected': '尚未连接',
    'This service will appear when the site operator connects the desktop service to a public address. You can keep using the question bank and your own Math Tutor LLM.': '网站运营者将桌面服务连接到公网地址后，此服务才会开放。在此之前，你仍然可以使用题库和自己的数学辅导大语言模型。',
    'Tutor requests go directly to your chosen API provider. The site operator does not provide your Math Tutor LLM.': '辅导请求直接发送给你选择的 API 服务商。数学辅导大语言模型由你自己连接。',
    'Reloading or closing the practice tab clears any unsubmitted work. After a valid submission, your browser saves the submitted work in your practice history and notebook.': '重新加载或关闭练习标签页会清除未提交的作答。提交有效作答后，浏览器会将你提交的内容保存到练习历史和笔记本。',
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
    return t(message);
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
  const serviceToggle = $('serviceEnabled');
  function renderServices() {
    const preferences = services.preferences();
    const bothEnabled = preferences.speech && preferences.decision;
    const partial = preferences.speech !== preferences.decision;
    text(serviceToggle, bothEnabled ? 'Turn off Ailleo Math Practice Service' : 'Agree and enable both features');
    serviceToggle.classList.toggle('primary', !bothEnabled);
    serviceToggle.classList.toggle('secondary', bothEnabled);
    serviceToggle.disabled = false;
    $('legacyServiceChoice').hidden = !partial;
    $('clearServiceChoice').hidden = !partial;
    if (partial) say('legacyServiceChoice', preferences.speech
      ? 'Only Speech-to-Text LLM is enabled from your previous settings.'
      : 'Only Sentiment Check LLM is enabled from your previous settings.');
    for (const role of serviceRoles) {
      const status = services.status(role);
      const enabled = preferences[role] === true;
      const check = serviceCheckButton(role);
      check.disabled = !status.configured || serviceChecking[role];
      check.setAttribute('aria-busy', String(serviceChecking[role]));
      text(check, serviceChecking[role] ? 'Checking…' : 'Check connection');
      let label, message, state = '';
      if (!status.configured) {
        label = 'Waiting for server connection';
        message = enabled ? 'Your choice is saved. Ailleo’s server is not connected to this website yet.' : 'Ailleo’s server is not connected to this website yet. You can save your choice for later.';
      } else if (serviceChecking[role]) {
        label = 'Checking…'; message = 'Checking Ailleo’s server. No audio or thinking is sent.';
      } else if (!enabled) {
        label = 'Off';
        message = status.available === true ? 'The server is reachable. This feature is off.' : status.available === false ? 'Ailleo’s server is unavailable. This feature is off. Check connection to try again.' : 'This feature is off. You can enable both features above.';
      } else if (status.state === 'ready') {
        label = 'Service reachable'; message = 'The server is reachable. This check does not run the Speech-to-Text LLM or Sentiment Check LLM.'; state = 'ok';
      } else if (status.available === false) {
        label = 'Unavailable'; message = 'Your choice is saved, but Ailleo’s server is unavailable. Check connection to try again.';
      } else {
        label = 'Connection not checked'; message = 'Your choice is saved. Check the connection before using this feature.';
      }
      say(role + 'Badge', label, state);
      say(role + 'Status', serviceErrors[role] || message, serviceErrors[role] ? 'error' : '');
    }
  }
  async function checkService(role) {
    if (serviceChecking[role] || !services.config().configured) return;
    serviceChecking[role] = true; serviceErrors[role] = ''; renderServices();
    try { await services.check(role); }
    catch (error) { serviceErrors[role] = safeMessage(error || new Error(t('The service connection could not be checked. Try again.'))); }
    finally { serviceChecking[role] = false; renderServices(); notify(); }
  }
  function saveServiceChoice(enabled) {
    try {
      services.savePreferences({acknowledged: enabled, speech: enabled, decision: enabled});
      say('servicePreferencesResult', enabled ? 'Both features are enabled.' : 'Processing permission removed. Both optional features are off.');
      for (const role of serviceRoles) serviceErrors[role] = '';
      renderServices(); notify(); return true;
    } catch (error) {
      say('servicePreferencesResult', safeMessage(error || new Error(t('Your choice could not be saved. Try again.'))), 'error');
      renderServices(); return false;
    }
  }
  if (serviceToggle) {
    try {
      if (!services) throw new Error();
      renderServices();
      serviceToggle.addEventListener('click', () => {
        const preferences = services.preferences();
        const enable = !(preferences.speech && preferences.decision);
        if (saveServiceChoice(enable) && enable) serviceRoles.forEach(checkService);
      });
      $('clearServiceChoice').addEventListener('click', () => {
        if (saveServiceChoice(false)) serviceToggle.focus();
      });
      for (const role of serviceRoles) serviceCheckButton(role).addEventListener('click', () => checkService(role));
    } catch (_) {
      serviceToggle.disabled = true;
      for (const role of serviceRoles) serviceCheckButton(role).disabled = true;
      say('servicePreferencesResult', 'Optional service settings could not load. Reload this page to try again.', 'error');
    }
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
  const tabs = {tutor: $('tutorTab'), service: $('serviceTab')};
  const panels = {tutor: $('inferencePanel'), service: $('servicePanel')};
  function selectTab(name, updateHash = false) {
    for (const key of Object.keys(tabs)) {
      const selected = key === name;
      tabs[key].setAttribute('aria-selected', String(selected));
      tabs[key].tabIndex = selected ? 0 : -1;
      panels[key].hidden = !selected;
    }
    if (updateHash) history.replaceState(history.state, '', '#' + name);
  }
  function selectFragment() {
    const target = location.hash.slice(1);
    const service = target === 'service' || target === 'speechTab' || target === 'decisionTab' || panels.service.contains($(target));
    selectTab(service ? 'service' : 'tutor');
  }
  if (tabs.tutor && tabs.service) {
    for (const [name, tab] of Object.entries(tabs)) {
      tab.addEventListener('click', () => selectTab(name, true));
      tab.addEventListener('keydown', event => {
        const other = name === 'tutor' ? 'service' : 'tutor';
        const target = {ArrowLeft: other, ArrowRight: other, Home: 'tutor', End: 'service'}[event.key];
        if (!target) return;
        event.preventDefault();
        selectTab(target, true);
        tabs[target].focus();
      });
    }
    window.addEventListener('hashchange', selectFragment);
    selectFragment();
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
    saved = identity(); passed = api.status().ready === true ? saved : ''; badge();
    if (passed) say('inferenceResult', 'Text tutor test passed.', 'ok');
    say('pageStatus', 'Connection settings loaded. Secrets last only for this tab session.');
  } catch (_) { busy(true); say('pageStatus', 'Online tutor settings could not load. Reload this page to try again.', 'error'); }
}());
