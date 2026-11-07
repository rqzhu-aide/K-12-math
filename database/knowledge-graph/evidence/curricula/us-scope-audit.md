# Independent audit of the 32 US coverage additions

**November 7, 2026.** Three Sol 6.1 reviewers at xhigh and three Claude Code Opus 5.5 reviewers at medium independently examined the early, middle and high school groups. Each model family reviewed the original 32 decisions, 27 new shared concepts, 34 US links and 48 mathematical connections. The reviewers compared the stated student performances with Common Core, Illustrative Mathematics tasks, the Progressions documents and the Chinese topic definitions and mastery criteria. The review packets also identify the relevant Marble taxonomy entries. [Early grades](us-gap-early.json) · [Middle grades](us-gap-middle.json) · [High school](us-gap-high.json)

## Corrections that affect practice and tutoring

| US standard | Student performance now used for line-plot practice |
|---|---|
| 2.MD.D.9 | Measure in whole units and plot one mark per observation. |
| 3.MD.B.4 | Measure lengths with half- or quarter-inch ruler markings and plot them on an appropriate scale. |
| 4.MD.B.4 | Plot fractional measurements and use the data to add or subtract, expressing values in common units. |
| 5.MD.B.2 | Plot fractional measurements and use grade 5 fraction operations, including equal redistribution. |

The old graph had two broad concepts serving all four standards. In a test with eight synthetic bindings, grade 2 practice returned a fractional-inch task and grade 4 returned a grade 5 division task. With the rebuilt graph, each standard returned its two intended bindings, one assessing the concept directly and one using it on a solution route. All eight selected tutor contexts matched the intended US standard. These cases were run in an isolated database. The installed bank still has zero directly linked practice questions for the original 32 standards. [Grade 4 tasks](https://tasks.illustrativemathematics.org/content-standards/4/MD/B/4) · [Grade 5 tasks](https://tasks.illustrativemathematics.org/content-standards/5/MD/B/2)

For the companion standard **5.NF.B.5b**, the earlier graph linked fraction equivalence through `cnm_p167`. We added the shared scaling concept, which explains how the size of a multiplier changes a positive quantity and why multiplying by one preserves value. The existing equivalence link supplied all 37 installed practice candidates both before and after the audit. For example, `1992_AMC_8_Q02` asks students to recognize equivalent forms of 5/4. Solving it gives evidence about equivalence alone. [Standard and example tasks](https://tasks.illustrativemathematics.org/content-standards/5/NF/B/5)

## Dependency decisions

The Chinese spring-model example in `cnm_199` uses an initial length plus an extension proportional to mass. It now provides optional preparation for constructing arithmetic combinations of functions. The coordinate-combination topic `cnm_h087` likewise helps with one route to the segment-division formula. These intersections are too narrow to route every general function-arithmetic or segment-division question into those native CN topics. [Pinned CN topics](../../source/curricula.json)

The supplementary-angle sine identity is required within the obtuse-angle altitude derivation of triangle area. Students using another method can still solve area questions. The growth-comparison criteria now ask for an observation from graphs or tables. The rationality proof now states the inverse and nonzero conditions needed for its subtraction and division steps. Early-grade corrections clarify whole-dollar or whole-cent calculations, reading clocks at five-minute intervals, and the area standard's printed page reference. [Common Core growth standard](https://www.thecorestandards.org/Math/Content/HSF/LE/) · [Triangle-area standard](https://www.thecorestandards.org/Math/Content/HSG/SRT/)

## Installed coverage

| Measure | Before audit | After audit |
|---|---:|---:|
| Shared concepts | 934 | 936 |
| Shared concepts with a US link | 519 | 521 |
| US standards and substandards linked | 480 / 480 | 480 / 480 |
| US standards classified as mapped / partial | 109 / 371 | 113 / 367 |
| US concept-to-standard links | 1,038 | 1,037 |
| Native CN topics linked | 802 / 802 | 802 / 802 |
| Accepted mathematical connections | 1,626 | 1,634 |

The four revised plot standards now each have an exact link. Replacing their six overlapping links with four precise links, and adding the scaling link, accounts for the net decrease of one US link. The 1,634 connections comprise 892 scoped requirements, 515 preparation links, 204 method components and 23 associations. [Curriculum manifest](../../curriculum-manifest.json)

The installed database passed validation for all 8,794 question bindings. The native inventories and connection directions matched the pinned source data for all 1,299 CN and 1,015 US connections. The combined directed graph of 1,407 accepted requirement and preparation edges had no cycles. A separate targeted mathematical review of 19 older requirements across 32 topics found no clear direction or necessity error within their stated scopes. The remaining historical edges received structural checks in this audit. The CN comparison uses the project's pinned repository, whose topic definitions are machine-authored. [CN source layer](../../source/curricula.json) · [US source layer](../../source/curricula.json)
