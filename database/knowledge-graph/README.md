# Mathematics knowledge graph 1.0.0

The project's original graph is licensed under [Creative Commons Attribution-NonCommercial 4.0 International](LICENSE). See the [graph notice](NOTICE.md) for attribution and the terms of incorporated materials.

The graph connects **936 knowledge items** across 1,634 accepted mathematical relationships. The [Chinese question bank](../cn-math-bank/) and [AMC bank](../amc-bank/) supply 8,790 questions. Each has an annotation bound to its displayed prompt, answer requirements and figures. For 8,780 questions the annotation identifies an assessed concept or a solution route. Ten questions supply definitions for context.

| Practice path | What a student can browse |
|---|---|
| **ailleo** | The 936 shared mathematical ideas and their immediate connections, independent of grade placement. |
| **CN** | 802 Chinese mathematics topics and 1,299 connections from the pinned Chinese taxonomy. Its high school placement refers to textbook volumes. |
| **US** | 480 Common Core standards and substandards and 1,015 connections. All 480 link to shared concepts, with 113 classified as mapped and 367 as partial. |

A question can assess more than one concept. Each known solution route lists its immediate mathematical ingredients, so a student who uses another valid route can still receive credit. For example, a student can count the chords between six points by summing 5 + 4 + 3 + 2 + 1, or by choosing pairs of endpoints. Only the second route uses combinations. A link to a curriculum standard describes the scope of the content. Solving one question does not establish mastery of the whole standard.

## Search and inspect

| Source file | Contents |
|---|---|
| [nodes.json](source/nodes.json) | Stable concept IDs, names, descriptions, and observable learning criteria. |
| [relationships.json](source/relationships.json) | Connections between concepts, their direction, scope, rationale and review status. There are 892 accepted requirements, 515 preparation links, 204 method components, and 23 associations. |
| [curricula.json](source/curricula.json) | Separate CN and US inventories, placements, and native connections. |
| [alignments.json](source/alignments.json) | Links between a shared concept and a native curriculum entry, with exact, narrower, broader or partial scope. |
| [mappings.jsonl](source/mappings.jsonl) | One record per public question, with its content binding, assessed ideas, alternative routes and review history. |
| [metadata.json](source/metadata.json) | Graph version and provenance. Historical source receipts identify their original inputs. |

For a compact question, each worked method can list the concepts it uses directly in `directNodeIds`. The graph also retains the background associated with each reviewed learning route. Within a route, `methodDirectNodeIds` identifies the immediate concepts for each linked method and `contextNodeIds` records the remaining background. This lets students find a problem through a useful preparation topic while the tutor can still see which concepts the particular solution uses.

The [curriculum manifest](curriculum-manifest.json) records the original and reviewed alignments. The [independent audit](evidence/curricula/us-scope-audit.md) explains the most recent corrections. The release includes the solution and annotation records cited by the shipped questions under `evidence/`. Historical references beginning with `knowledge-graph/`, `amc-bank/` or `cn-math-bank/` use `database/` as their base. Construction inputs referenced by their historical hashes are kept in the development workspace.

Math Practice builds a searchable SQLite database on first launch. From the repository root, you can also build, validate and inspect a question yourself.

```sh
python math-practice/runtime/knowledge_graph.py build
python math-practice/runtime/knowledge_graph.py validate
python math-practice/runtime/knowledge_graph.py extract cnm_225_q4 --json
```

The public edition retains the 1.0.0 node IDs, relationships, placements and alignments. It omits auxiliary US course-classification flags. Common Core text and Coherence Map learning connections have separate rights notices. See [source credits and licenses](../../THIRD_PARTY_NOTICES.md).
