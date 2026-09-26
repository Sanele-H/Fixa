# Architecture

It is small on purpose: one Python backend, one React PWA, and data in memory. Everything runs on one laptop, and both demo phones connect to it over Wi-Fi.

## Layers (backend)

```
api/routes/   parse HTTP, call one service, return its result        (no rules here)
services/     the rules: who may do what, in which job state         (tests live here)
domain/       shared models, job states, trades, tokens              (the contract)
storage/      MemoryStore: one create/get/list/update method each    (swap for SQLite later)
safety/  translation/  ranking/  classification/                     (pure logic, easy to test)
```

- Routes never contain rules, so the rules can't be skipped by a new route.
- `ranking/` doesn't import FastAPI, the store or pydantic, so the fairness simulation can use it directly.
- Shared objects (the store, the translation pipeline, the ranking) come from `api/dependencies.py`. Tests swap them out with `app.dependency_overrides`.

## A chat message, step by step

```
sender types  ->  mask_contact_details   (safety, Role 3)   "o82 one two..." -> "[***]"
              ->  find_scam_warnings     (safety, Role 3)   -> ["upfront_payment"]
              ->  TranslationPipeline    (translation, Role 1)
                     protect_tokens      "R450", "10:00", "[***]" -> placeholders
                     backend.translate   (echo / Google / LLM / NLLB / Lelapa)
                     restore_tokens      placeholders -> exact original values
                     glossary check      flag if the expected trade word is missing
              ->  store.create_message   original (masked) + translation + flags
reader polls  ->  GET /messages          shows translation; "See original" shows masked original
```

Masking runs **first**. That way the raw number is never stored, and "See original" can't reveal it.

## Contact details: the core safety rule

- Phone numbers and addresses are **not** on `User`. They sit in a separate `ContactDetails` record.
- Only one function reads them, `services/jobs.get_contact_details_for_job`. It refuses unless the job is `unlocked` and the viewer is the job's customer or its assigned provider.
- The job only reaches `unlocked` through `posted → quoted → accepted (customer) → confirmed (provider) → unlocked`, and `job_states.ensure_transition_allowed` guards every step.

## Demo setup

- **Two phones:** both open the laptop's Vite address. Vite forwards `/api` to the backend, so the phones only need one address.
- **Updates:** screens poll every 2 seconds. That copes with bad venue Wi-Fi better than websockets.
- **State:** it's all in memory. Restarting the backend, or calling `POST /api/demo/reset`, gives a clean demo every time.
- **Service worker:** it's registered only in production builds, and it only makes the app installable. It never caches API data.
