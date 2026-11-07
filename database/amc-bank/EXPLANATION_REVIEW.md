# What the 200-question explanation experiment changed

The comparison identified **13 explanations for refinement out of 200**. The
other 187 were retained at that stage. The useful changes concerned particular
reasoning steps, examples, diagrams, notation, and repeated prose. They did not
require a different tone throughout the bank.

The resulting [style guide](../../question-bank-template/EXPLANATION_STYLE.md)
encourages a calm mathematical partner: explain why a move helps, make the
difficult inference followable, and use encouragement through concrete support.
A longer explanation or a friendlier sentence is not automatically more useful.

## Scope and method

The batch contains 125 AMC 8 and 75 AMC 10 questions from eight complete papers,
including the six earlier pilot explanations and 194 newly written solutions.
Papers were selected for verified official-source availability. This is not a
random sample of AMC problems.

| Paper | Compared | Retained | Selected for refinement |
| --- | ---: | ---: | ---: |
| 2018 AMC 8 | 25 | 25 | 0 |
| 2019 AMC 8 | 25 | 24 | 1 |
| 2020 AMC 8 | 25 | 24 | 1 |
| 2022 AMC 8 | 25 | 23 | 2 |
| 2023 AMC 8 | 25 | 20 | 5 |
| 2021 Spring AMC 10A | 25 | 23 | 2 |
| 2021 Fall AMC 10A | 25 | 25 | 0 |
| 2022 AMC 10A | 25 | 23 | 2 |
| **Total** | **200** | **187** | **13** |

Authors used official MAA solutions and the prior style guide for the 194 new
solutions. They did not consult archived LIVE explanations during that initial
drafting phase. A different agent then checked each full solution, with separate
judgments for mathematics and student-facing reasoning. All 200 reviewed drafts
were preserved before the paired comparison. The guide and six pilot solutions already reflected an
earlier twelve-pair style study, so this was not a study of drafts with no prior
exposure to those general teaching ideas.

Reviewers read the matching frozen and archived written explanations and relevant
figures. They recorded a useful teaching choice, a concrete gap or tradeoff,
a tone observation, and a retain-or-revise decision for every question. Hashes
tie those observations to the actual versions read. Original drafts and review
records remain in local evidence. Archived worked-solution prose and
solution-only diagrams are not reproduced in this report or the bank.

The lead accepted all 13 recommendations, and authors implemented the
refinements in original prose with official-source or newly drawn figures.
Changed explanations received a further check by an agent other than the revision
author. Initial reviews and the versions used for comparison were preserved
separately.

## Concrete findings

| Finding | Changes in this batch | General authoring lesson |
| --- | --- | --- |
| A short example can expose a changing whole. | 2019 AMC 8 Q8 illustrates successive percentages with an imagined 100-marble starting amount. | Use an example to reveal what each operation acts on, then explain why the scaling is valid. |
| A visual transition can carry more meaning than another paragraph. | 2023 AMC 8 Q2 shows the intermediate unfolding; Q7 adds the completed line plot; Q17 labels the shared corners used in the folding proof. | Draw the state or label the feature needed for the next inference. Keep the proof that the picture supports. |
| A diagram's omissions need interpretation. | 2020 AMC 8 Q21 explains why some reachable squares are blank in the pruned path-count diagram. | Say what the figure includes and excludes. Blank does not always mean zero. |
| Convenient notation can remove irrelevant work. | 2022 AMC 8 Q22 uses nonnegative stop numbers; 2023 AMC 8 Q12 chooses a radius unit that gives integer area coefficients; 2021 Spring AMC 10A Q23 uses a defined state legend and first-arrival cases. | Simplify labels or scale while preserving the relationships and meaning of each case. |
| An asserted comparison or prerequisite can leave a gap. | 2022 AMC 8 Q15 shows the other candidate unit prices; 2021 Spring AMC 10A Q14 explains how the factored polynomial gives the sum and product of roots. | Show the decisive comparison or derive the rule at its first consequential use. |
| Organized counting still needs a completeness argument. | 2022 AMC 10A Q24 replaces a 42-string listing with a multiplicity table and bounded-choice derivations. | Separate case counts from arrangement counts and explain the nontrivial entries. Do not trade a long list for unexplained totals. |
| A closing strategy sentence can repeat what the solution already teaches. | 2023 AMC 8 Q1 and 2022 AMC 10A Q2 remove repeated closing advice. | Keep simple solutions brief. A takeaway is useful only when it adds a recognizable clue or action. |

Some archived explanations offered a useful concrete example, a clearer visual
sequence, or more economical labels. The new explanations often made assumptions,
case coverage, bounds, and the reason for a method more explicit. Neither source
was treated as uniformly better. We retained complete arguments even when an
alternative presentation looked shorter or more elegant.

The tone observations were about the words on the page. Both collections often
used calm, direct explanations. This comparison does not establish how students
felt while reading them, and it makes no claim about LIVE videos or tutoring.

## Quality checks and limits

The initial independent reviews found and repaired mathematical or explanatory
gaps before the comparison, including a missing term in a displayed sum and
compressed justifications for bounds and boundary cases. A subsequent audit also
corrected six inaccurate descriptions in one reviewer's notes. The actual
solutions were reread against the official arguments; those note corrections
did not change their mathematics. Review records themselves need checking.

Browser inspection found a separate display issue in the 2021 Fall AMC 10A Q24
cube illustration: a viewBox-only SVG loaded but displayed at zero size. Explicit
dimensions and a standalone figure paragraph repaired it without changing the
diagram's geometry or the UI design. This is additional to the 13 editorial
recommendations above.

Validation distinguishes full written argument review, selected independent
computational checks, all-record LaTeX and source-reference checks, and sampled
browser inspection. Parsing mathematics or matching an answer key does not prove
an argument. Optional tutoring models and actual student comprehension were not
tested in this experiment.

The final checks matched all 200 solution hashes to their reviews, parsed 2,593
math fragments without errors, and verified files and attribution for 33 solution
figures. The 39 frontend, 21 bank/server, and 9 distribution tests passed. Actual
UI checks sampled 12 questions across the eight papers; final-version checks
covered the revised counting table, unfolding stages, annotated net, completed
line plot, and repaired cube figure. Phone-width checks found no horizontal
overflow in the inspected solutions. These samples do not establish that every
possible display size or every solution view has been visually tested.

This is a known-source, AI-assisted editorial experiment. It was not blinded,
randomized, or conducted with students, and the reviewers participated in other
parts of the authoring workflow. The counts describe editorial decisions, not
measured gains in learning or confidence. A later learner study should ask students
to explain the key inference and solve a related problem, then record their
actual reasoning and performance.

See [coverage, source provenance, and attribution](ADAPTATIONS.md). AMC problems,
official solutions, and these adaptations remain under [CC BY-NC-SA 4.0](LICENSE).
