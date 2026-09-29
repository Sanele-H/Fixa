"""Off-app jobs: past work a provider logs, which the customer confirms by replying to an SMS.

Only a confirmed job counts as evidence. The rules against fakes:
- the number that confirms can't be the provider's own;
- one job per provider, customer number and date (a repeat customer needs a different date);
- a provider can log at most MAX_LOGS_PER_MONTH jobs in 30 days;
- one phone gets at most MAX_REQUESTS_PER_PHONE_PER_DAY confirmation texts a day, from anyone;
- a number that confirms for FLAG_AFTER_DISTINCT_PROVIDERS different providers, or two providers
  who confirm each other's jobs, are flagged: the job doesn't count until the team reviews it.
"""

import datetime as dt
import re
import secrets
import uuid
from dataclasses import dataclass

from sqlmodel import Session, select

from fixa_api.auth import find_user_by_phone, normalise_phone
from fixa_api.messages import safe_text_for
from fixa_api.models import OffAppConfirmation, OffAppJob, Provider
from fixa_api.sms import SmsSender, send_safely
from fixa_api.sms_texts import off_app_confirmation_message
from lang import understand_job

AWAITING = "awaiting_sms_reply"
CONFIRMED = "confirmed"
DECLINED = "declined"
EXPIRED = "expired"
FLAGGED = "flagged"
NOT_COUNTED_STATES = {DECLINED, EXPIRED}  # don't block the same job being logged again

CODE_DIGITS = 6
CODE_LIFETIME = dt.timedelta(days=7)
MAX_WRONG_CODES = 5
MAX_LOGS_PER_MONTH = 10
MAX_REQUESTS_PER_PHONE_PER_DAY = 3
FLAG_AFTER_DISTINCT_PROVIDERS = 5
MAX_JOB_AGE_YEARS = 10
MOBILE_NUMBER_PATTERN = re.compile(r"^0[6-8]\d{8}$")
YES_WORDS = {"YES", "YEBO", "EWE"}
NO_WORDS = {"NO", "CHA", "HAYI"}
REFERENCE_WORD = "REF"


class OffAppError(Exception):
    """A request that can't be done. `error` is a short code the app can show a message for."""

    def __init__(self, status_code: int, error: str, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.error = error
        self.detail = detail


def format_phone(phone: str) -> str:
    """ "0830000001" -> "083 000 0001", the way the seed data writes numbers."""
    digits = normalise_phone(phone)
    return f"{digits[:3]} {digits[3:6]} {digits[6:]}"


def is_mobile_number(phone: str) -> bool:
    return bool(MOBILE_NUMBER_PATTERN.match(normalise_phone(phone)))


def new_code() -> str:
    return f"{secrets.randbelow(10**CODE_DIGITS):0{CODE_DIGITS}d}"


def pick_trade(provider: Provider, trade_task: str) -> str:
    """The trade a past job belongs to: the provider's only trade, or the one the words point
    to if the provider offers it."""
    if len(provider.trades) > 1:
        guess = understand_job(trade_task, provider.lang).trade
        if guess in provider.trades:
            return guess
    return provider.trades[0]


def jobs_of(session: Session, provider_id: str | None = None) -> list[OffAppJob]:
    query = select(OffAppJob)
    if provider_id:
        query = query.where(OffAppJob.provider_id == provider_id)
    return list(session.exec(query))


def check_can_log(
    session: Session, provider: Provider, customer_phone: str, date: dt.date, now: dt.datetime
) -> None:
    """Raise OffAppError for a job that breaks the rules against fakes."""
    wanted = normalise_phone(customer_phone)
    if wanted == normalise_phone(provider.phone):
        raise OffAppError(422, "self_confirmation", "You can't confirm your own job")
    if not is_mobile_number(customer_phone):
        raise OffAppError(422, "invalid_phone", "Enter the customer's cellphone number")
    today = now.date()
    if date > today or date < today.replace(year=today.year - MAX_JOB_AGE_YEARS):
        raise OffAppError(422, "invalid_date", "The date must be in the past, within 10 years")
    same_job = [
        job
        for job in jobs_of(session, provider.id)
        if normalise_phone(job.customer_phone) == wanted
        and job.date == date
        and job.state not in NOT_COUNTED_STATES
    ]
    if same_job:
        raise OffAppError(409, "duplicate", "You already logged a job for this customer and date")
    month_ago, day_ago = now - dt.timedelta(days=30), now - dt.timedelta(days=1)
    sent = list(session.exec(select(OffAppConfirmation, OffAppJob).join(OffAppJob)))
    recent_by_provider = [
        c for c, job in sent if job.provider_id == provider.id and c.sent_at >= month_ago
    ]
    if len(recent_by_provider) >= MAX_LOGS_PER_MONTH:
        raise OffAppError(429, "monthly_cap", "You logged the most jobs allowed this month")
    recent_to_phone = [
        c
        for c, job in sent
        if normalise_phone(job.customer_phone) == wanted and c.sent_at >= day_ago
    ]
    if len(recent_to_phone) >= MAX_REQUESTS_PER_PHONE_PER_DAY:
        raise OffAppError(429, "customer_busy", "This customer got too many requests today")


def log_off_app_job(
    session: Session,
    provider: Provider,
    sender: SmsSender,
    customer_phone: str,
    trade_task: str,
    date: dt.date,
    suburb: str,
    amount_rands: int | None,
) -> OffAppJob:
    """Save a past job and text the customer to confirm it. If the text can't be sent nothing
    is saved, so the provider can simply try again."""
    now = dt.datetime.now(dt.UTC)
    check_can_log(session, provider, customer_phone, date, now)
    task = safe_text_for(trade_task, provider.lang)
    suburb = safe_text_for(suburb, provider.lang)
    job = OffAppJob(
        id=f"offapp_{uuid.uuid4().hex[:8]}",
        provider_id=provider.id,
        state=AWAITING,
        trade=pick_trade(provider, trade_task),
        trade_task=task,
        date=date,
        suburb=suburb,
        amount_rands=amount_rands,
        customer_phone=format_phone(customer_phone),
    )
    code = new_code()
    known_customer = find_user_by_phone(session, customer_phone)
    lang = known_customer.lang if known_customer else provider.lang
    confirmation = OffAppConfirmation(
        off_app_job_id=job.id,
        code=code,
        lang=lang,
        sent_at=now,
        expires_at=now + CODE_LIFETIME,
    )
    session.add(job)
    session.flush()  # the job row must exist before the confirmation that points to it
    session.add(confirmation)
    session.flush()
    text = off_app_confirmation_message(
        lang, provider.display_name, task, suburb, date.isoformat(), code
    )
    if not send_safely(sender, customer_phone, text, "off-app confirmation").ok:
        session.rollback()
        raise OffAppError(502, "sms_failed", "We couldn't text the customer. Try again shortly.")
    session.commit()
    return job


# --- the customer's reply -------------------------------------------------------------------


@dataclass
class Reply:
    said_yes: bool
    code: str
    agrees_to_be_reference: bool


def parse_reply(text: str) -> Reply | None:
    """Read "YES 123456", "no 123456", "YEBO 123456 REF" and the like. None if it isn't clearly a
    yes or a no with the six-digit code."""
    words = re.findall(r"[A-Za-z]+|\d+", text.upper())
    said_yes = any(word in YES_WORDS for word in words)
    said_no = any(word in NO_WORDS for word in words)
    codes = [word for word in words if word.isdigit() and len(word) == CODE_DIGITS]
    if said_yes == said_no or len(codes) != 1:
        return None
    return Reply(said_yes, codes[0], REFERENCE_WORD in words)


def expire_old(session: Session, now: dt.datetime) -> None:
    for job, confirmation in session.exec(
        select(OffAppJob, OffAppConfirmation).join(OffAppConfirmation)
    ):
        if job.state == AWAITING and confirmation.expires_at <= now:
            job.state = EXPIRED
            session.add(job)


def looks_like_a_ring(session: Session, job: OffAppJob) -> bool:
    """A number that confirms for many providers, or two providers confirming each other."""
    phone = normalise_phone(job.customer_phone)
    others = jobs_of(session)
    providers_confirmed_for = {
        other.provider_id
        for other in others
        if normalise_phone(other.customer_phone) == phone and other.state == CONFIRMED
    } | {job.provider_id}
    if len(providers_confirmed_for) >= FLAG_AFTER_DISTINCT_PROVIDERS:
        return True
    provider = session.get(Provider, job.provider_id)
    customer_is = find_user_by_phone(session, job.customer_phone)
    if customer_is is None or customer_is.role != "provider":
        return False
    return any(
        other.provider_id == customer_is.id
        and normalise_phone(other.customer_phone) == normalise_phone(provider.phone)
        and other.state not in NOT_COUNTED_STATES
        for other in others
    )


def handle_reply(session: Session, from_phone: str, text: str) -> str:
    """Apply a customer's SMS reply. Returns what happened, for logs and tests only: the
    webhook always answers the same way, so nobody can probe it."""
    now = dt.datetime.now(dt.UTC)
    expire_old(session, now)
    phone = normalise_phone(from_phone)
    pending = [
        (job, confirmation)
        for job, confirmation in session.exec(
            select(OffAppJob, OffAppConfirmation).join(OffAppConfirmation)
        )
        if job.state == AWAITING and normalise_phone(job.customer_phone) == phone
    ]
    if not pending:
        session.commit()
        return "ignored"
    reply = parse_reply(text)
    if reply is None:
        session.commit()
        return "not_understood"
    match = next(
        (
            (job, confirmation)
            for job, confirmation in pending
            if secrets.compare_digest(confirmation.code, reply.code)
        ),
        None,
    )
    if match is None:
        for job, confirmation in pending:
            confirmation.wrong_attempts += 1
            if confirmation.wrong_attempts >= MAX_WRONG_CODES:
                job.state = EXPIRED
            session.add_all([job, confirmation])
        session.commit()
        return "wrong_code"
    job, _ = match
    job.confirmed_via = "sms"
    if not reply.said_yes:
        job.state = DECLINED
        outcome = "declined"
    else:
        job.reference_agreed = reply.agrees_to_be_reference
        job.state = FLAGGED if looks_like_a_ring(session, job) else CONFIRMED
        outcome = "flagged" if job.state == FLAGGED else "confirmed"
    session.add(job)
    session.commit()
    return outcome
