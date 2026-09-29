"""ID checks: the offline number check and the Home Affairs check (after POPIA consent)."""

import datetime as dt
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from fixa_api.auth import require_role
from fixa_api.db import get_session
from fixa_api.identity import (
    TIER_HOME_AFFAIRS,
    TIER_ID_NUMBER,
    IdentityVerifier,
    VerifierUnavailableError,
    better_tier,
    check_id_number,
    clean_id_number,
    get_verifier,
)
from fixa_api.models import IdentityCheck, Provider

router = APIRouter(prefix="/api/identity", tags=["identity"])

MAX_VERIFY_ATTEMPTS_PER_DAY = 5  # stops one account testing many ID numbers, and keeps costs down
ProviderUser = Annotated[Provider, Depends(require_role("provider"))]
DbSession = Annotated[Session, Depends(get_session)]
Verifier = Annotated[IdentityVerifier, Depends(get_verifier)]


class IdNumber(BaseModel):
    id_number: str = Field(max_length=40)


class IdVerification(BaseModel):
    id_number: str = Field(max_length=40)
    names: str = Field(min_length=1, max_length=100)
    consent: Literal[True]  # POPIA: the provider agreed on the consent screen


def attempts_today(session: Session, provider: Provider, now: dt.datetime) -> int:
    since = now - dt.timedelta(days=1)
    query = select(IdentityCheck).where(
        IdentityCheck.provider_id == provider.id, IdentityCheck.checked_at >= since
    )
    return len(list(session.exec(query)))


@router.post("/check-number")
def check_number(body: IdNumber, provider: ProviderUser):
    """The instant offline check, so a typo fails before anything is sent. Nothing is stored."""
    return check_id_number(body.id_number)


@router.post("/verify")
def verify_identity(
    body: IdVerification, provider: ProviderUser, session: DbSession, verifier: Verifier
):
    """Check the ID number and name with Home Affairs. Only the result is stored.

    A number that passes the offline check earns the `id_number` badge. If the verifier also
    finds it and the name matches, the badge is `home_affairs`. A badge is never lowered.
    """
    offline = check_id_number(body.id_number)
    if not offline["valid"]:
        raise HTTPException(
            status_code=422, detail={"error": "invalid_id_number", "reason": offline["reason"]}
        )
    now = dt.datetime.now(dt.UTC)
    if attempts_today(session, provider, now) >= MAX_VERIFY_ATTEMPTS_PER_DAY:
        raise HTTPException(status_code=429, detail="Too many ID checks today. Try again tomorrow.")
    try:
        result = verifier.verify(clean_id_number(body.id_number), body.names, consent=True)
    except VerifierUnavailableError:
        raise HTTPException(
            status_code=503, detail="The ID check is unavailable right now"
        ) from None
    tier = TIER_HOME_AFFAIRS if result.verified and result.name_match else TIER_ID_NUMBER
    check = IdentityCheck(
        id=f"idcheck_{uuid.uuid4().hex[:10]}",
        provider_id=provider.id,
        tier=tier,
        verified=result.verified,
        name_match=result.name_match,
        provider=result.provider,
        reference=result.reference,
        checked_at=now,
        consent_at=now,
    )
    provider.id_badge = better_tier(provider.id_badge, tier)
    session.add_all([check, provider])
    session.commit()
    return {
        "tier": tier,
        "verified": result.verified,
        "name_match": result.name_match,
        "provider": result.provider,
        "reference": result.reference,
        "checked_at": now.isoformat(),
    }
