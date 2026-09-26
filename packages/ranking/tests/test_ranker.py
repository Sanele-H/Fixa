"""rank_providers. Step 0 stub: every candidate, nearest first, as agreed provider cards."""

from datetime import date

import numpy as np
import pytest
from pydantic import ValidationError

from ranking import Candidate, JobOutcome, JobRequest, ProviderStats, rank_providers

TODAY = date(2026, 9, 29)
SMALL_PLUMBING_JOB = JobRequest(trade="plumbing", size="small", posted_on=TODAY)
SEED = 7


def make_stats(completed_jobs: int = 0, off_app_jobs: int = 0) -> ProviderStats:
    """Makes evidence with the given numbers of completed in-app and off-app jobs."""
    in_app = [JobOutcome(finished_on=TODAY, completed=True) for _ in range(completed_jobs)]
    off_app = [
        JobOutcome(finished_on=TODAY, completed=True, off_app=True) for _ in range(off_app_jobs)
    ]
    return ProviderStats(outcomes=in_app + off_app)


def make_candidate(provider_id: str, distance_km: float, **fields) -> Candidate:
    """Makes a plumber candidate; any other Candidate field can be passed in."""
    fields.setdefault("stats", make_stats())
    return Candidate(
        provider_id=provider_id,
        display_name=provider_id.title(),
        trades=["plumbing"],
        distance_km=distance_km,
        **fields,
    )


def rank_ids(candidates: list[Candidate]) -> list[str]:
    """Ranks the candidates for the small plumbing job and returns their ids in order."""
    ranked = rank_providers(SMALL_PLUMBING_JOB, candidates, np.random.default_rng(SEED))
    return [provider.provider_id for provider in ranked]


def test_orders_nearest_first():
    candidates = [
        make_candidate("far", 7.5),
        make_candidate("near", 0.9),
        make_candidate("middle", 3.1),
    ]
    assert rank_ids(candidates) == ["near", "middle", "far"]


def test_returns_nothing_for_no_candidates():
    assert rank_ids([]) == []


def test_newcomer_card_has_no_score_and_the_new_label():
    newcomer = make_candidate("sipho", 3.1, stats=make_stats(completed_jobs=0, off_app_jobs=1))
    [card] = rank_providers(SMALL_PLUMBING_JOB, [newcomer], np.random.default_rng(SEED))
    assert card.is_newcomer
    assert card.trust.score is None
    assert card.trust.label == "New, building a record"


def test_established_card_has_a_score_inside_its_range():
    established = make_candidate("thabo", 1.8, stats=make_stats(completed_jobs=9))
    [card] = rank_providers(SMALL_PLUMBING_JOB, [established], np.random.default_rng(SEED))
    assert not card.is_newcomer
    assert card.trust.low <= card.trust.score <= card.trust.high


def test_card_carries_the_evidence_strip_and_display_fields():
    stats = make_stats(completed_jobs=9, off_app_jobs=3).model_copy(update={"repeat_customers": 2})
    candidate = make_candidate("thabo", 1.8, stats=stats, photos=14, id_badge="id_number")
    [card] = rank_providers(SMALL_PLUMBING_JOB, [candidate], np.random.default_rng(SEED))
    assert card.evidence.model_dump() == {
        "jobs": 9,
        "repeat_customers": 2,
        "photos": 14,
        "off_app_confirmed": 3,
    }
    assert card.id_badge == "id_number"
    assert card.display_name == "Thabo"


def test_rounds_distance_to_one_decimal():
    [card] = rank_providers(
        SMALL_PLUMBING_JOB, [make_candidate("thabo", 1.8372)], np.random.default_rng(SEED)
    )
    assert card.distance_km == 1.8


def test_id_badge_does_not_change_the_order():
    with_badges = [
        make_candidate("a", 2.0, id_badge="none"),
        make_candidate("b", 3.0, id_badge="home_affairs"),
    ]
    badges_swapped = [
        make_candidate("a", 2.0, id_badge="home_affairs"),
        make_candidate("b", 3.0, id_badge="none"),
    ]
    assert rank_ids(with_badges) == rank_ids(badges_swapped)


@pytest.mark.parametrize("forbidden_field", ["id_badge", "first_language", "nationality"])
def test_provider_stats_refuses_anything_but_job_evidence(forbidden_field):
    with pytest.raises(ValidationError):
        ProviderStats(outcomes=[], **{forbidden_field: "x"})
