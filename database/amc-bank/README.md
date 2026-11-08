# AMC practice bank 2.1.0

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

[Download the 3,978 questions with worked solutions, their figures, and their source credits](https://github.com/rqzhu-aide/K-12-math/releases/download/amc-bank-v2.1.0/amc-bank-2.1.0-compact-3978.zip).

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

The other questions retain their original keys and transcription credits. Where
a new worked explanation has been added, its source is **Original Math Practice
solution**. Its review record binds the explanation to the displayed question
and figures. A separate AI review checks the mathematics, level and method
annotations. These explanations have not been teacher reviewed. Only the 200
official-source adaptations above carry an `OfficialSolution` PDF reference.
**Copied LIVE by Po-Shen Loh worked solutions and 119 solution-only diagrams are
not included.**

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

The 3,978 questions with stored worked solutions use the [compact 3.0 schema](../../question-bank-template/question-v3.schema.json). Their question and method credits are in [source-index.json](source-index.json). The other 1,457 questions use [schema 2.0](schema.json) and have answer keys. The original prompts, choices,
LaTeX, figure positions, and reviewed grading metadata are preserved. Domain
and skill catalogs are in `taxonomy/`; older records with uncurated topics remain
explicitly unclassified. Structural validation does not constitute a proof
audit of every problem or answer key.

Of the 5,435 questions, 3,978 have stored worked solutions. These comprise 200 adaptations of official MAA solutions and 3,778 additional questions with project-authored explanations. All 65 papers from 1950 through 1999 have a worked solution for every question. All 5,435 questions have answer keys and graph annotations. Open the [Math Practice UI](../../math-practice/) to use the bundled browser data. To prepare an additional collection, see the [question-bank template](../../question-bank-template/).

See [NOTICE.md](NOTICE.md) for attribution, modifications, and license scope.
