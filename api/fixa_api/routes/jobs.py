"""Jobs: posting, the state changes, quotes, the provider feed and the ranked provider list."""

import datetime as dt
import uuid
from typing import Annotated, Literal

import numpy as np
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import AwareDatetime, BaseModel, Field, field_validator
from sqlmodel import Session, select

from fixa_api import job_states as states
from fixa_api.auth import current_user, require_role
from fixa_api.db import get_session
from fixa_api.job_views import (
    can_see_job,
    is_job_customer,
    is_job_provider,
    job_view,
    quote_view,
)
from fixa_api.messages import safe_text_for
from fixa_api.models import Customer, Job, Photo, Provider, Quote
from fixa_api.photos import PHOTO_URL_PREFIX
from fixa_api.ranking_inputs import build_candidates, today
from fixa_api.sms import SmsSender, get_sms_sender, send_safely
from fixa_api.sms_texts import details_unlocked_messages
from fixa_api.trades import known_trades
from lang import detect_language
from lang import understand_job as read_job_description
from ranking import JobRequest, rank_providers

router = APIRouter(prefix="/api", tags=["jobs"])

FEED_LIMIT = 20  # each job is translated for the reader, so keep the feed short

Lang = Literal["en", "zu", "xh"]
User = Annotated[Customer | Provider, Depends(current_user)]
CustomerUser = Annotated[Customer, Depends(require_role("customer"))]
ProviderUser = Annotated[Provider, Depends(require_role("provider"))]
DbSession = Annotated[Session, Depends(get_session)]
Sender = Annotated[SmsSender, Depends(get_sms_sender)]


class UnderstandRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    lang: Lang


class NewJob(BaseModel):
    description: str = Field(min_length=1, max_length=1000)
    lang: Lang
    trade: str
    urgency: Literal["low", "normal", "urgent"]
    size: Literal["small", "medium", "large"]
    suburb: str
    photo_id: str | None = None

    @field_validator("trade")
    @classmethod
    def trade_must_be_known(cls, trade: str) -> str:
        if trade not in known_trades():
            raise ValueError(f"trade must be one of {sorted(known_trades())}")
        return trade


class NewQuote(BaseModel):
    amount_rands: int = Field(gt=0, le=1_000_000)
    when: AwareDatetime
    message: str | None = Field(default=None, max_length=500)


def now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def find_job(session: Session, job_id: str, viewer: Customer | Provider) -> Job:
    """The job, or 404. Someone who may not see a job gets the same 404 as a job that isn't
    there, so job ids can't be probed."""
    job = session.get(Job, job_id)
    if job is None or not can_see_job(session, job, viewer):
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def attach_photo(session: Session, customer: Customer, photo_id: str | None) -> str | None:
    """The link to store for a job's photo. It must be the customer's own upload, not already
    used on another job."""
    if photo_id is None:
        return None
    photo = session.get(Photo, photo_id)
    url = f"{PHOTO_URL_PREFIX}{photo_id}"
    taken = session.exec(select(Job).where(Job.photo_url == url)).first()
    if photo is None or photo.owner_id != customer.id or taken is not None:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_photo", "message": "That photo can't be used for this job"},
        )
    return url


def move_job(job: Job, new_state: str) -> None:
    try:
        states.check_transition(job.state, new_state)
    except states.InvalidTransitionError as problem:
        raise HTTPException(status_code=409, detail=str(problem)) from None
    job.state = new_state


def job_quotes(session: Session, job_id: str) -> list[Quote]:
    query = select(Quote).where(Quote.job_id == job_id).order_by(Quote.created_at)
    return list(session.exec(query))


@router.post("/jobs/understand")
def understand_job(body: UnderstandRequest, customer: CustomerUser):
    """Suggest a trade, urgency and size from the customer's own words, in any of our languages.
    The customer confirms or changes it before posting."""
    return read_job_description(body.text, body.lang).model_dump()


@router.post("/jobs", status_code=201)
def create_job(body: NewJob, customer: CustomerUser, session: DbSession):
    """Post a job. The address and location come from the customer's account and the suburb
    from their home, so whatever suburb the phone sends can't misplace the job."""
    photo_url = attach_photo(session, customer, body.photo_id)
    problem = safe_text_for(body.description, body.lang)
    job = Job(
        id=new_id("job"),
        customer_id=customer.id,
        state=states.POSTED,
        trade=body.trade,
        trade_task=body.trade,
        size=body.size,
        urgency=body.urgency,
        needs_licence=False,
        suburb=customer.suburb,
        address=customer.address,
        lat=customer.lat,
        lng=customer.lng,
        problem=problem,
        problem_lang=detect_language(problem, body.lang),
        photo_url=photo_url,
        created_at=now(),
    )
    session.add(job)
    session.commit()
    return job_view(session, job, customer)


@router.get("/jobs/{job_id}")
def read_job(job_id: str, user: User, session: DbSession):
    return job_view(session, find_job(session, job_id, user), user)


@router.get("/jobs/{job_id}/providers")
def read_ranked_providers(job_id: str, customer: CustomerUser, session: DbSession):
    """The providers for this job, best first. A fresh random generator per search is what lets
    newcomers be shown some of the time (see ranking.rank_providers)."""
    job = session.get(Job, job_id)
    if job is None or not is_job_customer(job, customer):
        raise HTTPException(status_code=404, detail="Job not found")
    request = JobRequest(
        trade=job.trade, size=job.size, needs_licence=job.needs_licence, posted_on=today()
    )
    ranked = rank_providers(request, build_candidates(session, job), np.random.default_rng())
    return [provider.model_dump() for provider in ranked]


@router.get("/feed")
def read_feed(provider: ProviderUser, session: DbSession):
    """Open jobs in the provider's trades, newest first: the suburb and the problem only."""
    query = (
        select(Job)
        .where(Job.state.in_(states.OPEN_FOR_QUOTES), Job.trade.in_(provider.trades))
        .order_by(Job.created_at.desc())
        .limit(FEED_LIMIT)
    )
    return [job_view(session, job, provider) for job in session.exec(query)]


@router.post("/jobs/{job_id}/quotes", status_code=201)
def create_quote(job_id: str, body: NewQuote, provider: ProviderUser, session: DbSession):
    job = find_job(session, job_id, provider)
    if job.state not in states.OPEN_FOR_QUOTES:
        raise HTTPException(status_code=409, detail="This job is no longer asking for quotes")
    already_open = [
        quote
        for quote in job_quotes(session, job.id)
        if quote.provider_id == provider.id and quote.state == "open"
    ]
    if already_open:
        raise HTTPException(status_code=409, detail="You already have an open quote on this job")
    quote = Quote(
        id=new_id("quote"),
        job_id=job.id,
        provider_id=provider.id,
        amount_rands=body.amount_rands,
        when=body.when,
        message=safe_text_for(body.message, provider.lang) if body.message else None,
        state="open",
        created_at=now(),
    )
    if job.state == states.POSTED:
        move_job(job, states.QUOTING)
    session.add_all([quote, job])
    session.commit()
    return quote_view(quote, provider, provider.lang)


@router.get("/jobs/{job_id}/quotes")
def read_quotes(job_id: str, user: User, session: DbSession):
    """The customer sees every quote on their job; a provider sees only their own."""
    job = find_job(session, job_id, user)
    quotes = job_quotes(session, job.id)
    if not is_job_customer(job, user):
        quotes = [quote for quote in quotes if quote.provider_id == user.id]
    languages = {p.id: p.lang for p in session.exec(select(Provider))}
    return [quote_view(quote, user, languages[quote.provider_id]) for quote in quotes]


@router.post("/quotes/{quote_id}/accept")
def accept_quote(quote_id: str, customer: CustomerUser, session: DbSession):
    quote = session.get(Quote, quote_id)
    job = session.get(Job, quote.job_id) if quote else None
    if job is None or not is_job_customer(job, customer):
        raise HTTPException(status_code=404, detail="Quote not found")
    if quote.state != "open":
        raise HTTPException(status_code=409, detail="This quote is no longer open")
    move_job(job, states.QUOTE_ACCEPTED)
    quote.state = "accepted"
    job.provider_id = quote.provider_id
    session.add_all([quote, job])
    session.commit()
    return job_view(session, job, customer)


def find_job_of_accepted_provider(session: Session, job_id: str, provider: Provider) -> Job:
    job = session.get(Job, job_id)
    if job is None or not is_job_provider(job, provider):
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/confirm")
def confirm_job(
    job_id: str,
    provider: ProviderUser,
    session: DbSession,
    background: BackgroundTasks,
    sender: Sender,
):
    """The provider agrees to the accepted quote. Contact details unlock from here, and both
    sides get an SMS in their own language in case a push notification is late."""
    job = find_job_of_accepted_provider(session, job_id, provider)
    move_job(job, states.CONFIRMED)
    for quote in job_quotes(session, job.id):
        if quote.state == "open":
            quote.state = "declined"
            session.add(quote)
    session.add(job)
    session.commit()
    customer = session.get(Customer, job.customer_id)
    for phone, text in details_unlocked_messages(job, customer, provider):
        background.add_task(send_safely, sender, phone, text, "details unlocked")
    return job_view(session, job, provider)


@router.post("/jobs/{job_id}/decline")
def decline_job(job_id: str, provider: ProviderUser, session: DbSession):
    """The provider turns down the accepted quote. The job goes back to quoting and nothing
    personal has been shared."""
    job = find_job_of_accepted_provider(session, job_id, provider)
    move_job(job, states.QUOTING)
    for quote in job_quotes(session, job.id):
        if quote.state == "accepted":
            quote.state = "declined"
            session.add(quote)
    job.provider_id = None
    session.add(job)
    session.commit()
    return job_view(session, job, provider)


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, customer: CustomerUser, session: DbSession):
    job = session.get(Job, job_id)
    if job is None or not is_job_customer(job, customer):
        raise HTTPException(status_code=404, detail="Job not found")
    move_job(job, states.CANCELLED)
    for quote in job_quotes(session, job.id):
        if quote.state == "open":
            quote.state = "withdrawn"
            session.add(quote)
    session.add(job)
    session.commit()
    return job_view(session, job, customer)
