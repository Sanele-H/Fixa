"""rank_providers: which providers a customer sees for a job, and in what order.

1. Leave out providers who can't take the job: another trade, at their cap of open quotes
   or active jobs (so work spreads out), or unlicensed for licensed work.
2. Score the rest. Distance is the main factor, plus one Thompson-sampled draw of each
   provider's chance of doing the job well. A provider with little evidence has a wide
   posterior, so their draws vary and they get shown some of the time: that's exploring.
3. On small and medium jobs, one of the top 5 is always a newcomer (fewer than 3
   completed jobs) if any newcomer can take the job. Large jobs are ranked on score alone,
   so newcomers are shown small jobs first.

Only job evidence and distance are scored. ID badges, names, photos, language and
nationality are never inputs.
"""

import numpy as np

from ranking.evidence import build_evidence, is_newcomer
from ranking.models import Candidate, JobRequest, RankedProvider
from ranking.posterior import calculate_posterior, draw_success_chance
from ranking.trust import trust_summary

DISTANCE_WEIGHT = 0.6  # distance is the main factor
SUCCESS_WEIGHT = 0.4
DISTANCE_SCALE_KM = 3.0  # closeness is 1 at 0 km and halves at this distance
MAX_OPEN_QUOTES = 5  # providers with this many open quotes are left out until some close
MAX_ACTIVE_JOBS = 3  # the same for confirmed jobs not yet done
TOP_PLACES = 5
NEWCOMER_SLOT_JOB_SIZES = {"small", "medium"}
# Distances go out rounded, like "2.4 km", so a provider's exact location can't be worked out.
DISTANCE_DECIMALS = 1


def rank_providers(
    job: JobRequest, candidates: list[Candidate], rng: np.random.Generator
) -> list[RankedProvider]:
    """Orders the providers who can take a job, best first.

    Args:
        job: the job being ranked for.
        candidates: the providers P2 could show, with their evidence and distance.
        rng: the random generator for Thompson sampling. P2 passes a fresh
            np.random.default_rng() per search; tests and the simulation pass a seeded
            one so that results can be reproduced.

    Returns:
        One RankedProvider per provider who can take the job, best first. Providers who
        can't take it (another trade, at a cap, unlicensed for licensed work) are left out.
    """
    eligible_candidates = [candidate for candidate in candidates if can_take_job(candidate, job)]
    scores = [score_candidate(candidate, job, rng) for candidate in eligible_candidates]
    best_first = order_by_score(eligible_candidates, scores)
    if job.size in NEWCOMER_SLOT_JOB_SIZES:
        best_first = move_newcomer_into_top(best_first)
    return [build_ranked_provider(candidate) for candidate in best_first]


def can_take_job(candidate: Candidate, job: JobRequest) -> bool:
    """True if the provider offers the trade, is under both caps, and is licensed if needed."""
    return (
        job.trade in candidate.trades
        and candidate.open_quotes < MAX_OPEN_QUOTES
        and candidate.active_jobs < MAX_ACTIVE_JOBS
        and (candidate.licensed or not job.needs_licence)
    )


def score_candidate(candidate: Candidate, job: JobRequest, rng: np.random.Generator) -> float:
    """Scores a provider for a job: closeness plus a Thompson-sampled chance of success.

    Reads only the provider's job evidence and distance.
    """
    posterior = calculate_posterior(candidate.stats, job.posted_on)
    success_chance = draw_success_chance(posterior, rng)
    closeness = calculate_closeness(candidate.distance_km)
    return DISTANCE_WEIGHT * closeness + SUCCESS_WEIGHT * success_chance


def calculate_closeness(distance_km: float) -> float:
    """Turns a distance into a closeness from 1 (next door) towards 0 (far away)."""
    return 1.0 / (1.0 + distance_km / DISTANCE_SCALE_KM)


def order_by_score(candidates: list[Candidate], scores: list[float]) -> list[Candidate]:
    """Orders candidates by score, highest first. Equal scores keep their input order."""
    ranked_pairs = sorted(
        zip(scores, candidates, strict=True), key=lambda pair: pair[0], reverse=True
    )
    return [candidate for _, candidate in ranked_pairs]


def move_newcomer_into_top(best_first: list[Candidate]) -> list[Candidate]:
    """Makes sure one of the top TOP_PLACES is a newcomer, if the list has one.

    If none of the top places holds a newcomer, the best-scoring newcomer moves up to the
    last top place and everyone from that place down moves down one.
    """
    if any(is_newcomer(candidate.stats) for candidate in best_first[:TOP_PLACES]):
        return best_first
    newcomer = next((candidate for candidate in best_first if is_newcomer(candidate.stats)), None)
    if newcomer is None:
        return best_first
    others = [candidate for candidate in best_first if candidate is not newcomer]
    slot_index = TOP_PLACES - 1
    return others[:slot_index] + [newcomer] + others[slot_index:]


def build_ranked_provider(candidate: Candidate) -> RankedProvider:
    """Builds one provider card: display fields, evidence strip and trust badge."""
    return RankedProvider(
        provider_id=candidate.provider_id,
        display_name=candidate.display_name,
        trades=candidate.trades,
        distance_km=round(candidate.distance_km, DISTANCE_DECIMALS),
        is_newcomer=is_newcomer(candidate.stats),
        id_badge=candidate.id_badge,
        evidence=build_evidence(candidate),
        trust=trust_summary(candidate.stats).to_badge(),
    )
