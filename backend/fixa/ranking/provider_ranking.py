"""Ranking strategies: plain sort-by-rating (the baseline) versus our newcomer-friendly ranking.

This module must stay free of FastAPI, the store and pydantic, so the simulation can import
it on its own. It only works with ProviderRecord.

Add a new strategy by subclassing RankingStrategy; existing code doesn't change.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

SHORTLIST_SIZE = 5


@dataclass(frozen=True)
class ProviderRecord:
    """Everything ranking may look at for one provider.

    Attributes:
        provider_id: The provider's user id.
        rating_sum: Sum of all star ratings received (1-5 each).
        rating_count: Number of ratings received.
        completed_job_count: Jobs done through the app, including logged off-app jobs.
        offer_count: How many times this provider has been shortlisted before.
    """

    provider_id: str
    rating_sum: float
    rating_count: int
    completed_job_count: int
    offer_count: int


class RankingStrategy(ABC):
    """Orders candidate providers for one job, best first."""

    name: str

    @abstractmethod
    def rank_providers(
        self, candidates: Sequence[ProviderRecord], is_small_job: bool
    ) -> list[ProviderRecord]:
        """Return all `candidates` in the order the customer should see them."""


class SortByRatingStrategy(RankingStrategy):
    """The baseline most marketplaces use: highest average rating first, unrated last.

    TODO (Role 4, Day 2): implement. It's the comparison line on the fairness chart.
    """

    name = "sort_by_rating"

    def rank_providers(
        self, candidates: Sequence[ProviderRecord], is_small_job: bool
    ) -> list[ProviderRecord]:
        """Sort by average rating, highest first. Providers with no ratings go last."""
        raise NotImplementedError("TODO Role 4: SortByRatingStrategy")


class NewcomerFriendlyStrategy(RankingStrategy):
    """Our ranking: gives good newcomers a fair shot at small, low-risk jobs.

    TODO (Role 4, Day 2-3): design and implement. Decisions to make and write down:
    - Who counts as a newcomer (how many completed jobs)?
    - How many shortlist slots are reserved for newcomers, and at which position?
    - How do you rotate between several newcomers (offer_count helps)?
    - How do you stop a few early ratings from dominating (e.g. a Bayesian average)?
    """

    name = "newcomer_friendly"

    def rank_providers(
        self, candidates: Sequence[ProviderRecord], is_small_job: bool
    ) -> list[ProviderRecord]:
        """Rank established providers by rating, reserving room for newcomers on small jobs."""
        raise NotImplementedError("TODO Role 4: NewcomerFriendlyStrategy")


def shortlist_providers(
    candidates: Sequence[ProviderRecord],
    strategy: RankingStrategy,
    is_small_job: bool,
    shortlist_size: int = SHORTLIST_SIZE,
) -> list[ProviderRecord]:
    """Return the top `shortlist_size` providers under `strategy`. These see the job."""
    return strategy.rank_providers(candidates, is_small_job)[:shortlist_size]
