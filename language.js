/* UI language only. Questions, solutions, model responses and learner text keep their original language. */
(function () {
  'use strict';
  const storageKey = 'math-practice-language';
  const dictionary = Object.create(null), bindings = new Map();
  const normalize = value => value === 'zh-CN' || value === 'zh' || value === 'cn' ? 'zh-CN' : 'en';
  let language = 'en';
  try { language = normalize(localStorage.getItem(storageKey)); } catch (_) { /* Keep English when storage is unavailable. */ }
  function resolve(value) { return typeof value === 'function' ? value() : value; }
  function t(source, params) {
    source = source == null ? '' : String(source);
    const translated = language === 'zh-CN' && Object.hasOwn(dictionary, source) ? dictionary[source] : source;
    return translated.replace(/\{(\w+)\}/g, (match, key) => params && Object.hasOwn(params, key) ? String(params[key]) : match);
  }
  function translated(source, params) {
    source = resolve(source);
    return source && typeof source === 'object' ? t(source.key, resolve(source.params)) : t(source, resolve(params));
  }
  function update(node, attribute, source, params) {
    const value = translated(source, params);
    if (attribute) node.setAttribute(attribute, value); else node.textContent = value;
  }
  function bind(node, attribute, source, params) {
    if (!node) return node;
    // Dynamic bindings own this leaf; a former static marker must not overwrite it.
    node.removeAttribute(attribute ? 'data-i18n-' + attribute : 'data-i18n');
    if (!bindings.has(node)) bindings.set(node, new Map());
    bindings.get(node).set(attribute || '', {source, params});
    update(node, attribute, source, params);
    return node;
  }
  function apply(scope) {
    scope = scope || document;
    document.documentElement.lang = language;
    document.documentElement.dataset.language = language;
    const nodes = [];
    if (scope.nodeType === 1) nodes.push(scope);
    nodes.push(...scope.querySelectorAll('[data-i18n], [data-i18n-title], [data-i18n-aria-label], [data-i18n-placeholder], [data-language-choice]'));
    for (const node of nodes) {
      if (node.hasAttribute('data-i18n')) node.textContent = t(node.getAttribute('data-i18n'));
      for (const attribute of ['title', 'aria-label', 'placeholder']) {
        const source = node.getAttribute('data-i18n-' + attribute);
        if (source !== null) node.setAttribute(attribute, t(source));
      }
      if (node.hasAttribute('data-language-choice')) node.setAttribute('aria-pressed', String(normalize(node.dataset.languageChoice) === language));
    }
    for (const [node, entries] of bindings) {
      if (!node.isConnected) { bindings.delete(node); continue; }
      if (scope !== document && scope !== node && !scope.contains(node)) continue;
      for (const [attribute, value] of entries) update(node, attribute, value.source, value.params);
    }
  }
  function setLanguage(value, persist) {
    const next = normalize(value), changed = next !== language;
    language = next;
    if (persist !== false) try { localStorage.setItem(storageKey, language); } catch (_) { /* The live page still switches. */ }
    apply();
    if (changed) window.dispatchEvent(new CustomEvent('languagechange', {detail: {language}}));
  }
  function register(values) { Object.assign(dictionary, values); apply(); }
  window.MathPracticeLanguage = {t, getLanguage: () => language, setLanguage, register, apply,
    unbindText: node => { const entries = bindings.get(node); if (entries) entries.delete(''); },
    bindText: (node, source, params) => bind(node, '', source, params),
    bindAttribute: (node, attribute, source, params) => bind(node, attribute, source, params)};
  document.documentElement.lang = language;
  document.documentElement.dataset.language = language;
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-language-choice]');
    if (button) setLanguage(button.dataset.languageChoice);
  });
  window.addEventListener('storage', event => {
    if (event.key !== storageKey && event.key !== null) return;
    if (event.storageArea && event.storageArea !== window.localStorage) return;
    setLanguage(event.newValue, false);
  });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => apply(), {once: true});
  else apply();

  register({
    'Language': '界面语言', 'English': '英语', 'Chinese': '中文', 'Appearance': '外观', 'Light theme': '浅色模式', 'Dark theme': '深色模式',
    'Math Practice': '数学练习', 'Model settings · Math Practice': '模型设置 · 数学练习', 'Back to practice': '返回练习',
    'Model settings': '模型设置',
    'Connect your tutor': '连接辅导模型',
    'Connect a tutor for feedback and hints on submitted work. Choose a model that can read images for problems with figures.': '连接辅导模型后，可获得对已提交作答的反馈和提示。练习带图题时，请选择能读取图片的模型。',
    'The launcher stores API keys on this computer and sends tutor requests to your provider. A test sends a text-only sample and may use API credits or plan usage. The provider’s data policy applies.': '启动器将 API 密钥保存在本机，并向你的服务商发送辅导请求。连接测试只发送文字示例，可能消耗 API 额度或套餐用量。数据处理遵循服务商的政策。',
    'Speech-to-text tests use a silent clip. Keep the local launcher running to use your model connections.': '语音转文字测试使用静音片段。使用模型连接时，请保持本地启动器运行。',
    'Settings saved.': '设置已保存。', 'Settings saved. Text test passed.': '设置已保存。文字测试已通过。',
    'Text test passed.': '文字测试已通过。', 'Saved settings loaded.': '已加载保存的设置。', 'Saved all settings.': '所有设置已保存。',
    'Choose your own Math Tutor LLM, then test the connection. You can browse questions, check answers and read included solutions without AI.': '选择你自己的数学辅导大语言模型，然后测试连接。不使用 AI 也可以浏览题目、核对答案和阅读已有解答。',
    'Experimental features': '实验性功能',
    'Connect with': '连接方式', 'ChatGPT account': 'ChatGPT 账户', 'Custom API': '自定义 API',
    'Complete the connection settings, then test again.': '请完善连接设置，然后重新测试。',
    'Loading saved settings…': '正在加载已保存的设置…', 'Model connections': '模型连接',
    'Service agreement': '服务使用协议',
    'Math Tutor LLM': '数学辅导大语言模型', 'Answers, reasoning and hints.': '检查答案与解题思路，提供提示。',
    'Speech-to-Text LLM': '语音转文字大语言模型', 'Spoken thinking to editable text.': '将口述思路转换为可编辑的文字。',
    'Sentiment Check LLM': '情绪分析大语言模型', 'Confidence, clarity and engagement.': '信心、表达清晰度与学习投入。',
    'Uses your original speech transcript to observe expressed confidence and engagement, and how clearly you explain your thinking. Clarity describes the explanation, not mathematical correctness. No voice tone is analyzed.': '根据未经编辑的语音转录文字，观察你表达出的自信程度、投入程度和思路的清晰度。清晰度指表达是否清楚，不代表数学是否正确。不会分析语音语调。',
    'Turns your spoken thinking into a text draft you can review and edit.': '将口述思路转换成文字草稿，供你检查和编辑。',
    'Reviews your answers and reasoning and offers hints. Questions with figures need a model that can read images.': '检查答案与推理，并提供提示。带图题目需要能理解图片的模型。',
    'Not tested': '尚未测试', 'Not configured': '未配置', 'Incomplete': '设置不完整', 'Testing': '测试中', 'Testing…': '正在测试…', 'Test failed': '测试失败',
    'URL': '网址', 'API Key': 'API 密钥', 'Optional': '可选', 'Model Name': '模型名称', 'Your model name': '输入模型名称',
    'Test Connection': '测试连接', 'Save Settings': '保存设置', 'Test All Connections': '测试所有连接', 'Save All Settings': '保存所有设置', 'Load Settings': '加载设置',
    'Use a ChatGPT plan': '使用 ChatGPT 套餐', 'ChatGPT plan': 'ChatGPT 套餐', 'Codex account': 'Codex 账户', 'Use custom API': '使用自定义 API',
    'Continue with ChatGPT': '使用 ChatGPT 继续', 'Cancel sign-in': '取消登录', 'Manage usage': '管理用量', 'Refresh model list': '刷新模型列表', 'Disconnect': '断开连接',
    'ChatGPT plan connected': '已连接 ChatGPT 套餐', 'Got it': '知道了',
    'Tutor tests use your ChatGPT plan. Save your chosen model to use the plan during practice. You can manage usage in ChatGPT settings.': '辅导测试将使用你的 ChatGPT 套餐。保存所选模型后，即可在练习中使用该套餐。你可以在 ChatGPT 设置中管理用量。',
    'Test sends a short example to the addresses entered above.': '测试会向上方填写的网址发送一个简短示例。',
    'Test sends a one-second silent WAV to check the connection. It does not use your microphone.': '测试会发送一段一秒钟的静音 WAV 音频来检查连接，不会使用麦克风。',
    'The test sends a sample answer for a text tutor review.': '测试会发送一个示例答案，供辅导模型进行文字点评。',
    'Tests send small samples and may use API credits or ChatGPT plan usage. The Speech-to-Text LLM test uses a silent clip.': '测试会发送少量示例，可能消耗 API 额度或 ChatGPT 套餐用量。语音转文字大语言模型测试使用静音片段。',
    'Your data and connections': '你的数据与连接',
    'Your keys are saved on the computer running Math Practice. AI features send audio and text to configured services, which may be remote. Provider data-use policies apply. Do not include personal information in your work.': '密钥保存在运行数学练习的电脑上。AI 功能会将音频和文字发送给已配置的服务，这些服务可能位于远程服务器。数据处理遵循提供商的政策。请勿在作答中包含个人信息。',
    'Answer-key checks and included solutions work without AI. To use connections, keep the local Math Practice launcher running.': '标准答案检查和内置解答无需 AI 即可使用。使用模型连接时，请保持本地数学练习启动器运行。',
    'Settings apply to this installation.': '这些设置适用于此安装。',
    'Privacy & use agreement': '隐私与使用协议',
    'Dataset acknowledgements': '题库来源与致谢', 'Software license': '软件许可',
    'Developed by Ruoqing Zhu · ': '开发者 Ruoqing Zhu · ',
    'Saved key (leave blank to keep)': '已保存密钥（留空则保留）', 'Text tutor test passed': '文字辅导测试通过', 'Test passed': '测试通过',
    'Choose a plan model': '选择套餐模型', 'Enter model name': '输入模型名称', 'Sign in to see models': '登录后查看模型',
    'Using the Codex sign-in on this computer.': '正在使用这台电脑上的 Codex 登录信息。', 'Checking sign-in…': '正在检查登录状态…',
    'Opening ChatGPT sign-in…': '正在打开 ChatGPT 登录…', 'Updating sign-in…': '正在更新登录状态…',
    'Signed in. Tutor tests use your ChatGPT plan.': '已登录。辅导测试将使用你的 ChatGPT 套餐。',
    'Signed in as {name}. Tutor tests use your ChatGPT plan.': '已以 {name} 登录。辅导测试将使用你的 ChatGPT 套餐。',
    'Sign in to use your ChatGPT plan for Mathematics.': '登录后即可使用 ChatGPT 套餐进行数学辅导。',
    'Check your ChatGPT sign-in.': '请检查 ChatGPT 登录状态。', 'Continue as {name}.': '以 {name} 继续。', 'Use {name}': '使用 {name}', 'Use another account': '使用其他账户',
    'Test these settings before using them in practice.': '在练习中使用这些设置前，请先测试。',
    'Test this connection again to verify the saved API key.': '请重新测试此连接，以验证已保存的 API 密钥。',
    'Saved settings have changed. Choose Save All Settings to keep the values here, or Load Settings to read the saved values.': '已保存的设置发生了变化。选择“保存所有设置”可保留当前填写的值，选择“加载设置”可读取已保存的值。',
    'Your other Mathematics method still has an unsaved draft.': '另一种数学连接方式仍有未保存的草稿。', 'These connections match your saved settings.': '当前连接与已保存的设置一致。',
    'Could not check saved settings. {error}': '无法检查已保存的设置。{error}', 'Saving…': '正在保存…', 'Loading…': '正在加载…',
    'Settings saved on this computer. Connection test passed.': '设置已保存在这台电脑上。连接测试通过。',
    'Settings saved on this computer. Run a connection test when you are ready.': '设置已保存在这台电脑上。准备好后可运行连接测试。',
    'Connection saved. Your other Mathematics method still has an unsaved draft.': '连接已保存。另一种数学连接方式仍有未保存的草稿。',
    'Connection settings are saved to config.json.': '连接设置已保存至 config.json。',
    'Choose a model name to test the tutor.': '请选择模型名称，以测试辅导功能。', 'Enter a URL to test this connection.': '请输入网址，以测试此连接。',
    'Enter a model name to test this connection.': '请输入模型名称，以测试此连接。', 'Enter a URL and model name to test this connection.': '请输入网址和模型名称，以测试此连接。',
    'Running a short connection test…': '正在进行简短的连接测试…', 'This connection is not configured.': '此连接尚未配置。',
    'These settings are not saved yet.': '这些设置尚未保存。', '{effort} reasoning': '{effort} 推理强度',
    'Load saved settings and discard the unsaved edits on this page?': '加载已保存的设置，并放弃本页未保存的修改？',
    'Loading configuration…': '正在加载配置…', 'Configuration loaded. Choose Test Connection to check it.': '配置已加载。选择“测试连接”可进行检查。',
    'No model is configured for this optional connection.': '此可选连接尚未配置模型。', 'Saving configuration…': '正在保存配置…',
    'Connections saved on this computer. Your other Mathematics method still has an unsaved draft.': '连接已保存在这台电脑上。另一种数学连接方式仍有未保存的草稿。',
    'Connections saved on this computer. Return to practice when ready.': '连接已保存在这台电脑上。准备好后即可返回练习。',
    'Connection saved. Test it to check a model response.': '连接已保存。可通过测试检查模型的响应。', 'Testing configured connections…': '正在测试已配置的连接…',
    'Choose Save All Settings to use these settings.': '选择“保存所有设置”后即可使用这些设置。', 'Ready to practice.': '可以开始练习。',
    '{passed} of {attempted} configured connections passed.': '已配置的 {attempted} 个连接中，{passed} 个测试通过。',
    'Complete the settings in this tab, then test again.': '请补全此选项卡中的设置，然后重新测试。', 'No models are configured. Answer checks and solutions are ready to use.': '尚未配置模型。标准答案检查和解答已可使用。',
    'Check the results below.': '请查看下方的测试结果。', 'You have unsaved connection settings.': '有尚未保存的连接设置。',
    'The local engine is unavailable. Open Start Math Practice.cmd beside index.html, then return here.': '本地引擎不可用。请打开 index.html 旁的 Start Math Practice.cmd，然后返回此处。',
    'The local backend did not respond. Start the latest launcher, then reload this page.': '本地服务未响应。请启动最新版启动器，然后重新加载此页面。',
    'The request could not finish. Try again.': '请求未能完成，请重试。', 'Restart the local launcher to enable all three model connections, then reload this page.': '请重启本地启动器，以启用全部三种模型连接，然后重新加载此页面。',
    'ChatGPT is connected. Test the selected model before using it.': '已连接 ChatGPT。使用前请测试所选模型。',
    'ChatGPT is signed in. Enable permission to use your ChatGPT plan.': '已登录 ChatGPT。请启用使用 ChatGPT 套餐的权限。',
    'Continue with ChatGPT to request access to an eligible plan.': '选择“使用 ChatGPT 继续”以申请使用符合条件的套餐。',
    'Your ChatGPT connection ended. Continue with ChatGPT to sign in again.': 'ChatGPT 连接已结束。请选择“使用 ChatGPT 继续”以重新登录。',
    'Complete sign-in in your browser, then return here.': '请在浏览器中完成登录，然后返回此处。',
    'ChatGPT sign-in expired. Continue with ChatGPT to try again.': 'ChatGPT 登录已过期。请选择“使用 ChatGPT 继续”以重试。',
    'ChatGPT sign-in was declined or could not finish. Continue with ChatGPT to try again.': 'ChatGPT 登录被拒绝或未能完成。请选择“使用 ChatGPT 继续”以重试。',
    'OpenAI registration was incomplete. Continue with ChatGPT to start a fresh sign-in.': 'OpenAI 注册未完成。请选择“使用 ChatGPT 继续”以重新登录。',
    'Math Practice could not save its protected account connection.': '数学练习无法保存受保护的账户连接。',
    'No models are currently listed for this ChatGPT account.': '目前未列出此 ChatGPT 账户可用的模型。',
    'Signed out of ChatGPT in Math Practice.': '已在数学练习中退出 ChatGPT。',
    'Signed out locally. Remote revocation was not confirmed; disconnect Math Practice in ChatGPT Settings > Security and login > Sign in with ChatGPT.': '已在本地退出，尚未确认远程授权已撤销。请在 ChatGPT 设置 > 安全与登录 > 使用 ChatGPT 登录中断开数学练习的连接。',
    'Enter a decision server address and model ID to test this connection.': '请输入分析服务器地址和模型名称，以测试此连接。',
    'The model returned all three learning signals in the required format.': '模型已按要求的格式返回全部三项学习信号。',
    'The model returned all three learning signals, a mathematical reasoning assessment, and a typed answer assessment in the required formats.': '模型已按要求的格式返回全部三项学习信号、数学推理评估和输入答案评估。',
    'Speech service accepted a one-second silent WAV. This checks the connection, not speech accuracy.': '语音服务已接受一秒钟的静音 WAV 音频。此测试检查连接，不评估语音识别准确性。',
    'The model completed a structured text tutor review.': '模型已完成结构化的文字辅导点评。',
    'Enter a server address and model ID to enable this optional connection.': '输入服务器地址和模型名称，即可启用此可选连接。',
    'The service returned an invalid model list. Use Test Connection in Settings to check the configured model.': '服务返回的模型列表无效。请在设置中选择“测试连接”以检查已配置的模型。',
    'The service did not list this model ID. It may still accept requests for it. Use Test Connection in Settings to check it.': '服务未列出此模型名称，但仍可能接受对它的请求。请在设置中选择“测试连接”进行检查。',
    'The service lists the configured model and accepted the connection. Use its test in Settings to check a real response.': '服务已列出所配置的模型，并接受了连接。请在设置中测试该连接，以检查实际响应。',
    'Model review is optional. Configure the Math Tutor LLM in Settings to enable it.': '模型点评为可选功能。在设置中配置数学辅导大语言模型即可启用。',
    'Sign in with OpenAI to connect the Math Tutor LLM.': '登录 OpenAI 以连接数学辅导大语言模型。',
    'The Math Tutor LLM could not finish the review. Check its connection and try again.': '数学辅导大语言模型未能完成点评。请检查连接后重试。',
    'Answer checks and solutions are available without a Sentiment Check LLM.': '未配置情绪分析大语言模型时，仍可使用标准答案检查和解答。',
    'Learning signals need a configured Sentiment Check LLM.': '学习状态分析需要配置情绪分析大语言模型。',
    "OpenAI's model service is busy. Try again later.": 'OpenAI 模型服务繁忙，请稍后重试。',
    'ChatGPT plan usage is unavailable for this account, workspace, or policy. Choose an eligible account or use a custom API.': '此账户、工作区或策略不支持使用 ChatGPT 套餐。请选择符合条件的账户，或使用自定义 API。',
    'This app or ChatGPT plan has reached a usage limit. Review the app limit in ChatGPT Settings > Usage.': '此应用或 ChatGPT 套餐已达到用量限制。请在 ChatGPT 设置 > 用量中查看应用限制。',
    'OpenAI did not accept this app registration. Check the Sign in with ChatGPT registration guidance before trying again.': 'OpenAI 未接受此应用的注册。请检查“使用 ChatGPT 登录”的注册说明后重试。',
    'OpenAI did not accept this account authorization. Sign in again to check its permissions.': 'OpenAI 未接受此账户授权。请重新登录以检查权限。',
    'OpenAI restricted this request. Check account eligibility, app permission, and serving-region policy.': 'OpenAI 限制了此请求。请检查账户资格、应用权限和服务地区策略。',
    'OpenAI has limited requests for this account. Check ChatGPT Settings > Usage and try later.': 'OpenAI 已限制此账户的请求。请检查 ChatGPT 设置 > 用量，稍后再试。',
    'ChatGPT plan routing is unavailable or not enabled for this integration. Keep the connection and try later.': 'ChatGPT 套餐路由暂时不可用，或此集成尚未启用该路由。请保留连接，稍后重试。',
    'OpenAI could not complete this request. Check the selected model and account permissions.': 'OpenAI 无法完成此请求。请检查所选模型和账户权限。',
    'Install PyJWT[crypto] in your shared Python installation, then restart Math Practice: python -m pip install --user "PyJWT[crypto]".': '请在共享 Python 安装中安装 PyJWT[crypto]，然后重启数学练习：python -m pip install --user "PyJWT[crypto]"。'
  });
}());
