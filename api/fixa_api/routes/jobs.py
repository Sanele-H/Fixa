"""Jobs: posting, the state changes, quotes, the provider feed and the ranked provider list."""

import datetime as dt
import uuid
from typing import Annotated, Literal

import numpy as np
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from pydantic import AwareDatetime, BaseModel, Field, field_validator
from sqlmodel import Session, or_, select

from fixa_api import job_states as states
from fixa_api.auth import current_user, require_role
from fixa_api.blocking import ensure_not_restricted, refuse_if_prohibited
from fixa_api.db import get_session
from fixa_api.geocoding import Geocoder, get_geocoder
from fixa_api.job_views import (
    can_see_job,
    is_job_customer,
    is_job_provider,
    job_view,
    quote_view,
)
from fixa_api.licence import needs_licence_for
from fixa_api.messages import safe_text_for
from fixa_api.models import DEFAULT_QUOTE_PAYMENT_METHODS, Customer, Job, Photo, Provider, Quote
from fixa_api.notifications import notify
from fixa_api.payment_plans import (
    IN_APP_SPLIT,
    REFUND_OWED,
    UNDER_REVIEW,
    check_deposit,
    create_plan,
    delete_plan,
    list_payments,
    read_pending_change,
    settle_cancelled_job,
)
from fixa_api.photos import PHOTO_URL_PREFIX
from fixa_api.ranking_inputs import build_candidates, today
from fixa_api.routes.places import find_place_or_refuse
from fixa_api.sms import SmsSender, get_sms_sender, send_safely
from fixa_api.sms_texts import details_unlocked_messages
from fixa_api.trades import known_trades
from lang import detect_language
from lang import understand_job as read_job_description
from ranking import JobRequest, rank_providers

router = APIRouter(prefix="/api", tags=["jobs"])

FEED_LIMIT = 20  # each job is translated for the reader, so keep the feed short
MY_JOBS_LIMIT = 20  # the same reason, for GET /api/jobs

Lang = Literal["en", "zu", "xh"]
PaymentMethod = Literal["in_app_after", "in_app_split", "cash"]
User = Annotated[Customer | Provider, Depends(current_user)]
CustomerUser = Annotated[Customer, Depends(require_role("customer"))]
ProviderUser = Annotated[Provider, Depends(require_role("provider"))]
DbSession = Annotated[Session, Depends(get_session)]
Sender = Annotated[SmsSender, Depends(get_sms_sender)]
PlaceFinder = Annotated[Geocoder, Depends(get_geocoder)]

COORDINATE_DECIMALS = 5  # about 1 m, like the seed data


class UnderstandRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    lang: Lang


class JobLocation(BaseModel):
    """A pin the customer dropped on the map, when the job isn't at their home."""

    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class NewJob(BaseModel):
    description: str = Field(min_length=1, max_length=1000)
    lang: Lang
    trade: str
    urgency: Literal["low", "normal", "urgent"]
    size: Literal["small", "medium", "large"]
    suburb: str
    photo_id: str | None = None
    needs_licence: bool = False  # the customer can insist on a licensed provider
    directions: str | None = Field(default=None, max_length=500)
    location: JobLocation | None = None  # None: the job is at the customer's home

    @field_validator("trade")
    @classmethod
    def trade_must_be_known(cls, trade: str) -> str:
        if trade not in known_trades():
            raise ValueError(f"trade must be one of {sorted(known_trades())}")
        return trade


class NewQuote(BaseModel):
    """A quote, and the ways the provider accepts payment. deposit_rands is needed (at most
    half the amount) when in_app_split is offered, and ignored otherwise."""

    amount_rands: int = Field(gt=0, le=1_000_000)
    when: AwareDatetime
    message: str | None = Field(default=None, max_length=500)
    payment_methods: list[PaymentMethod] = Field(
        default_factory=lambda: list(DEFAULT_QUOTE_PAYMENT_METHODS), min_length=1
    )
    deposit_rands: int | None = Field(default=None, gt=0)

    @field_validator("payment_methods")
    @classmethod
    def drop_repeated_methods(cls, methods: list[str]) -> list[str]:
        return list(dict.fromkeys(methods))


class AcceptQuote(BaseModel):
    """How the customer will pay: one of the quote's payment_methods. Left out, the quote's
    first one."""

    payment_method: PaymentMethod | None = None


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
def understand_job(body: UnderstandRequest, customer: CustomerUser, session: DbSession):
    """Suggest a trade, urgency and size from the customer's own words, in any of our languages.
    The customer confirms or changes it before posting."""
    refuse_if_prohibited(session, customer, body.text, "understand")
    # A flagged text was refused above, so `prohibited` is always empty here: leave it out to keep
    # the contract's shape (trade, urgency, size, confidence).
    return read_job_description(body.text, body.lang).model_dump(exclude={"prohibited"})


def place_job(job: Job, customer: Customer, location: JobLocation | None, geocoder: Geocoder):
    """Sets where the job is: the customer's home, or the pin they dropped. A pin's suburb and
    street address come from the server's own lookup, never from the phone, so a job can't claim
    a suburb it isn't in. Ranking, the feed's distances and the price range all read these."""
    if location is None:
        job.suburb, job.address, job.lat, job.lng = (
            customer.suburb,
            customer.address,
            customer.lat,
            customer.lng,
        )
        return
    place = find_place_or_refuse(geocoder, location.lat, location.lng)
    job.suburb, job.address = place.suburb, place.label
    job.lat = round(location.lat, COORDINATE_DECIMALS)
    job.lng = round(location.lng, COORDINATE_DECIMALS)


@router.post("/jobs", status_code=201)
def create_job(body: NewJob, customer: CustomerUser, session: DbSession, geocoder: PlaceFinder):
    """Post a job, at the customer's home or at a pin on the map. Whatever suburb the phone sends
    is ignored (see place_job)."""
    refuse_if_prohibited(session, customer, body.description, "job_post")
    photo_url = attach_photo(session, customer, body.photo_id)
    problem = safe_text_for(body.description, body.lang)
    safe_directions = safe_text_for(body.directions, body.lang) if body.directions else None
    job = Job(
        id=new_id("job"),
        customer_id=customer.id,
        state=states.POSTED,
        trade=body.trade,
        trade_task=body.trade,
        size=body.size,
        urgency=body.urgency,
        needs_licence=body.needs_licence or needs_licence_for(body.trade, body.description),
        suburb="",
        address="",
        lat=0.0,
        lng=0.0,
        problem=problem,
        problem_lang=detect_language(problem, body.lang),
        directions=safe_directions,
        photo_url=photo_url,
        created_at=now(),
    )
    place_job(job, customer, body.location, geocoder)
    session.add(job)
    session.commit()
    return job_view(session, job, customer)


def is_my_job(user: Customer | Provider):
    """The condition for a person's own jobs: a customer's posts, or the jobs a provider quoted
    on or was picked for."""
    if user.role == "customer":
        return (Job.customer_id == user.id) & Job.deleted_at.is_(None)
    quoted_job_ids = select(Quote.job_id).where(Quote.provider_id == user.id)
    return or_(Job.provider_id == user.id, Job.id.in_(quoted_job_ids))


@router.get("/jobs")
def read_my_jobs(user: User, session: DbSession):
    """A person's own jobs, newest first. Each goes through the same privacy gate as the job
    page, so contact details show only on confirmed jobs, and only to their two people."""
    query = select(Job).where(is_my_job(user)).order_by(Job.created_at.desc()).limit(MY_JOBS_LIMIT)
    return [job_view(session, job, user) for job in session.exec(query)]


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
    """Open jobs in the provider's trades, newest first: the suburb and the problem only. Work
    that needs a licence is left out for providers who don't hold one."""
    query = select(Job).where(Job.state.in_(states.OPEN_FOR_QUOTES), Job.trade.in_(provider.trades))
    if not provider.licensed:
        query = query.where(Job.needs_licence.is_(False))  # licensed work isn't shown to them
    query = query.order_by(Job.created_at.desc()).limit(FEED_LIMIT)
    return [job_view(session, job, provider) for job in session.exec(query)]


@router.post("/jobs/{job_id}/quotes", status_code=201)
def create_quote(job_id: str, body: NewQuote, provider: ProviderUser, session: DbSession):
    job = find_job(session, job_id, provider)
    ensure_not_restricted(session, provider)  # a quote without a note is still publishing
    if body.message:
        refuse_if_prohibited(session, provider, body.message, "quote")
    if job.state not in states.OPEN_FOR_QUOTES:
        raise HTTPException(status_code=409, detail="This job is no longer asking for quotes")
    already_open = [
        quote
        for quote in job_quotes(session, job.id)
        if quote.provider_id == provider.id and quote.state == "open"
    ]
    if already_open:
        raise HTTPException(status_code=409, detail="You already have an open quote on this job")
    deposit_rands = None
    if IN_APP_SPLIT in body.payment_methods:
        deposit_rands = check_deposit(IN_APP_SPLIT, body.deposit_rands, body.amount_rands)
    quote = Quote(
        id=new_id("quote"),
        job_id=job.id,
        provider_id=provider.id,
        amount_rands=body.amount_rands,
        when=body.when,
        message=safe_text_for(body.message, provider.lang) if body.message else None,
        state="open",
        created_at=now(),
        payment_methods=body.payment_methods,
        deposit_rands=deposit_rands,
    )
    if job.state == states.POSTED:
        move_job(job, states.QUOTING)
    session.add_all([quote, job])
    session.commit()
    notify(
        session,
        session.get(Customer, job.customer_id),
        "quote_received",
        job.id,
        name=provider.display_name,
        amount=quote.amount_rands,
    )
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
def accept_quote(
    quote_id: str, customer: CustomerUser, session: DbSession, body: AcceptQuote | None = None
):
    """The customer picks a quote and one of the ways it can be paid. The payment plan is agreed
    here (see payment_plans.py); the body can be left out, for the quote's first way."""
    quote = session.get(Quote, quote_id)
    job = session.get(Job, quote.job_id) if quote else None
    if job is None or not is_job_customer(job, customer):
        raise HTTPException(status_code=404, detail="Quote not found")
    if quote.state != "open":
        raise HTTPException(status_code=409, detail="This quote is no longer open")
    # The plan first: a way to pay the quote doesn't offer is refused before anything changes.
    create_plan(session, job, quote, body.payment_method if body else None)
    move_job(job, states.QUOTE_ACCEPTED)
    quote.state = "accepted"
    job.provider_id = quote.provider_id
    session.add_all([quote, job])
    session.commit()
    notify(
        session,
        session.get(Provider, quote.provider_id),
        "quote_accepted",
        job.id,
        name=customer.display_name,
        amount=quote.amount_rands,
    )
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
    notify(session, customer, "job_confirmed", job.id, name=provider.display_name)
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
    delete_plan(session, job.id)  # the next accepted quote brings its own
    job.provider_id = None
    session.add(job)
    session.commit()
    notify(
        session,
        session.get(Customer, job.customer_id),
        "job_declined",
        job.id,
        name=provider.display_name,
    )
    return job_view(session, job, provider)


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, customer: CustomerUser, session: DbSession):
    job = session.get(Job, job_id)
    if job is None or not is_job_customer(job, customer):
        raise HTTPException(status_code=404, detail="Job not found")
    state_before = job.state
    move_job(job, states.CANCELLED)
    for quote in job_quotes(session, job.id):
        if quote.state == "open":
            quote.state = "withdrawn"
            session.add(quote)
    change = read_pending_change(session, job.id)
    if change is not None:
        change.state = "withdrawn"
        session.add(change)
    session.add(job)
    session.commit()
    settle_cancelled_job(session, job, state_before)  # refunds any deposit, or holds it
    return job_view(session, job, customer)


# A customer can delete a job nobody has quoted on yet, or one that's over (cancelled).
DELETABLE_STATES = {states.POSTED, states.CANCELLED}
# Money still to be settled keeps a job on the list, so its receipt stays in reach.
UNSETTLED_REFUND_STATES = {REFUND_OWED, UNDER_REVIEW}


def has_unsettled_money(session: Session, job_id: str) -> bool:
    return any(p.refund_state in UNSETTLED_REFUND_STATES for p in list_payments(session, job_id))


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: str, customer: CustomerUser, session: DbSession) -> Response:
    """Removes a job from the customer's list: one still posted (no quotes yet), which is also
    taken off the feed, or a cancelled one. Refused (409) for a job with quotes or work under
    way (cancel it first) and while a refund is still owed or under review. The row is kept and
    marked deleted, so providers' records and the ranking's no-show evidence stay as they were."""
    job = session.get(Job, job_id)
    if job is None or not is_job_customer(job, customer) or job.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.state not in DELETABLE_STATES:
        raise HTTPException(
            status_code=409,
            detail={"error": "job_in_use", "message": "Cancel this job before deleting it"},
        )
    if has_unsettled_money(session, job.id):
        raise HTTPException(
            status_code=409,
            detail={"error": "refund_pending", "message": "Wait until the refund is settled"},
        )
    if job.state == states.POSTED:
        move_job(job, states.CANCELLED)  # off the providers' feed too
    job.deleted_at = now()
    session.add(job)
    session.commit()
    return Response(status_code=204)
