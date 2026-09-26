# Fairness simulation (Role 4)

**The question:** how long does a good newcomer wait for a first job when providers are sorted by rating, compared with our ranking? And does the quality of completed jobs drop?

A judge will probably ask "Isn't showing newcomers unfair to customers?", so the answer has to be a number.

## How it's built

- `run_simulation.py` imports `fixa.ranking.provider_ranking`, which is the same code the app uses when a job is posted. Implement the two strategies there first.
- Fixed at 200 providers and 2,000 jobs over 30 days, as in the plan. Every other setting is a constant at the top of the file.
- Each strategy runs 20 times on the same random seeds, so the comparison is fair and you can show a range, not just one lucky run.

## Write down your assumptions

Fill this in as you decide. Judges may ask about any of them.

| Assumption | Value | Why |
|---|---|---|
| Share of newcomers | 25% | TODO |
| How customers choose from the shortlist | TODO | TODO |
| How ratings relate to true quality | TODO | TODO |
| Who counts as a "good" newcomer | TODO | TODO |

## The chart (one chart, for one slide)

- **Form:** line chart. X-axis: day (0–30). Y-axis: % of good newcomers who have had their first job.
- **Two lines:** sort-by-rating and our ranking. Label both lines directly at their right-hand end, and keep a small legend as well.
- **Colours:** our ranking `#2a78d6` (blue), sort-by-rating `#eb6834` (orange). Keep them the same on every slide.
- 2px lines, light grid, and no second y-axis.
- Put the headline number in the slide title, for example "Good newcomers get a first job in X days instead of never".
- Show the quality result as a stat next to the chart, not on a second axis: "Average job rating: 4.3 vs 4.3".
