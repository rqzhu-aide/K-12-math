# Math Practice

[Open Math Practice online](https://math-practice.ailleo.net/) to practice from all eight collections, or [run the desktop app](#run-locally) for offline practice with Chinese curriculum, AMC and your own questions. [Question bank directory](../database/QUESTION_BANKS.md) · [Question counts and download information](../README.md)

## Start practicing online

1. Review and accept the use agreement when prompted. A parent or legal guardian must accept for a child and supervise their practice. [Privacy and use agreement](https://math-practice.ailleo.net/agreement.html)
2. Choose **Try a problem**, or open **Browse → By topic** to follow a concept. To browse by source, open **Browse → By source → Question bank** and choose Chinese curriculum, AMC contests or GSM8K. Choose **Other** to see the remaining collections under **Question repository**.
3. Enter your answer and reasoning. Choose **Submit answer** for an answer-key check where available, or open **Explore solution** at any time. Basic practice requires no model connection.

On the website, drafts stay in the open tab. The browser saves submitted work and any problems you mark to revisit.

For an app icon, use your browser’s **Install** option where available. On iPhone, open the site in Safari and choose **Share → Add to Home Screen**. New questions still load online.

## Connect your tutor online

Open **Settings → Math Tutor LLM** for feedback on submitted answers and reasoning, with hints when needed. Enter your OpenAI-compatible **Provider API URL**, **API Key** if required, and **Model Name**. Choose **Test Connection**, then **Save Settings**. Choose a model with image support for diagram questions.

Your browser sends requests directly to your provider, which must allow requests from the Math Practice website (CORS). The key stays in the tab session. Your provider’s charges and data-use terms apply. ChatGPT account sign-in is available in the [desktop app](#optional-ai-connections).

### Optional Ailleo Math Practice Service

Open **Settings → Ailleo Math Practice Service** and choose **Agree and enable** to turn on all three features together. This setting is independent of your tutor connection.

- **Speech-to-Text LLM** turns a recording into an editable draft.
- **Sentiment Check LLM**, when available, reads the question and original transcript before you edit or submit. It comments on clarity and confidence or frustration expressed in words. The tutor receives the reasoning you submit.
- **Suggest my next problem** appears after a scored Chinese curriculum or AMC submission. It uses a limited practice history and works with typed or spoken reasoning. You can switch topics or pause suggestions.

Ailleo temporarily processes these service requests. Practice data collection for model training is off. Keep confidential information out of requests. You can turn off the service in Settings, which clears this browser’s recommendation history. [Service agreement and data use](https://math-practice.ailleo.net/agreement.html#experimentalAgreement)

## Run locally

1. If needed, install Python **3.11 or newer** for your user or machine. [Download Python](https://www.python.org/downloads/)
2. Download the desktop app from `main`, extract the ZIP, and open the **K-12-math-main** folder. [Download the desktop app (ZIP)](https://github.com/rqzhu-aide/K-12-math/archive/refs/heads/main.zip)
3. **On Windows**, double-click **Start Math Practice.cmd** to open practice in your browser. **On macOS or Linux**, run `python3 math-practice/runtime/serve_math_practice.py` in a terminal from the extracted folder. Keep the terminal open and visit [Math Practice on this computer](http://127.0.0.1:8877/math-practice/).

The first launch builds a search index and can take a few minutes. Basic practice uses Python’s standard library.

## Use your own question bank

Follow the [question-bank template and import guide](https://github.com/rqzhu-aide/K-12-math/blob/main/question-bank-template/README.md) to prepare and validate your bank. It includes an importable example, schemas and commands for updating a bank. Preserve each question’s answer, worked solution, figures and source credits. [Explanation style guide](https://github.com/rqzhu-aide/K-12-math/blob/main/question-bank-template/EXPLANATION_STYLE.md)

After importing, open the local app and select your bank to practice it. Imported banks stay on your computer in `custom-banks/` under their existing license.

## Optional AI connections

In the desktop app, open **Settings → Connection settings**. The local Python server handles model requests, API keys and ChatGPT sign-in. Audio and text sent to a configured provider follow that provider’s data-use terms.

### Math tutor

Select **Math reasoning & feedback** and choose how to connect. [Desktop settings screenshot](https://math-practice.ailleo.net/images/model-settings.png)

| Connection | Steps |
|---|---|
| **ChatGPT plan** | Install the shared sign-in dependency with `python -m pip install --user "PyJWT[crypto]>=2.10,<3"` (use `python3` on macOS or Linux). Choose **Use a ChatGPT plan → Continue with ChatGPT**. Sign in to an eligible account, return to the app, and choose a model. [OpenAI local-app sign-in guide](https://developers.openai.com/siwc/token-sharing-open-source/sign-in) |
| **OpenAI API key** | In the custom API form, enter `https://api.openai.com/v1` under **URL**, paste your own project key under **API Key**, and enter the name of a Chat Completions model your API project can use. [Create an OpenAI API key](https://platform.openai.com/api-keys) |

Choose **Test Connection**, then **Save Settings**. A successful math test returns a tutor review. Tests send a small sample and may use API credits or your plan allowance.

### Separate and local connections

Each role can use its own provider. Enter the server URL and model name, add an API key if required, then test and save the connection. Leave the URL and model blank to disable it.

| Connection | Adds | Required API |
| --- | --- | --- |
| Math reasoning & feedback | Reviews the submitted answer and explanation in one call, with feedback and a hint when needed | Compatible `POST /v1/chat/completions` returning a structured tutor review, or a supported account connection |
| Voice to text | Turns recorded thinking into an editable transcript | `POST /v1/audio/transcriptions` accepting multipart WAV and returning a text field |
| Sentiment analysis | Reads the original transcript for expressed confidence, engagement and clarity | Compatible `POST /v1/chat/completions` with JSON responses, or custom `POST /v1/systemone` with rubric choices and probabilities |

Model listing through `GET /v1/models` is optional. The connection tests call the task endpoints directly. The math tutor receives the reasoning the student submits, including any edits to the transcript.

Use an address such as `http://localhost:8000` and the model ID reported by your
own server. An address ending in `/v1` is also accepted. New text connections use
compatible chat APIs. Existing custom `/v1/systemone` connections keep their saved
format; it can also be set with `decision.protocol: "systemone"` in `config.json`.

Deeper review of questions with figures also needs an inference model that accepts
image content. Install its image helpers in your shared Python installation:

```sh
python -m pip install --user PyMuPDF Pillow
```

Figures with even-odd clipping also use an existing system or user installation of
Chrome, Chromium, or Edge. This preserves white holes and overlapping outlines in
the image sent to the tutor. The app does not download a browser.

ChatGPT plan credentials are stored in the app’s user-data directory.

Settings are stored in ignored `math-practice/config.json`. The server creates
it with empty connections on first start. You may also copy
`math-practice/config.example.json` to that path and edit it, then use
**Load Settings**. The example contains no working credentials or private
addresses. Startup does not run model tests or inference.

You can load a separate private JSON or YAML profile at startup:

```sh
python math-practice/runtime/launch_math_practice.py --settings "path/to/setting.yaml" --port 8879
```

The server also accepts `--settings`. **Load Settings** reloads the selected file.
**Save Settings** updates it. YAML profiles use the same `decision`, `speech`,
and `inference` sections as JSON and require shared **PyYAML**
(`python -m pip install --user PyYAML`). A connection may use
`apiKeyFile: api_key.txt`, resolved relative to the profile, instead of embedding
its key. Unchanged key-file references are preserved when saving.

New installations use `mathAssessment: inference`: the math tutor checks the
answer and reasoning and returns its feedback and any hint in one inference.
Exact answer-key checks still work locally without a model. An existing profile
that omits `mathAssessment` or explicitly sets it to `decision` keeps the older
separate math check. Set it to `inference` to use the new routing with that profile.
Existing Codex connections use `inference.provider: codex` with a model and effort, the user's Codex installation and login, and the shared `openai-codex` package. Private profiles and `local-service/` are Git-ignored. To use a different profile while Math Practice is running, choose another port or restart the server.

## Updating the hosted site

GitHub Pages serves the root of [`gh-pages`](https://github.com/rqzhu-aide/K-12-math/tree/gh-pages). The hosted build uses the release source checkout with the supplemental question bundles and Pages exporter. The desktop ZIP from `main` contains the two bundled banks for local practice.

From the hosted release source root, use shared installations of Python 3.11 or newer and Node.js to test and export the site to an empty output directory.

```sh
node --test scripts/test_hosted_runtime.js scripts/test_agreement.js
python scripts/test_pages_export.py
python scripts/build_pages.py --output ../math-practice-pages-build
```

Preview the export before updating `gh-pages`, then check the deployed app version, bank version and question counts. [Published build record](https://math-practice.ailleo.net/build-info.json)

For gateway configuration, endpoint checks and browser verification, see the [Ailleo service maintainer guide](https://github.com/rqzhu-aide/K-12-math/blob/gh-pages/DESKTOP_SERVICES_CONNECT.md).
