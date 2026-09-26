"""The simulated city: providers with a hidden true skill, and the jobs customers post.

Locations are (x, y) in km on a square city. Everyone is a plumber, so every provider
within the search radius competes for every job. Some providers have been working for a
year before the simulation starts (with a record), the rest join during it (newcomers).
True skill and group are hidden: the rankers only ever see job outcomes.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np

from ranking.models import JobOutcome, ProviderStats

SIM_START_DATE = date(2026, 1, 1)
TRADE = "plumbing"
CITY_SIZE_KM = 20.0
TRUE_SKILL_BETA = (8.0, 2.0)  # mean 0.8: most providers are good, some much less so
# Hidden group label (first language), drawn independently of skill for the fairness check.
GROUP_WEIGHTS = {"zu": 0.35, "xh": 0.25, "st": 0.2, "sn": 0.2}
ESTABLISHED_SHARE = 0.6  # share of providers already working when the simulation starts
MEAN_HISTORY_JOBS = 10  # jobs an established provider did in the year before the start
HISTORY_DAYS = 365
NEWCOMER_JOIN_SHARE_OF_RUN = 0.75  # newcomers join during the first 75% of the run
JOB_SIZE_WEIGHTS = {"small": 0.6, "medium": 0.3, "large": 0.1}


@dataclass(frozen=True)
class SimConfig:
    """How big a simulation run is."""

    provider_count: int = 200
    job_count: int = 2000
    day_count: int = 200
    search_radius_km: float = 10.0  # the providers P2 would pass in for a job


@dataclass
class SimProvider:
    """A provider in the simulation, with the hidden truth and their current workload."""

    provider_id: str
    x_km: float
    y_km: float
    true_skill: float  # the chance a job they do goes well; hidden from the rankers
    group: str  # hidden first language
    joined_day: int  # negative for providers working before the simulation starts
    stats: ProviderStats  # the evidence the rankers see
    pending_outcomes: list[tuple[int, JobOutcome]] = field(default_factory=list)
    active_job_end_days: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class SimJob:
    """A job a customer posts on a given day, at a given spot."""

    day: int
    x_km: float
    y_km: float
    size: str


def convert_day_to_date(day: int) -> date:
    """Converts a simulation day (0 is the start) to a calendar date."""
    return SIM_START_DATE + timedelta(days=day)


def create_providers(rng: np.random.Generator, config: SimConfig) -> list[SimProvider]:
    """Creates the providers: established ones with a year's record, and newcomers."""
    return [create_provider(rng, index, config) for index in range(1, config.provider_count + 1)]


def create_provider(rng: np.random.Generator, number: int, config: SimConfig) -> SimProvider:
    """Creates one provider at a random spot, with a hidden true skill and group."""
    true_skill = float(rng.beta(*TRUE_SKILL_BETA))
    groups = list(GROUP_WEIGHTS)
    group = groups[int(rng.choice(len(groups), p=list(GROUP_WEIGHTS.values())))]
    is_established = rng.random() < ESTABLISHED_SHARE
    newcomer_join_days = int(config.day_count * NEWCOMER_JOIN_SHARE_OF_RUN)
    joined_day = -HISTORY_DAYS if is_established else int(rng.integers(0, newcomer_join_days))
    history = create_history(rng, true_skill) if is_established else []
    return SimProvider(
        provider_id=f"sim_{number:03d}",
        x_km=float(rng.uniform(0.0, CITY_SIZE_KM)),
        y_km=float(rng.uniform(0.0, CITY_SIZE_KM)),
        true_skill=true_skill,
        group=group,
        joined_day=joined_day,
        stats=ProviderStats(outcomes=history),
    )


def create_history(rng: np.random.Generator, true_skill: float) -> list[JobOutcome]:
    """Creates an established provider's record from the year before the simulation."""
    job_count = int(rng.poisson(MEAN_HISTORY_JOBS))
    return [
        JobOutcome(
            finished_on=convert_day_to_date(-int(rng.integers(1, HISTORY_DAYS + 1))),
            completed=True,
            still_working=bool(rng.random() < true_skill),
        )
        for _ in range(job_count)
    ]


def create_jobs(rng: np.random.Generator, config: SimConfig) -> list[SimJob]:
    """Creates the jobs customers post, spread over the run's days, in day order."""
    days = np.sort(rng.integers(0, config.day_count, size=config.job_count))
    sizes = list(JOB_SIZE_WEIGHTS)
    size_probabilities = list(JOB_SIZE_WEIGHTS.values())
    return [
        SimJob(
            day=int(day),
            x_km=float(rng.uniform(0.0, CITY_SIZE_KM)),
            y_km=float(rng.uniform(0.0, CITY_SIZE_KM)),
            size=sizes[int(rng.choice(len(sizes), p=size_probabilities))],
        )
        for day in days
    ]
