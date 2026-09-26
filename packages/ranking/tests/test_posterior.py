"""The Beta posterior behind the ranking: what counts as a good job, and how much it counts."""

from datetime import date, timedelta

import numpy as np
import pytest

from ranking import JobOutcome, ProviderStats
from ranking.posterior import (
    PRIOR_FAILURES,
    PRIOR_SUCCESSES,
    RECENCY_HALF_LIFE_DAYS,
    calculate_posterior,
    draw_success_chance,
    weigh_outcome,
    went_well,
)

TODAY = date(2026, 9, 29)
LAST_WEEK = TODAY - timedelta(days=7)
THREE_YEARS_AGO = TODAY - timedelta(days=3 * 365)


def make_outcomes(count: int, finished_on: date, **fields) -> list[JobOutcome]:
    """Makes count identical outcomes finished on the given day."""
    return [JobOutcome(finished_on=finished_on, **fields) for _ in range(count)]


def test_no_evidence_gives_the_prior():
    posterior = calculate_posterior(ProviderStats(), TODAY)
    assert (posterior.successes, posterior.failures) == (PRIOR_SUCCESSES, PRIOR_FAILURES)
    assert posterior.mean == pytest.approx(0.8)


@pytest.mark.parametrize(
    ("outcome_fields", "expected"),
    [
        ({"completed": True}, True),  # no "still working?" answer yet
        ({"completed": True, "still_working": True}, True),
        ({"completed": True, "still_working": False}, False),
        ({"completed": False}, False),  # a no-show
    ],
)
def test_what_counts_as_a_job_that_went_well(outcome_fields, expected):
    assert went_well(JobOutcome(finished_on=TODAY, **outcome_fields)) is expected


def test_good_jobs_raise_the_mean_and_bad_ones_lower_it():
    prior_mean = calculate_posterior(ProviderStats(), TODAY).mean
    good = ProviderStats(outcomes=make_outcomes(5, TODAY, completed=True, still_working=True))
    bad = ProviderStats(outcomes=make_outcomes(5, TODAY, completed=True, still_working=False))
    assert calculate_posterior(good, TODAY).mean > prior_mean
    assert calculate_posterior(bad, TODAY).mean < prior_mean


def test_weight_halves_every_half_life_and_off_app_counts_half():
    half_life_ago = TODAY - timedelta(days=RECENCY_HALF_LIFE_DAYS)
    assert weigh_outcome(JobOutcome(finished_on=TODAY, completed=True), TODAY) == 1.0
    assert weigh_outcome(JobOutcome(finished_on=half_life_ago, completed=True), TODAY) == 0.5
    off_app = JobOutcome(finished_on=TODAY, completed=True, off_app=True)
    assert weigh_outcome(off_app, TODAY) == 0.5


def test_a_future_date_counts_as_today():
    tomorrow = TODAY + timedelta(days=1)
    assert weigh_outcome(JobOutcome(finished_on=tomorrow, completed=True), TODAY) == 1.0


def test_recent_failures_hurt_more_than_old_ones():
    good_jobs = make_outcomes(10, LAST_WEEK, completed=True, still_working=True)
    recent_failures = make_outcomes(5, LAST_WEEK, completed=False)
    old_failures = make_outcomes(5, THREE_YEARS_AGO, completed=False)
    recent_stats = ProviderStats(outcomes=good_jobs + recent_failures)
    old_stats = ProviderStats(outcomes=good_jobs + old_failures)
    assert (
        calculate_posterior(recent_stats, TODAY).mean < calculate_posterior(old_stats, TODAY).mean
    )


def test_draws_are_chances_and_repeat_with_the_same_seed():
    posterior = calculate_posterior(ProviderStats(), TODAY)
    first_draws = [draw_success_chance(posterior, np.random.default_rng(3)) for _ in range(5)]
    second_draws = [draw_success_chance(posterior, np.random.default_rng(3)) for _ in range(5)]
    assert first_draws == second_draws
    assert all(0.0 <= draw <= 1.0 for draw in first_draws)
