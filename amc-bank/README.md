# AMC practice bank

**5,435 questions and answer keys from 195 papers**, with question and choice
diagrams. American Mathematics Competitions (AMC) content is credited to the
[Mathematical Association of America (MAA)](https://maa.org/student-programs/amc/)
and distributed with permission under **[CC BY-NC-SA 4.0](LICENSE)**.

| Archive family | Years represented | Papers | Questions |
| --- | --- | ---: | ---: |
| AMC 8 / AJHSME | 1985-2026 | 41 | 1,025 |
| AMC 10 | 2000-2025 | 52 | 1,300 |
| AMC 12 / AHSME | 1950-2025 | 102 | 3,110 |

This is the complete currently processed collection in this project, not a claim
to include every MAA competition. Historical high-school papers have between
25 and 50 questions. The 2021 high-school editions include regular and Fall
papers. Historical series names remain in record metadata.

## Questions and solutions

Choose **AMC contests** in Math Practice, then a level, year, batch, and problem.
Answer checking works without models. Disputed questions retain their historical
choices and key but are not automatically graded; the UI explains the dispute.

Eight **official MAA solution booklets** are included as retrieved. All 25 questions
in each paper also have a reviewed, learner-facing adaptation:

| Paper | Original official booklet |
| --- | --- |
| 2018 AMC 8 | [Solutions](official-solutions/AMC8_2018_Solutions.pdf) |
| 2019 AMC 8 | [Solutions](official-solutions/AMC8_2019_Solutions.pdf) |
| 2020 AMC 8 | [Solutions](official-solutions/AMC8_2020_Solutions.pdf) |
| 2022 AMC 8 | [Solutions](official-solutions/AMC8_2022_Solutions.pdf) |
| 2023 AMC 8 | [Solutions](official-solutions/AMC8_2023_Solutions.pdf) |
| 2021 Spring AMC 10A | [Solutions](official-solutions/AMC10A_2021_Spring_Solutions.pdf) |
| 2021 Fall AMC 10A | [Solutions](official-solutions/AMC10A_2021_Fall_Solutions.pdf) |
| 2022 AMC 10A | [Solutions](official-solutions/AMC10A_2022_Solutions.pdf) |

The **200 explanations** work without models and supply reference text to optional
feedback models. Matching questions also link to the worked solution's first page
in its booklet. Each PDF preserves MAA's mathematics, diagrams, authorship, and
copyright notices. Six booklets were obtained from mirrors of the MAA originals;
the source checks and retrieval hashes are documented in [sources.json](sources.json).
See [adaptation sources and review scope](ADAPTATIONS.md).

The other questions include answer keys and retain source provenance in metadata.
**Copied LIVE by Po-Shen Loh worked solutions and 119 solution-only diagrams are
not included.** The `Solution` field is empty for the other 5,235 questions;
all 200 questions above carry an `OfficialSolution` PDF reference.
Do not label LIVE explanations as official MAA solutions. Chinese and custom
banks retain their own included worked solutions.

Copied explanations, old source captures, and their import tools have been
retired to a private archive outside this repository. The adaptations were drafted
from official sources and independently reviewed before a separate comparison
studied teaching choices in the archived explanations and informed original
refinements. Archived worked-solution prose and solution-only diagrams are not
reproduced. Historical transcription credits remain because
the original question text and answer keys were obtained through that archive.

## Provenance and format

Question transcriptions and answer-key provenance come from
[LIVE by Po-Shen Loh's past-contest archive](https://live.poshenloh.com/past-contests).
This source credit is separate from MAA's permission to share the AMC content.
Three retained original question illustrations have their earlier AoPS source
URLs recorded. Per-question metadata preserves source URLs and hashes, reviewed
corrections, figure provenance, and historical series names. Raw website pages,
third-party solution text, private processing files, and local paths are not
included. [sources.json](sources.json) lists historical source URLs and hashes
and the official solution booklets as retrieved.

Records use [schema version 2.0](schema.json). The original prompts, choices,
LaTeX, figure positions, and reviewed grading metadata are preserved. Domain
and skill catalogs are in `taxonomy/`; older records with uncurated topics remain
explicitly unclassified. Structural validation does not constitute a proof
audit of every problem or answer key.

To rebuild the bundled browser data after editing published JSON records:

```sh
python scripts/export_amc_bank.py
```

Run that command from the repository root. It needs only Python's standard
library and files already in this repository. The exporter refuses nonempty
solutions unless they are marked as reviewed adaptations with an official MAA
reference. A status marker is bookkeeping, not a substitute for the review.

See [NOTICE.md](NOTICE.md) for attribution, modifications, and license scope.
