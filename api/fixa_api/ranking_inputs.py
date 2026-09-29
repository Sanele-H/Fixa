"""Turns database rows into the inputs P4's ranking package asks for.

The API calls the ranking package only through its public functions: rank_providers,
trust_summary, price_range and list_nearby_providers. This module builds what they take.

Fairness: a provider's job evidence (ProviderStats) is built from finished jobs and confirmed
off-app jobs only. Language, nationality, ID badge and photos of the person never go into it.
Exact locations stay here: the package only receives a distance in kilometres.
"""

import datetime as dt
from collections import Counter, defaultdict

from sqlmodel import Session, select

from fixa_api.geo import distance_km
from fixa_api.job_states import CONFIRMED, IN_PROGRESS
from fixa_api.models import Customer, Job, OffAppJob, Provider, Quote
from ranking import AcceptedQuote, Candidate, NearbyCandidate, ProviderStats
from ranking.models import JobOutcome

ACTIVE_JOB_STATES = {CONFIRMED, IN_PROGRESS}
CONFIRMED_OFF_APP = "confirmed"


def build_stats(session: Session) -> dict[str, ProviderStats]:
    """Job evidence for every provider: finished in-app jobs, plus off-app jobs the customer
    confirmed. A job with no finish date yet says nothing about the provider, so it is left out."""
    outcomes: dict[str, list[JobOutcome]] = defaultdict(list)
    jobs_per_customer: dict[str, Counter] = defaultdict(Counter)
    finished_jobs = select(Job).where(Job.provider_id.is_not(None), Job.completed.is_not(None))
    for job in session.exec(finished_jobs):
        if job.finished_on is None:
            continue
        outcomes[job.provider_id].append(
            JobOutcome(
                finished_on=job.finished_on,
                completed=job.completed,
                still_working=job.still_working,
            )
        )
        if job.completed:
            jobs_per_customer[job.provider_id][job.customer_id] += 1
    confirmed_off_app = select(OffAppJob).where(OffAppJob.state == CONFIRMED_OFF_APP)
    for job in session.exec(confirmed_off_app):
        outcomes[job.provider_id].append(
            JobOutcome(finished_on=job.date, completed=True, off_app=True)
        )
    return {
        provider_id: ProviderStats(
            outcomes=provider_outcomes,
            repeat_customers=sum(1 for n in jobs_per_customer[provider_id].values() if n > 1),
        )
        for provider_id, provider_outcomes in outcomes.items()
    }


def stats_for(all_stats: dict[str, ProviderStats], provider_id: str) -> ProviderStats:
    """A provider's evidence, or an empty record for a provider with no work yet."""
    return all_stats.get(provider_id, ProviderStats())


def count_open_quotes(session: Session) -> Counter:
    """Open quotes per provider, for the cap that spreads work out."""
    return Counter(session.exec(select(Quote.provider_id).where(Quote.state == "open")))


def count_active_jobs(session: Session) -> Counter:
    """Confirmed jobs not yet done, per provider, for the same cap."""
    query = select(Job.provider_id).where(
        Job.state.in_(ACTIVE_JOB_STATES), Job.provider_id.is_not(None)
    )
    return Counter(session.exec(query))


def build_candidates(session: Session, job: Job) -> list[Candidate]:
    """Every provider of the job's trade, with distance from the job (rounded, never exact)."""
    all_stats = build_stats(session)
    open_quotes, active_jobs = count_open_quotes(session), count_active_jobs(session)
    return [
        Candidate(
            provider_id=provider.id,
            display_name=provider.display_name,
            trades=provider.trades,
            distance_km=distance_km(provider.lat, provider.lng, job.lat, job.lng),
            id_badge=provider.id_badge,
            licensed=provider.licensed,
            open_quotes=open_quotes[provider.id],
            active_jobs=active_jobs[provider.id],
            stats=stats_for(all_stats, provider.id),
        )
        for provider in session.exec(select(Provider))
        if job.trade in provider.trades
    ]


def build_nearby_candidate(
    provider: Provider, all_stats: dict[str, ProviderStats], home_lat: float, home_lng: float
) -> NearbyCandidate:
    return NearbyCandidate(
        provider_id=provider.id,
        display_name=provider.display_name,
        suburb=provider.suburb,
        trades=provider.trades,
        langs=provider.langs,
        distance_km=distance_km(provider.lat, provider.lng, home_lat, home_lng),
        id_badge=provider.id_badge,
        stats=stats_for(all_stats, provider.id),
    )


def build_nearby_candidates(session: Session, customer: Customer) -> list[NearbyCandidate]:
    """Every provider, with distance from the customer's home."""
    all_stats = build_stats(session)
    return [
        build_nearby_candidate(provider, all_stats, customer.lat, customer.lng)
        for provider in session.exec(select(Provider))
    ]


def build_accepted_quotes(session: Session) -> list[AcceptedQuote]:
    """Accepted quotes joined with their job's trade, size and suburb, for the price range."""
    query = select(Quote, Job).join(Job, Job.id == Quote.job_id).where(Quote.state == "accepted")
    return [
        AcceptedQuote(
            trade=job.trade, size=job.size, suburb=job.suburb, amount_rands=quote.amount_rands
        )
        for quote, job in session.exec(query)
    ]


def today() -> dt.date:
    return dt.datetime.now(dt.UTC).date()
