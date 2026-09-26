"""rank_providers: which providers a customer sees for a job, and in what order.

STUB (step 0): nearest first, with no filtering. Step 1 adds the Thompson-sampled success
estimate, the newcomer slot, the caps and the licence rule, behind the same signature.
"""

import numpy as np

from ranking.evidence import build_evidence, is_newcomer
from ranking.models import Candidate, JobRequest, RankedProvider
from ranking.trust import trust_summary

# Distances go out rounded, like "2.4 km", so a provider's exact location can't be worked out.
DISTANCE_DECIMALS = 1


def rank_providers(
    job: JobRequest, candidates: list[Candidate], rng: np.random.Generator
) -> list[RankedProvider]:
    """Orders the candidates for a job, best first.

    Args:
        job: the job being ranked for.
        candidates: the providers P2 could show, with their evidence and distance.
        rng: the random generator for Thompson sampling. P2 passes a fresh
            np.random.default_rng() per search; tests and the simulation pass a seeded
            one so that results can be reproduced.

    Returns:
        One RankedProvider per candidate shown, best first.
        STUB: every candidate, nearest first. job and rng are not used yet.
    """
    nearest_first = sorted(candidates, key=lambda candidate: candidate.distance_km)
    return [build_ranked_provider(candidate) for candidate in nearest_first]


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
