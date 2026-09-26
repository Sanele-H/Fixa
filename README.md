# Fixa

> Hire someone nearby in your own language, without handing your number or address to a stranger, **and give skilled newcomers a fair shot at their first job.**

This is our hackathon build: a 7-day sprint (Sat 26 Sep → pitch on Sat 3 Oct) by 4 people, ending in one demo on two phones.

This repo is a **scaffold**. The folders, tooling and agreed interfaces are in place, and every feature is a clearly marked `TODO` for the person who owns it. Start with your role guide in [docs/roles/](docs/roles/).

## Quick start

You need **Git**, **Python 3.11+** and **Node 22+**.

```bash
git clone https://github.com/Sanele-H/Fixa.git
cd Fixa
npm install        # root tools (runs backend + frontend together)
npm run setup      # .venv + backend packages, frontend packages, creates .env
npm run dev        # backend on :8000, frontend on :5173
```

- App: http://localhost:5173. Pick a demo user; the page also shows whether the backend is reachable.
- API docs (try every endpoint): http://localhost:8000/docs
- On a phone on the same Wi-Fi: `http://<your-laptop-ip>:5173`. Vite prints the address. On Windows, allow Node through the firewall when asked.

| Command | What it does |
|---|---|
| `npm test` | Backend tests, Python lint, frontend build. Run before every PR. |
| `npm run test:api` | Backend tests only |
| `npm run format:api` | Auto-format Python |
| `npm run simulate` | Fairness simulation (Role 4) |
| `npm run translation-test -- --backends echo` | 30-message translation test (Role 1) |

Tests marked **xfailed** are to-do lists: cases that are expected to fail until their owner builds the feature. **passed** means it works. **failed** means something broke.

## Your first hour

1. Get the code and run it (Quick start above). The app's first page should say the backend is running.
2. Run `npm test`. You should see **passed** and **xfailed**, and nothing **failed**.
3. Read your role guide in [docs/roles/](docs/roles/) and skim [docs/sprint-plan.md](docs/sprint-plan.md).
4. Read [CONTRIBUTING.md](CONTRIBUTING.md) before your first commit.
5. Branch off `main` for your first feature, for example `number-protection` (Role 1), `chat-screen` (Role 2), `job-states` (Role 3) or `sort-by-rating` (Role 4):

   ```bash
   git switch main
   git pull
   git switch -c chat-screen
   ```

## Who owns what

Each person owns one area and makes the decisions in it. Roles are picked at the Day 1 meeting. Fill in names here and in [.github/CODEOWNERS](.github/CODEOWNERS).

| Role | Owner | Folders | Guide |
|---|---|---|---|
| 1. Language and translation | _TBD_ | `backend/fixa/translation/`, `experiments/translation_test/` | [role-1](docs/roles/role-1-language.md) |
| 2. App and demo screens | _TBD_ | `frontend/`, `backend/fixa/seed/` | [role-2](docs/roles/role-2-app.md) |
| 3. Backend and safety | _TBD_ | `backend/fixa/{api,domain,services,storage,safety,classification}/` | [role-3](docs/roles/role-3-backend-safety.md) |
| 4. Fairness, research and pitch | _TBD_ | `backend/fixa/ranking/`, `experiments/fairness_simulation/`, `research/` | [role-4](docs/roles/role-4-fairness-pitch.md) |

## How the pieces fit

```
 phone (PWA, React)  --/api-->  Vite dev server  --proxy-->  FastAPI (backend/fixa/api)
                                                                  |
                   services/  (rules: who can do what, when)      |
                     |-- safety/        mask numbers, scam warnings       (Role 3)
                     |-- translation/   protect values, glossary, backend (Role 1)
                     |-- ranking/       who gets shown a job              (Role 4)
                     '-- storage/       in-memory store + seed data       (Role 3, 2)
```

More in [docs/architecture.md](docs/architecture.md). The endpoint list is in [docs/api-contract.md](docs/api-contract.md).

## The plan

- [docs/sprint-plan.md](docs/sprint-plan.md) covers scope (build, fake, skip), the day-by-day plan and the questions for the organisers.
- [research/pitch/demo-script.md](research/pitch/demo-script.md) is the 5-step demo everything is built for.
- [CONTRIBUTING.md](CONTRIBUTING.md) covers branches, commits, reviews and code style.
