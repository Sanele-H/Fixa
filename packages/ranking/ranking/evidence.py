"""Counts taken from a provider's job evidence, shared by the trust summary and the ranking."""

from ranking.models import Candidate, Evidence, ProviderStats, TrustBreakdown

# Providers with fewer completed in-app jobs than this are newcomers.
ESTABLISHED_AT_COMPLETED_JOBS = 3


def count_completed_jobs(stats: ProviderStats) -> int:
    """Counts completed in-app jobs. Confirmed off-app jobs are counted separately."""
    return sum(1 for outcome in stats.outcomes if outcome.completed and not outcome.off_app)


def count_off_app_confirmed(stats: ProviderStats) -> int:
    """Counts off-app jobs the customer confirmed."""
    return sum(1 for outcome in stats.outcomes if outcome.completed and outcome.off_app)


def calculate_still_working_rate(stats: ProviderStats) -> float | None:
    """Returns the share of "still working?" answers that were yes.

    Returns None when no customer has answered yet, so "no answers" never reads as 0%.
    """
    answers = [
        outcome.still_working for outcome in stats.outcomes if outcome.still_working is not None
    ]
    if not answers:
        return None
    return sum(answers) / len(answers)


def is_newcomer(stats: ProviderStats) -> bool:
    """True while the provider has fewer than ESTABLISHED_AT_COMPLETED_JOBS completed in-app jobs.

    Off-app jobs don't count here: a provider new to the app is shown as new, however
    much work they did before joining.
    """
    return count_completed_jobs(stats) < ESTABLISHED_AT_COMPLETED_JOBS


def build_trust_breakdown(stats: ProviderStats) -> TrustBreakdown:
    """Builds the breakdown behind a trust score: jobs, repeat customers, off-app, still working."""
    return TrustBreakdown(
        jobs=count_completed_jobs(stats),
        repeat_customers=stats.repeat_customers,
        off_app_confirmed=count_off_app_confirmed(stats),
        still_working_rate=calculate_still_working_rate(stats),
    )


def build_evidence(candidate: Candidate) -> Evidence:
    """Builds the evidence strip for a provider card."""
    return Evidence(
        jobs=count_completed_jobs(candidate.stats),
        repeat_customers=candidate.stats.repeat_customers,
        photos=candidate.photos,
        off_app_confirmed=count_off_app_confirmed(candidate.stats),
    )
