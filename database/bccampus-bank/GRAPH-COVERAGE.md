# BCcampus graph coverage

Books 4 and 5 add direct practice for decimal meaning and rewriting fractions with a common denominator using existing canonical concepts. The broader series also exposes distinct gaps, especially unit rates, metric prefix conversions across measurement types, and scaled picture graphs.

## Coverage before the import

A direct item is a unique question ID with the canonical node in its question-level assessment tags. A worked method can use a node without requiring the learner to demonstrate it in the answer. Curriculum alignments describe related content and do not count as questions.

| Local inventory | Unique questions | Nodes with 0 direct items | 1 | 2 |
| --- | ---: | ---: | ---: | ---: |
| Public canonical mappings, AMC and CN | 8,790 | 60 | 85 | 83 |
| Eight existing practice collections, including AMC and CN | 18,687 | 53 | 79 | 84 |
| Recommender catalog, AMC and CN | 8,497 | 62 | 88 | 83 |

The denominator is 936 canonical nodes in each row. The first row counts `assessedIds` in [canonical mappings](../knowledge-graph/source/mappings.jsonl). In those same mappings, 43 nodes have neither a question-level assessment tag nor a method-direct tag. The eight-collection row adds `assessedNodeIds` from GSM8K (8,766 questions), England KS2 (254), Illustrative Mathematics (67), Waterloo CEMC (338), U.S. NAEP (305), and OATutor (167). The inputs have no duplicate question IDs across collections and no unresolved assessed node IDs. Of the 18,687 questions, 8,914 have one or more direct tags. The last row counts indexed tags in the recommender catalog after resolving them through its graph. [Browser collections](../../math-practice/practice-banks/manifest.js) · [Recommender catalog](../../math-practice/recommender/catalog.json) · [Recommender graph](../../math-practice/recommender/graph.json)

## Where questions help

The grades below are native CN placements unless a US grade is specified. BCcampus book numbers follow the adult education sequence. Each count is a unique question ID. A method-direct count indicates how many AMC and CN questions have at least one worked method with that node. [BCcampus adult mathematics outcomes](https://pressbooks.bccampus.ca/abehandbook/chapter/adult-literacy-fundamental-mathematics-alfm/)

| Existing concept | Grade and scope | AMC/CN direct | AMC/CN method-direct | Eight collections direct |
| --- | --- | ---: | ---: | ---: |
| `cnm_p118` Decimal meaning | CN 4. US 5.NBT.A.3a partial. Tenths and hundredths are explicit. | 0 | 2 | 0 |
| `cnm_p172` Common-denominator rewriting | CN 5. Find the denominators’ LCM and rewrite both fractions. No accepted US link. | 0 | 9 | 0 |
| `cnm_p093` One-decimal-place introduction | CN 3. The native criteria name one jiao as a tenth of a yuan and compare one-place decimals. | 1 | 2 | 1 |
| `cnm_p119` Comparing decimals | CN 4. US 5.NBT.A.3b partial. Compare two numerals by place value. | 5 | 11 | 8 |
| `cnm_p170` Fraction–decimal conversion | CN 5. US 4.NF.C.6 narrower. Convert tenths and hundredths. | 5 | 12 | 10 |
| `cnm_p159` Least common multiple | CN 5. US 6.NS.B.4 partial. Find an LCM without also having to rewrite fractions. | 20 | 48 | 20 |
| `cnm_p173` Unlike-denominator fraction addition and subtraction | CN 5. US 5.NF.A.1 partial. The assessed answer is a sum or difference. | 14 | 38 | 24 |
| `cnm_p135` Approximating products | CN 5. Find an exact decimal product and then round it. | 0 | 0 | 0 |
| `cnm_p164` Capacity | CN 5. US 3.MD.A.2, 4.MD.A.1 and 5.MD.A.1 partial. Interpret capacity or convert between liters and milliliters. | 0 | 1 | 0 |
| `cnm_p166` Proper, improper and mixed fraction forms | CN 5. US 3.NF.A.3c partial. Identify the forms and recognize whether a fraction equals or exceeds 1. | 1 | 3 | 1 |
| `cnm_p167` Equal-value fractions | CN 5. US 4.NF.A.1 partial. Scale both numerator and denominator by the same factor. | 1 | 6 | 1 |
| `cnm_p195` Percent, fraction and decimal conversion | CN 6. Convert percents to fractions or decimals and decimals to percents. | 2 | 13 | 5 |

Book 5 U1 B supplies examples for identifying fraction forms, and U2 A supplies exercises for generating equivalent fractions. These could add practice to the existing nodes `cnm_p166` and `cnm_p167`. [Common fractions](https://opentextbc.ca/alfm5/chapter/common-fractions/) · [Equivalent fractions](https://opentextbc.ca/alfm5/chapter/equivalent-fractions/)

### Scope of the import

The 102 BCcampus records, 51 per book, add 85 directly tagged question IDs across seven existing nodes. The available item-tag inventory rises from 18,687 to 18,789 questions, and the number with at least one direct tag rises from 8,914 to 8,999. Nodes with zero directly tagged questions drop from 53 to 51, with 79 nodes having exactly one and 84 having exactly two. The newly covered nodes are decimal meaning and common-denominator rewriting. All BCcampus item IDs and assessed tags match between source records and the generated browser collection. [Browser bundle](../../math-practice/practice-banks/bccampus.js)

The ID suffixes below use the common prefix `bccampus__`. A range after `q` denotes individual records.

| Direct node | Exact ID suffixes | Eight-collection baseline → after BCcampus |
| --- | --- | ---: |
| `cnm_p118` | `b04_u01b_e03_q03`–`q05`, `b04_u01b_e04_q03`–`q05`, `b04_u01b_e13_qc`, `qf`, `qg`, `qi`, `qj`, `ql` | 0 → 12 |
| `cnm_p170` | `b04_u01b_e03_q03`–`q05`, `b04_u01b_e04_q03`–`q05`, `b04_u01b_e05_q03`–`q10` | 10 → 24 |
| `cnm_p119` | `b04_u01c_e02_q03`–`q10`, `b04_u01c_e03_q01`–`q06` | 8 → 22 |
| `cnm_p159` | `b05_u04a_e10_q01`–`q06`, `q08`–`q12` | 20 → 31 |
| `cnm_p172` | `b05_u04a_e11_qb`–`qe` | 0 → 4 |
| `cnm_p173` | `b05_u04a_e12_q03`–`q08`, `b05_u04a_e13_q03`–`q08`, `b05_u04a_e14_q02`, `q04`, `q06`–`q08`, `b05_u04a_e15_q02`–`q06`, `b05_u04b_e02_q03`–`q16` | 24 → 60 |
| `cnm_p168` | `b05_u04a_e12_q03`–`q08`, `b05_u04a_e15_q02`–`q06`, `b05_u04b_e02_q03`–`q16` | 9 → 34 |

The Book 4 Exercise 3 and 4 options connect tenths and hundredths to both fraction notation and place-value language. The Exercise 13 review includes items that test the integer part, including two with thousandths as the fractional part. The 17 deeper-place-only records provide practice with thousandths and ten-thousandths and have empty direct tags pending a matching criterion. The four Book 5 Exercise 11 adaptations require the LCD and both rewritten numerators. That response directly demonstrates the two criteria of `cnm_p172`. The neighboring addition and subtraction items assess the final arithmetic, and 25 also require learners to enter the reduced numerator and denominator in order. The worked methods show the common-denominator step. [Book 4 decimal source](https://opentextbc.ca/alfm4/chapter/reading-writing-decimals/) · [Book 5 addition source](https://opentextbc.ca/alfm5/chapter/adding-common-fractions/) · [Book 5 subtraction source](https://opentextbc.ca/alfm5/chapter/subtracting-common-fractions/)

## Which tags reach the recommender

New v3 records can describe the directly assessed node in `assessedNodeIds` and a worked method’s concepts in `solutions[].directNodeIds`. In the canonical AMC/CN paths these project to separate `assessedIds` and route `methodDirectNodeIds`. Route context, support IDs, classification labels and curriculum alignments can aid explanation or browsing. They do not become scored recommender tags. [V3 projection](../../math-practice/runtime/question_format_v3.py#L358) · [Canonical graph roles](../knowledge-graph/README.md)

The current recommendation service reads an indexed item catalog, graph and model. A scored known item updates the ability posterior, and single-tag items also contribute node-specific answer residuals for prerequisite review. The local and hosted paths both limit the recommendation policy to AMC and CN. Adding BCcampus item annotations improves the available practice supply. It yields zero automatically scored BCcampus observations or BCcampus suggestions in the current recommender. [Browser recording](../../math-practice/practice-recommendations.js#L220) · [Recommendation policy](../../math-practice/runtime/practice_recommender.py#L232) · [Private service](../../desktop-service/private-recommender/service.py#L74)

In a local replay, both policy loaders return 8,497 items. A correct event for a BCcampus ID leaves the posterior at its starting value and contributes zero node-specific residuals. A request with `bank: "bccampus"` returns the unsupported-bank error.

## Candidate graph gaps

The scope comparison searched the names, aliases, descriptions and learning criteria of all 936 shared nodes in English and Chinese and checked the closest CN originals and US links. A partial US link establishes an overlap. The question to ask is what a learner has to demonstrate beyond that overlap. [Canonical nodes](../knowledge-graph/source/nodes.json) · [Native curricula and original criteria](../knowledge-graph/source/curricula.json) · [Accepted crosswalks](../knowledge-graph/source/alignments.json) · [Common Core mathematics standards](https://corestandards.org/wp-content/uploads/2023/09/ADA-Compliant-Math-Standards.pdf)

| Candidate | Distinct observable skill and closest neighbors | Proposed placement and evidence |
| --- | --- | --- |
| Interpret and compute unit rates | Convert a two-quantity ratio to a per-one rate, keep the order of the quantities straight, and state the compound unit. `cnm_p185` defines a quotient of a ratio, `cnm_p111` emphasizes using a given unit price or speed to find the total, and `cnm_p215` solves proportion problems. The accepted links for US 6.RP.A.2 and 6.RP.A.3b explicitly flag the missing unit-rate criterion. | Grade 6. Prepare with ratio meaning (`cnm_p185`) and division. In Book 6 U1 B Exercise 1, require a computed rate and its units. For a second setting, adapt Book 4 U5 A Exercise 3 to compare two prices per identical quantity. [Rates](https://opentextbc.ca/alfm6/chapter/rates/) · [Unit pricing](https://opentextbc.ca/alfm4/chapter/unit-pricing/) |
| Convert using metric prefixes across measurement types | Use the relative sizes of two prefixed units to preserve the same quantity, then repeat the reasoning for a different base unit. Existing length, mass and capacity nodes `cnm_p041`, `cnm_p056`, `cnm_p067` to `cnm_p069` and `cnm_p164` cover named pairs. `cnm_p120` explains decimal scaling. Together they supply preparation; conventional conversions such as kg to g alone can already assess existing nodes. | Grade 5, consistent with US 5.MD.A.1 overlap. Prepare with decimal scaling (`cnm_p120`) and one familiar metric conversion. Adapt Book 4 U6 B and D so the learner must explain the factor and convert both a mass and a capacity using a shared chart, including an unfamiliar pair. [Metric prefixes](https://opentextbc.ca/alfm4/chapter/the-prefixes/) · [Conversions, Exercise 1](https://opentextbc.ca/alfm4/chapter/conversion-within-the-metric-system/) |
| Interpret and construct scaled picture graphs | Apply a legend that maps one icon to several observations, interpret category totals and make a matching legend and display from a table. `cnm_p108` specifies bars; the measurement line-plot concepts use marks for individual observations arranged by numerical value. The US 2.MD.D.10 and 3.MD.B.3 crosswalks explicitly identify the unrepresented picture-graph component. | Grade 3 for scaled graphs and grade 2 for preparation with one icon per observation. Prepare with grouping and multiplication (`cnm_p038`). Book 6 U5 C Graph 1 can assess legend interpretation. Adapt a separate item to construct the displayed icon counts from a frequency table. [Picture graphs](https://opentextbc.ca/alfm6/chapter/picture-graphs/) |
| Read and write decimals through thousandths in words and expanded form | A direct task across several places can expose an internal zero or wrong digit weight. The meaning of tenths and hundredths is already `cnm_p118`, dividing or multiplying by powers of ten is `cnm_p120`, and fraction conversion is `cnm_p170`. The partial 5.NBT.A.3a link records the missing place-value representation criteria. | Grade 5. Prepare with `cnm_p118`. Use Book 4 U1 B Exercise 6 or 7 as a model and require numeral, number name and expanded sum. Review the scope of `cnm_p118` before giving this neighboring representation skill a new ID. [Reading and writing decimals](https://opentextbc.ca/alfm4/chapter/reading-writing-decimals/) |
| Convert between improper fractions and mixed numbers | The criteria for `cnm_p166` check recognition, despite the title covering all three forms. The additional performance is producing equal values in both forms and explaining the role of the quotient and remainder. | Grade 4–5. Prepare with fraction meaning (`cnm_p165`) and remainders (`cnm_p050`). Book 5 U1 B Exercises 4 and 6 ask for both conversion directions. This can be reviewed as a criterion extension of `cnm_p166`. [Common fractions](https://opentextbc.ca/alfm5/chapter/common-fractions/) |

LCD is an application of LCM with equivalent fractions and is already explicit in `cnm_p172`. Its lack of an accepted US alignment is a crosswalk gap. The equivalent-fraction rewriting step in 5.NF.A.1 is a possible scoped alignment. Pie and circle graphs refer to `cnm_p199`. Rates given in a word problem can serve as context for `cnm_p111`, and a task that sets up and solves a proportion can use `cnm_p215`. Ordinary sales tax and commission exercises asking for a fixed percent of a given amount assess `cnm_p196`. A task with percentage bands or distinct bases would warrant a separate scope check. [Book 5 common denominators](https://opentextbc.ca/alfm5/chapter/adding-common-fractions/) · [Book 6 contents](https://opentextbc.ca/alfm6/) · [Book 6 percent applications](https://opentextbc.ca/alfm6/chapter/finding-a-percent-of-a-number/)

## Next batch

1. Assess **approximating products** (`cnm_p135`, CN grade 5, zero direct items) with Book 4 U3 A Self-Test 2.1. Ask for the exact product and its value rounded to the nearest cent. [Published exercise](https://opentextbc.ca/alfm4/chapter/multiplying-decimals/)
2. Assess **capacity** (`cnm_p164`, CN grade 5, zero direct items) with the liters-to-milliliters subpart of Book 4 U6 D Exercise 1.7. A second item in the reverse direction can test the same equivalence. [Published exercise](https://opentextbc.ca/alfm4/chapter/conversion-within-the-metric-system/)
3. Review **unit rates** as the first new-node candidate. Require both the numerical rate and units using Book 6 U1 B, and use the Book 4 U5 A unit-pricing exercise to test whether learners can use the same reasoning to compare offers. [Rate exercises](https://opentextbc.ca/alfm6/chapter/rates/) · [Unit pricing exercises](https://opentextbc.ca/alfm4/chapter/unit-pricing/)
