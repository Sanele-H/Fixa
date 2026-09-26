"""Role 4's to-do list for ranking. Expected to fail until the strategies exist."""

import pytest

from fixa.ranking.provider_ranking import (
    NewcomerFriendlyStrategy,
    ProviderRecord,
    SortByRatingStrategy,
    shortlist_providers,
)

pytestmark = pytest.mark.xfail(raises=NotImplementedError, reason="TODO Role 4: ranking")

ESTABLISHED_PROVIDERS = [
    ProviderRecord(
        f"established-{index}",
        rating_sum=4.7 * 30,
        rating_count=30,
        completed_job_count=30,
        offer_count=50,
    )
    for index in range(6)
]
NEWCOMER = ProviderRecord(
    "nomsa", rating_sum=0, rating_count=0, completed_job_count=0, offer_count=0
)


def test_sort_by_rating_never_shortlists_an_unrated_newcomer():
    shortlist = shortlist_providers(
        [NEWCOMER, *ESTABLISHED_PROVIDERS], SortByRatingStrategy(), is_small_job=True
    )

    assert NEWCOMER not in shortlist


def test_our_ranking_shortlists_a_newcomer_for_a_small_job():
    shortlist = shortlist_providers(
        [NEWCOMER, *ESTABLISHED_PROVIDERS], NewcomerFriendlyStrategy(), is_small_job=True
    )

    assert NEWCOMER in shortlist


def test_ranking_returns_every_candidate_exactly_once():
    candidates = [NEWCOMER, *ESTABLISHED_PROVIDERS]

    ranked = NewcomerFriendlyStrategy().rank_providers(candidates, is_small_job=True)

    assert sorted(record.provider_id for record in ranked) == sorted(
        record.provider_id for record in candidates
    )
