# Demo seed data (P4)

P4's seed generator writes the demo data here. P2's seed loader reads it into SQLite locally and Supabase Postgres when live.

Everything is made up: names, phone numbers and addresses. Suburbs are real Johannesburg suburbs, so distances look right.

## Regenerate

From the repo root:

```bash
node scripts/run-python.mjs -m ranking.seed
```

- It overwrites the JSON files here. The same seed always gives the same files.
- Trade ids come from `data/glossary.json`, so rerun it after P3 adds trades.
- Options: `--seed N` and `--today YYYY-MM-DD`. The default today is 2026-09-29, the demo day in the fixtures.
- The code is in `packages/ranking/ranking/seed/`.

## Files

Each file is a JSON array with one row per line. Ids look like the fixtures' ids (`prov_001`, `job_001`).

| File | Rows | Load it? |
|---|---|---|
| `providers.json` | Providers | Yes |
| `customers.json` | Customers | Yes |
| `jobs.json` | Past jobs with their outcomes, and open jobs | Yes |
| `quotes.json` | Accepted, declined and open quotes | Yes |
| `off_app_jobs.json` | Past work providers logged, confirmed or awaiting the customer's SMS reply | Yes |
| `hidden_truth.json` | Each provider's true skill and first language | **No.** Only the fairness check reads it. It must never reach the app's database. |

### providers.json

These rows have the User fields from `me.json` plus:

| Field | Meaning |
|---|---|
| `phone` | Made up, in the fixtures' pattern: `071 000 0001` |
| `langs` | App languages they speak, for the profile (`provider_profile.json`) |
| `lat`, `lng` | Exact home location. Stays on the server; only work out `distance_km` from it. |
| `trades` | Trade ids from the glossary |
| `licensed` | May do licensed work: geyser installs, work needing a CoC |
| `bio` | Profile line |
| `joined_on` | Date they joined the app |

### customers.json

These rows have the User fields from `me.json` plus:
- `phone`: for example `082 000 0001`
- `address`: for example `12 Example Street, Braamfontein`
- `lat` and `lng`

### jobs.json

These rows have the JobPublic fields that are stored rather than computed (`id, state, trade, size, urgency, suburb, problem, problem_lang, photo_url, created_at`). They also have:

| Field | Meaning |
|---|---|
| `customer_id` | Who posted it |
| `provider_id` | Who did it. `null` while the job is open. |
| `trade_task` | The kind of job, such as "Replace geyser valve". The work record groups jobs by this. |
| `needs_licence` | Only licensed providers may be shown or take it |
| `address`, `lat`, `lng` | The customer's, copied onto the job. JobUnlocked only. |
| `finished_on` | The date it was done, or cancelled as a no-show. `null` while open. |
| `completed` | `true` if done, `false` if the provider didn't turn up (state `cancelled`), `null` while open |
| `still_working` | The two-week "still working?" answer. `null` if not asked yet or no answer. Answered jobs are in state `followed_up`. |

To build a provider's `ProviderStats` for `rank_providers` and `trust_summary`:
- Each job with that `provider_id` and a `finished_on` becomes one `JobOutcome(finished_on, completed, still_working)`.
- Each of their `confirmed` off-app jobs becomes one `JobOutcome(finished_on=date, completed=True, off_app=True)`.
- `repeat_customers` is the number of customers with more than one completed job with them.

### quotes.json

These rows have exactly the Quote fields (`quote.json`). Each finished job has one `accepted` quote, from the provider who did it. `price_range` works from the accepted quotes, joined with their job's `trade`, `size` and `suburb`.

### off_app_jobs.json

These rows have the fields in `off_app_job.json` plus:

| Field | Meaning |
|---|---|
| `provider_id` | Who logged it |
| `trade` | Trade id |
| `customer_phone` | Made up, for example `083 000 0001`. One number per job. |
| `confirmed_via` | `sms` or `ussd`, or `null` while awaiting the reply |
| `reference_agreed` | Whether the customer agreed to be listed as a reference, or `null` while awaiting the reply |

`state` is `confirmed` or `awaiting_sms_reply`.

## The demo characters

They come first in each table, so their ids match the fixtures:

- **Lindiwe (`cust_001`)** is the demo customer in Braamfontein. She posted `job_001` (leaking geyser), which is `quoting` with Sipho's `quote_001`.
- **Thabo (`prov_001`)** is an established, licensed plumber 1.8 km from `job_001`. He has 9 jobs, 2 repeat customers and 3 confirmed off-app jobs, as in `ranked_providers.json`.
- **Sipho (`prov_002`)** is a plumber with 6 years' experience who joined 5 days ago. He has no app jobs, 1 confirmed off-app job, and `offapp_001` awaiting the reply.
- **Nosipho (`prov_003`)** is an unlicensed plumber in Yeoville with about 4 years of confirmed work (70 off-app jobs and 16 app jobs). She's the ARPL export demo.

## Known gaps in v1

- **The demo trades come first.** Plumbing and electrical make the first 60 providers and their jobs, from the seed's main random stream, so those rows (and the ids the tests and demo use) stay the same as trades are added. The other 11 trades get 40 more providers and their jobs afterwards, from a second stream.
- **English job descriptions.** P3 translates them for each reader. The only isiZulu text is the placeholder in `quote_001`, from the fixture.
- **No photos yet.** `photo_url` is `null` everywhere, including `job_001`, because the fixture's `photo_001` has no file.
- **Before/after photos and vouches** come in the Day 4 seed.
- **Phone numbers follow the fixtures' pattern but aren't checked as unallocated.** Keep SMS on the Africa's Talking sandbox for seeded users.
