"""list_nearby_providers: who works near a customer, for browsing before there's a job.

Browsing is for looking, not for picking. Hiring still goes through a job and
rank_providers, where the caps and the newcomer slot spread the work around.

1. Keep providers who offer the trade and are within the customer's chosen radius.
2. If the customer picked a language, keep providers who speak it. This is the only place
   a provider's language is read, and only as the customer's own filter, never as a score.
3. Order by distance alone, nearest first. Trust is never read here, so a strong record
   doesn't buy a head start before a job exists, and the result carries no trust badge.
"""

from ranking.evidence import build_evidence, is_newcomer
from ranking.models import Language, NearbyCandidate, NearbyProvider
from ranking.ranker import DISTANCE_DECIMALS

DEFAULT_RADIUS_KM = 10.0  # covers the inner city from Braamfontein, not Soweto or Tembisa
MAX_RADIUS_KM = 30.0  # the widest radius a customer may ask for, so the list stays short


def list_nearby_providers(
    candidates: list[NearbyCandidate],
    trade: str,
    lang: Language | None = None,
    radius_km: float = DEFAULT_RADIUS_KM,
) -> list[NearbyProvider]:
    """Lists the providers of a trade near a customer, nearest first.

    Args:
        candidates: every provider P2 could show, with distance_km from the customer's home.
        trade: the trade id the customer is browsing, for example "plumbing".
        lang: only keep providers who speak this app language. None keeps everyone.
        radius_km: how far from home counts as near, chosen by the customer. Must be more
            than 0 and at most MAX_RADIUS_KM; P2 should reject anything else with a 422.

    Returns:
        One NearbyProvider per matching provider, nearest first. Providers at the same
        distance keep their input order.

    Raises:
        ValueError: if radius_km is 0 or less, or more than MAX_RADIUS_KM.
    """
    check_radius(radius_km)
    matching_candidates = [
        candidate for candidate in candidates if is_match(candidate, trade, lang, radius_km)
    ]
    nearest_first = sorted(matching_candidates, key=lambda candidate: candidate.distance_km)
    return [build_nearby_provider(candidate) for candidate in nearest_first]


def check_radius(radius_km: float) -> None:
    """Raises ValueError unless the radius is more than 0 and at most MAX_RADIUS_KM."""
    if not 0 < radius_km <= MAX_RADIUS_KM:
        raise ValueError(f"radius_km must be more than 0 and at most {MAX_RADIUS_KM}")


def is_match(
    candidate: NearbyCandidate, trade: str, lang: Language | None, radius_km: float
) -> bool:
    """True if the provider offers the trade, is within the radius, and speaks lang if given."""
    return (
        trade in candidate.trades
        and candidate.distance_km <= radius_km
        and (lang is None or lang in candidate.langs)
    )


def build_nearby_provider(candidate: NearbyCandidate) -> NearbyProvider:
    """Builds one card on the nearby list: display fields and the evidence strip, no trust."""
    return NearbyProvider(
        provider_id=candidate.provider_id,
        display_name=candidate.display_name,
        suburb=candidate.suburb,
        trades=candidate.trades,
        langs=candidate.langs,
        distance_km=round(candidate.distance_km, DISTANCE_DECIMALS),
        is_newcomer=is_newcomer(candidate.stats),
        id_badge=candidate.id_badge,
        evidence=build_evidence(candidate),
    )
