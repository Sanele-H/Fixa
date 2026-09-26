"""The fairness check (step 4): do groups of equal true skill get equal work and scores?

The groups are providers' hidden first language. No ranker ever sees it, so a difference
between groups could only creep in through the evidence. The check compares like with like:

- Work: each provider's jobs per 30 days on the app, divided by the average for providers
  in the same true-skill band. 100% means as much work as equally skilled providers.
- Scores: each established provider's trust score at the end of the run, divided by
  their true skill. Equal ratios across groups mean equal skill gets an equal score.

Each group's figure is the average over its providers.
"""

import bisect
from dataclasses import dataclass

from ranking.simulation.run import SimulationResult
from ranking.simulation.world import SimConfig, SimProvider, convert_day_to_date
from ranking.trust import trust_summary

GROUP_NAMES = {"zu": "isiZulu", "xh": "isiXhosa", "st": "Sesotho", "sn": "chiShona"}
SKILL_BAND_EDGES = [0.7, 0.8, 0.9]  # bands: below 0.7, 0.7-0.8, 0.8-0.9, 0.9 and above
DAYS_PER_MONTH = 30


@dataclass(frozen=True)
class GroupFairness:
    """How one group fared, relative to equally skilled providers."""

    group: str
    provider_count: int
    work_ratio: float  # 1.0 = as much work as equally skilled providers
    score_ratio: float | None  # average trust score / true skill; None with no scores yet


def check_fairness(result: SimulationResult, config: SimConfig) -> list[GroupFairness]:
    """Compares each hidden group's work and trust scores with equally skilled providers."""
    monthly_jobs = calculate_monthly_jobs(result, config)
    relative_work = compare_with_same_skill(result.providers, monthly_jobs)
    score_ratios = calculate_score_ratios(result.providers, config)
    return [
        summarise_group(group, result.providers, relative_work, score_ratios)
        for group in GROUP_NAMES
    ]


def calculate_monthly_jobs(result: SimulationResult, config: SimConfig) -> dict[str, float]:
    """Returns each provider's jobs per 30 days on the app during the run, by provider id."""
    job_counts = {provider.provider_id: 0 for provider in result.providers}
    for hire in result.hires:
        job_counts[hire.provider_id] += 1
    return {
        provider.provider_id: job_counts[provider.provider_id]
        * DAYS_PER_MONTH
        / max(1, config.day_count - max(0, provider.joined_day))
        for provider in result.providers
    }


def compare_with_same_skill(
    providers: list[SimProvider], monthly_jobs: dict[str, float]
) -> dict[str, float]:
    """Divides each provider's monthly jobs by the average in their true-skill band."""
    band_by_id = {
        provider.provider_id: bisect.bisect(SKILL_BAND_EDGES, provider.true_skill)
        for provider in providers
    }
    band_averages = {
        band: average([monthly_jobs[id_] for id_, id_band in band_by_id.items() if id_band == band])
        for band in set(band_by_id.values())
    }
    return {
        id_: monthly_jobs[id_] / band_averages[band] if band_averages[band] > 0 else 1.0
        for id_, band in band_by_id.items()
    }


def calculate_score_ratios(providers: list[SimProvider], config: SimConfig) -> dict[str, float]:
    """Returns trust score / true skill at the end of the run, for providers with a score."""
    end_date = convert_day_to_date(config.day_count)
    score_ratios = {}
    for provider in providers:
        score = trust_summary(provider.stats, end_date).score
        if score is not None:
            score_ratios[provider.provider_id] = score / provider.true_skill
    return score_ratios


def summarise_group(
    group: str,
    providers: list[SimProvider],
    relative_work: dict[str, float],
    score_ratios: dict[str, float],
) -> GroupFairness:
    """Averages the work and score ratios over one group's providers."""
    member_ids = [provider.provider_id for provider in providers if provider.group == group]
    member_scores = [score_ratios[id_] for id_ in member_ids if id_ in score_ratios]
    return GroupFairness(
        group=group,
        provider_count=len(member_ids),
        work_ratio=average([relative_work[id_] for id_ in member_ids]),
        score_ratio=average(member_scores) if member_scores else None,
    )


def average(values: list[float]) -> float:
    """Returns the mean of a non-empty list."""
    return sum(values) / len(values)
