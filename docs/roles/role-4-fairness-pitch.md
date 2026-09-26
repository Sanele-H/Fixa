# Role 4: Fairness, research and pitch

**You own** `backend/fixa/ranking/`, `experiments/fairness_simulation/` and `research/`.

**Your part of the demo:** Nomsa gets the job through the newcomer slot (step 2), then the fairness chart (step 5). You also run the interviews, the business case, the deck and the rehearsals.

## Already in place

| File | State |
|---|---|
| `backend/fixa/ranking/provider_ranking.py` | `ProviderRecord`, the `RankingStrategy` interface and `shortlist_providers` ✅. Both strategies are **TODO**. |
| `backend/tests/test_provider_ranking.py` | Your to-do list as tests |
| `experiments/fairness_simulation/run_simulation.py` | Parameters and structure; the simulation steps are **TODO**. It imports the real ranking. |
| `experiments/fairness_simulation/README.md` | The chart spec, and a table for writing down your assumptions |
| `research/interviews/` | Interview guide (consent, questions) and a log CSV |
| `research/business-model.md` | Revenue table, market numbers to source, facts to verify |
| `research/pitch/` | Demo script, deck outline mapped to the judging criteria, judge Q&A |

## Your week

| Day | Deliverable |
|---|---|
| Sat 26 | Email the organisers the questions in [sprint-plan.md](../sprint-plan.md). |
| Sun 27 | Book interviews. Implement `SortByRatingStrategy`. Simulation v0 runs. |
| Mon 28 | Design and implement `NewcomerFriendlyStrategy`. First comparison numbers. |
| Tue 29 | Most interviews happen today. Log them within the hour. |
| Wed 30 | Final fairness chart. |
| Thu 1 | Full deck with interview quotes, Role 1's test results and the chart. |
| Fri 2 | Three timed rehearsals and Q&A practice. |

## Decisions that are yours

- **Who counts as a newcomer**, how many shortlist slots they get and at which position, and how several newcomers take turns.
- **Simulation assumptions:** how customers choose from a shortlist, and how noisy ratings are. Write them in the simulation README. Judges may ask.
- **The quality check:** does the average job rating drop under our ranking? Show that number next to the chart.

## Contracts you must keep

- `ranking/` imports nothing from FastAPI, the store or pydantic, so the simulation can use it on its own.
- Role 3 calls `shortlist_providers(candidates, strategy, is_small_job)` when a job is posted. Keep that signature.
- Every number on a slide needs a source and a date (see `business-model.md`).
- Interview notes use participant codes only. Ask permission before quoting anyone.

## Run your part

```bash
npm run test:api    # ranking tests go from xfailed to passed
npm run simulate    # writes experiments/fairness_simulation/results/
```
