# Question bank template 1.0.0

Use this template to prepare an English question bank for K-12 Math Practice.
It uses the compact format exercised by the 12-question pilot: each question
file contains its prompt, answer, classification, assessed concepts, and
separately credited solution methods. The four-question example is ready to
import and includes numeric, choice, short, and self-assessed responses plus
a diagram.

**Template release:** `1.0.0`, recorded in [VERSION](VERSION).
**Question and source-index schema:** `3.0`, recorded as `schemaVersion` in JSON.
These versions describe different things. Keep `schemaVersion: "3.0"` when using
this release. [question-v3.schema.json](question-v3.schema.json) is the current
question schema; [question.schema.json](question.schema.json) documents the
older 2.0 format, which the application can still read.

The example questions, solutions, and SVG are original project material under
[CC BY-NC 4.0](../LICENSE). Their credits are in
[example/source-index.json](example/source-index.json). Use the actual license
and credits for your own material. The importer reads prepared JSON and images;
it does not extract or translate PDFs, websites, or documents.

## Import and read the example

Use Python 3.11 or newer installed for your user or machine. No Python packages
or project environment are needed. From the repository root, run:

```sh
python math-practice/runtime/import_question_bank.py question-bank-template/example --check
python math-practice/runtime/import_question_bank.py question-bank-template/example
python math-practice/runtime/serve_math_practice.py
```

`--check` validates without changing installed content. The next command copies
the bank to `custom-banks/example/` and rebuilds `custom-banks/banks.js`. Open
[Math Practice](http://127.0.0.1:8877/math-practice/), reload if already open, and
select **Example: Grade 7 geometry** in the bank selector. Read both topics and
open **Explore solution** to see the explanations and credits. The bank works
without model connections; optional AI feedback requires a configured server.

To update an installed bank, edit your source folder and import deliberately:

```sh
python math-practice/runtime/import_question_bank.py path/to/your-bank --check
python math-practice/runtime/import_question_bank.py path/to/your-bank --replace
```

Keep question IDs stable so saved practice history can still refer to the same
questions. Do not edit generated `banks.js`. Installed custom banks are local
content ignored by Git. Their browser bundle includes answers and explanations,
so put only material intended for practice in a bank.

## Copy the bank

Copy [example/](example/) to a working folder, then change the manifest, IDs,
content, and source entries together:

```text
your-bank/
  bank.json
  source-index.json
  questions/
    school_geometry__triangle_area.json
  figures/
    triangle-area.svg
```

The manifest describes the collection:

```json
{
  "id": "school_geometry",
  "label": "School geometry",
  "attribution": "The actual author or rights holder, with required credits",
  "license": "The actual license or permission terms"
}
```

Choose a bank ID with at most 48 characters, beginning with a lowercase letter.
Use lowercase letters, digits, and single underscores between nonempty parts.
Each question ID starts with `<bank-id>__`, uses only letters, digits, and
underscores, and has at most 120 characters. Save it as `questions/<id>.json`.
Its `bank` must match `bank.json` and `source-index.json`. An optional manifest
`sourceURL` must be an HTTP or HTTPS URL.

See [the annotated worked example](ANNOTATED_EXAMPLE.md) for a complete question
and its two source entries. JSON has no comments; keep author notes in a separate
document rather than adding unsupported fields to the question.

## Question fields

The ten top-level fields below are required. Extra top-level fields are rejected.
Omit unknown optional information rather than writing placeholders.

| Field | What to write |
| --- | --- |
| `schemaVersion` | The string `"3.0"`. |
| `id`, `bank`, `language` | Stable namespaced ID, matching bank ID, and `"en"`. This compact format is English. |
| `question` | `{ "prompt": "..." }`, with ordered `choices` only for `choice` or `multiSelect`. Each choice has stable `id` and `content`. |
| `answer` | Response type and complete accepted responses, or a rubric for `self`. See below. |
| `classification` | Known browsing information: `area`, `domainIds`, `topicIds`, `skillIds`, `grade`, `level`, `unit`, `difficulty`. ID fields are arrays of distinct strings; grade is a nonnegative integer; other fields are text. `{}` is valid when nothing is known. |
| `assessedNodeIds` | Concepts the question assesses. `[]` means no assessed target has been recorded. |
| `solutions` | Method objects with distinct `id`, `title`, and `explanation`, `directNodeIds`, or both. `[]` means neither explanation nor method annotation is available. |
| `sourceRef` | Key of the question's entry in `source-index.json`. |

The example uses two topics in one Grade 7 unit. For a given level and grade,
keep the unit consistent. Keep topic labels consistent and question numbers
unique within each topic. Topic labels and display positions live in the
question source's `topicLabels` and `position`, rather than being repeated in
the compact question.

### Answers and local checking

| `answer.type` | Specification | Local checking |
| --- | --- | --- |
| `choice` | `"accepted": ["B"]`; `question.choices` contains that ID. `["A", "C"]` accepts either choice. | Compares the selected choice with any accepted ID. |
| `multiSelect` | `"accepted": [["A", "C"]]` is one complete selection containing both. | Requires an exact accepted set, in either order. |
| `numeric` | `"accepted": ["63"]`, `["3/4"]`, or `["3,-3"]`. Each string is one complete response without units or LaTeX. | Compares numeric values and supported lists. Add `"unordered": true` only if list order does not matter. |
| `short` | `"accepted": ["5x+15", "15+5x"]`. List literal valid forms you want recognized. | Basic text normalization; general algebraic equivalence is not established. |
| `self` | `"rubric": "Explain why ..."`; omit `accepted`. | The learner compares with the rubric and explanation. No answer-only automatic mark. |

For example, `["3,-3", "-3,3"]` lists two complete numeric responses, whereas
`["3", "-3"]` accepts either single number. A short question can request an
expanded expression and deliberately omit a valid but unexpanded form.

Optional answer fields are `rejected` (explicit rejected strings), `form`
(`decimal`, `standard-monomial`, or `ordered-list`), and `gradingNote`.
A nonempty `gradingNote` suspends automatic grading and states why. Use it for
a disputed or unsuitable recorded key; do not invent agreement with the key.
Make any required answer form explicit in the prompt.

### Solutions and concept annotations

Each solution is its own object. Put its worked text in `explanation` and the
concepts used directly by that method in `directNodeIds`. Keep alternative
methods separate, including their sources. The selected curriculum graph
supplies prerequisite connections; do not copy every lower-level prerequisite
into every method.

Use canonical IDs from `database/knowledge-graph/source/nodes.json`. An assessed
target can differ from the knowledge a method uses. If the direct set is unknown,
omit `directNodeIds`; an empty array is invalid. A method with only node IDs is
a graph route awaiting written explanation and is not shown as a worked solution.
A method with only `explanation` remains readable without invented annotations.
Importing alone does not create reviewed curriculum mappings or establish that
the concept IDs are appropriate.

Follow [EXPLANATION_STYLE.md](EXPLANATION_STYLE.md): explain why the method fits,
justify its decisive steps, and keep complete methods within the intended
learner's reach. Mathematical correctness and student readability need review.

## Sources, credits, and diagrams

Every bank needs `source-index.json` with `schemaVersion: "3.0"`, `bank`, and
`sources`. Every question and explicit method `sourceRef` must resolve there.
A method without `sourceRef` inherits the question's source. Use a separate
method source for different authorship, licensing, or review.

The example includes question credits, license, browsing position, topic labels,
figure credit and alt text, plus separate solution provenance. Record actual
source URLs, revisions or pages, translation and modification history, and review
status when applicable. Distinguish an official solution from a teacher derivation
or AI-authored explanation. A license label records terms; it does not grant
permission or prove a review occurred.

Original banks need no migration archive. When converting existing material,
retain original-language records, correction history, and review evidence in the
index or a bank-local archive. Indexed `archive/` files must have matching SHA-256
hashes; the importer checks and copies those references. Do not leave references
to files that exist only in your private checkout.

Use `\(...\)` for inline mathematics and `\[...\]` for display mathematics.
Double backslashes inside JSON. Use portable prose and supported LaTeX; arbitrary
source-page HTML is not part of this format.

```json
{
  "prompt": "Find the area when \\(b=14\\) and \\(h=9\\).\n\n[Figure 1](figures/triangle-area.svg)"
}
```

Place diagrams in `figures/` and use `[Figure 1](figures/triangle-area.svg)` in
prompts, choices, or explanations. Use flat filenames beginning with a letter or
digit and continuing with letters, digits, underscores, hyphens, or periods.
Supported extensions are `.svg`, `.png`, `.jpg`, `.jpeg`, and `.webp`. Match case
exactly. Remote image links and nested figure folders are not supported.
Each question source's `assets` can record a figure's relative `path`, `alt`,
attribution, license, and source. Preserve essential labels, perpendicular
markers, dimensions, and scale caveats.

SVGs must be static and self-contained, without scripts, event handlers,
external references, embedded HTML, or animation. Use legible scanned crops
when permitted and preserve their credits. A necessary diagram cannot be replaced
by a caption. Model review of diagrams needs an image-capable connection and
must be tested separately.

## Review before using a bank

1. Establish source identity and permission. Preserve required text and figure
   credits, revisions, and original identifiers.
2. Check transcription or translation against the original layout, including
   signs, fractions, choices, units, tables, and diagrams.
3. Solve every question. Check each accepted response, rubric, method, annotation,
   and reason to withhold grading.
4. Run `--check`, then import. Read every question and revealed method in the UI.
   Try correct responses, plausible errors, and relevant alternative forms.
   Check formulas, figures, and source credits.

[bank.schema.json](bank.schema.json),
[question-v3.schema.json](question-v3.schema.json), and
[source-index.schema.json](source-index.schema.json) help editors check structure.
The importer also resolves sources, checks filenames and grouping, and validates
supported figures. A successful check is structural evidence, not proof of
mathematical correctness, permission, or teaching quality.
