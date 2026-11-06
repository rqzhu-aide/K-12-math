# Bring your own question bank

Use this folder to convert a question collection into the JSON format used by
Math Practice. The example contains four original Grade 7 questions, covering
numeric, multiple-choice, short-answer, and explanation responses, plus a diagram.
The template, original example questions, solutions, and diagram are licensed
under [CC BY-NC 4.0](../LICENSE), like the project's original code and documentation.
Use the actual license or permission terms for your own collection; importing
a bank does not change its license.

The importer accepts prepared JSON and figure files. It does not extract questions
from PDFs, documents, spreadsheets, or websites. Transcribe or convert those
sources first, then review the result using the checklist below.

## Try the example

Use Python 3.11 or newer installed for your user or machine. The importer uses
the standard library, so no packages or project environment are needed. From the
repository root, run:

```sh
python scripts/import_question_bank.py question-bank-template/example --check
python scripts/import_question_bank.py question-bank-template/example
```

`--check` validates without installing. The second command installs the bank in
`custom-banks/example/` and rebuilds `custom-banks/banks.js`. Reload Math Practice
and choose **Example: Grade 7 geometry** in the bank selector.

For the local server, run `python scripts/serve_math_practice.py` and open
[Math Practice](http://127.0.0.1:8877/math-practice/). If a server was already
running when you updated the application code, restart it. Imported banks also
work when opening `math-practice/index.html` directly or serving the repository
as static files. Optional model features need the local server and configured
connections.

To replace an installed bank deliberately, use:

```sh
python scripts/import_question_bank.py path/to/your-bank --replace
```

The importer refuses an existing bank ID unless `--replace` is present. Edit your
source files and reimport; do not edit the generated `banks.js`. Installed banks
are ignored by Git. The local server exposes the generated browser bundle and
images; the bundle includes prompts, answers, and solutions. A generic static
server for the whole checkout may also expose the source JSON. Keep credentials
and private notes out of bank content. Do not publish an imported bank without
the necessary rights.

## Prepare a bank

Copy `example/` to a working folder and use this layout:

```text
your-bank/
  bank.json
  questions/
    school_geometry__triangle_area.json
    school_geometry__rectangle_perimeter.json
  figures/
    triangle-area.svg
```

`bank.json` describes the whole collection:

```json
{
  "id": "school_geometry",
  "label": "School geometry",
  "attribution": "The actual author or rights holder, with required credits",
  "license": "The actual license or permission terms"
}
```

An optional `sourceURL` must be an `http://` or `https://` URL. A license field
records the terms; it does not establish permission to use someone else's work.

Choose a stable bank ID with at most 48 characters, beginning with a lowercase
letter. Use lowercase letters, digits, and single underscores between nonempty
parts, such as `school_geometry`. Leading, trailing, or repeated underscores
are not allowed. Give every question a unique ID of the form
`<bank-id>__<question-name>` and save it as `questions/<ID>.json`. Question names
may contain letters, digits, and underscores; the complete ID is at most 120
characters. Every question's `Bank` must equal the manifest `id`.

## Question field map

All fields in this table are required. Use the example records as complete,
copyable starting points.

| Field | Meaning and format |
| --- | --- |
| `ID`, `Bank`, `SchemaVersion` | Namespaced ID, matching bank ID, and the string `"2.0"`. |
| `ResponseType` | `numeric`, `choice`, `short`, or `self`; see the marking rules below. |
| `Language` | A nonempty language tag, such as `en` or `zh-CN`. The interface labels remain English. |
| `Level`, `Grade`, `CurriculumUnit` | Display grouping, such as `"Middle school"`, `7`, and `"Perimeter and area"`. Grade is a nonnegative integer; `0` can represent kindergarten. |
| `Batch`, `Topic` | Stable topic ID and `{ "id": "area", "label": "Area" }`. `Batch` must equal `Topic.id`. |
| `Number` | Positive integer giving the question's order within its topic. |
| `Question` | Nonempty prompt with any supported LaTeX and figure links. |
| `Choices` | For `choice`, an object with 2 to 5 nonempty entries keyed `A` through `E`. For every other type, use `{}`. |
| `Correct Answer` | A choice key, numeric answer, short reference answer, or explanation reference, according to response type. |
| `Solution` | A nonempty worked solution, including the reasoning needed to justify the answer. |
| `domain` | Nonempty array of broad tags, for example `["domain:geometry"]`. Tags use lowercase letters, digits, and hyphens after `domain:`. |
| `skill` | Nonempty array of specific skill tags, for example `["skill:geometry:triangle-area"]`. Letters, digits, colons, underscores, and hyphens are allowed after `skill:`. |
| `Meta` | Object containing nonempty `Attribution`, `License`, and `SolutionSource`. |

Within one bank, keep `CurriculumUnit` consistent for a given `Level` and `Grade`.
For each `Level`, `Grade`, and `Batch` group, use one `Topic.label` and unique
`Number` values. Use different topic IDs to distinguish topics. The example has
two topics within one Grade 7 unit.

The existing SchemaVersion 2.0 optional fields remain available:

| Optional field | Use |
| --- | --- |
| `Question Type`, `Choices Type` | Default to `text`. Question type also supports `mixed` and `figure`; choices type also supports `figure`. Use `mixed` for prose with a diagram. |
| `Accepted Answers` | Additional literal strings for `short` questions. Omit or use `[]` for other response types. |
| `Rejected Answers` | Explicit strings that must not receive credit. |
| `Unordered Answers` | Set `true` only when order does not matter in a numeric list. |
| `Answer Form` | `decimal`, `standard-monomial`, or `ordered-list` when that form is part of the task. Make the requested form clear in the prompt. |
| `GradingStatus`, `GradingNote` | `gradable` or `disputed`. A disputed item needs a nonempty note and is not automatically marked. |
| `Year`, `Area`, `Difficulty` | Additional descriptive metadata. `Year` is an integer or `null`. |
| `Meta.SourceURL` | Optional `http://` or `https://` source link for this question. |
| Other `Meta` fields | Preserve source IDs, revision, modifications, translation status, figure credits, and review notes as appropriate. `Meta.Original` can hold the original source record before adaptation. |

Describe where the solution came from honestly in `Meta.SolutionSource`, such
as an official published solution, a teacher's derivation, or an AI-generated
draft. Record modifications and translation review status when applicable.

Use the [explanation style guide](EXPLANATION_STYLE.md) to write solutions that
explain why the method fits, connect the important steps, and give the learner a
useful strategy to recognize again. Review reasoning and student readability
alongside the mathematical answer.

## Choose the response type deliberately

| Type | Reference answer | Local answer check |
| --- | --- | --- |
| `choice` | One supplied key, such as `"B"`. | Checks the selected key. |
| `numeric` | A numeral or fraction, such as `"63"` or `"3/4"`; comma-separated numeric lists are supported. Omit units and LaTeX. | Compares numeric values and supported list forms. Use `Unordered Answers` or `Answer Form` only when appropriate. |
| `short` | A short string, such as `"5x+15"`, with explicit alternatives in `Accepted Answers`. | Recognizes the reference and listed alternatives with basic text normalization. It does not establish general algebraic equivalence. |
| `self` | A reference explanation or rubric, with a worked `Solution`. | No answer-only automatic mark. The learner can compare with the solution, or use a configured model for review. |

For example, the garden question accepts `5x+15` and the listed `15+5x`.
It does not promise to recognize every equivalent expression. Choose `self`
for proofs, constructions, or explanations with many valid answers. Model review
is optional; importing a bank does not configure or verify a model connection.

## Mathematics and diagrams

Use `\(...\)` for inline mathematics and `\[...\]` for display mathematics.
Backslashes must be doubled inside JSON strings:

```json
{
  "Question": "Find the area when \\(b=14\\) and \\(h=9\\).\n\n[Figure 1](figures/triangle-area.svg)",
  "Solution": "Use \\[A=\\frac{1}{2}bh=63.\\]"
}
```

Use plain prose, supported LaTeX, and the figure-link convention. A source page's
layout or arbitrary HTML is not a portable question format. Keep the information
needed to solve the problem in the prompt or its diagram.

Place diagrams in the bank's `figures/` folder and refer to them as
`[Figure 1](figures/triangle-area.svg)`. The same convention can be used in
choices and solutions. For picture choices, set `Choices Type` to `figure`.
Use flat filenames beginning with a letter or digit, followed by letters, digits,
underscores, hyphens, or periods. Supported extensions are `.svg`, `.png`, `.jpg`,
`.jpeg`, and `.webp`. Match filenames exactly, including case. Subfolders and
remote image links are not part of this format.

SVGs must be static and self-contained: no scripts, event handlers, external
references, embedded HTML, or animation. For scanned material, use a clear raster
crop when you have permission. Redraw a diagram when that improves legibility,
and record that change and the original figure's attribution. Check labels,
right-angle marks, dimensions, and whether a diagram is to scale. Diagram-based
model review requires a model connection that can receive images.

## Conversion and review checklist

1. **Check the source and permission.** Identify the author, license or written
   permission, source URL, edition or revision, and original question IDs. Keep
   original wording and answers under `Meta.Original` when useful. Preserve
   required credits for figures separately from question text.
2. **Read the source layout.** Separate each prompt, choice, answer, solution,
   table, and diagram. Recheck subscripts, minus signs, fractions, units, and
   symbols after OCR or translation. Remove page headers and answer leakage.
3. **Write complete JSON records.** Choose stable IDs, consistent grouping, a
   suitable response type, and useful domain and skill tags. Preserve provenance
   and distinguish an official solution from a newly written or generated one.
4. **Prepare the figures.** Link every required image using the convention
   above. Verify that each diagram agrees with the text and is readable at the
   size used in practice. Do not replace a necessary diagram with a caption.
5. **Review the mathematics and marking.** Solve every item independently.
   Confirm the choice key, units, assumptions, worked steps, and accepted
   variants. Try a correct answer, a plausible wrong answer, and an alternate
   valid form. Use `self` where answer-only checking would be misleading.
6. **Validate, import, and inspect.** Run `--check`, correct every reported
   issue, then import. Reload the UI, choose the bank, and inspect every response
   type, topic, formula, figure, choice, and worked solution. Test any configured
   model features separately if you intend to rely on them.

[bank.schema.json](bank.schema.json) and
[question.schema.json](question.schema.json) help editors spot structural errors.
The importer checks the supported contract, cross-file relationships, and
figure references without requiring a JSON Schema package. Neither schema
validation nor successful import proves mathematical correctness, diagram
accuracy, permission, or live AI teaching quality.
