"""trust_summary: how likely a provider's next job is to go well, and how sure we are.

It shows the same Beta posterior the ranking draws from: the score is its mean, and the
range holds its middle 90%. Only job evidence goes in: never photos, names, language or
nationality.

Labels:
- "New, building a record": fewer than 3 completed in-app jobs. No score is shown yet.
- "Strong record": even the low end of the range is at least 0.8.
- "Good record": the score is at least 0.7.
- "Mixed record": anything below that.
"""

from datetime import date

from ranking.evidence import build_trust_breakdown, is_newcomer
from ranking.models import ProviderStats, TrustSummary
from ranking.posterior import calculate_credible_range, calculate_posterior

NEW_PROVIDER_LABEL = "New, building a record"
STRONG_RECORD_LABEL = "Strong record"
GOOD_RECORD_LABEL = "Good record"
MIXED_RECORD_LABEL = "Mixed record"
STRONG_RECORD_MIN_LOW = 0.8
GOOD_RECORD_MIN_SCORE = 0.7
SCORE_DECIMALS = 2


def trust_summary(stats: ProviderStats, today: date | None = None) -> TrustSummary:
    """Summarises a provider's job evidence as a score with a range, a breakdown and a label.

    Args:
        stats: the provider's job evidence. Nothing else about the provider is an input.
        today: the date recent outcomes are weighed against (older ones count less).
            Defaults to the real date; the ranking passes the job's date.

    Returns:
        A TrustSummary with score, low and high rounded to 2 decimals. For a newcomer
        they are None and the label is "New, building a record".
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
    posterior = calculate_posterior(stats, today or date.today())
    low, high = calculate_credible_range(posterior)
    return TrustSummary(
        score=round(posterior.mean, SCORE_DECIMALS),
        low=round(low, SCORE_DECIMALS),
        high=round(high, SCORE_DECIMALS),
        n_evidence=evidence_count,
        breakdown=breakdown,
        label=choose_label(posterior.mean, low),
    )


def choose_label(score: float, low: float) -> str:
    """Chooses the label for an established provider from their score and the range's low end."""
    if low >= STRONG_RECORD_MIN_LOW:
        return STRONG_RECORD_LABEL
    if score >= GOOD_RECORD_MIN_SCORE:
        return GOOD_RECORD_LABEL
    return MIXED_RECORD_LABEL
