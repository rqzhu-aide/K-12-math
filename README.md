# K-12-Math knowledge graph, questions and practice UI

[![Knowledge graph 1.0.0](https://img.shields.io/badge/Knowledge_graph-1.0.0-245984)](https://github.com/rqzhu-aide/K-12-math/blob/main/database/knowledge-graph/source/metadata.json)
[![Question Bank 2.0.0](https://img.shields.io/badge/Question_Bank-2.0.0-427354)](https://github.com/rqzhu-aide/K-12-math/releases/tag/ailleo-question-bank-v2.0.0)
[![Online Math Practice 2.3.3](https://img.shields.io/badge/Online_Math_Practice-2.3.3-625395)](https://math-practice.ailleo.net/build-info.json)

**Ailleo Question Bank 2.0.0** brings together **18,687 questions from eight sources**, each with a worked solution. [Practice free online](https://math-practice.ailleo.net/) · [Browse the question bank directory](database/QUESTION_BANKS.md) · [Download the full question bank (ZIP)](https://github.com/rqzhu-aide/K-12-math/releases/download/ailleo-question-bank-v2.0.0/ailleo-question-bank-2.0.0.zip)

The Ailleo knowledge graph connects 936 mathematical concepts. Students can follow the Chinese curriculum, browse US Common Core standards, or explore a mathematical idea across grade levels. A question can assess several concepts, and different solutions can use different skills.

## What’s in the repository

| Component | Version | Contents |
|---|---|---|
| [Mathematics knowledge graph](https://github.com/rqzhu-aide/K-12-math/tree/main/database/knowledge-graph) | 1.0.0 | Connects 936 concepts through 1,634 accepted relationships and links questions to the concepts they assess or use in a solution. |
| [Ailleo Question Bank](#question-counts) | 2.0.0 | Includes all eight sources, their worked solutions, figures and credits. |
| [Math Practice desktop edition on `main`](math-practice/README.md#run-locally) | [2.2.0](https://github.com/rqzhu-aide/K-12-math/blob/main/math-practice/VERSION) | Runs locally with 8,790 Chinese curriculum and AMC questions. You can also import your own bank. |

## Question counts

See the question counts and coverage for all eight collections. [Question bank directory](database/QUESTION_BANKS.md) · [Bilingual directory, source credits and licenses](https://math-practice.ailleo.net/dataset-acknowledgements.html)

Question and solution credits identify the original source and any Ailleo-authored explanation or arithmetic correction. The six newer collections include 9,916 worked methods for 9,897 questions.

### Chinese curriculum and AMC breakdown

These two banks contain 8,790 questions with graph annotations. Each appearance of a problem on a separate AMC paper counts as one entry.

| CN curriculum | Questions | AMC contest family | Questions |
|---|---:|---|---:|
| Primary | 864 | AMC 8 / AJHSME | 1,025 |
| Middle school | 1,407 | AMC 10 | 1,300 |
| High school, required | 572 | Modern AMC 12 | 1,300 |
| High school, elective | 512 | Historical high school, 1950 to 1999 | 1,810 |
| **CN total** | **3,355** | **AMC total** | **5,435** |

For 8,780 questions, the annotation identifies an assessed concept or a solution route. The other ten link to definitions for context. The banks contain 9,780 written methods, and 977 questions have more than one. Of the AMC questions, 608 include an adaptation of an official MAA solution. The question banks identify the sources of their explanations.

## Practice with the collection

The [Math Practice guide](math-practice/README.md) explains how to find and solve problems, connect optional online services, or run the desktop app.

## Further development and custom question banks

The Chinese curriculum and AMC questions use the compact English format in [question-bank template 1.0.0](https://github.com/rqzhu-aide/K-12-math/tree/main/question-bank-template). The template includes an importable example.

## License and sources

The project’s original **mathematics knowledge graph is licensed under [CC BY-NC 4.0](database/knowledge-graph/LICENSE)**. This covers its original concept definitions, relationship and alignment decisions, and the selection and arrangement of the graph. The same [project license](LICENSE) covers the original UI and template. Incorporated materials keep their source terms. [Graph license scope](database/knowledge-graph/NOTICE.md)

The [Chinese mathematics taxonomy](https://github.com/xiaoyang111222/cn-math-taxonomy) supplies the CN questions and the initial graph. AMC questions, included official booklets, and their adaptations are credited to the [Mathematical Association of America](https://maa.org/student-programs/amc/) and distributed under [CC BY-NC-SA 4.0](database/amc-bank/NOTICE.md). The AMC bank credits [LIVE by Po-Shen Loh](https://live.poshenloh.com/past-contests) for transcription.

The US map uses the [Common Core State Standards for Mathematics](https://www.thecorestandards.org/Math/) and [Student Achievement Partners’ Coherence Map](https://tools.achievethecore.org/coherence-map/). The graph review also consulted [Illustrative Mathematics](https://tasks.illustrativemathematics.org/), the [Common Core mathematics Progressions](https://archive.math.arizona.edu/ime/progressions/), and [Marble’s open skill taxonomy](https://github.com/withmarbleapp/os-taxonomy). See the [source credits and license terms](THIRD_PARTY_NOTICES.md) for attribution by component.
