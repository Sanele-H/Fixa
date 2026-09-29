"""Provider profiles, browsing nearby providers and price guidance, from P4's ranking package.

Nothing here returns a phone number or a location: only a rounded distance in kilometres.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from fixa_api.auth import current_user, require_role
from fixa_api.db import get_session
from fixa_api.geo import distance_km
from fixa_api.models import Customer, Provider
from fixa_api.ranking_inputs import (
    build_accepted_quotes,
    build_nearby_candidate,
    build_nearby_candidates,
    build_stats,
    today,
)
from fixa_api.trades import known_trades
from lang import translate
from ranking import list_nearby_providers, price_range, trust_summary
from ranking.nearby import DEFAULT_RADIUS_KM, MAX_RADIUS_KM

router = APIRouter(prefix="/api", tags=["providers"])

User = Annotated[Customer | Provider, Depends(current_user)]
CustomerUser = Annotated[Customer, Depends(require_role("customer"))]
DbSession = Annotated[Session, Depends(get_session)]


def check_trade(trade: str) -> None:
    if trade not in known_trades():
        raise HTTPException(
            status_code=422, detail=f"trade must be one of {sorted(known_trades())}"
        )


@router.get("/providers")
def read_nearby_providers(
    customer: CustomerUser,
    session: DbSession,
    trade: str,
    lang: Literal["en", "zu", "xh"] | None = None,
    radius_km: Annotated[float, Query(gt=0, le=MAX_RADIUS_KM)] = DEFAULT_RADIUS_KM,
):
    """Who works near the customer's home, nearest first. For looking, not booking: no trust
    badge and no way to contact anyone from here."""
    check_trade(trade)
    rows = list_nearby_providers(build_nearby_candidates(session, customer), trade, lang, radius_km)
    return [row.model_dump() for row in rows]


@router.get("/providers/{provider_id}")
def read_provider(provider_id: str, viewer: User, session: DbSession):
    """A provider's profile: evidence strip, trust range and bio, never a phone or address.
    The distance is from the viewer's own home."""
    provider = session.get(Provider, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    all_stats = build_stats(session)
    candidate = build_nearby_candidate(provider, all_stats, viewer.lat, viewer.lng)
    # The public nearby function gives the evidence strip and the newcomer flag. Radius and trade
    # don't matter for one known provider, so use the widest radius and the provider's own trade.
    row = list_nearby_providers(
        [candidate.model_copy(update={"distance_km": 0.0})], provider.trades[0], None, MAX_RADIUS_KM
    )[0]
    trust = trust_summary(candidate.stats, today())
    return {
        "provider_id": provider.id,
        "display_name": provider.display_name,
        "trades": provider.trades,
        "distance_km": distance_km(provider.lat, provider.lng, viewer.lat, viewer.lng),
        "is_newcomer": row.is_newcomer,
        "id_badge": provider.id_badge,
        "evidence": row.evidence.model_dump(),
        "trust": trust.to_badge().model_dump(),
        "suburb": provider.suburb,
        "langs": provider.langs,
        "bio": translate(provider.bio, viewer.lang, provider.lang).text,
    }


@router.get("/price-range")
def read_price_range(
    viewer: User,
    session: DbSession,
    trade: str,
    size: Literal["small", "medium", "large"],
    suburb: str,
):
    """The typical price from accepted quotes, or null when there is too little data."""
    check_trade(trade)
    result = price_range(trade, size, suburb, build_accepted_quotes(session))
    return None if result is None else result.model_dump()
