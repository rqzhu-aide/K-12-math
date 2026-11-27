# BCcampus Fundamental Mathematics

This bank contains 102 text and math questions from the second editions of Books 4 and 5 of *Adult Literacy Fundamental Mathematics*. Each has a publisher answer key and a separately authored Ailleo worked solution. [Source and solution licenses](LICENSE)

| Source | Included exercises | Questions |
| --- | --- | ---: |
| [Book 4, Unit 1, Topic B](https://opentextbc.ca/alfm4/chapter/reading-writing-decimals/) | 3(c-e), 4(c-e), 5(c-j), 6(c-e), 7(c-h), 8(c-f), 9(c-f), 13(c, f, g, i, j, l) | 37 |
| [Book 4, Unit 1, Topic C](https://opentextbc.ca/alfm4/chapter/comparing-decimals/) | 2(c-j), 3(a-f) | 14 |
| [Book 5, Unit 4, Topic A](https://opentextbc.ca/alfm5/chapter/adding-common-fractions/) | 10(a-f, h-l), 11(b-e), 12(c-h), 13(c-h), 14(b, d, f, g, h), 15(b-f) | 37 |
| [Book 5, Unit 4, Topic B](https://opentextbc.ca/alfm5/chapter/subtracting-common-fractions/) | 2(c-p) | 14 |

The importer selects unanswered exercises with public keys. It skips worked examples, diagrams, classroom activities, money exercises, and other book content outside this selection. Book 5 Exercise 10(g) uses the same numbers as Exercise 11(e). Exercise 14(c, e) gives same-denominator sums.

## How the exercises work in Ailleo

The decimal questions include choosing a matching fraction and place-value name, writing a decimal from its fraction or words, splitting a decimal into its whole and fractional parts, and comparing decimal values. Choice adaptations assess recognition of the fraction and words. The original workbook asks learners to produce both.

The four least-common-denominator questions in Book 5 Exercise 11 ask learners to compute the denominator and use it to rewrite both fractions. Ailleo checks the denominator and two new numerators in order. The publisher supplies the denominator, and Ailleo calculates the rewritten fractions. For the 25 exercises that ask for lowest terms, learners enter the reduced numerator followed by the denominator. For example, they enter `7, 4` for \(7/4\). The remaining free-response sum questions accept an equivalent decimal or fraction. When the publisher gives a mixed number for one of those sums, Ailleo also accepts that notation, such as `2 1/3`.

Each question's source index entry retains the original instructions, expressions, key, exact locator and description of changes. Item IDs identify the source volume, unit, topic, exercise and original subpart. `meta.familyId` groups numeric variants of the same exercise pattern into 13 families.

## Graph coverage

85 questions supply direct evidence for seven Ailleo concepts. Ailleo assigns the lowest grade among the concepts the question assesses. The level field identifies the source book.

| Concept | Direct questions |
| --- | ---: |
| `cnm_p118` Meaning of decimals | 12 |
| `cnm_p119` Comparing decimals | 14 |
| `cnm_p159` Least common multiple | 11 |
| `cnm_p168` Reducing fractions | 25 |
| `cnm_p170` Converting between fractions and decimals | 14 |
| `cnm_p172` Converting fractions to a common denominator | 4 |
| `cnm_p173` Adding and subtracting fractions with unlike denominators | 36 |

The 17 standalone conversions that exclusively test thousandths or ten-thousandths stay available as practice without direct tags or a grade. The narrower meaning and conversion nodes name tenths and hundredths. A mixed decimal may still directly test the whole-number part, as in Book 4 Exercise 13(g, j). A worked method can use a skill that the prompt does not require the learner to demonstrate separately. For example, a sum can be checked without seeing the intermediate common denominator, while the worked solution shows it.

## Rebuild the bank

Use the two publisher EPUBs below with Python 3.10 or later. The importer uses the standard library, verifies each SHA-256, rebuilds the records and checks the selected exercise keys with integer, decimal or exact fraction arithmetic. In the publisher web edition, Book 4 currently lists revision 2.06. The import is pinned to the archived revision 2.05. [Book 4 revision history](https://opentextbc.ca/alfm4/back-matter/versioning-history/) · [Book 5 revision history](https://opentextbc.ca/alfm5/back-matter/versioning-history/)

| Archive | Revision | SHA-256 |
| --- | --- | --- |
| [Book 4 EPUB](https://public-archive.bccampus.ca/pressbooks-exports/opentextbc.ca/sites/421/Adult-Literacy-Fundamental-Mathematics-Book-4-2nd-Edition.epub) | 2.05 | `e0eba7105326a64d04c9f50725605d7d0c8b3d071879caf9832b083ec477ea2c` |
| [Book 5 EPUB](https://public-archive.bccampus.ca/pressbooks-exports/opentextbc.ca/sites/437/Adult-Literacy-Fundamental-Mathematics-Book-5-2nd-Edition.epub) | 2.02 | `f21e9c12c716cb5a480c5749206a8b9bd9506f232b522f66ed3952c7edb87be2` |

From the repository root, pass the local EPUB filenames in volume order.

```sh
python database/bccampus-bank/import_bank.py path/to/book4.epub path/to/book5.epub
```
