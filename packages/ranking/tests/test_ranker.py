"""rank_providers: distance first, a sampled track record, caps, licences and the newcomer slot.

Thompson sampling makes the order random, so rules that must always hold are checked on
many seeds, and tendencies are checked as shares over many seeds.
"""

from datetime import date, timedelta

import numpy as np
import pytest
from pydantic import ValidationError

from ranking import Candidate, JobOutcome, JobRequest, ProviderStats, rank_providers
from ranking.ranker import MAX_ACTIVE_JOBS, MAX_OPEN_QUOTES, TOP_PLACES, move_newcomer_into_top

TODAY = date(2026, 9, 29)
LAST_MONTH = TODAY - timedelta(days=30)
SEED = 7
SEEDS = range(200)
ESTABLISHED_GOOD_JOBS = 20


def make_stats(good_jobs: int = 0, bad_jobs: int = 0, off_app_jobs: int = 0) -> ProviderStats:
    """Makes evidence: good and bad (no-show) in-app jobs, and confirmed off-app jobs."""
    good = [JobOutcome(finished_on=LAST_MONTH, completed=True) for _ in range(good_jobs)]
    bad = [JobOutcome(finished_on=LAST_MONTH, completed=False) for _ in range(bad_jobs)]
    off_app = [
        JobOutcome(finished_on=LAST_MONTH, completed=True, off_app=True)
        for _ in range(off_app_jobs)
    ]
    return ProviderStats(outcomes=good + bad + off_app)


def make_candidate(provider_id: str, distance_km: float, **fields) -> Candidate:
    """Makes a plumber with a strong record; any other Candidate field can be passed in."""
    fields.setdefault("stats", make_stats(good_jobs=ESTABLISHED_GOOD_JOBS))
    return Candidate(
        provider_id=provider_id,
        display_name=provider_id.title(),
        trades=["plumbing"],
        distance_km=distance_km,
        **fields,
    )


def make_newcomer(provider_id: str, distance_km: float) -> Candidate:
    """Makes a plumber with no completed jobs yet."""
    return make_candidate(provider_id, distance_km, stats=make_stats())


def make_job(size: str = "small", needs_licence: bool = False) -> JobRequest:
    """Makes a plumbing job posted today."""
    return JobRequest(trade="plumbing", size=size, needs_licence=needs_licence, posted_on=TODAY)


def rank_ids(candidates: list[Candidate], job: JobRequest | None = None, seed: int = SEED):
    """Ranks the candidates (for a small job by default) and returns their ids in order."""
    ranked = rank_providers(job or make_job(), candidates, np.random.default_rng(seed))
    return [provider.provider_id for provider in ranked]


def count_seeds_where_first(provider_id: str, candidates: list[Candidate], job=None) -> int:
    """Counts the seeds in SEEDS for which the provider comes first."""
    return sum(rank_ids(candidates, job, seed)[0] == provider_id for seed in SEEDS)


def test_distance_decides_between_similar_records():
    candidates = [
        make_candidate("far", 7.5),
        make_candidate("near", 0.9),
        make_candidate("middle", 3.1),
    ]
    for seed in SEEDS:
        assert rank_ids(candidates, seed=seed) == ["near", "middle", "far"]


def test_a_better_record_usually_wins_at_the_same_distance():
    candidates = [
        make_candidate("patchy", 2.0, stats=make_stats(good_jobs=10, bad_jobs=10)),
        make_candidate("reliable", 2.0),
    ]
    assert count_seeds_where_first("reliable", candidates) >= 0.95 * len(SEEDS)


def test_a_newcomer_sometimes_beats_an_average_provider_at_the_same_distance():
    candidates = [
        make_candidate("average", 2.0, stats=make_stats(good_jobs=16, bad_jobs=4)),
        make_newcomer("newcomer", 2.0),
    ]
    newcomer_wins = count_seeds_where_first("newcomer", candidates)
    assert 0.2 * len(SEEDS) < newcomer_wins < 0.9 * len(SEEDS)


def test_the_same_seed_gives_the_same_order():
    candidates = [make_newcomer(f"new_{index}", 1.0 + index) for index in range(8)]
    assert rank_ids(candidates, seed=11) == rank_ids(candidates, seed=11)


@pytest.mark.parametrize("size", ["small", "medium"])
def test_a_far_newcomer_gets_the_last_top_place_on_small_and_medium_jobs(size):
    candidates = [make_candidate(f"pro_{km}", float(km)) for km in range(1, 7)]
    candidates.append(make_newcomer("newcomer", 10.0))
    for seed in SEEDS:
        assert rank_ids(candidates, make_job(size), seed)[TOP_PLACES - 1] == "newcomer"


def test_large_jobs_have_no_newcomer_slot():
    candidates = [make_candidate(f"pro_{km}", float(km)) for km in range(1, 7)]
    candidates.append(make_newcomer("newcomer", 10.0))
    for seed in SEEDS:
        assert "newcomer" not in rank_ids(candidates, make_job("large"), seed)[:TOP_PLACES]


def test_move_newcomer_into_top_moves_the_best_newcomer_to_the_last_top_place():
    best_first = [make_candidate(f"pro_{index}", 1.0) for index in range(7)]
    best_first += [make_newcomer("first_newcomer", 9.0), make_newcomer("second_newcomer", 9.0)]
    moved_ids = [candidate.provider_id for candidate in move_newcomer_into_top(best_first)]
    assert moved_ids[:TOP_PLACES] == ["pro_0", "pro_1", "pro_2", "pro_3", "first_newcomer"]
    assert moved_ids[TOP_PLACES:] == ["pro_4", "pro_5", "pro_6", "second_newcomer"]


def test_move_newcomer_into_top_leaves_a_list_that_needs_no_change():
    newcomer_in_top = [make_candidate("pro_0", 1.0), make_newcomer("newcomer", 2.0)]
    newcomer_in_top += [make_candidate(f"pro_{index}", 3.0) for index in range(1, 7)]
    no_newcomer = [make_candidate(f"pro_{index}", 1.0) for index in range(7)]
    assert move_newcomer_into_top(newcomer_in_top) == newcomer_in_top
    assert move_newcomer_into_top(no_newcomer) == no_newcomer


@pytest.mark.parametrize(
    "at_cap_fields", [{"open_quotes": MAX_OPEN_QUOTES}, {"active_jobs": MAX_ACTIVE_JOBS}]
)
def test_providers_at_a_cap_are_left_out(at_cap_fields):
    candidates = [
        make_candidate("busy", 0.5, **at_cap_fields),
        make_candidate(
            "free", 4.0, open_quotes=MAX_OPEN_QUOTES - 1, active_jobs=MAX_ACTIVE_JOBS - 1
        ),
    ]
    assert rank_ids(candidates) == ["free"]


def test_licensed_work_goes_only_to_licensed_providers():
    candidates = [make_candidate("unlicensed", 0.5), make_candidate("licensed", 4.0, licensed=True)]
    assert rank_ids(candidates, make_job(needs_licence=True)) == ["licensed"]
    assert rank_ids(candidates, make_job(needs_licence=False)) == ["unlicensed", "licensed"]


def test_providers_in_other_trades_are_left_out():
    electrician = make_candidate("electrician", 0.5).model_copy(update={"trades": ["electrical"]})
    assert rank_ids([electrician, make_candidate("plumber", 4.0)]) == ["plumber"]


def test_returns_nothing_for_no_candidates():
    assert rank_ids([]) == []


def test_id_badge_does_not_change_the_order():
    records = [make_stats(good_jobs=3), make_stats(good_jobs=8, bad_jobs=2), make_stats()]
    badges = ["none", "id_number", "home_affairs"]
    for seed in range(20):
        with_badges = [
            make_candidate(f"p{index}", 2.0, stats=stats, id_badge=badge)
            for index, (stats, badge) in enumerate(zip(records, badges, strict=True))
        ]
        badges_swapped = [
            candidate.model_copy(update={"id_badge": badges[-1 - index]})
            for index, candidate in enumerate(with_badges)
        ]
        assert rank_ids(with_badges, seed=seed) == rank_ids(badges_swapped, seed=seed)


def test_newcomer_card_has_no_score_and_the_new_label():
    newcomer = make_candidate("sipho", 3.1, stats=make_stats(off_app_jobs=1))
    [card] = rank_providers(make_job(), [newcomer], np.random.default_rng(SEED))
    assert card.is_newcomer
    assert card.trust.score is None
    assert card.trust.label == "New, building a record"


def test_card_carries_the_evidence_strip_and_display_fields():
    stats = make_stats(good_jobs=9, off_app_jobs=3).model_copy(update={"repeat_customers": 2})
    candidate = make_candidate("thabo", 1.8, stats=stats, photos=14, id_badge="id_number")
    [card] = rank_providers(make_job(), [candidate], np.random.default_rng(SEED))
    assert card.evidence.model_dump() == {
        "jobs": 9,
        "repeat_customers": 2,
        "photos": 14,
        "off_app_confirmed": 3,
    }
    assert (card.id_badge, card.display_name) == ("id_number", "Thabo")
    assert not card.is_newcomer


def test_rounds_distance_to_one_decimal():
    [card] = rank_providers(
        make_job(), [make_candidate("thabo", 1.8372)], np.random.default_rng(SEED)
    )
    assert card.distance_km == 1.8


@pytest.mark.parametrize("forbidden_field", ["id_badge", "first_language", "nationality"])
def test_provider_stats_refuses_anything_but_job_evidence(forbidden_field):
    with pytest.raises(ValidationError):
        ProviderStats(outcomes=[], **{forbidden_field: "x"})
