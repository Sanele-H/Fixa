"""The rankings Fixa is compared with.

- rank_by_rating: plain sort-by-rating, as most listing apps do it.
- rank_without_exploring: Fixa's ranking with exploring switched off. It exists only to
  measure what exploring costs in job quality.
"""

import numpy as np

from ranking.models import Candidate, JobRequest, RankedProvider
from ranking.posterior import calculate_posterior, went_well
from ranking.ranker import build_ranked_provider, can_take_job, combine_score, order_by_score


def rank_by_rating(
    job: JobRequest, candidates: list[Candidate], rng: np.random.Generator
) -> list[RankedProvider]:
    """Orders providers by their average rating, best first.

    The rating is the share of their jobs that went well. Unrated providers (no jobs yet)
    come last. Ties go to the provider with more jobs, then to the nearer one. There are
    no caps, no newcomer slot and no exploring. rng isn't used; it's there so this has
    the same signature as rank_providers.
    """
    in_trade = [candidate for candidate in candidates if job.trade in candidate.trades]
    return [build_ranked_provider(candidate) for candidate in sorted(in_trade, key=sort_by_rating)]


def sort_by_rating(candidate: Candidate) -> tuple:
    """Sort key: rated before unrated, then higher rating, more jobs, and nearer first."""
    outcomes = candidate.stats.outcomes
    if not outcomes:
        return (1, 0.0, 0, candidate.distance_km)
    rating = sum(went_well(outcome) for outcome in outcomes) / len(outcomes)
    return (0, -rating, -len(outcomes), candidate.distance_km)


def rank_without_exploring(
    job: JobRequest, candidates: list[Candidate], rng: np.random.Generator
) -> list[RankedProvider]:
    """Fixa's ranking with exploring switched off, to measure what exploring costs.

    Same filters and score as rank_providers, but each provider's expected chance of
    success (the posterior mean) replaces the Thompson draw, and there's no newcomer slot.
    rng isn't used.
    """
    eligible_candidates = [candidate for candidate in candidates if can_take_job(candidate, job)]
    scores = [score_by_expected_success(candidate, job) for candidate in eligible_candidates]
    best_first = order_by_score(eligible_candidates, scores)
    return [build_ranked_provider(candidate) for candidate in best_first]


def score_by_expected_success(candidate: Candidate, job: JobRequest) -> float:
    """Scores a provider with their expected chance of success instead of a random draw."""
    posterior = calculate_posterior(candidate.stats, job.posted_on)
    return combine_score(candidate.distance_km, posterior.mean)
