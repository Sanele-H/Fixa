"""What the simulation measures, for one run.

- How concentrated work is: the share of jobs the busiest 10% of providers get, and the
  Gini score of jobs per provider (0 = everyone gets the same, near 1 = one gets all).
- How long good newcomers wait for their first job.
- The cost of exploring: the average true skill of whoever got each job.
- How far providers travel to jobs.
"""

import math

from ranking.simulation.run import SimulationResult
from ranking.simulation.world import SimConfig

TOP_PROVIDER_SHARE = 0.1  # "the busiest 10% of providers"
GOOD_NEWCOMER_SKILL = 0.8  # a good newcomer is at least as skilled as the average provider
WAIT_WINDOW_DAYS = 60  # only newcomers who joined at least this long before the end count
HIRED_WITHIN_DAYS = 30


def count_jobs_per_provider(result: SimulationResult) -> list[int]:
    """Counts the jobs each provider got, including the ones who got none."""
    job_counts = {provider.provider_id: 0 for provider in result.providers}
    for hire in result.hires:
        job_counts[hire.provider_id] += 1
    return list(job_counts.values())


def calculate_top_share(job_counts: list[int], provider_share: float = TOP_PROVIDER_SHARE) -> float:
    """Returns the share of all jobs that went to the busiest provider_share of providers."""
    total_jobs = sum(job_counts)
    if total_jobs == 0:
        return 0.0
    top_count = max(1, round(len(job_counts) * provider_share))
    return sum(sorted(job_counts, reverse=True)[:top_count]) / total_jobs


def calculate_gini(job_counts: list[int]) -> float:
    """Returns the Gini score of jobs per provider: 0 if all equal, near 1 if one gets all."""
    total_jobs = sum(job_counts)
    provider_count = len(job_counts)
    if total_jobs == 0:
        return 0.0
    weighted_sum = sum(rank * count for rank, count in enumerate(sorted(job_counts), start=1))
    return 2 * weighted_sum / (provider_count * total_jobs) - (provider_count + 1) / provider_count


def list_good_newcomer_waits(result: SimulationResult, config: SimConfig) -> list[int | None]:
    """Lists how many days each good newcomer waited for a first job (None: never got one).

    A good newcomer joined during the run, at least WAIT_WINDOW_DAYS before the end, and
    has a true skill of at least GOOD_NEWCOMER_SKILL.
    """
    first_job_days: dict[str, int] = {}
    for hire in result.hires:
        first_job_days.setdefault(hire.provider_id, hire.job_day)
    last_join_day = config.day_count - WAIT_WINDOW_DAYS
    good_newcomers = [
        provider
        for provider in result.providers
        if 0 <= provider.joined_day <= last_join_day and provider.true_skill >= GOOD_NEWCOMER_SKILL
    ]
    return [
        first_job_days[provider.provider_id] - provider.joined_day
        if provider.provider_id in first_job_days
        else None
        for provider in good_newcomers
    ]


def calculate_share_hired_within(waits: list[int | None], days: int) -> float:
    """Returns the share of newcomers whose first job came within this many days of joining."""
    if not waits:
        return 0.0
    return sum(1 for wait in waits if wait is not None and wait <= days) / len(waits)


def calculate_median_wait_days(waits: list[int | None]) -> float | None:
    """Returns the median wait for a first job, or None if most never got one."""
    if not waits:
        return None
    sorted_waits = sorted(math.inf if wait is None else wait for wait in waits)
    median_wait = sorted_waits[len(sorted_waits) // 2]
    return None if median_wait == math.inf else float(median_wait)


def calculate_average_hired_skill(result: SimulationResult) -> float:
    """Returns the average true skill of whoever got each job: the expected job quality."""
    return sum(hire.true_skill for hire in result.hires) / len(result.hires)


def calculate_average_distance_km(result: SimulationResult) -> float:
    """Returns how far, on average, the hired provider was from the job."""
    return sum(hire.distance_km for hire in result.hires) / len(result.hires)


def summarise_result(result: SimulationResult, config: SimConfig) -> dict:
    """Returns every measure for one run, by name."""
    job_counts = count_jobs_per_provider(result)
    waits = list_good_newcomer_waits(result, config)
    return {
        "jobs_filled": len(result.hires),
        "jobs_unfilled": result.unfilled_job_count,
        "top_10_percent_share": calculate_top_share(job_counts),
        "gini": calculate_gini(job_counts),
        "good_newcomers": len(waits),
        "good_newcomers_hired_within_30_days": calculate_share_hired_within(
            waits, HIRED_WITHIN_DAYS
        ),
        "median_first_job_wait_days": calculate_median_wait_days(waits),
        "average_hired_skill": calculate_average_hired_skill(result),
        "average_distance_km": calculate_average_distance_km(result),
    }
