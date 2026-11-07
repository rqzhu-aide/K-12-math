# Annotated worked example

This example asks a learner to find a triangle area. Copy the actual files in
[example/](example/) to start a bank; this guide explains how they fit together.
The question, explanation, and diagram are original project content under
CC BY-NC 4.0. No third-party question or solution is needed.

## The question file

Save this as `questions/example__triangle_area.json` in the `example` bank.
The template release is **1.0.0**; the JSON format remains **3.0**.

```json
{
  "schemaVersion": "3.0",
  "id": "example__triangle_area",
  "bank": "example",
  "language": "en",
  "question": {
    "prompt": "In triangle \\(ABC\\), base \\(AB = 14\\) cm and the perpendicular height from \\(C\\) to \\(AB\\) is \\(9\\) cm. Find the area of the triangle in square centimetres. Enter the number only.\n\n[Figure 1](figures/triangle-area.svg)"
  },
  "answer": {
    "accepted": [
      "63"
    ],
    "type": "numeric"
  },
  "classification": {
    "domainIds": [
      "domain:geometry"
    ],
    "grade": 7,
    "level": "Middle school",
    "skillIds": [
      "skill:geometry:triangle-area"
    ],
    "topicIds": [
      "area"
    ],
    "unit": "Perimeter and area"
  },
  "assessedNodeIds": [
    "cnm_p148"
  ],
  "solutions": [
    {
      "directNodeIds": [
        "cnm_p148"
      ],
      "explanation": "The area of a triangle is half the product of its base and perpendicular height:\n\\[A = \\frac{1}{2} \\times 14 \\times 9 = 63.\\]\nThe area is \\(63\\) square centimetres.",
      "id": "primary",
      "sourceRef": "example/example__triangle_area#primary",
      "title": "Worked solution"
    }
  ],
  "sourceRef": "example/example__triangle_area"
}
```

The prompt gives the base and perpendicular height, includes the required unit,
and asks for a number only. The answer specification therefore accepts `63`
without units. The worked explanation applies the triangle-area formula and
states the resulting area. Backslashes in LaTeX are doubled because this is JSON.
The figure link resolves inside the bank, independently of its installation path.

The assessed target and this method both use `cnm_p148`, the shared graph
concept for triangle area. These are different roles even when their IDs match:
`assessedNodeIds` describes what the question assesses; `directNodeIds` describes
what the particular method uses. Alternative methods keep their own direct sets.
Do not copy these IDs into unrelated questions. If an annotation is unknown,
use an empty assessed array or omit a method's direct set.

`classification.topicIds` refers to the `area` topic. Its readable label and
position are held in the source index. `id` matches the filename, and its `example__`
prefix matches the manifest bank ID. The method's `primary` ID is local to this
question and should remain stable during later edits.

## The source index

The following is a complete source index for this one question. The supplied
[example/source-index.json](example/source-index.json) adds the other three
questions. Save the index next to `bank.json`, not inside `questions/`.

```json
{
  "schemaVersion": "3.0",
  "bank": "example",
  "sources": {
    "example/example__triangle_area": {
      "kind": "question",
      "label": "Original Grade 7 example question",
      "attribution": "Math Practice contributors; original example question and diagram",
      "license": "CC-BY-NC-4.0",
      "licenseURL": "https://creativecommons.org/licenses/by-nc/4.0/",
      "position": {
        "batch": "area",
        "number": 1
      },
      "topicLabels": {
        "area": "Area and algebraic expressions"
      },
      "assets": [
        {
          "path": "figures/triangle-area.svg",
          "alt": "Triangle with base 14 cm and perpendicular height 9 cm Triangle ABC has horizontal base AB. A dashed perpendicular from C to the base marks a height of 9 cm. The base is labelled 14 cm. The drawing is not to scale.",
          "attribution": "Math Practice contributors; original example diagram",
          "license": "CC-BY-NC-4.0",
          "licenseURL": "https://creativecommons.org/licenses/by-nc/4.0/"
        }
      ]
    },
    "example/example__triangle_area#primary": {
      "kind": "solution",
      "label": "Original worked solution",
      "questionRef": "example/example__triangle_area",
      "provenance": {
        "source": "Math Practice contributors; original worked solution for this example; no external source",
        "reviewStatus": "No teacher or independent content review claimed by this template",
        "attribution": "Math Practice contributors",
        "license": "CC-BY-NC-4.0",
        "licenseURL": "https://creativecommons.org/licenses/by-nc/4.0/"
      }
    }
  }
}
```

The question source supplies authorship, license, topic label, and display order.
The asset entry preserves both the diagram credit and an accessible description.
The method source separately credits the explanation and states the actual
review limitation. Neither a version number nor successful import certifies
mathematical or teacher review.

These bank-local source keys have no network dependency. An external source can
record its URL and revision or page alongside its credit. If that material has
different terms, record those actual terms rather than copying this example's
license. A method may inherit the question source when appropriate, but explicit
method sources make different authorship and review easy to see.

## What to change for your bank

1. Change the manifest ID, every question ID and filename prefix, each question
   `bank`, and the index `bank` together. Update all `sourceRef` keys and values.
2. Replace prompts, accepted responses, explanations, classifications, and graph
   annotations with content that fits the new questions. Keep each complete
   accepted response as one entry.
3. Supply your actual source and figure credits. Keep only existing portable
   figure files and source references.
4. Follow the [import commands](README.md#import-and-read-the-example), select
   the imported bank, answer the numeric question, and open Explore solution.
   Check that the triangle, rendered formula, answer, explanation, and credits
   all agree.

The remaining example records show ordered choices, several accepted short
responses, and a self-assessment rubric. Additional answer forms and missing
explanation cases are described in the [field guide](README.md#question-fields).
