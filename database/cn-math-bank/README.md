# Processed Chinese curriculum bank 1.0.0

This distribution includes 3,355 English question records and their worked
solutions. Each `questions/*.json` record preserves its Chinese source under
`Meta.Original`. The browser uses the included `bank.js`; no rebuild or model
call is needed to begin practice.

`figures/` contains 156 English display diagrams and 156 original Chinese
diagrams. `taxonomy/` and `schema/` describe topic labels and the record format.
The local backend reads `questions/` for reference answers and deeper review.

This is a processed snapshot. Raw upstream checkouts, translation tools, and
processing reports are not included. The pinned upstream revision and each
record's source and modification metadata preserve provenance. Some metadata
paths name processing-side records from the original workspace; they are
historical references, not runtime dependencies or files in this distribution.

The source and translations are AI-generated and not teacher reviewed.
See [attribution and modifications](NOTICE.md) and the [license](LICENSE).
