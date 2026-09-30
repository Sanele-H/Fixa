# Native-speaker review of Azure translations, 28 Sep 2026

Reviewer: P3 (native isiZulu speaker). Run: `translation_test_20260928_1649.md`, Azure Translator
(southafricanorth) with number protection, on the 30 messages in `data/test_messages.json`.

## Result

| Check | Score |
| --- | --- |
| Prices, times and other values kept exact | 30 of 30 (without protection: 26 of 30, R450 became $450) |
| Meaning fully right | 23 of 30 |
| Meaning wrong or partly lost | 7 of 30 (all isiZulu or isiXhosa into English) |
| English into isiZulu and isiXhosa (m25 to m30) | 6 of 6 right |
| Average time per message | about 0.9 to 2 s |

## Corrections

| Id | Azure said | Should say | Problem |
| --- | --- | --- | --- |
| m06 | The electricity always goes out when I open the door. | The electricity always goes out when I switch on the kettle. | Wrong word: iketela (kettle) became "the door" |
| m11 | I'm sorry, I'll be there in 20 minutes. | I'm sorry, I'm running late, I'll be there in 20 minutes. | Dropped "running late" |
| m12 | The toilet is closed and the water is leaking out of the floor. | The toilet is blocked and the water is coming out onto the floor. | ivalilekile means blocked here, not closed |
| m13 | …the lights are not flashing. | …the lights are not on. | izibani azikhanyi means the lights don't come on |
| m20 | I'll be back on Wednesday at 9:00, it'll cost R600. | I can come on Wednesday at 9:00, it'll cost R600. | Ndingeza means "I can come", not "I'll be back" |
| m21 | There is no electricity in the house. | There is no electricity in half the house. | Dropped kwisiqingatha (half) |
| m22 | The outside pipe broke and water rushed down the street. | The outside pipe broke and water ran into the street. | Small: close in meaning |

## What this means

- Numbers are solved: protection keeps every price and time exact.
- Meaning is mostly right, but about 1 in 4 isiZulu or isiXhosa messages loses or changes a detail.
  The "See original" toggle and the flag checks matter for exactly these cases.
- Trade words cause some of the errors (iketela, ivalilekile). Feeding the glossary to Azure should
  fix those.
- English into isiZulu and isiXhosa was right every time in this set.
