(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var sections = ["decision", "speech", "inference"];
  var tabOrder = ["inference", "speech", "decision"];
  var loaded = false;
  var initial = {}, working = {};
  var checkingAll = false, configurationBusy = false;
  var fileComparison = null, comparedSnapshot = null, comparisonTimer = null, comparisonVersion = 0;
  var testLabels = {decision: "Test Connection", speech: "Test Connection", inference: "Test Connection"};
  var savedSettings = null;
  var mathMethod = "api", methodModels = {};
  var accountState = null, accountVersion = 0, accountTimer = null;
  var passedTests = {}, testVersions = {};

  function selectConnection(section, focus) {
    tabOrder.forEach(function (name) {
      var selected = name === section;
      $(name + "Tab").setAttribute("aria-selected", String(selected));
      $(name + "Tab").tabIndex = selected ? 0 : -1;
      $(name + "Panel").hidden = !selected;
    });
    if (focus) $(section + "Tab").focus();
  }
  function changed() { return sections.some(edited); }
  function inactiveDrafts() {
    if (!loaded) return false;
    var saved = savedSettings.inference, models = saved.modelByProvider || {};
    return Object.keys(methodModels).some(function (method) {
      return method !== mathMethod && methodModels[method].trim() !== (models[method] || (saved.provider === method ? saved.model : ""));
    }) || mathMethod !== "api" && (normalizedBase($("inferenceBases").value) !== (saved.bases[0] || "") || !!$("inferenceKey").value.trim());
  }
  async function request(path, body) {
    var response;
    try {
      response = await fetch(path, body === undefined ? {} : {
        method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)
      });
    } catch (_) { throw new Error("The local engine is unavailable. Open Start Math Practice.cmd beside index.html, then return here."); }
    var json;
    try { json = await response.json(); } catch (_) { throw new Error("The local backend did not respond. Start the latest launcher, then reload this page."); }
    if (!response.ok) throw new Error(json.error && json.error.message || "The request could not finish. Try again.");
    return json;
  }
  function message(id, text, state) {
    $(id).textContent = text;
    $(id).dataset.state = state || "";
    if (sections.some(function (section) { return id === section + "Badge"; })) updateConnectionIndicators();
  }
  function updateConnectionIndicators() {
    var names = {inference: "Mathematics", speech: "Speech", decision: "Sentiment"};
    var descriptions = tabOrder.map(function (section) {
      var badge = $(section + "Badge"), description = names[section] + ": " + (badge.textContent || "Not tested");
      $(section + "Dot").dataset.state = badge.dataset.state === "ok" ? "ok" : "idle";
      $(section + "Dot").setAttribute("title", description);
      return description;
    });
    $("testConnections").setAttribute("aria-label", "Test All Connections. " + descriptions.join("; "));
  }
  function buttonId(action, section) { return action + section[0].toUpperCase() + section.slice(1); }
  function normalizedBase(value) { return value.trim().replace(/\/+$/, ""); }
  function payload(section) {
    var base = normalizedBase($(section + "Bases").value);
    var savedBases = savedSettings ? savedSettings[section].bases : [];
    var value = {
      // Keep existing fallback addresses when the displayed URL has not changed.
      bases: base ? savedBases[0] === base ? savedBases.slice() : [base] : [],
      model: $(section + "Model").value.trim(), apiKey: $(section + "Key").value.trim()
    };
    if (section === "inference") {
      value.provider = mathMethod;
      value.effort = savedSettings && savedSettings.inference.effort || 'medium';
      if (mathMethod !== 'api') {
        delete value.bases;
        delete value.apiKey;
      }
    }
    if (section === 'decision') {
      value.protocol = savedSettings && base === (savedBases[0] || '')
        ? savedSettings.decision.protocol || 'chat' : 'chat';
    }
    var patch = {}; patch[section] = value;
    return patch;
  }
  function serialize(section) { return JSON.stringify(payload(section)); }
  function testIdentity(section) {
    var value = payload(section)[section];
    delete value.apiKey;
    return JSON.stringify(value);
  }
  function invalidateTest(section) {
    testVersions[section] = (testVersions[section] || 0) + 1;
    delete passedTests[section];
    message(section + "Badge", configured(section) ? "Not tested" : "Not configured");
  }
  function keepPassedTest(section) {
    var passed = passedTests[section], value = payload(section)[section];
    if (!passed || passed.identity !== testIdentity(section)) return false;
    return !value.bases || passed.keyRevision === undefined || savedSettings[section].keyRevision === undefined ||
      passed.keyRevision === savedSettings[section].keyRevision;
  }
  function validateConnections(names) {
    var invalid = names.find(function (section) { return !$(section + "Form").checkValidity(); });
    if (!invalid) return true;
    selectConnection(invalid);
    $(invalid + "Form").reportValidity();
    return false;
  }
  function configured(section) {
    var value = payload(section)[section];
    return !!value.model && (section === 'inference' && value.provider !== 'api' || value.bases.length > 0);
  }
  function incomplete(section) {
    var value = payload(section)[section];
    return !configured(section) && (!value.bases || !!(value.model || value.bases.length || value.apiKey));
  }
  function configuration() {
    var value = {};
    sections.forEach(function (section) { Object.assign(value, payload(section)); });
    return value;
  }
  function edited(section) { return loaded && serialize(section) !== initial[section]; }
  function currentComparison() {
    return comparedSnapshot === JSON.stringify(configuration()) ? fileComparison : null;
  }
  function dirty(section) {
    if (!loaded) return false;
    var comparison = currentComparison();
    if (comparison) return comparison.changedSections.indexOf(section) !== -1;
    return edited(section);
  }
  async function compareConfiguration() {
    if (!loaded || configurationBusy) return;
    var snapshot = JSON.stringify(configuration()), version = ++comparisonVersion;
    try {
      var result = await request("/api/settings/compare", JSON.parse(snapshot));
      if (version !== comparisonVersion || snapshot !== JSON.stringify(configuration()) || configurationBusy) return;
      var wasDifferent = fileComparison && fileComparison.different;
      fileComparison = result; comparedSnapshot = snapshot;
      sections.forEach(function (section) {
        var passed = passedTests[section], value = payload(section)[section];
        if (passed && value.bases && !value.apiKey &&
            JSON.stringify(value.bases) === JSON.stringify(savedSettings[section].bases) &&
            result.keyRevisions && passed.keyRevision !== undefined &&
            passed.keyRevision !== result.keyRevisions[section]) {
          invalidateTest(section);
          message(section + "Result", "Test this connection again to verify the saved API key.");
        }
      });
      updateToolbar();
      if (result.different && !changed()) {
        message("pageStatus", "Saved settings have changed. Choose Save All Settings to keep the values here, or Load Settings to read the saved values.");
      } else if (!result.different && (wasDifferent || sections.some(edited))) {
        message("pageStatus", inactiveDrafts() ? "Your other Mathematics method still has an unsaved draft." : "These connections match your saved settings.");
      }
    } catch (error) {
      if (version !== comparisonVersion || snapshot !== JSON.stringify(configuration()) || configurationBusy) return;
      fileComparison = null; comparedSnapshot = null;
      updateToolbar(); message("pageStatus", "Could not check saved settings. " + error.message, "error");
    }
  }
  function scheduleComparison() {
    ++comparisonVersion;
    if (comparisonTimer) clearTimeout(comparisonTimer);
    comparisonTimer = setTimeout(function () { comparisonTimer = null; compareConfiguration(); }, 250);
  }
  function toolbarBusy() {
    return checkingAll || configurationBusy || sections.some(function (section) { return !!working[section]; });
  }
  function updateToolbar() {
    var blocked = toolbarBusy();
    $("loadConfiguration").disabled = blocked;
    $("testConnections").disabled = !loaded || blocked;
    $("saveConfiguration").hidden = false;
    $("saveConfiguration").disabled = !loaded || blocked || !(changed() || currentComparison() && fileComparison.different);
  }
  function busy(section, state) {
    working[section] = state;
    $(section + "Form").querySelectorAll("button, input, textarea, select").forEach(function (node) { node.disabled = state || !loaded; });
    if (section === "inference") {
      $("inferenceBases").disabled = $("inferenceKey").disabled = state || !loaded || mathMethod !== "api";
    }
    updateToolbar();
  }
  function updateKeyPlaceholder(section, configured) {
    $(section + "Key").placeholder = configured ? "Saved key (leave blank to keep)" : "Optional";
  }
  function passedLabel(section) {
    return section === "inference" ? "Text tutor test passed" : "Test passed";
  }
  function resetAccountView() {
    clearTimeout(accountTimer); ++accountVersion;
    accountState = null;
    var custom = mathMethod === "api", legacy = mathMethod === "codex";
    $("inferenceApiFields").hidden = !custom;
    $("planAccountFields").hidden = custom;
    $("inferenceBases").disabled = $("inferenceKey").disabled = !custom;
    $("planAccountLabel").textContent = legacy ? "Codex account" : "ChatGPT plan";
    $("legacyToPlan").hidden = !legacy;
    ["planLogin", "planAlternatives", "planCancel", "planDisconnect", "managePlan", "planModels"].forEach(function (id) { $(id).hidden = true; });
    $("inferenceModelNames").replaceChildren();
    $("inferenceModel").removeAttribute("list");
    $("inferenceModel").placeholder = mathMethod === "chatgpt" ? "Choose a plan model" : "Your model name";
    message("planAccountStatus", legacy ? "Using the Codex sign-in on this computer." : "Checking sign-in…");
  }
  function displayAccount(info) {
    var previous = accountState;
    accountState = info;
    var waiting = info.state === "waiting", signedIn = info.state === "signed_in";
    var identity = info.account && info.account.id;
    if (!info.canTest && ($("inferenceBadge").dataset.state === "ok" || $("inferenceBadge").textContent === "Testing") ||
        previous && (previous.canTest !== info.canTest || (previous.account && previous.account.id) !== identity)) {
      invalidateTest("inference");
      message("inferenceResult", "Test these settings before using them in practice.");
    }
    var label = info.account && info.account.label;
    var status = info.message;
    if (signedIn && info.canTest) status = (label ? "Signed in as " + label + "." : "Signed in.") + " Tutor tests use your ChatGPT plan.";
    if (info.state === "signed_out" && !info.account && !status) status = "Sign in to use your ChatGPT plan for Mathematics.";
    message("planAccountStatus", status || "Check your ChatGPT sign-in.", info.state === "failed" ? "error" : "");
    $("planLogin").hidden = waiting || signedIn && info.canTest || info.state === "unavailable";
    $("planCancel").hidden = !waiting;
    $("planDisconnect").hidden = !signedIn;
    $("managePlan").hidden = !signedIn;
    var remembered = info.registrations || [];
    var alternatives = $("planAlternatives");
    alternatives.replaceChildren();
    alternatives.hidden = info.state !== "signed_out" || !remembered.length;
    if (!alternatives.hidden) {
      message("planAccountStatus", (status ? status + " " : "") + "Continue as " + remembered[0].label + ".");
      var addChoice = function (text, choice) {
        var button = document.createElement("button");
        button.type = "button"; button.className = "method-link"; button.textContent = text;
        button.addEventListener("click", function () { if (!toolbarBusy()) return readAccount("login", choice); });
        alternatives.appendChild(button);
      };
      remembered.slice(1).forEach(function (item) { addChoice("Use " + item.label, {clientId: item.id}); });
      addChoice("Use another account", {newAccount: true});
    }
    var choices = (info.modelSuggestions || []).map(function (item) {
      var option = document.createElement("option");
      option.value = item.model; option.label = item.label || item.model;
      return option;
    });
    $("inferenceModelNames").replaceChildren(...choices);
    $("inferenceModel").setAttribute("list", "inferenceModelNames");
    $("inferenceModel").placeholder = signedIn && info.canTest ? (choices.length ? "Choose a plan model" : "Enter model name") : "Sign in to see models";
    $("planModels").hidden = !info.canTest || info.modelsLoading || choices.length > 0;
    if (signedIn && info.modelMessage && !working.inference && !passedTests.inference && $("inferenceBadge").dataset.state !== "error") message("inferenceResult", info.modelMessage);
    if (previous && previous.state === "waiting" && signedIn && info.canTest && identity) {
      var dialog = $("planWelcome");
      try {
        var welcomeKey = "math-practice-plan-welcome:" + identity;
        if (!localStorage.getItem(welcomeKey) && dialog.showModal) {
          dialog.showModal();
          localStorage.setItem(welcomeKey, "1");
        }
      } catch (_) { /* The account status also confirms sign-in if browser storage is blocked. */ }
    }
    if (waiting || info.modelsLoading) accountTimer = setTimeout(function () { readAccount(); }, 1600);
  }
  async function readAccount(action, choice) {
    if (mathMethod !== "chatgpt") return;
    clearTimeout(accountTimer);
    var version = ++accountVersion;
    if (action) {
      busy("inference", true);
      message("planAccountStatus", action === "login" ? "Opening ChatGPT sign-in…" : "Updating sign-in…");
    }
    try {
      var remembered = accountState && accountState.registrations;
      if (action === "login" && !choice && accountState && accountState.state === "signed_out" && remembered && remembered.length) {
        choice = {clientId: remembered[0].id};
      }
      var info = await request("/api/connections/chatgpt" + (action ? "/" + action : ""), action ? choice || {} : undefined);
      if (version === accountVersion) displayAccount(info);
    } catch (error) {
      if (version === accountVersion) {
        message("inferenceBadge", "Not tested");
        displayAccount({state: "failed", message: error.message, canTest: false});
      }
    } finally {
      if (action) busy("inference", false);
    }
  }
  async function switchMethod(method) {
    if (!loaded || toolbarBusy() || method === mathMethod) return;
    if (mathMethod === "chatgpt" && accountState && accountState.state === "waiting") await readAccount("cancel");
    methodModels[mathMethod] = $("inferenceModel").value;
    mathMethod = method;
    $("inferenceModel").value = methodModels[method] || "";
    resetAccountView();
    markEdited("inference");
    message("inferenceResult", "The test sends a sample answer for a text tutor review.");
    if (method === "chatgpt") readAccount();
    $(method === "api" ? "useChatgptPlan" : "useCustomApi").focus();
  }
  function apply(settings, preserveTests) {
    if (!settings.decision || !settings.speech || !settings.inference) throw new Error("Restart the local launcher to enable all three model connections, then reload this page.");
    var previousModels = preserveTests ? Object.assign({}, methodModels) : {};
    var apiDraft = preserveTests && mathMethod !== "api" ? {base: $("inferenceBases").value, key: $("inferenceKey").value} : null;
    var previousAccount = preserveTests && mathMethod === (settings.inference.provider || "api") ? accountState : null;
    savedSettings = settings;
    mathMethod = settings.inference.provider || "api";
    methodModels = Object.assign({}, settings.inference.modelByProvider, previousModels);
    methodModels[mathMethod] = settings.inference.model;
    resetAccountView();
    accountState = previousAccount;
    fileComparison = null; comparedSnapshot = null; ++comparisonVersion;
    if (comparisonTimer) { clearTimeout(comparisonTimer); comparisonTimer = null; }
    sections.forEach(function (section) {
      $(section + "Bases").value = settings[section].bases[0] || "";
      $(section + "Model").value = settings[section].model;
      $(section + "Key").value = "";
      updateKeyPlaceholder(section, settings[section].keyConfigured);
    });
    if (apiDraft) {
      $("inferenceBases").value = apiDraft.base;
      $("inferenceKey").value = apiDraft.key;
    }
    sections.forEach(function (section) {
      var passed = preserveTests && keepPassedTest(section);
      if (!passed) invalidateTest(section);
      message(section + "Badge", passed ? passedLabel(section) : configured(section) ? "Not tested" : "Not configured", passed ? "ok" : "");
    });
    sections.forEach(function (section) { initial[section] = serialize(section); });
    loaded = true;
    if (mathMethod === "chatgpt") readAccount();
    message("pageStatus", settings.notice || "");
  }
  async function save(section, event) {
    event.preventDefault();
    if (!loaded || toolbarBusy()) return;
    var patch = payload(section);
    busy(section, true); message(section + "Result", "Saving…");
    try {
      var settings = await request("/api/settings", patch);
      // Saving one card must preserve unsaved edits in the other cards.
      if (section !== "inference" || mathMethod === "api") {
        $(section + "Key").value = "";
        $(section + "Bases").value = settings[section].bases[0] || "";
      }
      $(section + "Model").value = settings[section].model;
      updateKeyPlaceholder(section, settings[section].keyConfigured);
      savedSettings[section] = settings[section];
      var passed = keepPassedTest(section);
      if (!passed) invalidateTest(section);
      initial[section] = serialize(section);
      fileComparison = null; comparedSnapshot = null; ++comparisonVersion;
      message(section + "Badge", passed ? passedLabel(section) : configured(section) ? "Not tested" : "Not configured", passed ? "ok" : "");
      message(section + "Result", passed ? "Settings saved on this computer. Connection test passed." : "Settings saved on this computer. Run a connection test when you are ready.", "ok");
      message("pageStatus", inactiveDrafts() ? "Connection saved. Your other Mathematics method still has an unsaved draft." : "Connection settings are saved to config.json.");
    } catch (error) { message(section + "Result", error.message, "error"); $(section + "Result").focus(); }
    finally { busy(section, false); compareConfiguration(); }
  }
  async function test(section) {
    if (!loaded || working[section] || configurationBusy || !validateConnections([section])) return false;
    if (!configured(section)) {
      var partial = incomplete(section), value = payload(section)[section];
      message(section + "Badge", partial ? "Incomplete" : "Not configured");
      message(section + "Result", section === "inference" && mathMethod !== "api"
        ? "Choose a model name to test the tutor." : value.model ? "Enter a URL to test this connection."
          : value.bases.length ? "Enter a model name to test this connection." : "Enter a URL and model name to test this connection.");
      return partial ? "incomplete" : null;
    }
    var snapshot = payload(section), button = $(buttonId("test", section));
    var version = (testVersions[section] || 0) + 1;
    testVersions[section] = version;
    delete passedTests[section];
    busy(section, true); message(section + "Result", "Running a short connection test…");
    message(section + "Badge", "Testing"); button.textContent = "Testing…";
    try {
      var result = await request("/api/settings/" + section + "/test", snapshot);
      if (version !== testVersions[section] || JSON.stringify(snapshot) !== serialize(section)) return false;
      if (result.ready !== true) throw new Error(result.message || 'This connection is not configured.');
      var detail = result.model + (result.effort ? " · " + result.effort + " reasoning" : "") + " · " + (result.elapsedMs / 1000).toFixed(1) + " s";
      message(section + "Result", result.message + " " + detail + (dirty(section) ? ". These settings are not saved yet." : ""), "ok");
      message(section + "Badge", passedLabel(section), "ok");
      passedTests[section] = {identity: testIdentity(section), keyRevision: result.keyRevision};
      return true;
    } catch (error) {
      if (version !== testVersions[section] || JSON.stringify(snapshot) !== serialize(section)) return false;
      message(section + "Result", error.message, "error"); message(section + "Badge", "Test failed", "error"); $(section + "Result").focus();
      return false;
    } finally { busy(section, false); button.textContent = testLabels[section]; compareConfiguration(); }
  }
  async function loadConfiguration() {
    if (toolbarBusy()) return;
    if ((changed() || inactiveDrafts()) && !window.confirm("Load saved settings and discard the unsaved edits on this page?")) return;
    configurationBusy = true;
    sections.forEach(function (section) { busy(section, true); });
    $("loadConfiguration").textContent = "Loading…";
    message("pageStatus", "Loading configuration…");
    try {
      apply(await request("/api/settings/reload", {}));
      sections.forEach(function (section) {
        message(section + "Badge", configured(section) ? "Not tested" : "Not configured");
        message(section + "Result", configured(section) ? "Configuration loaded. Choose Test Connection to check it." : "No model is configured for this optional connection.");
      });
    } catch (error) { message("pageStatus", error.message, "error"); }
    finally {
      configurationBusy = false;
      sections.forEach(function (section) { busy(section, false); });
      $("loadConfiguration").textContent = "Load Settings";
      compareConfiguration();
    }
  }
  async function saveConfiguration() {
    if (!loaded || toolbarBusy()) return;
    var changedSections = sections.filter(dirty);
    if (!validateConnections(tabOrder)) return;
    var patch = configuration();
    configurationBusy = true;
    sections.forEach(function (section) { busy(section, true); });
    $("saveConfiguration").textContent = "Saving…";
    message("pageStatus", "Saving configuration…");
    try {
      apply(await request("/api/settings", patch), true);
      message("pageStatus", inactiveDrafts() ? "Connections saved on this computer. Your other Mathematics method still has an unsaved draft." : "Connections saved on this computer. Return to practice when ready.", "ok");
      changedSections.forEach(function (section) { message(section + "Result", keepPassedTest(section) ? "Settings saved on this computer. Connection test passed." : "Connection saved. Test it to check a model response.", "ok"); });
    } catch (error) { message("pageStatus", error.message, "error"); }
    finally {
      configurationBusy = false;
      sections.forEach(function (section) { busy(section, false); });
      $("saveConfiguration").textContent = "Save All Settings";
      compareConfiguration();
    }
  }
  async function checkConnections() {
    if (!loaded || toolbarBusy()) return;
    if (!validateConnections(tabOrder)) return;
    checkingAll = true; updateToolbar();
    $("testConnectionsLabel").textContent = "Testing…";
    $("testConnections").setAttribute("aria-busy", "true");
    message("pageStatus", "Testing configured connections…");
    try {
      var results = await Promise.all(sections.map(test));
      var partial = tabOrder.find(function (section) { return results[sections.indexOf(section)] === "incomplete"; });
      var failed = partial || tabOrder.find(function (section) { return results[sections.indexOf(section)] === false; });
      if (failed) { selectConnection(failed); $(failed + "Result").focus(); }
      var passed = results.filter(function (result) { return result === true; }).length;
      var attempted = results.filter(function (result) { return result === true || result === false; }).length;
      var next = changed() ? " Choose Save All Settings to use these settings." : " Ready to practice.";
      var summary = attempted ? passed + " of " + attempted + " configured connections passed." : "";
      message("pageStatus", partial ? (summary ? summary + " " : "") + "Complete the settings in this tab, then test again."
        : !attempted ? "No models are configured. Answer checks and solutions are ready to use."
          : summary + (passed < attempted ? " Check the results below." : next), !partial && passed === attempted ? "ok" : "error");
    } catch (error) { message("pageStatus", error.message, "error"); }
    finally {
      checkingAll = false; updateToolbar();
      $("testConnectionsLabel").textContent = "Test All Connections";
      $("testConnections").removeAttribute("aria-busy");
    }
  }
  tabOrder.forEach(function (section, index) {
    $(section + "Tab").addEventListener("click", function () { selectConnection(section); });
    $(section + "Tab").addEventListener("keydown", function (event) {
      var next;
      if (event.key === "ArrowRight") next = (index + 1) % tabOrder.length;
      else if (event.key === "ArrowLeft") next = (index + tabOrder.length - 1) % tabOrder.length;
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = tabOrder.length - 1;
      else return;
      event.preventDefault();
      selectConnection(tabOrder[next], true);
    });
  });
  selectConnection("inference");
  function markEdited(section) {
    if (savedSettings && (section !== "inference" || mathMethod === "api")) {
      var sameBases = JSON.stringify(payload(section)[section].bases) === JSON.stringify(savedSettings[section].bases);
      updateKeyPlaceholder(section, savedSettings[section].keyConfigured && sameBases);
    }
    invalidateTest(section);
    message(section + "Result", "Test these settings before using them in practice.");
    message("pageStatus", changed() || inactiveDrafts() ? "You have unsaved connection settings." : "");
    updateToolbar();
    scheduleComparison();
  }
  $("useChatgptPlan").addEventListener("click", function () { switchMethod("chatgpt"); });
  $("legacyToPlan").addEventListener("click", function () { switchMethod("chatgpt"); });
  $("useCustomApi").addEventListener("click", function () { switchMethod("api"); });
  [["planLogin", "login"], ["planCancel", "cancel"], ["planDisconnect", "disconnect"], ["planModels", "models"]].forEach(function (pair) {
    $(pair[0]).addEventListener("click", function () { if (!toolbarBusy()) return readAccount(pair[1]); });
  });
  sections.forEach(function (section) {
    $(section + "Form").addEventListener("submit", save.bind(null, section));
    $(section + "Form").addEventListener("input", function () { markEdited(section); });
    $(buttonId("test", section)).addEventListener("click", test.bind(null, section));
  });
  $("loadConfiguration").addEventListener("click", loadConfiguration);
  $("testConnections").addEventListener("click", checkConnections);
  $("saveConfiguration").addEventListener("click", saveConfiguration);
  window.addEventListener("focus", compareConfiguration);
  window.addEventListener("focus", function () { if (!toolbarBusy()) return readAccount(); });
  document.addEventListener("visibilitychange", function () { if (!document.hidden) compareConfiguration(); });
  window.addEventListener("beforeunload", function (event) { if (inactiveDrafts() || changed() && (!currentComparison() || fileComparison.different)) { event.preventDefault(); event.returnValue = ""; } });
  sections.forEach(function (section) { busy(section, true); });
  request("/api/settings").then(function (settings) {
    apply(settings); sections.forEach(function (section) { busy(section, false); });
    compareConfiguration();
    if (window.location && new URLSearchParams(window.location.search).get("check") === "1") {
      if (window.history && window.history.replaceState) window.history.replaceState(null, "", window.location.pathname + window.location.hash);
      checkConnections();
    }
  }).catch(function (error) { working = {}; updateToolbar(); message("pageStatus", error.message, "error"); });
}());
