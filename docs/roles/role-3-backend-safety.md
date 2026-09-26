# Role 3: Backend and safety

**You own** `backend/fixa/` api, domain, services, storage, safety and classification.

**Your part of the demo:** "o82 one two three…" gets masked, and contact details unlock on both phones only after she accepts and Nomsa confirms. The server enforces this, not the app.

## Already in place

| File | State |
|---|---|
| `api/main.py`, `api/dependencies.py` | App, CORS, error → HTTP status mapping, demo login via `X-User-Id` |
| `api/routes/*.py` | Every endpoint declared. Users, health and reference data ✅ work; the rest answer 501. |
| `domain/models.py` | Starting data model (camelCase JSON). Contact details are kept apart on purpose. |
| `domain/job_states.py` | States defined; the transition rules are **TODO** |
| `services/jobs.py`, `services/messages.py` | Every use case stubbed with its docstring. **TODO** |
| `storage/memory_store.py` | Users work; jobs, quotes and messages are **TODO** |
| `safety/contact_masking.py`, `safety/scam_warnings.py` | Interfaces. **TODO** |
| `classification/trade_suggestion.py` | Interface. **TODO** (keep it simple or fake it) |
| `backend/tests/test_contact_masking.py`, `test_job_states.py`, `test_scam_warnings.py` | Your to-do lists as tests |

## Your week

| Day | Deliverable |
|---|---|
| Sun 27 | Job transitions, the store's CRUD methods, `post_job`, `list_jobs_for_user`, `create_quote`. |
| Mon 28 | Accept, confirm, unlock and `get_contact_details_for_job`. Masking catches the 10 trickiest cases. Unlock is enforced on the server. |
| Tue 29 | `send_message` pipeline (mask → warn → translate → store). Scam rules. Keyword trade suggester. |
| Wed 30 | Demo on two phones. Fix what breaks. |
| Thu 1 | One safety slide: which disguised numbers we catch. |

## A starting idea for masking

This is one approach, not the only one:

1. Split the text into word-like tokens and remember where each one sits in the text.
2. Turn each token into digits if you can: `082` → `082`, `o82` → `082` (letters that look like digits), `one` / `een` / `nul` → `1` / `1` / `0`. Add isiZulu number words once a first-language speaker has checked them.
3. Find runs of consecutive digit tokens separated only by spaces, `-`, `.` or brackets. A run with 9 or more digits is a phone number, so replace that span with `[***]`.
4. Let `:` and `,` break a run, so "10:00, 082…" masks only the number.
5. Mask emails and "12 Something Street" addresses separately.

Run the tests after each step. The "must not change" cases (R450, 10:00, 15mm) stop you over-masking.

## Contracts you must keep

- Only `get_contact_details_for_job` reads `ContactDetails`, and only for an `unlocked` job.
- Every state change goes through `ensure_transition_allowed`.
- Routes stay thin. Rules go in `services/`, so they can be tested without HTTP.
- If you change a model, update [docs/api-contract.md](../api-contract.md) and tell Role 2.

## Run your part

```bash
npm run test:api     # your to-do tests go from xfailed to passed
npm run dev:api      # then try endpoints at http://localhost:8000/docs
```

When `GET /api/jobs` works, change the last test in `test_api_smoke.py` to expect 200.
