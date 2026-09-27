"""Runs one ranker over the simulated jobs: rank, let the customer pick, record the outcome.

For each job, in day order:
1. Outcomes of jobs finished by that day become visible evidence, and finished jobs stop
   counting towards the provider's workload.
2. Providers within the search radius become Candidates, exactly as P2 builds them, and
   the ranker orders them.
3. The customer picks from the top 5, the top places more often. A provider already
   doing PROVIDER_CAPACITY_JOBS jobs turns it down, whichever ranker is used.
4. The job goes well as often as the hired provider's hidden true skill. The outcome
   becomes evidence when the job ends.
"""

import copy
import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from ranking.models import Candidate, JobOutcome, JobRequest, ProviderStats, RankedProvider
from ranking.simulation.world import TRADE, SimConfig, SimJob, SimProvider, convert_day_to_date

Ranker = Callable[[JobRequest, list[Candidate], np.random.Generator], list[RankedProvider]]

CUSTOMER_PICK_WEIGHTS = [0.4, 0.25, 0.15, 0.12, 0.08]  # how often each top place is picked
PROVIDER_CAPACITY_JOBS = 3  # a provider already doing this many jobs turns new ones down
MIN_JOB_DAYS = 1
MAX_JOB_DAYS = 3
RANKING_STREAM = 1  # separate random streams, so each ranker faces the same customers
CUSTOMER_STREAM = 2


@dataclass(frozen=True)
class Hire:
    """A job that found a provider."""

    job_day: int
    job_size: str
    provider_id: str
    true_skill: float
    distance_km: float


@dataclass
class SimulationResult:
    """What happened in one run: who got which job, and the providers' final state."""

    ranker_name: str
    providers: list[SimProvider]
    hires: list[Hire]
    unfilled_job_count: int


class SimulationRun:
    """One run of one ranker over the simulated jobs, on its own copy of the providers."""

    def __init__(
        self,
        ranker: Ranker,
        providers: list[SimProvider],
        config: SimConfig,
        seed: int,
    ) -> None:
        self.ranker = ranker
        self.providers = copy.deepcopy(providers)
        self.providers_by_id = {provider.provider_id: provider for provider in self.providers}
        self.config = config
        self.ranking_rng = np.random.default_rng([seed, RANKING_STREAM])
        self.customer_rng = np.random.default_rng([seed, CUSTOMER_STREAM])

    def fill_job(self, job: SimJob) -> Hire | None:
        """Ranks providers for a job and lets the customer hire one. None if nobody could."""
        for provider in self.providers:
            update_provider(provider, job.day)
        request = JobRequest(trade=TRADE, size=job.size, posted_on=convert_day_to_date(job.day))
        candidates = build_candidates(self.providers, job, self.config.search_radius_km)
        ranked = self.ranker(request, candidates, self.ranking_rng)
        card = pick_provider_card(self.customer_rng, ranked, self.providers_by_id)
        if card is None:
            return None
        provider = self.providers_by_id[card.provider_id]
        return record_hire(self.customer_rng, provider, job, card.distance_km)


def run_simulation(
    ranker_name: str,
    ranker: Ranker,
    providers: list[SimProvider],
    jobs: list[SimJob],
    config: SimConfig,
    seed: int,
) -> SimulationResult:
    """Runs a ranker over every job in order and returns who got what.

    The providers passed in aren't changed, so several rankers can run on the same world.
    """
    run = SimulationRun(ranker, providers, config, seed)
    hires_or_none = [run.fill_job(job) for job in jobs]
    hires = [hire for hire in hires_or_none if hire is not None]
    return SimulationResult(ranker_name, run.providers, hires, len(jobs) - len(hires))


def update_provider(provider: SimProvider, day: int) -> None:
    """Makes outcomes of jobs finished by this day visible, and frees up those jobs."""
    due_outcomes = [outcome for show_day, outcome in provider.pending_outcomes if show_day <= day]
    if due_outcomes:
        provider.stats = ProviderStats(
            outcomes=provider.stats.outcomes + due_outcomes,
            repeat_customers=provider.stats.repeat_customers,
        )
        provider.pending_outcomes = [
            (show_day, outcome) for show_day, outcome in provider.pending_outcomes if show_day > day
        ]
    provider.active_job_end_days = [
        end_day for end_day in provider.active_job_end_days if end_day > day
    ]


def build_candidates(
    providers: list[SimProvider], job: SimJob, search_radius_km: float
) -> list[Candidate]:
    """Builds a Candidate for each provider who has joined and is within the search radius."""
    candidates = []
    for provider in providers:
        distance_km = math.hypot(provider.x_km - job.x_km, provider.y_km - job.y_km)
        if provider.joined_day <= job.day and distance_km <= search_radius_km:
            candidates.append(create_candidate(provider, distance_km))
    return candidates


def create_candidate(provider: SimProvider, distance_km: float) -> Candidate:
    """Creates the Candidate the rankers see: evidence, distance and workload, never truth."""
    return Candidate(
        provider_id=provider.provider_id,
        display_name=provider.provider_id,
        trades=[TRADE],
        distance_km=distance_km,
        active_jobs=len(provider.active_job_end_days),
        stats=provider.stats,
    )


def pick_provider_card(
    rng: np.random.Generator, ranked: list[RankedProvider], providers_by_id: dict[str, SimProvider]
) -> RankedProvider | None:
    """Picks the provider the customer hires from the top of the list.

    Providers at capacity turn the job down, so the customer picks among the first few who
    are free, the higher places more often. None if nobody listed is free.
    """
    free_cards = [
        card
        for card in ranked
        if len(providers_by_id[card.provider_id].active_job_end_days) < PROVIDER_CAPACITY_JOBS
    ][: len(CUSTOMER_PICK_WEIGHTS)]
    if not free_cards:
        return None
    weights = np.array(CUSTOMER_PICK_WEIGHTS[: len(free_cards)])
    return free_cards[int(rng.choice(len(free_cards), p=weights / weights.sum()))]


def record_hire(
    rng: np.random.Generator, provider: SimProvider, job: SimJob, distance_km: float
) -> Hire:
    """Books the job into the provider's workload and schedules its outcome."""
    end_day = job.day + int(rng.integers(MIN_JOB_DAYS, MAX_JOB_DAYS + 1))
    went_well = bool(rng.random() < provider.true_skill)
    outcome = JobOutcome(
        finished_on=convert_day_to_date(end_day), completed=True, still_working=went_well
    )
    provider.active_job_end_days.append(end_day)
    provider.pending_outcomes.append((end_day, outcome))
    return Hire(job.day, job.size, provider.provider_id, provider.true_skill, distance_km)
