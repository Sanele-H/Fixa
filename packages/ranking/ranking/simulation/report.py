"""Turns simulation results into the pitch charts and a summary table (the charts' table view).

Chart titles are written from the numbers, so they stay true if the ranking is tuned.
"""

from pathlib import Path

from ranking.simulation.charts import SERIES_COLORS, draw_bar_chart, draw_step_chart
from ranking.simulation.fairness import check_fairness
from ranking.simulation.fairness_report import build_fairness_markdown, draw_fairness_charts
from ranking.simulation.metrics import (
    HIRED_WITHIN_DAYS,
    WAIT_WINDOW_DAYS,
    calculate_share_hired_within,
    list_good_newcomer_waits,
    summarise_result,
)
from ranking.simulation.run import SimulationResult
from ranking.simulation.world import SimConfig

WORK_CHART_FILE_NAME = "work_concentration.png"
NEWCOMER_CHART_FILE_NAME = "newcomer_first_job.png"
QUALITY_CHART_FILE_NAME = "job_quality.png"
SUMMARY_FILE_NAME = "summary.md"
MAIN_RANKER_COUNT = 2  # Fixa and sort-by-rating; the third ranker only prices exploring
PERCENTAGE_POINTS = 100


def write_report(
    results: dict[str, SimulationResult], config: SimConfig, seed: int, results_dir_path: Path
) -> dict[str, dict]:
    """Writes the five charts and summary.md, and returns each ranker's measures.

    results must list Fixa's ranking first, sort-by-rating second and Fixa without
    exploring third, as compare_rankers does. Colours follow that order on every chart.
    """
    summaries = {name: summarise_result(result, config) for name, result in results.items()}
    colors = dict(zip(results, SERIES_COLORS, strict=True))
    draw_work_chart(results_dir_path / WORK_CHART_FILE_NAME, summaries, colors, config)
    draw_newcomer_chart(results_dir_path / NEWCOMER_CHART_FILE_NAME, results, colors, config)
    draw_quality_chart(results_dir_path / QUALITY_CHART_FILE_NAME, summaries, colors)
    main_names = list(results)[:MAIN_RANKER_COUNT]
    fairness_by_ranker = {name: check_fairness(results[name], config) for name in main_names}
    draw_fairness_charts(results_dir_path, fairness_by_ranker, colors)
    summary_markdown = build_summary_markdown(summaries, config, seed) + build_fairness_markdown(
        fairness_by_ranker
    )
    (results_dir_path / SUMMARY_FILE_NAME).write_text(
        summary_markdown, encoding="utf-8", newline="\n"
    )
    return summaries


def draw_work_chart(path: Path, summaries: dict, colors: dict, config: SimConfig) -> None:
    """Draws the share of jobs the busiest 10% of providers got, per main ranker."""
    fixa, rating = list(summaries.values())[:MAIN_RANKER_COUNT]
    title = (
        f"The busiest 10% of providers get {fixa['top_10_percent_share']:.0%} of jobs, "
        f"not {rating['top_10_percent_share']:.0%}"
    )
    subtitle = (
        f"Share of all jobs. Simulated city: {config.provider_count} providers, "
        f"{config.job_count:,} jobs.\n"
        f"Gini score of jobs per provider: {fixa['gini']:.2f} with Fixa, "
        f"{rating['gini']:.2f} with sort-by-rating (0 = everyone gets the same)."
    )
    bars = [
        (name, summary["top_10_percent_share"], colors[name])
        for name, summary in list(summaries.items())[:MAIN_RANKER_COUNT]
    ]
    draw_bar_chart(path, title, subtitle, bars, format_percent)


def draw_newcomer_chart(
    path: Path, results: dict[str, SimulationResult], colors: dict, config: SimConfig
) -> None:
    """Draws the share of good newcomers with a first job, by days since joining."""
    main_results = list(results.items())[:MAIN_RANKER_COUNT]
    waits_by_name = {
        name: list_good_newcomer_waits(result, config) for name, result in main_results
    }
    lines = [
        (
            name,
            [calculate_share_hired_within(waits, days) for days in range(WAIT_WINDOW_DAYS + 1)],
            colors[name],
        )
        for name, waits in waits_by_name.items()
    ]
    fixa_waits, rating_waits = waits_by_name.values()
    title = (
        f"{calculate_share_hired_within(fixa_waits, HIRED_WITHIN_DAYS):.0%} of good newcomers get "
        f"a first job within {HIRED_WITHIN_DAYS} days, not "
        f"{calculate_share_hired_within(rating_waits, HIRED_WITHIN_DAYS):.0%}"
    )
    subtitle = (
        f"Share of good newcomers ({len(fixa_waits)} providers who joined during the run, "
        "at least as skilled as average)\nwith a first job, by days since joining."
    )
    draw_step_chart(path, title, subtitle, lines, x_label="Days since joining")


def draw_quality_chart(path: Path, summaries: dict, colors: dict) -> None:
    """Draws the average chance a job goes well, per ranker, to show what exploring costs.

    The two Fixa bars sit together, since the gap between them is what exploring costs.
    """
    fixa, rating, no_exploring = summaries.values()
    exploring_cost_points = (
        no_exploring["average_hired_skill"] - fixa["average_hired_skill"]
    ) * PERCENTAGE_POINTS
    cost_text = (
        "under 1 point" if exploring_cost_points < 1 else f"{exploring_cost_points:.1f} points"
    )
    title = f"Exploring costs {cost_text} of job quality"
    subtitle = (
        "Average chance a job goes well (the hired provider's hidden true skill).\n"
        f"Sort-by-rating's lead comes from hiring providers {rating['average_distance_km']:.1f} km "
        f"away on average, not {fixa['average_distance_km']:.1f} km."
    )
    fixa_name, rating_name, no_exploring_name = summaries
    bars = [
        (name, summaries[name]["average_hired_skill"], colors[name])
        for name in [fixa_name, no_exploring_name, rating_name]
    ]
    draw_bar_chart(path, title, subtitle, bars, format_percent_1dp)


def build_summary_markdown(summaries: dict[str, dict], config: SimConfig, seed: int) -> str:
    """Builds summary.md: every measure per ranker, and how the simulation works."""
    names = list(summaries)
    rows = [
        ("Jobs to the busiest 10% of providers", "top_10_percent_share", format_percent),
        ("Gini score of jobs per provider", "gini", format_decimal),
        (
            f"Good newcomers with a first job within {HIRED_WITHIN_DAYS} days",
            "good_newcomers_hired_within_30_days",
            format_percent,
        ),
        ("Median wait for a first job (good newcomers)", "median_first_job_wait_days", format_wait),
        ("Chance a job goes well (average hired skill)", "average_hired_skill", format_percent_1dp),
        ("Average distance to the job", "average_distance_km", format_km),
        ("Jobs filled", "jobs_filled", format_count),
    ]
    table_lines = [
        "| Measure | " + " | ".join(names) + " |",
        "|---" * (len(names) + 1) + "|",
        *(
            f"| {label} | " + " | ".join(formatter(summaries[name][key]) for name in names) + " |"
            for label, key, formatter in rows
        ),
    ]
    return SUMMARY_TEMPLATE.format(
        provider_count=config.provider_count,
        job_count=f"{config.job_count:,}",
        day_count=config.day_count,
        seed=seed,
        radius_km=config.search_radius_km,
        table="\n".join(table_lines),
    )


def format_percent(value: float) -> str:
    """Formats a share as a whole percentage."""
    return f"{value:.0%}"


def format_percent_1dp(value: float) -> str:
    """Formats a share as a percentage with one decimal."""
    return f"{value:.1%}"


def format_decimal(value: float) -> str:
    """Formats a score with two decimals."""
    return f"{value:.2f}"


def format_wait(days: float | None) -> str:
    """Formats a median wait, or "never" when most never got a job."""
    return "never" if days is None else f"{days:.0f} days"


def format_km(distance_km: float) -> str:
    """Formats a distance in km."""
    return f"{distance_km:.1f} km"


def format_count(count: int) -> str:
    """Formats a whole number with thousands separators."""
    return f"{count:,}"


SUMMARY_TEMPLATE = """# Fairness simulation results

Fixa's ranking (`rank_providers`, unchanged) against plain sort-by-rating, in a simulated
city: {provider_count} providers, {job_count} jobs over {day_count} days, random seed {seed}.
"Fixa without exploring" is the same ranking with the Thompson draw replaced by the
expected chance of success and no newcomer slot. It is only there to show what exploring
costs.

Regenerate from the repo root: `node scripts/run-python.mjs -m ranking.simulation`

{table}

## How the simulation works

- Providers and job spots are spread at random over a 20 km square city. Every provider
  within {radius_km:.0f} km of a job is a candidate, for every ranker.
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
"""
