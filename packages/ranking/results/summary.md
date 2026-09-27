# Fairness simulation results

Fixa's ranking (`rank_providers`, unchanged) against plain sort-by-rating, in a simulated
city: 200 providers, 2,000 jobs over 200 days, random seed 2026.
"Fixa without exploring" is the same ranking with the Thompson draw replaced by the
expected chance of success and no newcomer slot. It is only there to show what exploring
costs.

Regenerate from the repo root: `node scripts/run-python.mjs -m ranking.simulation`

| Measure | Fixa ranking | Sort by rating | Fixa without exploring |
|---|---|---|---|
| Jobs to the busiest 10% of providers | 23% | 91% | 27% |
| Gini score of jobs per provider | 0.36 | 0.93 | 0.45 |
| Good newcomers with a first job within 30 days | 95% | 0% | 69% |
| Median wait for a first job (good newcomers) | 4 days | never | 17 days |
| Chance a job goes well (average hired skill) | 83.0% | 91.8% | 83.9% |
| Average distance to the job | 1.5 km | 5.9 km | 1.4 km |
| Jobs filled | 2,000 | 2,000 | 2,000 |

## How the simulation works

- Providers and job spots are spread at random over a 20 km square city. Every provider
  within 10 km of a job is a candidate, for every ranker.
- Each provider has a hidden true skill (average 0.8): the chance a job they do goes well.
  The rankers never see it, only job outcomes.
- 60% of providers have a year of past jobs when the run starts. The rest join during
  the run with no record.
- The customer picks from the top 5 of the list, the top places more often (40%, 25%,
  15%, 12%, 8%). A provider already doing 3 jobs turns new ones down, with every ranker.
- A job goes well as often as the hired provider's true skill, and that outcome becomes
  evidence when the job ends, 1 to 3 days later.
- A good newcomer joined during the run, at least 60 days before the end, and is at
  least as skilled as the average provider.

## Fairness across language groups

Groups are providers' hidden first language, which no ranking or trust score ever sees.
Work is jobs per month compared with providers of the same true skill (100% = fair share).
Score is the average trust score divided by true skill, for providers with a score.

| Group | Providers | Work with Fixa | Work with sort-by-rating | Fixa trust score / true skill |
|---|---|---|---|---|
| isiZulu | 72 | 101% | 71% | 103% |
| isiXhosa | 58 | 97% | 73% | 100% |
| Sesotho | 28 | 93% | 153% | 99% |
| chiShona | 42 | 107% | 152% | 101% |

Sort-by-rating never sees language either. Its uneven shares come from giving most work to
a few providers: whichever groups those few belong to gain, by chance.
