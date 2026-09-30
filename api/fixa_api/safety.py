"""Safety during a job: the panic button, the safety timer, a trusted contact, and where each
person's phone was at the job's key moments.

- Panic: records an alert with the phone's location and texts the trusted contact straight away.
  The other person on the job is never told, since they may be the danger.
- Safety timer: "check on me in an hour". If the person hasn't said they're safe by then, the
  trusted contact gets an SMS. A loop started with the server checks every few seconds
  (sweep_missed_timers), and reads check too, so nothing depends on the loop alone.
- Location at key moments: the app sends the phone's location at check-in, finishing, marking it
  done, panic and starting a timer. Coordinates stay on the server; the job page only shows how
  far from the job address each moment happened, and a panic only to the person who pressed it.

SMS texts are in the person's own language (they know their contact). isiZulu by P3; isiXhosa
falls back to English until an isiXhosa speaker writes it.
"""

import datetime as dt
import uuid
from typing import Any

from sqlmodel import Session, select

from fixa_api.auth import find_user_by_id
from fixa_api.geo import distance_km
from fixa_api.job_views import is_job_customer, is_job_provider
from fixa_api.models import (
    Customer,
    Job,
    LocationPing,
    Provider,
    SafetyAlert,
    SafetyTimer,
    TrustedContact,
)
from fixa_api.notifications import notify
from fixa_api.sms import SmsSender, send_safely

EMERGENCY_NUMBERS = [
    {"label": "police", "number": "10111"},
    {"label": "emergency", "number": "112"},
]
MOMENTS = {"check_in", "check_out", "done", "panic", "timer_start"}
PRIVATE_MOMENTS = {"panic"}  # only the person who pressed it sees these
TIMER_MINUTES_ALLOWED = {1, 15, 30, 60, 120, 240}
FALLBACK_LANG = "en"

PANIC_SMS = {
    "en": (
        "Fixa safety alert: {name} pressed the panic button during a job in {suburb}. "
        "Last known location: {place}. Please call them now. Police: 10111."
    ),
    "zu": (
        "Isexwayiso sokuphepha sakwa-Fixa: U-{name} ucindezele inkinobho yosizo esemsebenzini "
        "e-{suburb}. Indawo agcine ekuyo: {place}. Ngicela umshayele manje. Amaphoyisa: 10111."
    ),
}
TIMER_SMS = {
    "en": (
        "Fixa safety check: {name} set a safety timer for a job in {suburb} and hasn't said "
        "they're safe. Please call them. Last known location: {place}."
    ),
    "zu": (
        "Ukuhlola ukuphepha kwa-Fixa: U-{name} ubeke isikhathi sokuphepha emsebenzini e-{suburb} "
        "kodwa akakasho ukuthi uphephile. Ngicela umshayele. Indawo agcine ekuyo: {place}."
    ),
}
NO_LOCATION = {"en": "not shared", "zu": "ayabelwanga"}


class SafetyError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


def now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def is_job_party(job: Job, user: Customer | Provider) -> bool:
    return is_job_customer(job, user) or is_job_provider(job, user)


def find_party_job(session: Session, job_id: str, user: Customer | Provider) -> Job:
    job = session.get(Job, job_id)
    if job is None or not is_job_party(job, user):
        raise SafetyError(404, "Job not found")
    return job


# --- trusted contact ---------------------------------------------------------------------------


def contact_view(contact: TrustedContact | None) -> dict[str, str] | None:
    return None if contact is None else {"name": contact.name, "phone": contact.phone}


def save_trusted_contact(
    session: Session, user: Customer | Provider, name: str, phone: str
) -> TrustedContact:
    contact = session.get(TrustedContact, user.id) or TrustedContact(
        user_id=user.id, name=name, phone=phone, updated_at=now()
    )
    contact.name, contact.phone, contact.updated_at = name.strip(), phone.strip(), now()
    session.add(contact)
    session.commit()
    return contact


# --- location at key moments -------------------------------------------------------------------


def record_location(
    session: Session,
    job: Job,
    user: Customer | Provider,
    moment: str,
    lat: float,
    lng: float,
    accuracy_m: float | None = None,
) -> LocationPing:
    if moment not in MOMENTS:
        raise SafetyError(422, f"Unknown moment: {moment}")
    ping = LocationPing(
        id=new_id("ping"),
        job_id=job.id,
        user_id=user.id,
        moment=moment,
        lat=lat,
        lng=lng,
        accuracy_m=accuracy_m,
        at=now(),
    )
    session.add(ping)
    session.commit()
    return ping


def read_locations(session: Session, job: Job, viewer: Customer | Provider) -> list[dict[str, Any]]:
    """Each key moment on the job: who, what, when and how far from the job address. Never the
    coordinates, and a panic only for the person who pressed it."""
    pings = session.exec(
        select(LocationPing).where(LocationPing.job_id == job.id).order_by(LocationPing.at)
    ).all()
    views = []
    for ping in pings:
        is_mine = ping.user_id == viewer.id
        if ping.moment in PRIVATE_MOMENTS and not is_mine:
            continue
        person = find_user_by_id(session, ping.user_id)
        views.append(
            {
                "moment": ping.moment,
                "role": person.role if person else "unknown",
                "name": person.display_name if person else "",
                "is_me": is_mine,
                "at": ping.at.isoformat(),
                "distance_km": distance_km(ping.lat, ping.lng, job.lat, job.lng),
            }
        )
    return views


def last_place(session: Session, job: Job, user: Customer | Provider, lang: str) -> str:
    """A map link to the person's last known location on this job, for their trusted contact."""
    ping = session.exec(
        select(LocationPing)
        .where(LocationPing.job_id == job.id, LocationPing.user_id == user.id)
        .order_by(LocationPing.at.desc())
    ).first()
    if ping is None:
        return NO_LOCATION.get(lang, NO_LOCATION[FALLBACK_LANG])
    return f"https://maps.google.com/?q={ping.lat:.5f},{ping.lng:.5f}"


def text_contact(
    session: Session,
    sender: SmsSender,
    job: Job,
    user: Customer | Provider,
    texts: dict[str, str],
    purpose: str,
) -> TrustedContact | None:
    """Text the person's trusted contact, if they have one. Returns the contact that was told."""
    contact = session.get(TrustedContact, user.id)
    if contact is None:
        return None
    lang = user.lang if user.lang in texts else FALLBACK_LANG
    message = texts[lang].format(
        name=user.display_name, suburb=job.suburb, place=last_place(session, job, user, lang)
    )
    send_safely(sender, contact.phone, message, purpose)
    return contact


# --- panic -------------------------------------------------------------------------------------


def press_panic(
    session: Session,
    sender: SmsSender,
    job: Job,
    user: Customer | Provider,
    lat: float | None,
    lng: float | None,
) -> dict[str, Any]:
    if lat is not None and lng is not None:
        record_location(session, job, user, "panic", lat, lng)
    contact = text_contact(session, sender, job, user, PANIC_SMS, "panic alert")
    alert = SafetyAlert(
        id=new_id("alert"),
        job_id=job.id,
        user_id=user.id,
        kind="panic",
        lat=lat,
        lng=lng,
        contact_notified=contact is not None,
        created_at=now(),
    )
    session.add(alert)
    session.commit()
    if contact is not None:
        notify(session, user, "panic_sent", job.id, contact=contact.name)
    else:
        notify(session, user, "panic_no_contact", job.id)
    return {
        "alert_id": alert.id,
        "contact": contact_view(contact),
        "location_shared": lat is not None,
        "emergency_numbers": EMERGENCY_NUMBERS,
    }


# --- safety timer ------------------------------------------------------------------------------


def running_timer(session: Session, job: Job, user: Customer | Provider) -> SafetyTimer | None:
    return session.exec(
        select(SafetyTimer).where(
            SafetyTimer.job_id == job.id,
            SafetyTimer.user_id == user.id,
            SafetyTimer.state == "running",
        )
    ).first()


def latest_timer(session: Session, job: Job, user: Customer | Provider) -> SafetyTimer | None:
    return session.exec(
        select(SafetyTimer)
        .where(SafetyTimer.job_id == job.id, SafetyTimer.user_id == user.id)
        .order_by(SafetyTimer.started_at.desc())
    ).first()


def timer_view(timer: SafetyTimer | None) -> dict[str, Any] | None:
    if timer is None:
        return None
    return {
        "id": timer.id,
        "state": timer.state,
        "started_at": timer.started_at.isoformat(),
        "due_at": timer.due_at.isoformat(),
    }


def start_timer(
    session: Session, job: Job, user: Customer | Provider, minutes: int
) -> SafetyTimer:
    if minutes not in TIMER_MINUTES_ALLOWED:
        raise SafetyError(422, f"Pick one of {sorted(TIMER_MINUTES_ALLOWED)} minutes")
    previous = running_timer(session, job, user)
    if previous is not None:
        previous.state, previous.ended_at = "safe", now()
        session.add(previous)
    started = now()
    timer = SafetyTimer(
        id=new_id("timer"),
        job_id=job.id,
        user_id=user.id,
        state="running",
        started_at=started,
        due_at=started + dt.timedelta(minutes=minutes),
    )
    session.add(timer)
    session.commit()
    return timer


def say_safe(session: Session, job: Job, user: Customer | Provider) -> SafetyTimer:
    timer = running_timer(session, job, user)
    if timer is None:
        raise SafetyError(409, "No safety timer is running")
    timer.state, timer.ended_at = "safe", now()
    session.add(timer)
    session.commit()
    return timer


def sweep_missed_timers(session: Session, sender: SmsSender) -> int:
    """Turn every running timer that's past due into a missed one: text the trusted contact,
    record an alert and tell the person. Returns how many were missed."""
    due = session.exec(
        select(SafetyTimer).where(SafetyTimer.state == "running", SafetyTimer.due_at <= now())
    ).all()
    for timer in due:
        timer.state, timer.ended_at = "missed", now()
        session.add(timer)
        session.commit()
        job = session.get(Job, timer.job_id)
        user = find_user_by_id(session, timer.user_id)
        if job is None or user is None:
            continue
        contact = text_contact(session, sender, job, user, TIMER_SMS, "safety timer")
        session.add(
            SafetyAlert(
                id=new_id("alert"),
                job_id=job.id,
                user_id=user.id,
                kind="timer_missed",
                contact_notified=contact is not None,
                created_at=now(),
            )
        )
        session.commit()
        if contact is not None:
            notify(session, user, "timer_missed", job.id, contact=contact.name)
        else:
            notify(session, user, "timer_missed_no_contact", job.id)
    return len(due)
