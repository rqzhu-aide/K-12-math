# Official-source explanations

Math Practice includes **200 reviewed explanations**, covering all 25 questions
in eight AMC papers. This expands the earlier six-question pilot by 194 solutions.
Each explanation connects the important deductions and explains how to recognize
the useful mathematical idea. The explanations work without models.

| Paper | Questions | Original MAA solution booklet |
| --- | ---: | --- |
| 2018 AMC 8 | 1-25 | [PDF](official-solutions/AMC8_2018_Solutions.pdf) |
| 2019 AMC 8 | 1-25 | [PDF](official-solutions/AMC8_2019_Solutions.pdf) |
| 2020 AMC 8 | 1-25 | [PDF](official-solutions/AMC8_2020_Solutions.pdf) |
| 2022 AMC 8 | 1-25 | [PDF](official-solutions/AMC8_2022_Solutions.pdf) |
| 2023 AMC 8 | 1-25 | [PDF](official-solutions/AMC8_2023_Solutions.pdf) |
| 2021 Spring AMC 10A | 1-25 | [PDF](official-solutions/AMC10A_2021_Spring_Solutions.pdf) |
| 2021 Fall AMC 10A | 1-25 | [PDF](official-solutions/AMC10A_2021_Fall_Solutions.pdf) |
| 2022 AMC 10A | 1-25 | [PDF](official-solutions/AMC10A_2022_Solutions.pdf) |

## Sources and changes

The booklets are distributed as retrieved. The 2023 AMC 8 and 2022 AMC 10A files were
obtained directly from MAA's website. The other six are MAA-authored booklets
obtained from mirrors. We inspected their covers, copyright and editorial
attributions, and complete worked solutions. Retrieval URLs and SHA-256 hashes
are recorded in [sources.json](sources.json). A retrieval hash identifies the
saved file; we do not have publisher-provided reference hashes for the mirrors.

Each question records its booklet, one-based PDF page, source URL, mathematical
method, modifications, and review status. Historical LIVE question and answer-key
transcription provenance remains separate from the source of the new explanation.
The UI opens the actual worked-solution page, including when the problem statement
starts on a preceding page.

The adaptations use original explanatory prose, expand difficult deductions, and
explain prerequisites where they are needed. Solution figures are cropped from
official pages or newly drawn by Math Practice; individual metadata records their
source and changes. No archived LIVE solution diagrams are reused.

The initial pilot corrected the 2023 AMC 8 Q17 prompt's shading description to
match the official diagram, replaced its diagrams with official crops, and
redrew the 2022 AMC 10A Q22 card row from the official question. The larger batch
preserves all question text, choices, and answer keys as they stood after that
pilot. It adds or revises explanations and source metadata.

## Mathematical and student-reasoning review

A different AI agent reviewed each author's explanations. Every one of the 200
records received separate judgments on mathematical correctness and whether a
student can follow the reasoning. Review covered the full argument, official
pages, answer agreement, necessary cases and assumptions, diagram interpretation,
method motivation, and prerequisite explanations. The lead inspected the findings
and checked selected arguments independently. An answer match alone was not the
acceptance criterion.

Review repairs included restoring a missing term in a displayed sum, explaining
an order-statistic bound, justifying a perimeter calculation, clarifying negative
congruence representatives, and making boundary cases explicit. Source-page links
were corrected when they initially pointed to the problem rather than its solution.

Selected independent finite checks included path counting, constrained colorings,
apple allocations, integer cube bounds, rectangle intersections, and the original
pilot's pairing and card-ordering arguments. Such checks support the corresponding
written arguments; they are not a formal verification of all 200 proofs.

All 200 reviewed drafts were preserved before comparison with archived LIVE
explanations. The [editorial experiment report](EXPLANATION_REVIEW.md) records what
that comparison revealed and how it informed the updated
[explanation style guide](../question-bank-template/EXPLANATION_STYLE.md).
After the initial drafts were frozen, the comparison informed original
refinements to teaching choices. Archived worked-solution sentences were not used
as a rewriting template, and their prose and solution-only diagrams are not
reproduced.

These are AI-assisted source and editorial reviews, not teacher certification or
evidence of student learning gains. Optional feedback models receive the stored
solution and instructions to recognize valid alternative methods; their live
tutoring behavior was not evaluated by this content experiment.

## Attribution and reuse

Original problems and official solutions: Mathematical Association of America
(MAA), American Mathematics Competitions. Explanatory adaptations and indicated
new illustrations: Math Practice. Distributed with permission under
[CC BY-NC-SA 4.0](LICENSE). Retain attribution, the license, and notices of changes.
These adaptations do not imply MAA endorsement. See [NOTICE.md](NOTICE.md).
