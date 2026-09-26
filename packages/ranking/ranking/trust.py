"""trust_summary: how likely a provider's next job is to go well, and how sure we are.

STUB (step 0): established providers all get the same fixed numbers. Step 3 replaces them
with the Beta posterior the ranking uses, behind the same signature.
"""

from ranking.evidence import build_trust_breakdown, is_newcomer
from ranking.models import ProviderStats, TrustSummary

NEW_PROVIDER_LABEL = "New, building a record"
STRONG_RECORD_LABEL = "Strong record"

# The numbers in contracts/fixtures/ranked_providers.json, until step 3 computes real ones.
STUB_SCORE = 0.86
STUB_LOW = 0.74
STUB_HIGH = 0.93


def trust_summary(stats: ProviderStats) -> TrustSummary:
    """Summarises a provider's job evidence as a score with a range and a breakdown.

    Args:
        stats: the provider's job evidence. Nothing else about the provider is an input:
            no photos, names, language or nationality.

    Returns:
        A TrustSummary. For a newcomer, score, low and high are None and the label is
        "New, building a record". STUB: everyone else gets the fixed fixture numbers.
    """
    breakdown = build_trust_breakdown(stats)
    evidence_count = len(stats.outcomes)
    if is_newcomer(stats):
        return TrustSummary(
            score=None,
            low=None,
            high=None,
            n_evidence=evidence_count,
            breakdown=breakdown,
            label=NEW_PROVIDER_LABEL,
        )
    return TrustSummary(
        score=STUB_SCORE,
        low=STUB_LOW,
        high=STUB_HIGH,
        n_evidence=evidence_count,
        breakdown=breakdown,
        label=STRONG_RECORD_LABEL,
    )
