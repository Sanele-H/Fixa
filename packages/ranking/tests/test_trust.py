"""trust_summary. Step 0 stub: fixed numbers, but a real breakdown and the newcomer label."""

from datetime import date

from ranking import JobOutcome, ProviderStats, trust_summary

FINISHED_ON = date(2026, 9, 1)


def test_newcomer_gets_no_score_and_the_new_label():
    stats = ProviderStats(outcomes=[JobOutcome(finished_on=FINISHED_ON, completed=True)])
    summary = trust_summary(stats)
    assert (summary.score, summary.low, summary.high) == (None, None, None)
    assert summary.label == "New, building a record"


def test_established_provider_gets_a_score_inside_its_range():
    stats = ProviderStats(
        outcomes=[JobOutcome(finished_on=FINISHED_ON, completed=True) for _ in range(5)]
    )
    summary = trust_summary(stats)
    assert 0 <= summary.low <= summary.score <= summary.high <= 1


def test_breakdown_counts_the_job_evidence():
    outcomes = [
        JobOutcome(finished_on=FINISHED_ON, completed=True, still_working=True),
        JobOutcome(finished_on=FINISHED_ON, completed=True, still_working=False),
        JobOutcome(finished_on=FINISHED_ON, completed=True),
        JobOutcome(finished_on=FINISHED_ON, completed=True),
        JobOutcome(finished_on=FINISHED_ON, completed=False),  # a no-show
        JobOutcome(finished_on=FINISHED_ON, completed=True, off_app=True),
        JobOutcome(finished_on=FINISHED_ON, completed=True, off_app=True),
    ]
    summary = trust_summary(ProviderStats(outcomes=outcomes, repeat_customers=1))
    assert summary.n_evidence == 7
    assert summary.breakdown.model_dump() == {
        "jobs": 4,
        "repeat_customers": 1,
        "off_app_confirmed": 2,
        "still_working_rate": 0.5,
    }


def test_still_working_rate_is_none_until_a_customer_answers():
    stats = ProviderStats(outcomes=[JobOutcome(finished_on=FINISHED_ON, completed=True)])
    assert trust_summary(stats).breakdown.still_working_rate is None
