"""Customer vouches: a few words from a customer who hired the provider, shown on their record.

Only a customer with a finished job with that provider can vouch, once. The text is scanned, so
a phone number or link never gets through, and illegal-request text is refused. Not in
contracts/api.md yet.
"""

import datetime as dt
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from fixa_api.auth import current_user, require_role
from fixa_api.blocking import refuse_if_prohibited
from fixa_api.db import get_session
from fixa_api.job_views import iso
from fixa_api.messages import safe_text_for
from fixa_api.models import Customer, CustomerVouch, Job, Provider

router = APIRouter(prefix="/api", tags=["vouches"])

MIN_VOUCH_CHARS = 10
MAX_VOUCH_CHARS = 300
CustomerUser = Annotated[Customer, Depends(require_role("customer"))]
User = Annotated[Customer | Provider, Depends(current_user)]
DbSession = Annotated[Session, Depends(get_session)]


class NewVouch(BaseModel):
    text: str = Field(min_length=MIN_VOUCH_CHARS, max_length=MAX_VOUCH_CHARS)


def vouch_view(vouch: CustomerVouch) -> dict[str, str]:
    """What a vouch shows: the words, the suburb and the date. Never who wrote it."""
    return {
        "id": vouch.id,
        "text": vouch.text,
        "suburb": vouch.suburb,
        "given_on": iso(vouch.created_at),
    }


def find_provider(session: Session, provider_id: str) -> Provider:
    provider = session.get(Provider, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


def has_finished_a_job_together(session: Session, customer: Customer, provider: Provider) -> bool:
    query = select(Job).where(
        Job.customer_id == customer.id, Job.provider_id == provider.id, Job.completed.is_(True)
    )
    return session.exec(query).first() is not None


@router.post("/providers/{provider_id}/vouches", status_code=201)
def create_vouch(provider_id: str, body: NewVouch, customer: CustomerUser, session: DbSession):
    provider = find_provider(session, provider_id)
    refuse_if_prohibited(session, customer, body.text, "vouch")
    if not has_finished_a_job_together(session, customer, provider):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "no_job_together",
                "message": "You can only vouch for a provider after they finished a job for you",
            },
        )
    existing = session.exec(
        select(CustomerVouch).where(
            CustomerVouch.provider_id == provider.id, CustomerVouch.customer_id == customer.id
        )
    ).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="You already vouched for this provider")
    vouch = CustomerVouch(
        id=f"vouch_{uuid.uuid4().hex[:10]}",
        provider_id=provider.id,
        customer_id=customer.id,
        text=safe_text_for(body.text, customer.lang),
        suburb=customer.suburb,
        created_at=dt.datetime.now(dt.UTC),
    )
    session.add(vouch)
    session.commit()
    return vouch_view(vouch)


@router.get("/providers/{provider_id}/vouches")
def read_vouches(provider_id: str, viewer: User, session: DbSession):
    """The vouches for a provider, newest first."""
    provider = find_provider(session, provider_id)
    query = (
        select(CustomerVouch)
        .where(CustomerVouch.provider_id == provider.id)
        .order_by(CustomerVouch.created_at.desc())
    )
    return [vouch_view(vouch) for vouch in session.exec(query)]
