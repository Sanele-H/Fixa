"""Charts and a summary table for the fairness check across hidden language groups.

Titles are written from the numbers, and they only claim equality when the groups really
are within FAIR_SPREAD of each other.
"""

import math
from pathlib import Path

from ranking.simulation.charts import draw_grouped_bar_chart
from ranking.simulation.fairness import GROUP_NAMES, GroupFairness

WORK_CHART_FILE_NAME = "fairness_work.png"
SCORE_CHART_FILE_NAME = "fairness_scores.png"
FAIR_SHARE = 1.0  # 100%: the same as equally skilled providers
FAIR_SPREAD = 0.1  # groups within 10 points of each other count as treated equally
AXIS_HEADROOM = 1.15  # room past the longest bar for its label
AXIS_STEP = 0.25  # the axis ends on a multiple of 25%
MIN_AXIS_MAX = 1.25


def draw_fairness_charts(
    results_dir_path: Path, fairness_by_ranker: dict[str, list[GroupFairness]], colors: dict
) -> None:
    """Draws the work chart (every ranker) and the trust score chart (Fixa, listed first)."""
    draw_work_chart(results_dir_path / WORK_CHART_FILE_NAME, fairness_by_ranker, colors)
    fixa_name = next(iter(fairness_by_ranker))
    draw_score_chart(
        results_dir_path / SCORE_CHART_FILE_NAME, fairness_by_ranker[fixa_name], colors[fixa_name]
    )


def draw_work_chart(
    path: Path, fairness_by_ranker: dict[str, list[GroupFairness]], colors: dict
) -> None:
    """Draws each language group's work compared with equally skilled providers, per ranker."""
    fixa_groups, rating_groups = fairness_by_ranker.values()
    fixa_low, fixa_high = find_range([group.work_ratio for group in fixa_groups])
    rating_low, rating_high = find_range([group.work_ratio for group in rating_groups])
    title = (
        f"With Fixa, every language group gets {fixa_low:.0%} to {fixa_high:.0%} "
        "of a fair share of work"
    )
    subtitle = (
        "Jobs per month compared with providers of the same true skill (100% = fair share).\n"
        f"Sort-by-rating: {rating_low:.0%} to {rating_high:.0%}. It never sees language either, "
        "but it gives most work to a few providers."
    )
    series = [
        (name, [group.work_ratio for group in groups], colors[name])
        for name, groups in fairness_by_ranker.items()
    ]
    all_values = [value for _, values, _ in series for value in values]
    draw_grouped_bar_chart(
        path,
        title,
        subtitle,
        list_group_names(fixa_groups),
        series,
        format_percent,
        choose_axis_max(all_values),
        FAIR_SHARE,
    )


def draw_score_chart(path: Path, groups: list[GroupFairness], color: str) -> None:
    """Draws each language group's average trust score divided by true skill."""
    score_ratios = [group.score_ratio or 0.0 for group in groups]
    low, high = find_range(score_ratios)
    if high - low <= FAIR_SPREAD:
        title = "Equal skill gets an equal trust score in every language group"
    else:
        title = f"Trust scores differ by up to {high - low:.0%} between language groups"
    subtitle = (
        f"Average trust score divided by true skill: {low:.0%} to {high:.0%} across groups.\n"
        "Groups are providers' first language, which no ranking or score ever sees."
    )
    draw_grouped_bar_chart(
        path,
        title,
        subtitle,
        list_group_names(groups),
        [("Fixa trust score", score_ratios, color)],
        format_percent,
        choose_axis_max(score_ratios),
        FAIR_SHARE,
    )


def build_fairness_markdown(fairness_by_ranker: dict[str, list[GroupFairness]]) -> str:
    """Builds the fairness section of summary.md: one row per language group."""
    fixa_groups, rating_groups = fairness_by_ranker.values()
    rows = [
        f"| {GROUP_NAMES[fixa.group]} | {fixa.provider_count} | {fixa.work_ratio:.0%} "
        f"| {rating.work_ratio:.0%} | {format_optional_percent(fixa.score_ratio)} |"
        for fixa, rating in zip(fixa_groups, rating_groups, strict=True)
    ]
    return FAIRNESS_TEMPLATE.format(rows="\n".join(rows))


def list_group_names(groups: list[GroupFairness]) -> list[str]:
    """Returns the display names of the groups, in order."""
    return [GROUP_NAMES[group.group] for group in groups]


def find_range(values: list[float]) -> tuple[float, float]:
    """Returns the smallest and largest value."""
    return min(values), max(values)


def choose_axis_max(values: list[float]) -> float:
    """Chooses an axis end past the longest bar, on a multiple of 25%."""
    return max(MIN_AXIS_MAX, math.ceil(max(values) * AXIS_HEADROOM / AXIS_STEP) * AXIS_STEP)


def format_percent(value: float) -> str:
    """Formats a ratio as a whole percentage."""
    return f"{value:.0%}"


def format_optional_percent(value: float | None) -> str:
    """Formats a ratio as a whole percentage, or a dash when there isn't one."""
    return "-" if value is None else f"{value:.0%}"


FAIRNESS_TEMPLATE = """
## Fairness across language groups

Groups are providers' hidden first language, which no ranking or trust score ever sees.
Work is jobs per month compared with providers of the same true skill (100% = fair share).
Score is the average trust score divided by true skill, for providers with a score.

| Group | Providers | Work with Fixa | Work with sort-by-rating | Fixa trust score / true skill |
|---|---|---|---|---|
{rows}

Sort-by-rating never sees language either. Its uneven shares come from giving most work to
a few providers: whichever groups those few belong to gain, by chance.
"""
