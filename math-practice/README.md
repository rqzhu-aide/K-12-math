# Math Practice

**[Open Math Practice online](https://math-practice.ailleo.net/)** for version 2.3.3 with **18,687 questions across eight collections**. The desktop ZIP from `main` contains version 2.2.0 and 8,790 Chinese curriculum and AMC questions. [Run locally](#run-locally)

| Practice a question | Configure the three model roles |
|:---:|:---:|
| [![Question with answer and reasoning controls](https://math-practice.ailleo.net/images/question-page.png)](https://math-practice.ailleo.net/images/question-page.png) | [![API settings for math reasoning and feedback, voice to text, and sentiment analysis](https://math-practice.ailleo.net/images/model-settings.png)](https://math-practice.ailleo.net/images/model-settings.png) |

## Start practicing

1. On your first visit, an adult reviews and accepts the use agreement. Children practice under a parent or legal guardian’s supervision. [Privacy and use agreement](https://math-practice.ailleo.net/agreement.html)
2. Choose **Try a problem** or open **Browse**. Under **By source**, choose Chinese curriculum, AMC contests or GSM8K. Choose **Other** for England KS2, U.S. NAEP, Illustrative Mathematics, Waterloo CEMC or OATutor. **By topic** lets you explore the knowledge graph. [Dataset acknowledgements](https://math-practice.ailleo.net/dataset-acknowledgements.html)
3. Type your answer and reasoning. Choose **Submit answer** to check a supported answer, or **Explore solution** to see the worked steps. Basic practice and worked solutions require no model connection. Unsubmitted drafts stay in the open tab. Saved problems stay in this browser.

For an app icon, use your browser’s **Install** option where available. On iPhone, open the site in Safari and choose **Share → Add to Home Screen**. New questions still load online.

## Connect your tutor online

Open **Settings → Math Tutor LLM** for feedback and hints on submitted reasoning. Enter your OpenAI-compatible provider’s API URL, key if required, and model. Use **Test Connection**. Requests go directly from your browser to your provider, which must allow requests from the Math Practice website (CORS). Choose a model with image support for diagram questions. The key stays in the current tab session. Your provider’s charges and data-use terms apply. Online ChatGPT account sign-in is marked **Forthcoming**.

Under **Settings → Ailleo Math Practice Service**, choose **Agree and enable** to use three optional features together.

- **Speech-to-Text LLM** turns a spoken explanation into a draft you can edit before submitting.
- **Sentiment Check LLM** reads the original speech transcript for cues such as expressed confidence. The Math Tutor LLM receives the reasoning you actually submit.
- **Suggest my next problem** uses a limited history of scored practice to recommend another Chinese curriculum or AMC question. You can use recommendations with typed answers, switch topics, or pause.

Ailleo temporarily processes service requests on its own server. Practice data collection for model training is off in this release. Please do not include any confidential information. [Privacy and use agreement](https://math-practice.ailleo.net/agreement.html#experimentalAgreement)

## Run locally

Choose the local edition for offline practice, your own question banks, or your own speech and learning-signal connections.

1. Install Python **3.11 or newer** on your computer. [Download Python](https://www.python.org/downloads/)
2. Download the project ZIP, extract it, and open the **K-12-math-main** folder. [Download the project ZIP](https://github.com/rqzhu-aide/K-12-math/archive/refs/heads/main.zip)
3. **On Windows**, double-click **Start Math Practice.cmd**. The launcher opens the practice page in your browser. **On macOS or Linux**, open a terminal in the extracted folder and run `python3 math-practice/runtime/serve_math_practice.py`. Keep the terminal open and visit [Math Practice on this computer](http://127.0.0.1:8877/math-practice/).

The first launch builds a search index from the included banks and can take a few minutes. Basic practice uses Python’s standard library. To connect a tutor, follow the steps below.

## Use your own question bank

Use the [question-bank template](https://github.com/rqzhu-aide/K-12-math/blob/main/question-bank-template/README.md) to process your
own questions into the shared JSON format, then use the Math Practice UI to serve
and practice the processed questions. The template includes schemas, four example
questions, a diagram, and a conversion guide. Preserve each question's answer,
worked solution, figures, and source attribution when preparing your collection.
The [explanation style guide](https://github.com/rqzhu-aide/K-12-math/blob/main/question-bank-template/EXPLANATION_STYLE.md) helps
authors turn correct solutions into connected, student-facing reasoning.

From the repository root, replace `path/to/your-bank` with your prepared bank
folder and run:

```sh
python math-practice/runtime/import_question_bank.py path/to/your-bank --check
python math-practice/runtime/import_question_bank.py path/to/your-bank
python math-practice/runtime/serve_math_practice.py
```

The importer validates the prepared JSON and referenced figures, then generates
the UI data and backend reference records. It does not extract questions from
PDFs or other raw sources. Open [Math Practice](http://127.0.0.1:8877/math-practice/)
and select your bank to browse questions, submit answers, and explore included solutions.
Ordinary practice works without models; configured models add the same optional
speech input and AI feedback available for the included bank.

To try the supplied examples, use `question-bank-template/example` as the bank
folder. Add `--replace` when importing an updated version of an existing bank,
then reload practice. Imported banks stay in ignored `custom-banks/`; importing
does not publish your collection or change its license. See the template guide
for conversion details and answer-checking limits.

## Optional AI connections

The connections below apply to the **local edition**. For the public website, use the [online custom API setup](#connect-your-tutor-online); online ChatGPT sign-in is forthcoming. The local Python server on your computer handles model requests, API keys, and ChatGPT sign-in. [OpenAI API authentication](https://developers.openai.com/api/reference/overview#authentication)

Open the local app’s **Settings → Connection settings → Math reasoning & feedback** and choose how to connect.

| Connection | Steps |
|---|---|
| **ChatGPT plan** | Install the shared sign-in dependency with `python -m pip install --user "PyJWT[crypto]>=2.10,<3"` (use `python3` on macOS or Linux). Choose **Use a ChatGPT plan → Continue with ChatGPT**. Sign in to an eligible account, return to the app, and choose a model. [OpenAI local-app sign-in guide](https://developers.openai.com/siwc/token-sharing-open-source/sign-in) |
| **OpenAI API key** | In the custom API form, enter `https://api.openai.com/v1` under **URL**, paste your own project key under **API Key**, and enter the name of a Chat Completions model your API project can use. [Create an OpenAI API key](https://platform.openai.com/api-keys) |

Choose **Test Connection**, then **Save Settings**. A successful math test returns a tutor review. Tests send a small sample and use the selected API or plan. You can leave the other two roles blank or connect your own models below.

### Separate and local connections

Open **Settings → Connection settings**. Each connection is independent. Enter
your server address and model ID, add a key only if your server requires one,
then save and test that connection. Leave its address and model blank to disable it.

| Connection | Adds | Required API |
| --- | --- | --- |
| Math reasoning and feedback | Reviews the submitted answer and explanation in one call, with feedback and a hint when needed | Compatible `POST /v1/chat/completions` returning a structured tutor review, or a supported account connection |
| Voice to text | Turns recorded thinking into an editable transcript | `POST /v1/audio/transcriptions` accepting multipart WAV and returning a text field |
| Sentiment analysis | Reads the original transcript for expressed confidence, engagement, and how clearly the student explained their reasoning; this does not require the reasoning to be correct | Compatible `POST /v1/chat/completions` with JSON responses, or custom `POST /v1/systemone` with rubric choices and probabilities |

Model listing through `GET /v1/models` is optional. The connection tests call
the task endpoints directly. Sentiment analysis uses the words in the original
speech transcript. The math tutor uses the thinking the student submits, including
any edits they make before submitting.

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

ChatGPT plan credentials are stored in the app’s user-data
directory. Existing **Codex account** connections continue to use the user's
Codex installation, login, and shared `openai-codex` Python package.

Settings are stored in ignored `math-practice/config.json`. The server creates
it with empty connections on first start. You may also copy
`math-practice/config.example.json` to that path and edit it, then use
**Load Settings**. The example contains no working credentials or private
addresses. Startup does not run model tests or inference.

You can load a separate private JSON or YAML profile at startup:

```sh
python math-practice/runtime/launch_math_practice.py --settings "path/to/setting.yaml" --port 8879
```

The server also accepts `--settings`. **Load Settings** reloads that selected file;
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
For an existing Codex account, use `inference.provider: codex`
with its model and effort; account credentials remain in the existing user-wide
sign-in. Private profiles and `local-service/` are Git-ignored. A launcher will not
reuse a running server with a different profile; choose another port or restart it.

## Updating the hosted site

GitHub Pages serves the root of `gh-pages`. To rebuild the eight-collection site,
use the release source checkout that contains the supplemental question bundles,
the Pages exporter, and the tests below. The desktop ZIP on `main` builds the
older two-bank edition. Run the following commands from the release source root
with shared installations of Python 3.11 or newer, Node.js, and Git.

```powershell
node --test scripts/test_hosted_runtime.js scripts/test_agreement.js
if ($LASTEXITCODE -ne 0) { throw 'Hosted practice tests failed.' }
python scripts/test_pages_export.py
if ($LASTEXITCODE -ne 0) { throw 'Pages export tests failed.' }
$pagesOutput = Join-Path (Split-Path -Parent $PWD.Path) ("K-12-math-pages-" + (Get-Date -Format yyyyMMdd-HHmmss))
$pagesWorktree = "$pagesOutput-branch"
python scripts/build_pages.py --output $pagesOutput
if ($LASTEXITCODE -ne 0) { throw 'The site export failed.' }
```

The export validates the public question and graph bindings, then writes the app,
browsing catalogs, individual questions, practice links, figures, and source
notices. Preview or inspect that folder before publishing. The exporter requires
an empty output folder and leaves the source checkout unchanged.

Prepare the update in a separate worktree of the published branch. The `git rm`
command clears the previously tracked website files in that worktree so that the
published branch also reflects removals from the collection.

```powershell
git fetch origin gh-pages
git worktree add --detach $pagesWorktree origin/gh-pages
if ($LASTEXITCODE -ne 0) { throw 'Could not prepare the deployment worktree.' }
git -C $pagesWorktree rm -qr --ignore-unmatch .
Get-ChildItem -LiteralPath $pagesOutput -Force | Copy-Item -Destination $pagesWorktree -Recurse -Force
git -C $pagesWorktree add --all
git -C $pagesWorktree diff --cached --stat
```

After reviewing the changes, publish the commit and remove the temporary worktree.

```powershell
git -C $pagesWorktree commit -m "Update hosted Math Practice"
git -C $pagesWorktree push origin HEAD:gh-pages
if ($LASTEXITCODE -ne 0) { throw 'Push failed. The worktree is available for retry.' }
git worktree remove $pagesWorktree
```

In GitHub **Settings → Pages**, the source is **Deploy from a branch**, with
`gh-pages` and **/(root)** selected. GitHub publishes each update to that branch. Check the published
[Math Practice site](https://math-practice.ailleo.net/) after deployment.

### Live domain and service

Cloudflare manages DNS for `ailleo.net`. The `math-practice` CNAME points to
`rqzhu-aide.github.io`, where GitHub Pages serves the website. The optional
Ailleo Math Practice Service runs on the desktop and uses `api.ailleo.net`.
The public build record gives the website version and the number of questions in
each collection. [Published build record](https://math-practice.ailleo.net/build-info.json)
