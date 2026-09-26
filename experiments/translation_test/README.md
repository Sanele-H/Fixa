# 30-message translation test (Role 1)

This test answers two questions: how good is the translation really, and which language pairs fail?

## Writing the messages (Day 2)

Add rows to `test_messages.csv` until you have 30. Make them sound like real people:

- Prices written every way people write them, for example `R450`, `R 1 500`, `450 rand` and `R1500.00`.
- Times the same way, for example `10:00`, `10h00`, `3pm` and "Tuesday morning".
- Trade words and slang, including SA English such as "geyser", "plug point" and "DB board".
- Mixed English and isiZulu in one message (code-switching), plus SMS-style spelling.
- A few messages that try to sneak a phone number through. These also help Role 3.

Ask a first-language speaker to write or check every non-English message. Put their first name in `written_by`, and only if they agree to it.

| Column | Meaning |
|---|---|
| `must_survive` | Exact values that must appear unchanged in the translation, separated by `\|` |
| `glossary_terms` | `term_id`s from `backend/fixa/translation/data/glossary.csv`, separated by `\|` |
| `category` | Your own label (price, time, slang, mixed…) so you can report results by category |

## Running it (Day 4)

```bash
npm run translation-test -- --backends echo,google
```

`evaluate_backend` and `write_results` in `run_translation_test.py` are TODO. Record these for each backend:

- Values broken **without** protection (the raw backend) and **with** protection (our pipeline)
- Glossary terms missed
- Messages flagged as unsure, and whether the flag was right

Also try each backend's cost and speed settings. Chat needs answers in about 2 seconds.

Commit the final results file on purpose (`git add -f`). It becomes a slide.
