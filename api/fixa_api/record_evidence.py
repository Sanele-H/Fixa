"""Builds the evidence behind a work record from a provider's confirmed jobs.

Only confirmed work goes in: finished in-app jobs, and off-app jobs the customer confirmed. A
job's customer never appears by name, number or address, only the suburb, date and task.
"""

from sqlmodel import Session, select

from fixa_api.models import Job, OffAppJob, Provider, Quote
from record import RecordEvidence, RecordJob

ACCEPTED = "accepted"
CONFIRMED_OFF_APP = "confirmed"


def in_app_record_jobs(session: Session, provider: Provider) -> list[RecordJob]:
    """Finished in-app jobs, with the agreed amount from the accepted quote."""
    finished = select(Job).where(
        Job.provider_id == provider.id, Job.completed.is_(True), Job.finished_on.is_not(None)
    )
    jobs = list(session.exec(finished))
    accepted = select(Quote).where(
        Quote.provider_id == provider.id,
        Quote.state == ACCEPTED,
        Quote.job_id.in_([job.id for job in jobs]),
    )
    amounts = {quote.job_id: quote.amount_rands for quote in session.exec(accepted)}
    return [
        RecordJob(
            done_on=job.finished_on,
            suburb=job.suburb,
            trade=job.trade,
            trade_task=job.trade_task,
            confirmed_via="app",
            amount_rands=amounts.get(job.id),
        )
        for job in jobs
    ]


def off_app_record_jobs(session: Session, provider: Provider) -> list[RecordJob]:
    """Off-app jobs the customer confirmed by SMS or USSD."""
    confirmed = select(OffAppJob).where(
        OffAppJob.provider_id == provider.id, OffAppJob.state == CONFIRMED_OFF_APP
    )
    return [
        RecordJob(
            done_on=job.date,
            suburb=job.suburb,
            trade=job.trade,
            trade_task=job.trade_task,
            confirmed_via=job.confirmed_via or "sms",
            amount_rands=job.amount_rands,
            reference_agreed=bool(job.reference_agreed),
        )
        for job in session.exec(confirmed)
    ]


def build_evidence(session: Session, provider: Provider) -> RecordEvidence:
    """Everything an export or the public record page is built from, oldest job first."""
    jobs = in_app_record_jobs(session, provider) + off_app_record_jobs(session, provider)
    jobs.sort(key=lambda job: job.done_on)
    return RecordEvidence(
        provider_id=provider.id,
        display_name=provider.display_name,
        trades=provider.trades,
        jobs=jobs,
    )
