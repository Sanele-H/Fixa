"""Safety routes: trusted contact, panic button, safety timer and location at key moments.
See fixa_api/safety.py for how each works. Not in contracts/api.md's first version; listed in its
"Safety and notifications" section."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from fixa_api import safety
from fixa_api.auth import current_user
from fixa_api.db import get_session
from fixa_api.models import Customer, Provider, TrustedContact
from fixa_api.sms import SmsSender, get_sms_sender

router = APIRouter(prefix="/api", tags=["safety"])

User = Annotated[Customer | Provider, Depends(current_user)]
DbSession = Annotated[Session, Depends(get_session)]
Sender = Annotated[SmsSender, Depends(get_sms_sender)]


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    phone: str = Field(min_length=9, max_length=20)


class Place(BaseModel):
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)


class LocationIn(BaseModel):
    moment: str
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0)


class TimerIn(BaseModel):
    minutes: int


def party_job(session: Session, job_id: str, user: Customer | Provider):
    try:
        return safety.find_party_job(session, job_id, user)
    except safety.SafetyError as problem:
        raise HTTPException(status_code=problem.status_code, detail=problem.detail) from None


@router.get("/me/trusted-contact")
def read_trusted_contact(user: User, session: DbSession):
    """{name, phone}, or null when the person hasn't added one."""
    return safety.contact_view(session.get(TrustedContact, user.id))


@router.put("/me/trusted-contact")
def save_trusted_contact(body: ContactIn, user: User, session: DbSession):
    return safety.contact_view(safety.save_trusted_contact(session, user, body.name, body.phone))


@router.post("/jobs/{job_id}/location", status_code=201)
def record_location(job_id: str, body: LocationIn, user: User, session: DbSession):
    """Where the phone was at a key moment: check_in, check_out, done, panic or timer_start."""
    job = party_job(session, job_id, user)
    try:
        safety.record_location(
            session, job, user, body.moment, body.lat, body.lng, body.accuracy_m
        )
    except safety.SafetyError as problem:
        raise HTTPException(status_code=problem.status_code, detail=problem.detail) from None
    return {"recorded": True}


@router.get("/jobs/{job_id}/locations")
def read_locations(job_id: str, user: User, session: DbSession):
    """Each key moment and how far from the job address it happened. No coordinates."""
    job = party_job(session, job_id, user)
    return safety.read_locations(session, job, user)


@router.post("/jobs/{job_id}/panic", status_code=201)
def press_panic(job_id: str, body: Place, user: User, session: DbSession, sender: Sender):
    """Texts the trusted contact with the phone's location and records the alert. The other
    person on the job is not told."""
    job = party_job(session, job_id, user)
    return safety.press_panic(session, sender, job, user, body.lat, body.lng)


@router.get("/jobs/{job_id}/safety-timer")
def read_safety_timer(job_id: str, user: User, session: DbSession, sender: Sender):
    """The person's latest safety timer on this job (running, safe or missed), or null."""
    job = party_job(session, job_id, user)
    safety.sweep_missed_timers(session, sender)
    return safety.timer_view(safety.latest_timer(session, job, user))


@router.post("/jobs/{job_id}/safety-timer", status_code=201)
def start_safety_timer(job_id: str, body: TimerIn, user: User, session: DbSession):
    job = party_job(session, job_id, user)
    try:
        timer = safety.start_timer(session, job, user, body.minutes)
    except safety.SafetyError as problem:
        raise HTTPException(status_code=problem.status_code, detail=problem.detail) from None
    return safety.timer_view(timer)


@router.post("/jobs/{job_id}/safety-timer/safe")
def say_safe(job_id: str, user: User, session: DbSession):
    job = party_job(session, job_id, user)
    try:
        timer = safety.say_safe(session, job, user)
    except safety.SafetyError as problem:
        raise HTTPException(status_code=problem.status_code, detail=problem.detail) from None
    return safety.timer_view(timer)
