# How we work

These rules come from the [build plan](https://claude.ai/artifact/557FkdjEJmAe4VLfCgo7Ge).

## Stay unblocked

- **One folder per person.** Only edit your own folder, so merge conflicts are close to impossible. See the layout in the [README](README.md).
- **Contracts first.** `contracts/` is agreed on Day 1 morning. After that, a change needs a heads-up in the group chat. `api.md` and the fixtures change in the same commit, and you tell whoever calls it.
- **Stubs before real code.** Each package returns fake data in the right shape within hours. Everyone builds against the stubs, and real code replaces them behind the same interface.

## Branches

- Use one short branch off `main` per feature, lowercase and hyphenated, for example `privacy-gate`, `chat-redaction`, `newcomer-slot`, `price-range` or `off-app-sms`.
- A branch merges to `main` only after **the whole team** has reviewed it. Review sessions are Day 3 evening, Day 5 morning, and Day 6 before the final tag.

## Commits

```
tag: short plain-English description
```

- Use one tag: `feat`, `fix`, `refactor`, `chore`, `docs` or `test`. For example: `feat: add newcomer slot to ranking`.
- Make one commit per independent piece of work.
- **Check staged changes for keys before every commit** (`git diff --staged`). `.env` stays out of git; `.env.example` goes in. If a key is ever committed, tell the team and rotate it.

## Code style

| Rule | Example |
|---|---|
| Variables are nouns, functions are verbs | `completed_job_count`, `scan_message()` |
| Put units in names | `amount_rands`, `distance_km` |
| No magic numbers or strings | `NEWCOMER_MAX_COMPLETED_JOBS = 3` |
| Small functions that do one thing, with one CRUD operation each | `create_quote`, not `save_or_update_quote` |
| Write docstrings and comments as you write the code | |
| Casing | Python `snake_case`, TypeScript `camelCase`, API JSON `snake_case` |

Python is checked with ruff (`npm run lint:py`, `npm run format:py`). The app is checked with `tsc` as part of `npm run build:app`.
