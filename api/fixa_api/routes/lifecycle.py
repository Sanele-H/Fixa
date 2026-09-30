"""A job's day and its follow-up: check-in, done (or no-show), and the two-week "still working?".

These are what turn a confirmed job into evidence: finished jobs and "still working" answers feed
the provider's trust range and their record. Routes here are not in contracts/api.md yet.
"""

import datetime as dt
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from fixa_api import job_states as states
from fixa_api.auth import require_role
from fixa_api.db import get_session
from fixa_api.job_views import is_job_customer, is_job_provider, job_view
from fixa_api.models import Customer, Job, JobEvent, Provider
from fixa_api.notifications import notify
from fixa_api.payment_plans import settle_cancelled_job
from fixa_api.routes.jobs import move_job
from fixa_api.safety import start_check_in_timer, stop_timer

router = APIRouter(prefix="/api", tags=["job lifecycle"])

FOLLOW_UP_AFTER = dt.timedelta(days=14)
CustomerUser = Annotated[Customer, Depends(require_role("customer"))]
ProviderUser = Annotated[Provider, Depends(require_role("provider"))]
DbSession = Annotated[Session, Depends(get_session)]


class Finish(BaseModel):
    completed: bool = True  # False: the provider didn't turn up


class StillWorking(BaseModel):
    still_working: bool


def today() -> dt.date:
    return dt.datetime.now(dt.UTC).date()


def record_event(session: Session, job: Job, kind: str, actor_id: str) -> None:
    session.add(
        JobEvent(
            id=f"event_{uuid.uuid4().hex[:10]}",
            job_id=job.id,
            kind=kind,
            actor_id=actor_id,
            at=dt.datetime.now(dt.UTC),
        )
    )


def customer_job(session: Session, job_id: str, customer: Customer) -> Job:
    job = session.get(Job, job_id)
    if job is None or not is_job_customer(job, customer):
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def provider_job(session: Session, job_id: str, provider: Provider) -> Job:
    job = session.get(Job, job_id)
    if job is None or not is_job_provider(job, provider):
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/check-in")
def check_in(job_id: str, provider: ProviderUser, session: DbSession):
    """The provider has arrived: a confirmed job becomes in progress."""
    job = provider_job(session, job_id, provider)
    move_job(job, states.IN_PROGRESS)
    record_event(session, job, "check_in", provider.id)
    session.add(job)
    session.commit()
    start_check_in_timer(session, job, provider)  # "Are you OK?" if the work runs long
    customer = session.get(Customer, job.customer_id)
    notify(session, customer, "checked_in", job.id, name=provider.display_name)
    return job_view(session, job, provider)


@router.post("/jobs/{job_id}/check-out")
def check_out(job_id: str, provider: ProviderUser, session: DbSession):
    """The provider says the work is finished. It is noted for the customer to confirm; only the
    customer marking the job done makes it count."""
    job = provider_job(session, job_id, provider)
    if job.state != states.IN_PROGRESS:
        raise HTTPException(status_code=409, detail="Check in first")
    record_event(session, job, "check_out", provider.id)
    session.commit()
    stop_timer(session, job, provider)
    customer = session.get(Customer, job.customer_id)
    notify(session, customer, "checked_out", job.id, name=provider.display_name)
    return job_view(session, job, provider)


@router.post("/jobs/{job_id}/done")
def mark_done(job_id: str, body: Finish, customer: CustomerUser, session: DbSession):
    """The customer says the job is done, or that the provider didn't turn up.

    Done makes it count as a completed job. A no-show ends the job and counts against the
    provider (the ranking reads it), which is why only the customer can say it.
    """
    job = customer_job(session, job_id, customer)
    if job.state not in (states.CONFIRMED, states.IN_PROGRESS):
        raise HTTPException(status_code=409, detail=f"A job that is {job.state} can't be finished")
    if body.completed:
        if job.state == states.CONFIRMED:  # the provider forgot to check in
            move_job(job, states.IN_PROGRESS)
        move_job(job, states.DONE)
        record_event(session, job, "marked_done", customer.id)
    else:
        move_job(job, states.CANCELLED)
        record_event(session, job, "no_show", customer.id)
    job.completed = body.completed
    job.finished_on = today()
    session.add(job)
    session.commit()
    if not body.completed:
        settle_cancelled_job(session, job, states.CONFIRMED, is_no_show=True)  # all back
    if body.completed and job.provider_id:
        provider = session.get(Provider, job.provider_id)
        notify(session, provider, "job_done", job.id, name=customer.display_name)
    return job_view(session, job, customer)


def is_follow_up_due(job: Job) -> bool:
    return (
        job.state == states.DONE
        and job.still_working is None
        and job.finished_on is not None
        and today() - job.finished_on >= FOLLOW_UP_AFTER
    )


@router.get("/follow-ups")
def read_follow_ups(customer: CustomerUser, session: DbSession):
    """The customer's jobs that finished two weeks ago or more and still need the question "is
    the fix still working?"."""
    query = select(Job).where(Job.customer_id == customer.id, Job.state == states.DONE)
    due = [job for job in session.exec(query) if is_follow_up_due(job)]
    due.sort(key=lambda job: job.finished_on)
    return [job_view(session, job, customer) for job in due]


@router.post("/jobs/{job_id}/still-working")
def answer_still_working(
    job_id: str, body: StillWorking, customer: CustomerUser, session: DbSession
):
    """The customer's answer, two weeks or more after the job. It is one of the signals behind
    the provider's trust range."""
    job = customer_job(session, job_id, customer)
    if job.state == states.FOLLOWED_UP:
        raise HTTPException(status_code=409, detail="You already answered this")
    if job.state != states.DONE:
        raise HTTPException(status_code=409, detail="This job isn't finished yet")
    if not is_follow_up_due(job):
        raise HTTPException(status_code=409, detail="Ask again two weeks after the job")
    move_job(job, states.FOLLOWED_UP)
    job.still_working = body.still_working
    record_event(session, job, "still_working_answer", customer.id)
    session.add(job)
    session.commit()
    return job_view(session, job, customer)
