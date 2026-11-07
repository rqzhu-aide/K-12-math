# Explanations that help a student reason

Write for a curious, capable young mathematician. A worked solution should help
the reader understand why the method fits, follow the important deductions, and
recognize a useful idea in a new problem. A correct answer and a friendly voice
are not enough if the decisive step remains unexplained.

This is an authoring guide for stored solutions and future teaching work. It
does not change the application's feedback prompts or add a hint feature.

## Choose the explanation to fit the obstacle

| What makes the problem difficult? | A useful way to explain it |
| --- | --- |
| Applying a familiar rule accurately | Name the rule, show the relevant operations, and keep the explanation short. |
| Finding a productive first move | Connect a clue in the question to the choice of method. Explain what the choice makes easier. |
| Understanding an abstract construction | Work through one small example, identify what the example reveals, then justify the general argument. An example illustrates a proof; it does not replace one. |
| Visualizing a diagram or a fold | Name the points, edges, or faces to track. Explain which connections remain true and how they support the next deduction. |
| Choosing an algebraic manipulation | State what we want to eliminate or reveal. Show the decisive expansion or cancellation once, with its meaning. |
| Counting without omission or duplication | Explain why every valid object is included, why it is counted once, and what each exception removes. |

These are flexible approaches, not mandatory sections for every solution. An
arithmetic question may need only a few connected sentences. A difficult counting
argument may need a small example and a longer justification. Add words where a
reader would otherwise have to guess the reason.

## Keep alternative methods within reach

Consider whether the problem admits genuinely different methods, using the
question and each complete solution to identify the knowledge they need. Include
an alternative when it offers a useful new way to reason without requiring more
advanced knowledge than the main method. Explain necessary prerequisites where
they are used. Do not count a rearranged calculation as a distinct method or add
an advanced shortcut merely to increase the method count.

In question format 3.0, store each method as a separate object in `solutions`,
with a useful `title`, its own `explanation`, and any known `directNodeIds` and
`sourceRef`. For an older 2.0 record, keep the methods in `Solution` prose with
clear labels and blank lines between sections. Use ordinary text, supported
LaTeX, and the existing figure notation. Each method must justify the answer
independently. Graph annotations should reflect the question and the actual
completed methods, with method-local knowledge kept in separate alternative
routes rather than merged into a single required checklist.

## Make the reasoning discoverable

Open with a useful observation or plan. Connect it to the problem: equal spacing
suggests counting gaps; symmetry suggests paired coordinates; a fixed internal
order suggests choosing positions. Naming a technique alone does not explain
why it is useful here.

At each important transition, connect what is known, what it allows us to do,
and why that helps. Define symbols when they first matter. Explain the conditions
of a theorem before relying on it. For an unfamiliar manipulation, show enough
working to teach the move, then use that pattern without repeating every detail.

Explain an unfamiliar rule where it first carries the argument. For example,
before reading a sum of roots from a polynomial coefficient, show how choosing
one constant term from its linear factors produces that coefficient. Naming
the rule or repeating the resulting equation leaves the same gap.

Choose units and labels that simplify the actual reasoning. If only an area
ratio matters, a convenient radius can be the unit of length, provided the
explanation says why a common scale cancels. Numbering a journey from its starting
stop may avoid unnecessary negative labels. Simplification must preserve the
given relationships, not introduce a special case.

Use a concrete example when it exposes a changing quantity or a hidden step.
An imagined 100-object collection can make successive percentages visible,
but explain why scaling the original collection does not change the percentage.
Keep the general reasoning beside the example. Do not add an illustration that
merely repeats arithmetic already clear to the reader.

Keep one well-explained main route. Offer another method only when it supplies a
distinct insight or a more accessible prerequisite path. A collection of short
proofs can leave a learner with the same unanswered question several times.

Use a check that tests something relevant: substitute into the original ranges,
trace an example through the rule, or compare a ratio with the stated geometry.
Say when a check establishes only plausibility. Do not add a checking paragraph
when it merely repeats the answer.

When a closing connection helps, identify the clue to notice and the action it
suggests. Omit it when it repeats an opening observation already fully explained,
especially in a short arithmetic solution. “Try a clever substitution” gives
little help. “When two
distance equations share the same vertical term, subtracting them removes that
term” identifies a move and when to try it.

## Make counts, comparisons, and diagrams inspectable

A claim that one candidate is best needs the decisive comparisons. If a graph
eliminates most candidates, explain that elimination and show the remaining
ratios or bounds. Distinguish coordinates read approximately from a plot from
exact values given in the question.

For a finite count, group cases by a property that makes the restrictions easier
to apply. A compact table can keep the count and the number of arrangements
separate. Explain how the nontrivial table entries are obtained, why the groups
exhaust the possibilities, and why no object belongs to two groups. Replacing
a long list with unexplained totals is not an improvement. A structural method
also needs its correspondence justified; elegance alone does not make it easier
to learn.

A diagram should support a particular inference. Show an intermediate unfolding
when the reader must track two reflections. Label the shared corner that a fold
preserves, or plot the lines whose contact with a region is being counted. State
what a diagram omits: in a path-count figure, a blank cell may be omitted because
it cannot reach the target, rather than because no path can reach it. Keep the
argument that establishes the result; a plausible picture cannot establish
uniqueness, exhaust all cases, or justify an unmarked equality.

## Sound like a thoughtful mathematical partner

Use calm, direct language. Acknowledge a real obstacle by making it manageable:
explain which part to track, what can stay unknown, or why a smaller example
helps. Warmth comes from helping the reader make progress, without constant
praise or treating difficulty as a personal failing.

Do not describe a crucial unfamiliar step as obvious or trivial. Do not claim
to know how the learner feels. In a stored solution, describe possible mistakes
conditionally. In feedback on an actual attempt, credit a specific valid idea,
locate the first unsupported step, and suggest a useful next move. A different
valid method deserves credit even when it differs from the reference solution.

For progressive hints, reveal one useful observation before a decisive step,
and reserve the complete argument for the solution. Keep these different reading
purposes separate. The full solution should still make sense on its own when
opened after an attempt.

## Review mathematical and explanatory sufficiency separately

A reviewer should check both the proof and the reading experience:

- Is the argument correct, including assumptions, cases, figures, and the answer?
- Can the learner see why this method was chosen, rather than only verify its calculations?
- Does each difficult transition have a reason, with necessary prerequisites explained at the point of use?
- Does a diagram or example clarify a specific step without introducing an extra assumption?
- If there is a final takeaway, does it add a useful clue and action without repeating the opening?
- Could any passage be removed without losing reasoning, orientation, or a meaningful check?

Inspect the rendered solution as well as its source text. Use the existing
supported LaTeX and figure notation described in [README.md](README.md).
Longer equations must remain readable on a narrow screen.
Keep figure references in their own paragraphs. Give original SVGs explicit
width and height as well as a viewBox, and check their visible size in the actual
solution dialog. A file that loads successfully may still display at zero size.

An author or AI review can identify likely reading obstacles. It cannot establish
that students understood the explanation. A useful later learner check is to ask
the student to explain the key step in their own words and try a related problem;
record what they actually do rather than inferring learning from tone.

## Sources and original writing

Use authorized mathematical sources and record the source, page, changes, and
review status. Draft in original language from the problem and verified argument.
Do not use a third-party explanation as a sentence-by-sentence rewriting template.
Keep mathematical attribution separate from a study of general teaching style.

The first version drew on twelve selected official/archived explanation pairs.
The next editorial experiment applied that guide to 200 questions across eight
complete papers: the six earlier pilot explanations and 194 newly written drafts
from official MAA solutions. All 200 received independent mathematical
and student-reasoning review and were preserved before comparison with matching
archived LIVE explanations.

The comparison informed the advice above on examples, notation, visual transitions,
comparison evidence, counting organization, and unnecessary closing prose. Both
collections include useful teaching choices; a conversational voice is not itself
evidence of a complete argument. These are observations from a known-source,
AI-assisted editorial comparison, not findings about students' comprehension,
feelings, preferences, or learning gains.

See the [experiment and concrete revisions](../database/amc-bank/EXPLANATION_REVIEW.md)
and [official-source coverage](../database/amc-bank/ADAPTATIONS.md). The AMC adaptations
remain under the license and attribution stated there. This guide changes
authoring advice, not the application's model prompts or feedback behavior.
