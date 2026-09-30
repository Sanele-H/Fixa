"""Fair ranking, trust summary, price range and the fairness simulation for Fixa (P4).

Owner: P4. Only P4 edits files in packages/ranking/. P2's API imports this package.

Public functions (the contract; signatures change only with the team's agreement):
    rank_providers(job, candidates, rng) -> list[RankedProvider]
    trust_summary(stats, today=None) -> TrustSummary(score, low, high, n_evidence,
                                                     breakdown, label)
    price_range(trade, size, area, accepted_quotes) -> PriceRange | None
    is_underpriced(amount_rands, typical_range) -> bool   (added in step 5)
    list_nearby_providers(candidates, trade, lang=None, radius_km=10.0) -> list[NearbyProvider]

All randomness takes a seeded rng. The fairness simulation reuses rank_providers unchanged.
P4 also generates the demo data in data/seed/.

Status: rank_providers (step 1) and trust_summary (step 3) are real. trust_summary's
today is optional and defaults to the real date, so trust_summary(stats) still works.
price_range and is_underpriced (step 5) are real. list_nearby_providers is real: the
"Who works near you" list, nearest first, with no trust. The input and output shapes are in
ranking.models and are exported here.
"""

from ranking.models import (
    AcceptedQuote,
    Candidate,
    Evidence,
    JobOutcome,
    JobRequest,
    Language,
    NearbyCandidate,
    NearbyProvider,
    PriceRange,
    ProviderStats,
    RankedProvider,
    TrustBadge,
    TrustBreakdown,
    TrustSummary,
)
from ranking.nearby import list_nearby_providers
from ranking.pricing import is_underpriced, price_range
from ranking.ranker import rank_providers
from ranking.trust import trust_summary

__all__ = [
    "AcceptedQuote",
    "Candidate",
    "Evidence",
    "JobOutcome",
    "JobRequest",
    "Language",
    "NearbyCandidate",
    "NearbyProvider",
    "PriceRange",
    "ProviderStats",
    "RankedProvider",
    "TrustBadge",
    "TrustBreakdown",
    "TrustSummary",
    "is_underpriced",
    "list_nearby_providers",
    "price_range",
    "rank_providers",
    "trust_summary",
]
