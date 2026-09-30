"""The privacy gate: what each person may see of a job.

Every route that returns a job goes through `job_view`. It returns JobUnlocked (adds the exact
address, both phone numbers and the provider's photo) only when the job has reached `confirmed`
and the viewer is that job's customer or its confirmed provider. Everyone else gets JobPublic:
the suburb and the problem. Nothing else in the API builds a job response.
"""

import datetime as dt
from typing import Any

from sqlmodel import Session, select

from fixa_api.geo import distance_km
from fixa_api.job_states import OPEN_FOR_QUOTES, UNLOCKED_STATES
from fixa_api.models import Customer, Job, Provider, Quote
from fixa_api.photos import photo_id_from_url, signed_photo_url
from lang import detect_language, translate

PUBLIC_FIELDS = (
    "id",
    "state",
    "trade",
    "size",
    "urgency",
    "suburb",
    "problem_lang",
    "needs_licence",
)


def iso(moment: dt.datetime) -> str:
    return moment.isoformat()


def is_job_customer(job: Job, viewer: Customer | Provider) -> bool:
    return viewer.role == "customer" and job.customer_id == viewer.id


def is_job_provider(job: Job, viewer: Customer | Provider) -> bool:
    return viewer.role == "provider" and job.provider_id == viewer.id


def has_quote_on(session: Session, job: Job, provider: Provider) -> bool:
    query = select(Quote).where(Quote.job_id == job.id, Quote.provider_id == provider.id)
    return session.exec(query).first() is not None


def can_see_job(session: Session, job: Job, viewer: Customer | Provider) -> bool:
    """Its customer; its confirmed provider; a provider who quoted; or a provider of the right
    trade while the job is still asking for quotes (that is the feed)."""
    if is_job_customer(job, viewer) or is_job_provider(job, viewer):
        return True
    if viewer.role != "provider":
        return False
    if job.needs_licence and not viewer.licensed:
        return False  # licensed work is never shown to, or quoted on by, unlicensed providers
    if has_quote_on(session, job, viewer):
        return True
    return job.state in OPEN_FOR_QUOTES and job.trade in viewer.trades


def is_unlocked_for(job: Job, viewer: Customer | Provider) -> bool:
    return job.state in UNLOCKED_STATES and (
        is_job_customer(job, viewer) or is_job_provider(job, viewer)
    )


def reading_lang(viewer: Customer | Provider, author_id: str, written_lang: str) -> str:
    """The language a viewer reads a text in: their own, except for their own words, which
    they see as written. Their setting can differ from the language they wrote in."""
    return written_lang if viewer.id == author_id else viewer.lang


def distance_for(session: Session, job: Job, viewer: Customer | Provider) -> float:
    """A provider sees how far the job is from their home. A customer sees how far their
    provider is (0.0 until one is accepted). Only the rounded number leaves the server."""
    if viewer.role == "provider":
        return distance_km(viewer.lat, viewer.lng, job.lat, job.lng)
    provider = session.get(Provider, job.provider_id) if job.provider_id else None
    if provider is None:
        return 0.0
    return distance_km(provider.lat, provider.lng, job.lat, job.lng)


def job_view(session: Session, job: Job, viewer: Customer | Provider) -> dict[str, Any]:
    """JobPublic for everyone, or JobUnlocked when the gate is open for this viewer."""
    view: dict[str, Any] = {name: getattr(job, name) for name in PUBLIC_FIELDS}
    # job.problem was scanned when it was posted, so contact details are already hidden. The
    # reader gets it in their own language, with the text as written one tap away.
    target_lang = reading_lang(viewer, job.customer_id, job.problem_lang)
    translation = translate(job.problem, target_lang, job.problem_lang)
    view["problem"] = translation.text
    view["problem_original"] = job.problem
    view["translation_flagged"] = translation.flagged
    view["photo_url"] = (
        signed_photo_url(photo_id_from_url(job.photo_url)) if job.photo_url else None
    )
    view["distance_km"] = distance_for(session, job, viewer)
    view["created_at"] = iso(job.created_at)
    if is_unlocked_for(job, viewer):
        customer = session.get(Customer, job.customer_id)
        provider = session.get(Provider, job.provider_id)
        view["address"] = job.address
        view["customer_phone"] = customer.phone
        view["provider_phone"] = provider.phone
        view["provider_photo_url"] = None  # provider photos arrive with the photos endpoint
    return view


def quote_view(quote: Quote, viewer: Customer | Provider, sender_lang: str) -> dict[str, Any]:
    """A quote as the viewer reads it. The note was scanned when it was sent; the viewer gets it
    in their own language. Its language is detected here (and cached), since a quote has no
    column for it; sender_lang, the provider's setting, is the fallback."""
    message = quote.message
    if message:
        written_lang = detect_language(message, sender_lang)
        target_lang = reading_lang(viewer, quote.provider_id, written_lang)
        message = translate(message, target_lang, written_lang).text
    return {
        "id": quote.id,
        "job_id": quote.job_id,
        "provider_id": quote.provider_id,
        "amount_rands": quote.amount_rands,
        "when": iso(quote.when),
        "message": message,
        "state": quote.state,
        "created_at": iso(quote.created_at),
    }
