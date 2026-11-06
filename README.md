# math-practice

[![Version 2.0.0](https://img.shields.io/badge/version-2.0.0-blue)](VERSION)
[![Python 3.11 or newer](https://img.shields.io/badge/python-3.11%2B-blue)](#start-practicing)
[![8,790 questions](https://img.shields.io/badge/questions-8%2C790-green)](#interactive-practice)
[![Original code license: CC BY-NC 4.0](https://img.shields.io/badge/code_license-CC_BY--NC_4.0-orange)](LICENSE)

Content attribution: [CN bank: cn-math-taxonomy, CC BY-NC 4.0](cn-math-bank/NOTICE.md);
[AMC bank: Mathematical Association of America, CC BY-NC-SA 4.0](amc-bank/NOTICE.md).
Other imported material retains its [separate notices](THIRD_PARTY_NOTICES.md).

Repository: [rqzhu-aide/math-practice](https://github.com/rqzhu-aide/math-practice).

A local mathematics practice space developed by [Ruoqing Zhu](https://github.com/rqzhu-aide).
Includes **5,435 AMC questions and answer keys** and **3,355 processed Chinese
curriculum questions**, displayed in English. The Chinese bank includes worked
solutions, diagrams, and preserved Chinese originals. It is adapted from the Chinese K-12 mathematics repository
[xiaoyang111222/cn-math-taxonomy](https://github.com/xiaoyang111222/cn-math-taxonomy),
with source attribution and modification details preserved. There is no frontend
build step.

The **American Mathematics Competitions (AMC)** material is credited to the
**[Mathematical Association of America (MAA)](https://maa.org/student-programs/amc/)**
and shared with permission under **CC BY-NC-SA 4.0**. This bank includes all 195
papers in our processed AMC 8, AMC 10, and AMC 12 collection, including historical
predecessors. Eight included official MAA solution booklets cover **200 questions**
across five AMC 8 papers and three AMC 10A papers. All 200 also include
[reviewed adaptations of official MAA solutions](amc-bank/ADAPTATIONS.md),
with connected reasoning, diagrams where useful, and strategies to recognize again.
The explanations and original booklets work without models. Copied LIVE by Po-Shen Loh
worked solutions are not included. Other AMC questions provide answer keys;
historical transcription provenance remains in the bank metadata.
See [AMC coverage and attribution](amc-bank/README.md).

## Interactive practice

<table>
<tr>
<td width="50%" valign="top">
<a href="docs/images/interactive-practice.png"><img src="docs/images/interactive-practice.png" width="100%" alt="Math Practice showing the Record thinking control, mathematical feedback, a progressive hint, and Confidence, Clarity, and Engagement learning signals."></a>
<p><em>Illustrative session in the actual UI, using a sample transcript and model responses. Click the image to view it at full size.</em></p>
</td>
<td width="50%" valign="top">
<p><strong>Record thinking:</strong> talk through your approach as you work. AI speech recognition turns up to a minute of spoken reasoning into an editable draft. Review the transcript, correct any recognition errors, and refine your explanation before sending it to the tutoring agent.</p>
<p><strong>Get feedback:</strong> Mathematics checks your answer and your reasoning separately. Across question banks, it uses the displayed problem and available topic context to follow your method, acknowledge a useful step, and offer a focused check or hint. When you revise, it can use your previous attempt on this problem and the help you saw.</p>
<p><em>Experimental learning signals explore confidence, clarity, and engagement expressed in the original speech transcript. They are not validated emotion assessments.</em></p>
<p><em>Interactive model features require the optional connections below.</em></p>
<p><strong>Planned development:</strong> explore recommendations for questions and study approaches using practice history, feedback, and experimental learning signals. Recommendations are not implemented yet.</p>
</td>
</tr>
</table>

The [central mathematics database](knowledge-graph/README.md) connects all 8,790
shipped questions to 907 concepts and 1,578 accepted relationships. Mathematics
automatically receives the question's reviewed concepts, scoped prerequisites,
and complete alternative methods from a bounded local graph neighborhood.
The database rebuilds offline from the included source records. Review is
model-assisted; it does not certify curriculum alignment or student mastery.

The Mathematics request combines the displayed question, choices, answer key,
available worked solution and figures; the question's concepts and direct
prerequisite or preparation knowledge from the selected map; and the submitted
answer and thinking, including transcript edits. One inference returns independent
answer and reasoning judgments, visible tutoring feedback, and an optional hint.
An answer without thinking can receive an initial cue or a request for the first
step; missing reasoning is not treated as a demonstrated mathematical mistake.

**Worked-solution follow-up, recorded 2026-11-06:** add and review stored worked
solutions for the **5,235 AMC questions** whose solution text is currently empty,
and independently review the existing AI-generated CN solutions. Each added
solution must match its question, answer key and figures, retain source provenance,
and use the bank's mathematical prose and LaTeX format. Until this content work is
complete, a missing or deliberately omitted reference is identified explicitly.
The same tutoring inference works out a solution privately before assessing the
student; this temporary fallback does not create a verified solution-bank entry
or reveal the full solution in the coaching or hint fields. Available references
are supplied with their provenance and remain one possible valid method.

Open **Find a problem** to choose a practice path: **ailleo** browses mathematical
ideas without grade levels, **CN** follows the imported Chinese taxonomy, and
**US** follows Common Core Coherence Map standards. Select a concept or standard
and choose **Find practice**. Each path keeps its own connections and supplies
that context to Mathematics. Related questions can cover only part of a standard
or include additional ideas; a standard without linked practice stays visible.
These are linked practice choices, not an adaptive next-question sequence.

The Grade 9 **Completing the Square**, Problem 2, also includes a learner-evidence pilot.
With the local launcher, evidence for this problem works even without a model.
After submitting your work, open **Knowledge graph evidence**
beside your notebook. It shows the item result, the observed mathematical step,
supporting words when available, and the help seen before that attempt. These
observations stay in this practice tab. The pilot leaves unfamiliar reasoning
unclassified and keeps coached revisions separate from unaided first attempts.

## Start practicing

Install **Python 3.11 or newer** for your user or machine. No Python packages or
model services are needed for ordinary practice.

On first start, the server creates its default connection settings and builds the
local SQLite knowledge database from the bundled source records. A fresh checkout
does not need an existing `.local/` folder, database file, or private model profile.

From this repository's root, run:

```sh
python scripts/serve_math_practice.py
```

Open [Math Practice](http://127.0.0.1:8877/math-practice/). Keep the terminal running.
On Windows, you can instead double-click **Start Math Practice.cmd** to start the
server in the background and open practice. If the port is occupied, add
`--port 8878` to the Python command and use that port in the browser.
After updating the repository, stop and restart any running Math Practice server
so it can serve newly added banks and official solution booklets.

Choose **Try a problem** or browse by level, unit, and topic. Enter an answer,
write your thinking, and submit. Without models, known answers are checked
locally; reasoning and unfamiliar symbolic or open answers are not automatically
judged. Add some thinking to open the answer and available solution. Drafts and your notebook
stay in the browser. Opening `math-practice/index.html` directly also supports
practice without model services; microphone input needs the local server.

## Use your own question bank

Use the [question-bank template](question-bank-template/README.md) to process your
own questions into the shared JSON format, then use the Math Practice UI to serve
and practice the processed questions. The template includes schemas, four example
questions, a diagram, and a conversion guide. Preserve each question's answer,
worked solution, figures, and source attribution when preparing your collection.
The [explanation style guide](question-bank-template/EXPLANATION_STYLE.md) helps
authors turn correct solutions into connected, student-facing reasoning.

From the repository root, replace `path/to/your-bank` with your prepared bank
folder and run:

```sh
python scripts/import_question_bank.py path/to/your-bank --check
python scripts/import_question_bank.py path/to/your-bank
python scripts/serve_math_practice.py
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

Open **Settings → Connection settings**. The **Mathematics**, **Speech**, and
**Sentiment** tabs each have a URL, an optional API key, and a model name. Each
connection can use its own service or local model. Existing saved connections
load directly into these tabs.

Use **Test All Connections** to check each configured feature before saving.
Each colored dot means that tab passed its sample task. If a dot is gray, open
the matching tab to see its status or the reason a test failed. The tests use synthetic
samples, including a short silent recording, and may use API credits. Speech
accuracy and the quality of the feedback depend on the models you choose.
Chat-based learning signals describe the transcript's words and show brief
supporting evidence. Ordinary practice needs no API key.

### Separate and local connections

Open **Settings → Connection settings**. Each connection is independent. Enter
your server address and model ID, add a key only if your server requires one,
then save and test that connection. Leave its address and model blank to disable it.

| Connection | Adds | Required API |
| --- | --- | --- |
| Mathematics | Reviews answers and provides hints | Compatible `POST /v1/chat/completions` returning a structured tutor review |
| Speech | Turns recorded thinking into an editable draft | `POST /v1/audio/transcriptions` accepting multipart WAV and returning a text field |
| Sentiment | Checks learning signals in a transcript, mathematical reasoning, and typed answers | Compatible `POST /v1/chat/completions` with JSON responses, or custom `POST /v1/systemone` with rubric choices and probabilities |

Model listing through `GET /v1/models` is optional. The connection tests call
the task endpoints directly, including all three assessment tasks for Sentiment.

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

In **Mathematics**, choose **Use a ChatGPT plan** to connect an eligible plan.
**Continue with ChatGPT** opens OpenAI's sign-in page. After granting access,
choose a model, run **Test Connection**, then **Save Settings**. A passing
Mathematics test means the model returned a valid text tutor review. Figure
questions also require image support. Use **Manage usage** to check plan limits,
or **Use custom API** to switch back. Speech and Sentiment use their own endpoints.
[OpenAI's local-app sign-in guide](https://developers.openai.com/siwc/token-sharing-open-source)

ChatGPT sign-in uses the shared Python package `PyJWT[crypto]`. Install it once
with `python -m pip install --user "PyJWT[crypto]>=2.10,<3"`. Account credentials
are stored separately from the practice configuration, in the app's user-data
directory. Existing **Codex account** connections continue to use the user's
Codex installation, login, and shared `openai-codex` Python package.

Settings are stored in ignored `math-practice/config.json`. The server creates
it with empty connections on first start. You may also copy
`math-practice/config.example.json` to that path and edit it, then use
**Load Settings**. The example contains no working credentials or private
addresses. Startup does not run model tests or inference.

You can load a separate private JSON or YAML profile at startup:

```sh
python scripts/launch_math_practice.py --settings "path/to/setting.yaml" --port 8879
```

The server also accepts `--settings`. **Load Settings** reloads that selected file;
**Save Settings** updates it. YAML profiles use the same `decision`, `speech`,
and `inference` sections as JSON and require shared **PyYAML**
(`python -m pip install --user PyYAML`). A connection may use
`apiKeyFile: api_key.txt`, resolved relative to the profile, instead of embedding
its key. Unchanged key-file references are preserved when saving.

Set `mathAssessment: inference` to use one Mathematics inference for answer and
reasoning correctness together with tutoring feedback and any hint. The decision
connection handles only learning signals; there is no separate model-based math
grader in this mode. Exact answer-key checks still run locally without inference;
submitting an answer, with or without thinking, triggers the combined Mathematics
review.
The default `mathAssessment: decision` retains the separate decision-model math
check before tutoring. For an existing Codex account, use `inference.provider: codex`
with its model and effort; account credentials remain in the existing user-wide
sign-in. Private profiles and `local-service/` are Git-ignored. A launcher will not
reuse a running server with a different profile; choose another port or restart it.

## Folders and local files

The public release contains these folders:

| Folder | Purpose |
| --- | --- |
| `math-practice/` | Practice and connection-settings pages, browser scripts, styles, bundled KaTeX, and JavaScript tests |
| `scripts/` | Local server and launcher, model connections, question-bank tools, graph readers, and Python tests |
| `cn-math-bank/` | Processed CN records, browser data, figures, schemas, source attribution, and license |
| `amc-bank/` | AMC records, browser data, figures, included official MAA booklets, attribution, and license |
| `knowledge-graph/` | Reviewed graph sources, retained review evidence, curriculum manifest, and graph documentation |
| `question-bank-template/` | Bank schemas, example questions and figures, and the explanation style guide |
| `docs/images/` | The illustrative UI screenshot used in this README |

The root also contains `VERSION`, the Windows launcher, this README, and license
and third-party notices. Runtime state stays separate:

| Local path | Purpose |
| --- | --- |
| `../local-service/` | Optional private sibling folder for machine-specific service instructions, key files, and JSON/YAML profiles; outside this repository |
| `math-practice/config.json` | Default saved connections, created on first start and Git-ignored |
| `custom-banks/` | Imported personal banks, Git-ignored |
| `.local/` | Launcher logs and optional account work files, Git-ignored |
| `knowledge-graph/*.sqlite3` and `knowledge-graph/local/` | Generated databases and optional private mapping overlays, Git-ignored |
| `local-testing/` | Local verification evidence, excluded from the public release |

A sibling profile can be loaded with
`python scripts/launch_math_practice.py --settings "../local-service/setting.yaml"`.
The file must already exist. Keep language runtimes, packages, and development
tools in shared user or machine installations.

## Verify the release

Use a shared Python 3.11+ installation and a shared Node.js installation. The full
Python suite exercises optional image, YAML, and sign-in features. Install their
test dependencies in the same shared Python installation:

```sh
python -m pip install --user PyMuPDF Pillow PyYAML "PyJWT[crypto]>=2.10,<3"
python -m unittest discover -s scripts -p "test_*.py"
node --test math-practice/test/*.test.cjs
```

The tests use temporary records, mocked model responses, and local synthetic
services. No live account or paid-model request is needed. Actual even-odd figure
rendering tests use a shared Chrome, Chromium, or Edge installation and skip when
none is available. Optional upstream-source checks skip when their external
snapshots are absent from a standalone checkout. The YAML and token-signature
test groups report skips if their optional packages are unavailable.

For graph-source reproducibility and database checks, use the commands in the
[knowledge-graph guide](knowledge-graph/README.md#build-inspect-and-attach).

## Data and privacy

The server listens on this computer's loopback interface only. Keys stay in the
local backend and are not served as static files. When you enable a model,
the relevant submitted work or recorded audio is sent to your chosen service.
The harness does not save audio. Runtime logs and optional account work files
stay in ignored `.local/`.

The Git allowlist includes application code, bundled assets, tests, documentation
and its UI screenshot, the public question template, reviewed graph source records
and review evidence, and the published AMC and Chinese banks. It excludes private
configuration, logs, caches, raw source
collections, processing reports, copied third-party AMC solutions, and imported custom banks. Do not force-add
local files with `git add -f`; review staged changes before publishing.

## License

Copyright (c) 2026 Ruoqing Zhu and contributors.

Unless otherwise noted, this project's original code, documentation, question
templates, sample questions, and artwork are licensed under **Creative Commons
Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**. See the full
[license](LICENSE) and the [official license summary](https://creativecommons.org/licenses/by-nc/4.0/).

Different parts of this repository have different licenses:

| Material | Attribution | License |
| --- | --- | --- |
| Original app, documentation, template, and examples | Ruoqing Zhu and contributors | [CC BY-NC 4.0](LICENSE) |
| AMC questions, answer keys, included diagrams, official MAA solution booklets, and our adaptations of AMC material | Mathematical Association of America (MAA); transcription provenance credits LIVE by Po-Shen Loh | [CC BY-NC-SA 4.0](amc-bank/LICENSE) |
| Chinese K-12 questions and our adaptations | [xiaoyang111222/cn-math-taxonomy contributors](https://github.com/xiaoyang111222/cn-math-taxonomy) | [CC BY-NC 4.0](cn-math-bank/LICENSE) |
| Bundled KaTeX and fonts | KaTeX contributors | MIT and retained font notices |

AMC adaptations must retain ShareAlike terms. The original app license does not
replace the AMC license. Preserve attribution, license links, and modification
notices when sharing either bank. See [AMC notices](amc-bank/NOTICE.md),
[Chinese bank notices](cn-math-bank/NOTICE.md), and
[third-party notices](THIRD_PARTY_NOTICES.md). The Chinese source questions and
English translations are AI-generated and not teacher reviewed. None of these
attributions implies endorsement of Math Practice by the source authors.
