# How we work

## Branches

- `main` is the stable version. Nothing goes on it until everyone has reviewed it and agreed it's done.
- Use one branch per feature, branched off `main`. Keep names short, lowercase and hyphenated, for example `number-protection`, `contact-masking`, `chat-screen`, `fairness-chart`.
- Pull `main` into your branch at least once a day so the merges stay small.

## Commits

Use one commit per independent piece of work. Don't bundle "add masking" with "fix typo in README".

```
tag: short plain-English description
```

- The tag is one lowercase word: `feat`, `fix`, `refactor`, `chore`, `docs`, `style` or `test`.
- Write the description in the imperative, with no full stop at the end, for example `feat: mask phone numbers written as words`.
- If you need to explain more, use the commit body, not the subject line.

## Before you commit

- **No secrets.** API keys go in `.env`, which is git-ignored. Check `git diff --staged` before every commit. If a key ever gets committed, tell the team and **rotate the key**. Deleting it in a later commit doesn't remove it from history.
- **No personal data.** Interview notes use participant codes (`T01`, `H01`), not names or numbers. Raw notes go in `research/interviews/raw/`, which is git-ignored.
- Run `npm test`.

## Pull requests and merging

1. Push your branch and open a PR. The template has a checklist.
2. CI must be green.
3. **Every team member reviews and agrees it's finished** before it's merged into `main`.
4. If you changed an API shape or a shared model in `backend/fixa/domain/`, update [docs/api-contract.md](docs/api-contract.md) in the same PR and post it in the group chat.

Blocked for more than 30 minutes? Post it in the group chat's blockers channel.

## Code style

| Rule | Example |
|---|---|
| Variables are nouns, functions are verbs | `completed_job_count`, `mask_contact_details()` |
| Put units in names | `amount_in_rand`, `POLLING_INTERVAL_IN_MILLISECONDS` |
| Names don't lie | Don't call a dict `provider_list` |
| No magic numbers or strings | `SHORTLIST_SIZE = 5`, not a bare `5` |
| Small functions that do one thing | Prefer one level of indentation |
| One CRUD operation per function | `create_job`, `get_job`, `update_job`, not `save_or_update_job` |
| Write docstrings as you write the code | Say what it does, its arguments, what it returns and any edge cases |
| Casing | Python `snake_case`, JavaScript `camelCase`, JSON over the API `camelCase` |

Python is linted and formatted with ruff (`npm run lint:api`, `npm run format:api`).
