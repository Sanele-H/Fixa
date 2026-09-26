"""The fairness simulation: its measures, the comparison rankers, and a small full run."""

import copy
from datetime import date, timedelta

import numpy as np
import pytest

from ranking import Candidate, JobOutcome, JobRequest, ProviderStats
from ranking.simulation import (
    FIXA_RANKER_NAME,
    NO_EXPLORING_RANKER_NAME,
    RATING_RANKER_NAME,
    compare_rankers,
)
from ranking.simulation.baseline import rank_by_rating, rank_without_exploring
from ranking.simulation.metrics import (
    calculate_gini,
    calculate_median_wait_days,
    calculate_share_hired_within,
    calculate_top_share,
    summarise_result,
)
from ranking.simulation.report import write_report
from ranking.simulation.run import run_simulation
from ranking.simulation.world import SimConfig, create_jobs, create_providers

SMALL_CONFIG = SimConfig(provider_count=60, job_count=400, day_count=100)
SEED = 5
TODAY = date(2026, 9, 29)
LAST_MONTH = TODAY - timedelta(days=30)
SMALL_JOB = JobRequest(trade="plumbing", size="small", posted_on=TODAY)


@pytest.fixture(scope="module")
def results():
    return compare_rankers(SMALL_CONFIG, SEED)


@pytest.fixture(scope="module")
def summaries(results):
    return {name: summarise_result(result, SMALL_CONFIG) for name, result in results.items()}


def make_candidate(provider_id: str, distance_km: float, good_jobs: int, bad_jobs: int = 0):
    """Makes a plumber with the given numbers of good and bad (no-show) jobs."""
    outcomes = [JobOutcome(finished_on=LAST_MONTH, completed=True) for _ in range(good_jobs)]
    outcomes += [JobOutcome(finished_on=LAST_MONTH, completed=False) for _ in range(bad_jobs)]
    return Candidate(
        provider_id=provider_id,
        display_name=provider_id,
        trades=["plumbing"],
        distance_km=distance_km,
        stats=ProviderStats(outcomes=outcomes),
    )


def list_ids(ranked) -> list[str]:
    """Returns the provider ids of a ranked list, in order."""
    return [card.provider_id for card in ranked]


def test_gini_is_zero_when_equal_and_high_when_one_gets_everything():
    assert calculate_gini([5, 5, 5, 5]) == pytest.approx(0.0)
    assert calculate_gini([0, 0, 0, 20]) == pytest.approx(0.75)
    assert calculate_gini([0, 0, 0]) == 0.0


def test_top_share_counts_the_busiest_tenth():
    assert calculate_top_share([1] * 10) == pytest.approx(0.1)
    assert calculate_top_share([0] * 9 + [30]) == pytest.approx(1.0)


def test_waits_count_never_hired_newcomers_as_not_hired():
    waits = [2, 10, None, 40]
    assert calculate_share_hired_within(waits, 30) == 0.5
    assert calculate_median_wait_days([2, 10, None, 40, 50]) == 40.0
    assert calculate_median_wait_days([2, 10, None, None, None]) is None


def test_sort_by_rating_puts_the_best_rating_first_and_unrated_last():
    candidates = [
        make_candidate("unrated", 0.5, good_jobs=0),
        make_candidate("patchy", 1.0, good_jobs=5, bad_jobs=5),
        make_candidate("perfect_few", 9.0, good_jobs=2),
        make_candidate("perfect_many", 9.5, good_jobs=12),
    ]
    ranked = rank_by_rating(SMALL_JOB, candidates, np.random.default_rng(SEED))
    assert list_ids(ranked) == ["perfect_many", "perfect_few", "patchy", "unrated"]


def test_ranking_without_exploring_ignores_the_rng_and_has_no_newcomer_slot():
    candidates = [make_candidate(f"pro_{km}", float(km), good_jobs=20) for km in range(1, 7)]
    candidates.append(make_candidate("newcomer", 10.0, good_jobs=0))
    first = rank_without_exploring(SMALL_JOB, candidates, np.random.default_rng(1))
    second = rank_without_exploring(SMALL_JOB, candidates, np.random.default_rng(2))
    assert list_ids(first) == list_ids(second)
    assert list_ids(first)[-1] == "newcomer"


def test_a_run_repeats_with_the_same_seed_and_leaves_its_inputs_alone():
    world_rng = np.random.default_rng(SEED)
    providers = create_providers(world_rng, SMALL_CONFIG)
    jobs = create_jobs(world_rng, SMALL_CONFIG)
    providers_before = copy.deepcopy(providers)
    first = run_simulation("fixa", rank_by_rating, providers, jobs, SMALL_CONFIG, SEED)
    second = run_simulation("fixa", rank_by_rating, providers, jobs, SMALL_CONFIG, SEED)
    assert first.hires == second.hires
    assert providers == providers_before


def test_every_ranker_faces_the_same_jobs(summaries):
    filled_and_unfilled = {s["jobs_filled"] + s["jobs_unfilled"] for s in summaries.values()}
    assert filled_and_unfilled == {SMALL_CONFIG.job_count}


def test_fixa_spreads_work_more_than_sort_by_rating(summaries):
    fixa, rating = summaries[FIXA_RANKER_NAME], summaries[RATING_RANKER_NAME]
    assert fixa["top_10_percent_share"] < rating["top_10_percent_share"]
    assert fixa["gini"] < rating["gini"]


def test_good_newcomers_get_work_sooner_with_fixa(summaries):
    fixa, rating = summaries[FIXA_RANKER_NAME], summaries[RATING_RANKER_NAME]
    assert fixa["good_newcomers"] > 0
    assert (
        fixa["good_newcomers_hired_within_30_days"] > rating["good_newcomers_hired_within_30_days"]
    )


def test_exploring_costs_little_job_quality(summaries):
    fixa, no_exploring = summaries[FIXA_RANKER_NAME], summaries[NO_EXPLORING_RANKER_NAME]
    assert no_exploring["average_hired_skill"] - fixa["average_hired_skill"] < 0.03


def test_report_writes_three_charts_and_a_summary(results, tmp_path):
    write_report(results, SMALL_CONFIG, SEED, tmp_path)
    for file_name in ["work_concentration.png", "newcomer_first_job.png", "job_quality.png"]:
        assert (tmp_path / file_name).read_bytes().startswith(b"\x89PNG")
    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "| Jobs to the busiest 10% of providers |" in summary
