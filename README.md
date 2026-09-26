# Fixa

> Hire someone nearby in your own language, without handing your number or address to a stranger.

This is our hackathon build: 4 people and 6 days. **The plan is the [Fixa build plan](https://claude.ai/artifact/557FkdjEJmAe4VLfCgo7Ge).** It covers the features, roles, contracts, the day-by-day plan and each person's starting prompt. This repo follows it.

## Layout

```
contracts/          api.md + fixtures/      the whole team (DRAFT until agreed on Day 1 morning)
app/                the PWA                  P1
api/                FastAPI                  P2
packages/lang/      language and safety      P3
packages/ranking/   ranking + simulation     P4
packages/record/    work record + exports    P4
data/               glossary.json, test_messages.json, number_words.json (P3) · seed/ (P4)
.env.example        every key the team needs (the real .env is never committed)
```

**One folder per person.** Nobody edits another person's folder. Contracts change only after a heads-up in the group chat.

## What's already here

The skeleton covers the build plan's Day 1 *team morning* work:

- the folders above
- a **draft** of `contracts/`
- `.env.example`
- the Vite `/api` proxy and tunnel access
- one-command setup, run and test
- CI

Every person's folder is a **minimal shell**: it installs, runs and passes a smoke test, and nothing more. Everyone's own Day 1 work starts from their starting prompt in the build plan:

- P1: PWA, i18n and MSW
- P2: routes returning fixtures, models and the seed loader
- P3 and P4: stubs and the seed generator

## Quick start

You need **Git**, **Python 3.11+** and **Node 22+**.

```bash
git clone https://github.com/Sanele-H/Fixa.git
cd Fixa
npm install        # root tools
npm run setup      # .venv with api + packages, app packages, creates .env
npm run dev        # API on :8000, app on :5173
```

- App: http://localhost:5173
- API docs: http://localhost:8000/docs
- On a phone: install [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/), then run `npm run tunnel` and open the `https://…trycloudflare.com` address it prints. Phones need HTTPS for the camera, location and the service worker.

| Command | What it does |
|---|---|
| `npm test` | Python tests, Python lint, app type-check and build. Run before every PR. |
| `npm run test:py` | Python tests only (API and all packages) |
| `npm run format:py` | Auto-format Python |
| `npm run dev:api` / `npm run dev:app` | Run one side only |

## Your first hour

1. Run the quick start above.
2. Open the [build plan](https://claude.ai/artifact/557FkdjEJmAe4VLfCgo7Ge) and copy **your** starting prompt.
3. Branch off `main` for your first feature (for example `git switch -c privacy-gate`).
4. Open your AI coding assistant **at the repo root** and paste the prompt.
5. Read [CONTRIBUTING.md](CONTRIBUTING.md) before your first commit.
