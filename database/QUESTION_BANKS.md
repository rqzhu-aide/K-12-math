# Ailleo question bank directory

Ailleo Question Bank 2.1.0 contains 18,789 questions from 9 sources. Grade ranges and counts describe the questions included in this release. [Practice online](https://math-practice.ailleo.net/) · [Bilingual directory and credits](https://math-practice.ailleo.net/dataset-acknowledgements.html)

## Available in Ailleo

| Source | Questions | Approximate coverage | Source terms |
|---|---:|---|---|
| [Chinese curriculum](https://github.com/xiaoyang111222/cn-math-taxonomy) | 3,355 | Grades 1 to 9 and required and elective high-school mathematics. | [CC BY-NC 4.0](https://math-practice.ailleo.net/dataset-acknowledgements.html#cn-math) |
| [AMC contests](https://maa.org/student-programs/amc/) | 5,435 | Middle- and high-school contests, including AMC 8, 10, 12 and their predecessors (1950 to 2026). | [CC BY-NC-SA 4.0 with MAA permission](https://math-practice.ailleo.net/dataset-acknowledgements.html#amc) |
| [GSM8K](https://github.com/openai/grade-school-math) | 8,766 | Elementary-level, multistep arithmetic word problems. | [MIT](https://math-practice.ailleo.net/dataset-acknowledgements.html#gsm8k) |
| [England KS2](https://www.gov.uk/government/collections/national-curriculum-assessments-past-test-materials#key-stage-2-past-papers-standard-materials) | 254 | Year 6 arithmetic and reasoning papers, 2024 to 2026. | [OGL v3.0](https://math-practice.ailleo.net/dataset-acknowledgements.html#ks2) |
| [U.S. NAEP](https://www.nationsreportcard.gov/nqt/) | 305 | Grades 4, 8 and 12, plus long-term trend assessments at ages 9, 13 and 17. | [U.S. public domain for selected items](https://math-practice.ailleo.net/dataset-acknowledgements.html#naep) |
| [Illustrative Mathematics® (first edition)](https://im.kendallhunt.com/) | 67 | Grade 3, grades 6 to 8, and high-school Algebra 1, Geometry and Algebra 2. | [CC BY 4.0](https://math-practice.ailleo.net/dataset-acknowledgements.html#im_first) |
| [Waterloo CEMC](https://cemc.uwaterloo.ca/resources/past-contests) | 338 | Gauss contests (grades 7 and 8) and selected Problems of the Week (grades 3 to 12). | [CC BY-NC 4.0 with free access required](https://math-practice.ailleo.net/dataset-acknowledgements.html#cemc) |
| [OATutor](https://github.com/CAHLR/OATutor-Content/tree/08ef4819889e70835e86926f84037e79141652f3) | 167 | Solid Foundations algebra (137) and trigonometry (30). | [CC BY 4.0](https://math-practice.ailleo.net/dataset-acknowledgements.html#oatutor) |
| [BCcampus Fundamental Mathematics](https://github.com/rqzhu-aide/K-12-math/tree/main/database/bccampus-bank) | 102 | Selected exercises from Books 4 and 5 on decimal place value, comparing decimals, common denominators and fraction arithmetic. The books teach adult foundational mathematics. | [CC BY 4.0 for the selected exercises](https://math-practice.ailleo.net/dataset-acknowledgements.html#bccampus) |

Source terms cover the original materials. Individual credits identify worked solutions, figures and adaptations. CC BY requires attribution, NC limits use to noncommercial purposes, and SA requires shared adaptations to carry the same or a compatible license.

## Sources under review

Source sizes as of November 27, 2026. These collections are under review for a future release. Each size uses the unit shown.

| Source | Source size | Approximate coverage | Source terms |
|---|---:|---|---|
| [Oak National Academy](https://open-api.thenational.academy/bulk-download) | About 12,900 quiz entries (estimate) | England, Years 1 to 6. Clocks, decimals, capacity and fractions. | OGL v3.0 for eligible content |
| [Original Eureka Math](https://greatminds.org/math/eurekamath/engageny/new-york) | 848 numbered entries in 5 workbooks | Selected modules for grades 2, 3, 5 and 6. Measurement, volume and statistics. | CC BY-NC-SA 4.0 for these workbooks |
| [Numbas](https://numbas.mathcentre.ac.uk/stats/) | 11,724 published templates across subjects | Multiple levels and subjects. The reviewed maths templates cover fractions and cylinder surface area. | Item-specific (CC BY 4.0 for the two reviewed templates) |
| [Siyavula Mathematics](https://www.siyavula.com/read) | 1,057 question groups (2,516 parts) | South African Grade 10 learner book. Algebra, geometry, measurement and other topics. | CC BY, unbranded edition |
| [Active Calculus](https://activecalculus.org/single2e/) | 496 section exercises + 186 activities | Single Variable, 2nd edition. Introductory calculus, including derivatives and optimization. | CC BY-SA 4.0 for the text. External exercises have separate terms. |
| [OpenIntro statistics](https://openintrostat.github.io/ims/) | 368 chapter exercises + 126 guided practices | Introduction to Modern Statistics, 2nd edition. Data exploration, prediction and inference. | CC BY-SA 3.0 for the text |
| [Levin, Discrete Mathematics](https://discrete.openmathbooks.org/dmoi3.html) | 473 exercises in the tagged 3rd edition | Introductory discrete mathematics, including induction, counting and graph theory. | CC BY-SA 4.0 for the 3rd edition |

## Updating the directory

For each new collection, record the included question count, coverage and original license in [the source inventory](question-bank-directory.json). Link the questions and their worked methods to the skills they assess or use. Regenerate the directory with `python scripts/render_question_directory.py` and compare it with the release using `python scripts/render_question_directory.py --check --build-info PATH/TO/build-info.json`.
