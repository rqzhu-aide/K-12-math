# Processed Chinese curriculum bank 2.0.0

All 3,355 English questions and their worked solutions use the [compact 3.0 question schema](../../question-bank-template/question-v3.schema.json). Each question has a `sourceRef` in the [bank source index](source-index.json). Its entry preserves the original Chinese question and explanation under `meta.Original`. Each solution method also identifies its source. The browser reads the included `bank.js` for offline practice.

`figures/` contains 156 English display diagrams and 156 original Chinese
diagrams. `taxonomy/` describes the topic labels. `schema/` documents the earlier 2.0 record format.
The local backend reads `questions/` for reference answers and deeper review.

This is a processed snapshot. Raw upstream checkouts, translation tools, and
processing reports are not included. The pinned upstream revision and each
record's source and modification metadata preserve provenance. Some metadata
paths name processing-side records from the original workspace; they are
historical references, not runtime dependencies or files in this distribution.

The source and translations are AI-generated and not teacher reviewed.
See [attribution and modifications](NOTICE.md) and the [license](LICENSE).
