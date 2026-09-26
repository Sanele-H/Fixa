"""trust_summary: a score with a range from job evidence only, a breakdown, and a label."""

from datetime import date, timedelta

import pytest

from ranking import JobOutcome, ProviderStats, trust_summary

TODAY = date(2026, 9, 29)
LAST_MONTH = TODAY - timedelta(days=30)
THREE_YEARS_AGO = TODAY - timedelta(days=3 * 365)


def make_stats(good_jobs: int = 0, bad_jobs: int = 0, bad_on: date = LAST_MONTH) -> ProviderStats:
    """Makes evidence: good in-app jobs last month, and bad ones (no-shows) on bad_on."""
    good = [JobOutcome(finished_on=LAST_MONTH, completed=True) for _ in range(good_jobs)]
    bad = [JobOutcome(finished_on=bad_on, completed=False) for _ in range(bad_jobs)]
    return ProviderStats(outcomes=good + bad)


def test_newcomer_gets_no_score_and_the_new_label():
    summary = trust_summary(make_stats(good_jobs=2), TODAY)
    assert (summary.score, summary.low, summary.high) == (None, None, None)
    assert summary.label == "New, building a record"


@pytest.mark.parametrize(("good_jobs", "bad_jobs"), [(0, 1), (0, 8), (2, 1)])
def test_a_no_show_ends_the_new_label_and_shows_in_the_score(good_jobs, bad_jobs):
    summary = trust_summary(make_stats(good_jobs, bad_jobs), TODAY)
    assert summary.score is not None
    assert summary.label != "New, building a record"


def test_score_sits_inside_its_range_with_two_decimals():
    summary = trust_summary(make_stats(good_jobs=12, bad_jobs=3), TODAY)
    assert 0 <= summary.low <= summary.score <= summary.high <= 1
    for value in (summary.score, summary.low, summary.high):
        assert value == round(value, 2)


def test_more_evidence_narrows_the_range():
    few = trust_summary(make_stats(good_jobs=4, bad_jobs=1), TODAY)
    many = trust_summary(make_stats(good_jobs=40, bad_jobs=10), TODAY)
    assert many.high - many.low < few.high - few.low


@pytest.mark.parametrize(
    ("good_jobs", "bad_jobs", "label"),
    [
        (30, 0, "Strong record"),
        (16, 4, "Good record"),
        (6, 6, "Mixed record"),
    ],
)
def test_label_follows_the_score_and_range(good_jobs, bad_jobs, label):
    assert trust_summary(make_stats(good_jobs, bad_jobs), TODAY).label == label


def test_old_failures_count_less_than_recent_ones():
    recent = trust_summary(make_stats(good_jobs=10, bad_jobs=5), TODAY)
    old = trust_summary(make_stats(good_jobs=10, bad_jobs=5, bad_on=THREE_YEARS_AGO), TODAY)
    assert old.score > recent.score


def test_today_defaults_to_the_real_date():
    stats = make_stats(good_jobs=10, bad_jobs=2)
    assert trust_summary(stats) == trust_summary(stats, date.today())


def test_breakdown_counts_the_job_evidence():
    outcomes = [
        JobOutcome(finished_on=LAST_MONTH, completed=True, still_working=True),
        JobOutcome(finished_on=LAST_MONTH, completed=True, still_working=False),
        JobOutcome(finished_on=LAST_MONTH, completed=True),
        JobOutcome(finished_on=LAST_MONTH, completed=True),
        JobOutcome(finished_on=LAST_MONTH, completed=False),  # a no-show
        JobOutcome(finished_on=LAST_MONTH, completed=True, off_app=True),
        JobOutcome(finished_on=LAST_MONTH, completed=True, off_app=True),
    ]
    summary = trust_summary(ProviderStats(outcomes=outcomes, repeat_customers=1), TODAY)
    assert summary.n_evidence == 7
    assert summary.breakdown.model_dump() == {
        "jobs": 4,
        "repeat_customers": 1,
        "off_app_confirmed": 2,
        "still_working_rate": 0.5,
    }


def test_still_working_rate_is_none_until_a_customer_answers():
    summary = trust_summary(make_stats(good_jobs=3), TODAY)
    assert summary.breakdown.still_working_rate is None
