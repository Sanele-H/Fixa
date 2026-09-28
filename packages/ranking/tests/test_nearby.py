"""list_nearby_providers: trade, radius and language filters, nearest first, and no trust."""

from datetime import date

import pytest
from pydantic import ValidationError

from ranking import (
    Candidate,
    JobOutcome,
    NearbyCandidate,
    ProviderStats,
    list_nearby_providers,
)
from ranking.nearby import DEFAULT_RADIUS_KM, MAX_RADIUS_KM

LAST_MONTH = date(2026, 8, 29)
ESTABLISHED_GOOD_JOBS = 20


def make_stats(good_jobs: int = 0, off_app_jobs: int = 0) -> ProviderStats:
    """Makes evidence: completed in-app jobs and confirmed off-app jobs."""
    in_app = [JobOutcome(finished_on=LAST_MONTH, completed=True) for _ in range(good_jobs)]
    off_app = [
        JobOutcome(finished_on=LAST_MONTH, completed=True, off_app=True)
        for _ in range(off_app_jobs)
    ]
    return ProviderStats(outcomes=in_app + off_app)


def make_candidate(provider_id: str, distance_km: float, **fields) -> NearbyCandidate:
    """Makes a plumber in Braamfontein who speaks isiZulu and English, with a strong record."""
    fields.setdefault("trades", ["plumbing"])
    fields.setdefault("langs", ["zu", "en"])
    fields.setdefault("stats", make_stats(good_jobs=ESTABLISHED_GOOD_JOBS))
    return NearbyCandidate(
        provider_id=provider_id,
        display_name=provider_id.title(),
        suburb="Braamfontein",
        distance_km=distance_km,
        **fields,
    )


def list_ids(candidates: list[NearbyCandidate], **filters) -> list[str]:
    """Lists nearby plumbers (unless another trade is given) and returns their ids in order."""
    filters.setdefault("trade", "plumbing")
    return [provider.provider_id for provider in list_nearby_providers(candidates, **filters)]


def test_lists_nearest_first():
    candidates = [
        make_candidate("far", 6.0),
        make_candidate("near", 0.5),
        make_candidate("mid", 2.0),
    ]
    assert list_ids(candidates) == ["near", "mid", "far"]


def test_never_orders_by_track_record():
    newcomer = make_candidate("newcomer", 1.0, stats=make_stats())
    established = make_candidate("established", 2.0)
    assert list_ids([established, newcomer]) == ["newcomer", "established"]


def test_the_result_carries_no_trust():
    [card] = list_nearby_providers([make_candidate("thabo", 1.8)], trade="plumbing")
    assert "trust" not in card.model_dump()


def test_equal_distances_keep_their_input_order():
    candidates = [make_candidate("first", 1.0), make_candidate("second", 1.0)]
    assert list_ids(candidates) == ["first", "second"]


def test_leaves_out_other_trades():
    electrician = make_candidate("electrician", 1.0, trades=["electrical"])
    both = make_candidate("both", 2.0, trades=["electrical", "plumbing"])
    assert list_ids([electrician, both]) == ["both"]
    assert list_ids([electrician, both], trade="electrical") == ["electrician", "both"]


def test_keeps_providers_inside_the_default_radius_only():
    inside = make_candidate("inside", DEFAULT_RADIUS_KM)
    outside = make_candidate("outside", DEFAULT_RADIUS_KM + 0.1)
    assert list_ids([inside, outside]) == ["inside"]


def test_the_customer_chooses_the_radius():
    candidates = [make_candidate("near", 1.5), make_candidate("across_town", 18.0)]
    assert list_ids(candidates, radius_km=2) == ["near"]
    assert list_ids(candidates, radius_km=20) == ["near", "across_town"]


@pytest.mark.parametrize("radius_km", [0, -1, MAX_RADIUS_KM + 1])
def test_refuses_a_radius_out_of_bounds(radius_km):
    with pytest.raises(ValueError, match="radius_km"):
        list_nearby_providers([make_candidate("thabo", 1.8)], trade="plumbing", radius_km=radius_km)


def test_allows_the_widest_radius():
    assert list_ids([make_candidate("tembisa", MAX_RADIUS_KM)], radius_km=MAX_RADIUS_KM) == [
        "tembisa"
    ]


def test_language_filter_keeps_only_speakers():
    zulu_speaker = make_candidate("zulu_speaker", 1.0, langs=["zu", "en"])
    xhosa_speaker = make_candidate("xhosa_speaker", 2.0, langs=["xh", "en"])
    candidates = [zulu_speaker, xhosa_speaker]
    assert list_ids(candidates, lang="xh") == ["xhosa_speaker"]
    assert list_ids(candidates, lang="en") == ["zulu_speaker", "xhosa_speaker"]
    assert list_ids(candidates) == ["zulu_speaker", "xhosa_speaker"]


def test_builds_the_card_with_newcomer_flag_and_evidence():
    sipho = make_candidate("sipho", 3.14, stats=make_stats(off_app_jobs=1), id_badge="home_affairs")
    [card] = list_nearby_providers([sipho], trade="plumbing")
    assert card.is_newcomer
    assert card.distance_km == 3.1
    assert (card.suburb, card.langs, card.id_badge) == (
        "Braamfontein",
        ["zu", "en"],
        "home_affairs",
    )
    assert card.evidence.model_dump() == {
        "jobs": 0,
        "repeat_customers": 0,
        "photos": 0,
        "off_app_confirmed": 1,
    }


def test_nearby_candidate_refuses_unknown_fields():
    with pytest.raises(ValidationError):
        make_candidate("thabo", 1.8, nationality="x")


def test_ranking_candidate_still_refuses_language():
    with pytest.raises(ValidationError):
        Candidate(
            provider_id="thabo",
            display_name="Thabo",
            trades=["plumbing"],
            distance_km=1.8,
            langs=["zu"],
            stats=ProviderStats(),
        )
