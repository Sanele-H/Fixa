"""Fairness simulation: how long does a GOOD newcomer wait for their first job under
sort-by-rating versus our ranking, and does job quality drop?

Owner: Role 4. Run from the repo root:  npm run simulate
It imports the real ranking from fixa.ranking, so the chart measures what the app ships.

Outputs (git-ignored until you commit the final ones on purpose):
    results/fairness_summary.csv
    results/fairness_chart.png
"""

import random
from dataclasses import dataclass
from pathlib import Path

from fixa.ranking.provider_ranking import (
    NewcomerFriendlyStrategy,
    ProviderRecord,
    RankingStrategy,
    SortByRatingStrategy,
)

RESULTS_DIRECTORY_PATH = Path(__file__).parent / "results"

# Assumptions - every one of these is a judgement call. Write down why you chose each value
# (README.md), because judges may ask.
PROVIDER_COUNT = 200
NEWCOMER_SHARE = 0.25
JOB_COUNT = 2_000
SIMULATED_DAY_COUNT = 30
CANDIDATES_PER_JOB = 40
SMALL_JOB_SHARE = 0.6
RUN_COUNT = 20
RANDOM_SEED = 2026


@dataclass
class SimulatedProvider:
    """A provider plus the hidden truth the app can't see.

    Attributes:
        true_quality_in_stars: How good they really are (1-5). Ratings are noisy samples of it.
        first_job_day: Day they got their first job, or None if they never did.
    """

    provider_id: str
    true_quality_in_stars: float
    is_newcomer_at_start: bool
    rating_sum: float = 0.0
    rating_count: int = 0
    completed_job_count: int = 0
    offer_count: int = 0
    first_job_day: float | None = None

    def to_record(self) -> ProviderRecord:
        """Return what the ranking is allowed to see (no true quality)."""
        return ProviderRecord(
            provider_id=self.provider_id,
            rating_sum=self.rating_sum,
            rating_count=self.rating_count,
            completed_job_count=self.completed_job_count,
            offer_count=self.offer_count,
        )


def create_providers(random_generator: random.Random) -> list[SimulatedProvider]:
    """Create PROVIDER_COUNT providers: established ones with a rating history, and newcomers.

    TODO (Role 4, Day 2): choose the quality distribution and how much history established
    providers start with.
    """
    raise NotImplementedError("TODO Role 4: create_providers")


def simulate_jobs(
    providers: list[SimulatedProvider],
    strategy: RankingStrategy,
    random_generator: random.Random,
) -> list[float]:
    """Run JOB_COUNT jobs through `strategy` and return the star rating of every completed job.

    For each job: pick candidates, shortlist them with the strategy, let the customer choose
    (people mostly pick near the top), rate the work from the provider's true quality.

    TODO (Role 4, Day 2-3).
    """
    raise NotImplementedError("TODO Role 4: simulate_jobs")


def summarise_run(providers: list[SimulatedProvider], job_ratings: list[float]) -> dict:
    """Return the headline numbers for one run.

    TODO (Role 4, Day 3): share of good newcomers with a first job, median days to first job
    (count "never" separately), average job rating.
    """
    raise NotImplementedError("TODO Role 4: summarise_run")


def draw_fairness_chart(
    summaries_by_strategy_name: dict[str, list[dict]], chart_path: Path
) -> None:
    """Draw the pitch chart. See README.md for the chart spec.

    TODO (Role 4, Day 5): matplotlib, one chart, two lines.
    """
    raise NotImplementedError("TODO Role 4: draw_fairness_chart")


def main() -> None:
    """Run both strategies RUN_COUNT times with the same seeds and save the summary and chart."""
    strategies: list[RankingStrategy] = [
        SortByRatingStrategy(),
        NewcomerFriendlyStrategy(),
    ]
    summaries_by_strategy_name: dict[str, list[dict]] = {
        strategy.name: [] for strategy in strategies
    }
    for run_index in range(RUN_COUNT):
        for strategy in strategies:
            random_generator = random.Random(RANDOM_SEED + run_index)
            providers = create_providers(random_generator)
            job_ratings = simulate_jobs(providers, strategy, random_generator)
            summaries_by_strategy_name[strategy.name].append(summarise_run(providers, job_ratings))
    RESULTS_DIRECTORY_PATH.mkdir(exist_ok=True)
    draw_fairness_chart(summaries_by_strategy_name, RESULTS_DIRECTORY_PATH / "fairness_chart.png")


if __name__ == "__main__":
    main()
