# Mathematics knowledge database

This database connects mathematical concepts, their scoped dependencies, and the
displayed content of the installed question banks. The tutor reads a bounded local
neighborhood alongside the student's actual work. Graph connections do not imply
that a learner has mastered, or lacks, any concept.

## Installed coverage

The November 5, 2026 release contains 907 concepts, comprising the 802 source
mathematics concepts and 105 reviewed additions. Of 1,657 relationship records,
1,578 are accepted and 79 retain rejected claims for inspection. Accepted records
include 878 `requires`, 473 `prepares`, 204 `method_component`, and 23 `related`
connections.

All 8,790 shipped questions have content-bound records. The current installation
also has four custom examples in its separate local overlay. Across these 8,794
questions, 8,784 have diagnostic mappings and ten provide definition-only context.
There are 4,044 reviewed route alternatives across 2,095 questions. Confirmed
ambiguities in 59 questions and source conflicts in 12 withhold automatic grading;
the original questions and keys remain available.

Claude and agy reviewed the construction plan and dependency proposals. Question
review combined an initial content-based pass with targeted audits of high-risk
items and a recorded sample of the remainder. This is not universal independent
double review. The release includes 13 source-backed restorations of missing
question setup and a correction to how four SVG diagrams are rendered for models. Twelve restored
questions received fresh model audits; one definition-only item was adjudicated
against its source.

`evidence-index.json` lists the included public evidence and its hashes. References
marked `packaged: true` resolve within this directory. Other inputs retain explicit
historical hash commitments and are not claimed to be included. Private examples
and mixed raw private review material stay in the local workspace. One superseded
native review proposal lost its original metadata bytes; its history explicitly
records that limitation, while its mathematical decisions and external receipts
remain preserved.

## Records and meaning

### CN, US, and ailleo practice paths

The shared mathematical concepts and question mappings keep their existing IDs.
`ailleo` uses their accepted mathematical relationships without grade placement.
The native CN and US graphs are preserved separately in `source/curricula.json`:
CN has 802 concepts and 1,299 connections; US has 480 standards or substandards
and 1,015 connections. CN high school values 10 through 14 identify textbook
volumes, not school years. US high school placement is a band, not a universal
year assignment.

`source/alignments.json` connects native nodes to the shared concepts. Its 802 CN
and 1,004 US links describe an exact match, a narrower or broader shared concept,
or partial overlap. One standard can link to several concepts and vice versa.
`curriculum-manifest.json` records source identities and adopted review corrections.
These are machine-reviewed content alignments, not official equivalence claims.

Each shared concept exposes derived `CN`, `US`, and `ailleo` annotations. Native
connections remain in their own layer; alignment does not turn a curriculum
connection into a universal prerequisite. US progression links retain their
learning-connection meaning rather than claiming strict prerequisites.

The practice browser keeps all native nodes visible, including the 32 US
standards with no accepted alignment. Linked questions cover the aligned concepts,
not necessarily the whole standard. Selection uses assessed concepts and complete
alternative solution routes, with direct assessment and fewer additional concepts
ranked first. It is not a calibrated difficulty order or adaptive recommendation.

Tutoring keeps the question's bound concepts and complete methods. In CN or US,
it supplies only that native graph's connections; in ailleo, it supplies the
reviewed mathematical dependencies without a grade constraint. A selected
standard scopes context only when it matches the displayed question. Changing
paths does not change question IDs or establish learner mastery.

Reproduce the retained curriculum source records with:

```sh
python scripts/build_curriculum_sources.py --check
```

Then use the database build and validation commands below. Restart an existing
server after code or graph-source changes so its runtime matches these records.

`source/nodes.json`, `source/relationships.json`, `source/mappings.jsonl`, and
`source/metadata.json` are the inspectable source records. `knowledge.sqlite3` is
the derived local runtime database. The server checks its integrity and source
identity at startup, rebuilding offline when absent or when the source records or
local overlay change. It can also be rebuilt using the shared
Python installation and its standard library; no separate database service is needed.
The index is not version controlled. After changing source records, restart the
server or run `build` before using command-line extraction.

An edge points from the dependent node to its prerequisite or related node:

| Relation | Meaning |
| --- | --- |
| `requires` | Necessary within the explicitly stated scope. |
| `prepares` | Useful preparation, without claiming logical necessity. |
| `method_component` | A component of a named, optional method. |
| `related` | A useful association without required order. |

Relationships separately record acceptance, review provenance, scope, rationale,
and the original source claim. Rejected or unresolved relationships remain in the
records for inspection and are excluded from ordinary tutoring context.
Question routes are alternatives. They are not a conjunction of skills that every
student must demonstrate. Review by language models is not teacher validation.

A completed `mapped` record may have `assessedIds: []` when it contains at least
one complete reviewed solution route. Each route has its own nonempty `nodeIds`;
these are alternative sets, so no universal synthesis node needs to be invented.
Any `supportIds` still describe shared prerequisites. Support alone, without an
assessed node or a complete route, does not make a mapping complete. Unknown node
references and empty routes are rejected. A `non_diagnostic` record remains
definition-only and cannot contain solution routes.

Route-only records use the same bound database, question exports and automatic
tutor extraction as other completed mappings. Retrieval starts from their route
nodes, preserves shared prerequisites and keeps or omits each route as a whole.
A tight context budget reports omitted routes without reverting to source tags
or legacy routes. Neither a bare answer nor a route mapping establishes global
mastery of its concepts.

## Build, inspect, and attach

Run these commands from the application repository root:

```sh
python scripts/knowledge_graph.py build
python scripts/knowledge_graph.py validate
python scripts/knowledge_graph.py extract cnm_225_q4 --json
python scripts/knowledge_graph.py extract cnm_225_q4 --depth 2 --dependents --json
python scripts/knowledge_graph_questions.py apply --dry-run --require-complete
python scripts/knowledge_graph_questions.py apply --write --require-complete
python scripts/knowledge_graph_questions.py verify --require-complete
```

`apply` appends `KnowledgeGraph` to question JSON and refreshes the corresponding
`knowledgeGraph` in existing browser bundles, preserving the other fields. It
checks every mapping before writing. `export --write` refreshes only graph fields
in the browser bundles. A normal upstream question-bank rebuild should be followed
by `apply` and `verify` again.

Bindings include the displayed question, choices, answer requirements and actual
referenced figure bytes. Changing any of them invalidates the old mapping. A
question that refers to its visible topic heading can also bind that exact text
as `headingContext`. Other source labels and solutions are provenance, not proof
of a mapping.
An edited question needs a new content-grounded mapping before it can receive
canonical graph context. The reader uses ordinary displayed-task tutoring when a
binding is missing, stale, or unresolved.

Ordinary tutor retrieval uses at most 16 nodes, one dependency step and 8,000 JSON
characters. It reports omissions and preserves complete alternative route groups.
The CLI can request deeper or larger neighborhoods for inspection. Both use the
same database reader; the tutor does not send the entire graph to the model.
The final installed scan checked all 8,794 questions. Every one of the 2,095
questions with routes retained at least one complete route at the default limits.
Five additional alternative groups were omitted within those limits, with their
omissions reported. A route recovery can omit supplementary relationship
summaries before giving up a complete method or its grading qualifications.

Mappings distinguish concepts the item assesses from optional methods and
definition-only context. A `non_diagnostic` item supplies its own answer relation;
its contextual nodes do not trigger prerequisite traversal or claims about the
learner's knowledge. A separately confirmed ambiguous or inconsistent source item
keeps its original text and key but is not automatically graded. A model's first
disagreement with a key alone does not trigger this behavior.

New custom-bank questions can be imported without graph references. Supplied
references are checked against the installed database; a user's assertion does
not acquire machine-review provenance just by naming an existing node. The four
custom examples installed during this build use the optional, ignored
`local/mappings.jsonl` overlay. Public source mappings cover the shipped CN and
AMC banks. A clean checkout builds without the private overlay; an installed
overlay is validated just as strictly as public mappings. Imported private banks
and their mappings are not automatically published with the app.

## Attribution

The initial 802 mathematics nodes and 1,299 proposed relationships come from
[cn-math-taxonomy](https://github.com/xiaoyang111222/cn-math-taxonomy), revision
`62b341d4b66b175413d6e3f697e37639fd96aa2d`, under
[CC BY-NC 4.0](../cn-math-bank/LICENSE). The source is AI generated and is not
teacher reviewed. The English labels are the application's existing translations.
Original descriptions and criteria are retained in Chinese where applicable.
Project additions and revisions have their own provenance in the source records.

AMC question-specific mappings and mathematical adaptations retain the applicable
[AMC CC BY-NC-SA 4.0 terms and attribution](../amc-bank/NOTICE.md). Other original
project material uses [CC BY-NC 4.0](../LICENSE). Neither source authors nor the
MAA are represented as endorsing this database. These records do not certify
official curriculum alignment.
