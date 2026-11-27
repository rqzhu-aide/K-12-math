# K-12-Math knowledge graph, questions and practice UI

[![Knowledge graph 1.0.0](https://img.shields.io/badge/Knowledge_graph-1.0.0-245984)](https://github.com/rqzhu-aide/K-12-math/blob/main/database/knowledge-graph/source/metadata.json)
[![Question Bank 2.0.0](https://img.shields.io/badge/Question_Bank-2.0.0-427354)](https://github.com/rqzhu-aide/K-12-math/releases/tag/ailleo-question-bank-v2.0.0)
[![Online Math Practice 2.3.3](https://img.shields.io/badge/Online_Math_Practice-2.3.3-625395)](https://math-practice.ailleo.net/build-info.json)

**Ailleo Question Bank 2.0.0** brings together **18,687 questions from eight sources**, each with a worked solution. Practice is free in a browser, or you can download the whole bank as one ZIP. [Open Math Practice](https://math-practice.ailleo.net/) · [Download the question bank](https://github.com/rqzhu-aide/K-12-math/releases/download/ailleo-question-bank-v2.0.0/ailleo-question-bank-2.0.0.zip)

The Ailleo knowledge graph connects 936 mathematical concepts. Students can follow the Chinese curriculum, browse US Common Core standards, or explore a mathematical idea across grade levels. A question can assess several concepts, and different solutions can use different skills.

## What’s in the repository

| Component | Version | Contents |
|---|---|---|
| [Mathematics knowledge graph](https://github.com/rqzhu-aide/K-12-math/tree/main/database/knowledge-graph) | 1.0.0 | Connects 936 concepts through 1,634 accepted relationships and links questions to the concepts they assess or use in a solution. |
| [Ailleo Question Bank](#question-counts) | 2.0.0 | Includes all eight sources, their worked solutions, figures and credits. |
| [Math Practice desktop edition](math-practice/README.md#run-locally) | [2.2.0](https://github.com/rqzhu-aide/K-12-math/blob/main/math-practice/VERSION) | Includes 8,790 Chinese curriculum and AMC questions and can import your own questions. |

## Question counts

Open **Browse → By source → Question bank**. Chinese curriculum, AMC and GSM8K appear directly. Select **Other** to choose one of the remaining five collections under **Question repository**.

| Online collection | Selectable questions |
|---|---:|
| Chinese curriculum (English) | 3,355 |
| AMC contests | 5,435 |
| GSM8K | 8,766 |
| England KS2 | 254 |
| U.S. NAEP | 305 |
| Illustrative Mathematics, first edition | 67 |
| University of Waterloo CEMC | 338 |
| OATutor | 167 |
| **Total** | **18,687** |

Question and solution credits identify the original source and any Ailleo-authored explanation or arithmetic correction. The six newer collections include 9,916 worked methods for 9,897 questions. The acknowledgements page lists each publisher and its terms. [Dataset acknowledgements](https://math-practice.ailleo.net/dataset-acknowledgements.html)

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

**Online practice.** Choose **Try a problem**, or choose **Browse → By topic** to follow a concept. Use **Submit answer** to check an answer where automatic grading is available. **Explore solution** opens the worked methods at any time.

For hints on your reasoning, connect your own API under **Settings → Math Tutor LLM**. The optional **Ailleo Math Practice Service** provides voice transcription and sentiment feedback with one consent setting. After a scored Chinese curriculum or AMC submission, **Suggest my next problem** can recommend a follow-up. [Online setup and data use](math-practice/README.md#connect-your-tutor-online)

**Local practice.** For offline access, voice transcription, or AI feedback using your own model connections, download and extract the repository ZIP and install Python 3.11 or newer. On Windows, double-click **Start Math Practice.cmd** in the extracted folder. On macOS or Linux, run `python3 math-practice/runtime/serve_math_practice.py` from that folder. [Download ZIP](https://github.com/rqzhu-aide/K-12-math/archive/refs/heads/main.zip) · [Local setup instructions](math-practice/README.md#run-locally)

| 1. Practice a question | 2. Choose the model for each task |
|:---:|:---:|
| [![Question page with the problem, answer controls, and space to explain the solution](https://math-practice.ailleo.net/images/question-page.png)](https://math-practice.ailleo.net/images/question-page.png) | [![API connection settings showing math reasoning and feedback, voice to text, and sentiment analysis](https://math-practice.ailleo.net/images/model-settings.png)](https://math-practice.ailleo.net/images/model-settings.png) |

In the local edition, students can record their reasoning, edit the transcript, and submit it with their answer. In **Settings → Connection settings**, each of three optional roles can use its own provider. For example, use an OpenAI account for math and local models for the other two.

- **Math reasoning and feedback** checks the submitted answer and explanation together. If either has a problem, the tutor explains where and can offer a hint.
- **Voice to text** transcribes the recording into a draft the student can edit.
- **Sentiment analysis** reads the original transcript for expressed confidence, engagement, and how clearly the student explained their reasoning. It does not grade the math or analyze vocal tone.

See [UI and model setup](math-practice/README.md#optional-ai-connections) for supported APIs and local model settings.

## Further development and custom question banks

The 8,790 Chinese curriculum and AMC questions use the compact English format published in [question-bank template 1.0.0](https://github.com/rqzhu-aide/K-12-math/tree/main/question-bank-template). It records the prompt, choices, accepted answers, classification, sources, and the immediate knowledge nodes for each solution method. To use your own bank, prepare its questions in this format and import the folder into Math Practice. The template includes an importable example and the commands to check it.

Every stored AMC question has a worked solution. The earlier release notes document the final 236 AMC 12 explanations and their source credits. [AMC collection history](https://github.com/rqzhu-aide/K-12-math/releases/tag/amc-bank-v2.7.0)

## License and sources

The project’s original **mathematics knowledge graph is licensed under [CC BY-NC 4.0](database/knowledge-graph/LICENSE)**. This covers its original concept definitions, relationship and alignment decisions, and the selection and arrangement of the graph. The same [project license](LICENSE) covers the original UI and template. Incorporated materials keep their source terms. [Graph license scope](database/knowledge-graph/NOTICE.md)

The [Chinese mathematics taxonomy](https://github.com/xiaoyang111222/cn-math-taxonomy) supplies the CN questions and the initial graph. AMC questions, included official booklets, and their adaptations are credited to the [Mathematical Association of America](https://maa.org/student-programs/amc/) and distributed under [CC BY-NC-SA 4.0](database/amc-bank/NOTICE.md). The AMC bank credits [LIVE by Po-Shen Loh](https://live.poshenloh.com/past-contests) for transcription.

The US map uses the [Common Core State Standards for Mathematics](https://www.thecorestandards.org/Math/) and [Student Achievement Partners’ Coherence Map](https://tools.achievethecore.org/coherence-map/). The graph review also consulted [Illustrative Mathematics](https://tasks.illustrativemathematics.org/), the [Common Core mathematics Progressions](https://archive.math.arizona.edu/ime/progressions/), and [Marble’s open skill taxonomy](https://github.com/withmarbleapp/os-taxonomy). See the [source credits and license terms](THIRD_PARTY_NOTICES.md) for attribution by component.
