"""Database tables (P2). One table per file in data/seed/, with the same field names."""

import datetime as dt

from sqlalchemy import JSON, Column, DateTime, Dialect, LargeBinary, TypeDecorator
from sqlmodel import Field, SQLModel


class UtcDateTime(TypeDecorator):
    """A timezone-aware datetime, stored in UTC and read back in UTC on SQLite and Postgres.

    SQLite has no timezones: it would silently drop the seed's +02:00 and keep the local time.
    Converting to UTC on the way in, and labelling what comes back as UTC, makes both databases
    return the same instant. A datetime without a timezone is refused rather than guessed.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: dt.datetime | None, dialect: Dialect) -> dt.datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError(f"{value} has no timezone. Use an aware datetime, such as +02:00.")
        return value.astimezone(dt.UTC)

    def process_result_value(
        self, value: dt.datetime | None, dialect: Dialect
    ) -> dt.datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.UTC)
        return value.astimezone(dt.UTC)


class Provider(SQLModel, table=True):
    """A provider. lat and lng stay on the server; only a rounded distance_km is ever sent."""

    id: str = Field(primary_key=True)
    role: str
    display_name: str
    phone: str
    lang: str
    langs: list[str] = Field(sa_column=Column(JSON, nullable=False))
    suburb: str
    lat: float
    lng: float
    trades: list[str] = Field(sa_column=Column(JSON, nullable=False))
    licensed: bool
    id_badge: str
    bio: str
    joined_on: dt.date


class Customer(SQLModel, table=True):
    """A customer. Their address and phone only ever leave the server in JobUnlocked."""

    id: str = Field(primary_key=True)
    role: str
    display_name: str
    phone: str
    lang: str
    suburb: str
    address: str
    lat: float
    lng: float
    id_badge: str


class Job(SQLModel, table=True):
    """A job, open or finished. address, lat and lng are copied from the customer."""

    id: str = Field(primary_key=True)
    customer_id: str = Field(foreign_key="customer.id")
    provider_id: str | None = Field(default=None, foreign_key="provider.id")
    state: str
    trade: str
    trade_task: str
    size: str
    urgency: str
    needs_licence: bool
    suburb: str
    address: str
    lat: float
    lng: float
    problem: str
    problem_lang: str
    directions: str | None = None  # free-text hints for the provider; only sent in JobUnlocked
    # When the customer deleted it from their list. The row stays: a cancelled job can hold a
    # provider's no-show (the ranking reads it) and payment receipts.
    deleted_at: dt.datetime | None = Field(default=None, sa_type=UtcDateTime)
    photo_url: str | None = None
    created_at: dt.datetime = Field(sa_type=UtcDateTime)
    finished_on: dt.date | None = None
    completed: bool | None = None
    still_working: bool | None = None


# The ways a customer can pay, and the ones a quote offers when the provider doesn't say:
# in_app_after (pay in the app once it's done), in_app_split (a deposit once the job is
# confirmed, the rest once it's done) and cash (off the app; Fixa never touches it).
PAYMENT_METHODS = ("in_app_after", "in_app_split", "cash")
DEFAULT_QUOTE_PAYMENT_METHODS = ("in_app_after", "cash")


class Quote(SQLModel, table=True):
    """A provider's quote on a job: open, accepted or declined. payment_methods are the ways the
    provider accepts payment; deposit_rands is set only when in_app_split is one of them."""

    id: str = Field(primary_key=True)
    job_id: str = Field(foreign_key="job.id")
    provider_id: str = Field(foreign_key="provider.id")
    amount_rands: int
    when: dt.datetime = Field(sa_type=UtcDateTime)
    message: str | None = None
    state: str
    created_at: dt.datetime = Field(sa_type=UtcDateTime)
    payment_methods: list[str] = Field(
        default_factory=lambda: list(DEFAULT_QUOTE_PAYMENT_METHODS),
        sa_column=Column(JSON, nullable=False),
    )
    deposit_rands: int | None = None


class OffAppJob(SQLModel, table=True):
    """Past work a provider logged, confirmed or awaiting the customer's SMS reply."""

    __tablename__ = "off_app_job"

    id: str = Field(primary_key=True)
    provider_id: str = Field(foreign_key="provider.id")
    state: str
    trade: str
    trade_task: str
    date: dt.date
    suburb: str
    amount_rands: int | None = None
    customer_phone: str
    confirmed_via: str | None = None
    reference_agreed: bool | None = None


class Message(SQLModel, table=True):
    """A chat message on a job, between the customer and one provider.

    original_text is exactly what was typed and is kept for review only: it can hold a phone
    number the sender tried to slip in, so it is never sent to anyone. safe_text is what the
    other side may read (contact details hidden until the job is confirmed), and
    original_lang is the language the sender wrote it in.
    """

    id: str = Field(primary_key=True)
    job_id: str = Field(foreign_key="job.id", index=True)
    sender_id: str = Field(index=True)
    recipient_id: str = Field(index=True)
    original_text: str
    safe_text: str
    original_lang: str
    contacts_hidden: bool
    scam_warnings: list[str] = Field(sa_column=Column(JSON, nullable=False))
    sent_at: dt.datetime = Field(sa_type=UtcDateTime)


class IdentityCheck(SQLModel, table=True):
    """One ID check a provider ran (POPIA). It keeps only the result: never the ID number, the
    names, ID photos or the verifier's full response. consent_at is when they agreed."""

    __tablename__ = "identity_check"

    id: str = Field(primary_key=True)
    provider_id: str = Field(foreign_key="provider.id", index=True)
    tier: str
    verified: bool
    name_match: bool
    provider: str
    reference: str
    checked_at: dt.datetime = Field(sa_type=UtcDateTime)
    consent_at: dt.datetime = Field(sa_type=UtcDateTime)


class OffAppConfirmation(SQLModel, table=True):
    """The SMS check behind one off-app job: the code the customer must send back, and how many
    wrong codes came in. Kept apart from OffAppJob, which the seed data fills."""

    __tablename__ = "off_app_confirmation"

    off_app_job_id: str = Field(primary_key=True, foreign_key="off_app_job.id")
    code: str
    lang: str
    sent_at: dt.datetime = Field(sa_type=UtcDateTime)
    expires_at: dt.datetime = Field(sa_type=UtcDateTime)
    wrong_attempts: int = 0


class ExportedRecord(SQLModel, table=True):
    """A work record a provider exported, kept so /verify/{code} can check it later.

    evidence is exactly what was hashed (no customer names, numbers or addresses), and pdf is
    the file the provider downloads and shares.
    """

    __tablename__ = "exported_record"

    verify_code: str = Field(primary_key=True)
    provider_id: str = Field(foreign_key="provider.id", index=True)
    mode: str
    sha256: str
    evidence: dict = Field(sa_column=Column(JSON, nullable=False))
    issued_on: dt.date
    created_at: dt.datetime = Field(sa_type=UtcDateTime)
    pdf: bytes = Field(sa_column=Column(LargeBinary, nullable=False))


class Photo(SQLModel, table=True):
    """An uploaded photo. The image itself lives in the photo store (local disk, or Supabase
    Storage when live); this row says who uploaded it and when. It has been re-encoded, so it
    holds no EXIF data such as the phone's GPS location."""

    id: str = Field(primary_key=True)
    owner_id: str = Field(index=True)
    size_bytes: int
    created_at: dt.datetime = Field(sa_type=UtcDateTime)


class JobEvent(SQLModel, table=True):
    """Something that happened on a job: a check-in, a check-out, marking it done, a no-show or
    the two-week "still working?" answer. A log only, so the job's own row stays as it is."""

    __tablename__ = "job_event"

    id: str = Field(primary_key=True)
    job_id: str = Field(foreign_key="job.id", index=True)
    kind: str
    actor_id: str
    at: dt.datetime = Field(sa_type=UtcDateTime)


class BlockLog(SQLModel, table=True):
    """A request the illegal-request check refused, kept for the team to review. The text is
    what the person wrote (cut to 500 characters). It is never published or delivered."""

    __tablename__ = "block_log"

    id: str = Field(primary_key=True)
    user_id: str = Field(index=True)
    kind: str  # job_post, understand, quote, message or off_app_job
    category: str
    text: str
    at: dt.datetime = Field(sa_type=UtcDateTime)


class AccountRestriction(SQLModel, table=True):
    """An account that can no longer post, quote or message until the team reviews it. Delete
    the row to lift it."""

    __tablename__ = "account_restriction"

    user_id: str = Field(primary_key=True)
    since: dt.datetime = Field(sa_type=UtcDateTime)
    reason: str


class Report(SQLModel, table=True):
    """Something a person reported with the report button, for the team to review. The note is
    for the team only; it is never shown to anyone else."""

    id: str = Field(primary_key=True)
    reporter_id: str = Field(index=True)
    target_type: str  # job, provider or message
    target_id: str
    reason: str
    note: str | None = None
    status: str = "open"
    created_at: dt.datetime = Field(sa_type=UtcDateTime)


class CustomerVouch(SQLModel, table=True):
    """A customer's own words about a provider they hired: a few lines, with the suburb and date
    only. One per customer and provider. The text was scanned, so it holds no contact details."""

    __tablename__ = "customer_vouch"

    id: str = Field(primary_key=True)
    provider_id: str = Field(foreign_key="provider.id", index=True)
    customer_id: str = Field(index=True)
    text: str
    suburb: str
    created_at: dt.datetime = Field(sa_type=UtcDateTime)


# --- Safety and notifications. New tables only, so an existing fixa.db gets them on the next
# start (create_all) without a reseed.


class TrustedContact(SQLModel, table=True):
    """Someone a person trusts, told by SMS when they press the panic button or miss a safety
    timer. One per person."""

    __tablename__ = "trusted_contact"

    user_id: str = Field(primary_key=True)
    name: str
    phone: str
    updated_at: dt.datetime = Field(sa_type=UtcDateTime)


class SafetyAlert(SQLModel, table=True):
    """A panic button press, or a safety timer that ran out, during a job."""

    __tablename__ = "safety_alert"

    id: str = Field(primary_key=True)
    job_id: str = Field(foreign_key="job.id", index=True)
    user_id: str = Field(index=True)
    kind: str  # panic or timer_missed
    lat: float | None = None
    lng: float | None = None
    contact_notified: bool = False
    created_at: dt.datetime = Field(sa_type=UtcDateTime)


class SafetyTimer(SQLModel, table=True):
    """ "Check on me in an hour": at due_at the person is asked "Are you OK?"; if they haven't said
    they're safe by alert_at, their trusted contact gets an SMS."""

    __tablename__ = "safety_timer"

    id: str = Field(primary_key=True)
    job_id: str = Field(foreign_key="job.id", index=True)
    user_id: str = Field(index=True)
    state: str  # running, asking ("Are you OK?"), safe or missed
    reason: str = "manual"  # manual, or check_in when checking in started it
    started_at: dt.datetime = Field(sa_type=UtcDateTime)
    due_at: dt.datetime = Field(sa_type=UtcDateTime)
    alert_at: dt.datetime = Field(sa_type=UtcDateTime)
    ended_at: dt.datetime | None = Field(default=None, sa_type=UtcDateTime)


class LocationPing(SQLModel, table=True):
    """Where a person's phone was at a key moment of a job (check-in, finished, panic...). Exact
    coordinates stay on the server; the job page only shows the distance from the job."""

    __tablename__ = "location_ping"

    id: str = Field(primary_key=True)
    job_id: str = Field(foreign_key="job.id", index=True)
    user_id: str = Field(index=True)
    moment: str
    lat: float
    lng: float
    accuracy_m: float | None = None
    at: dt.datetime = Field(sa_type=UtcDateTime)


class Notification(SQLModel, table=True):
    """One item in a person's inbox (the bell): a new quote, a confirmed job, a message..."""

    id: str = Field(primary_key=True)
    user_id: str = Field(index=True)
    job_id: str | None = Field(default=None, index=True)
    kind: str
    params: dict = Field(sa_column=Column(JSON, nullable=False))
    created_at: dt.datetime = Field(sa_type=UtcDateTime)
    read_at: dt.datetime | None = Field(default=None, sa_type=UtcDateTime)


class PushSubscription(SQLModel, table=True):
    """A browser that agreed to push notifications for a person. The endpoint is unique per
    browser; the keys encrypt what we send."""

    __tablename__ = "push_subscription"

    endpoint: str = Field(primary_key=True)
    user_id: str = Field(index=True)
    p256dh: str
    auth: str
    created_at: dt.datetime = Field(sa_type=UtcDateTime)


# --- Payments. The plan and payment tables are new; Quote's payment columns are added to an
# existing database by migrations.py.


class PaymentPlan(SQLModel, table=True):
    """How the customer and provider agreed the job will be paid: set when the customer accepts
    a quote, changed only when both agree, before the work starts. deposit_rands is 0 unless the
    method is in_app_split, and never more than half of total_rands."""

    __tablename__ = "payment_plan"

    job_id: str = Field(primary_key=True, foreign_key="job.id")
    quote_id: str = Field(foreign_key="quote.id")
    method: str
    total_rands: int
    deposit_rands: int = 0
    agreed_at: dt.datetime = Field(sa_type=UtcDateTime)


class PaymentPlanChange(SQLModel, table=True):
    """One side asking to change the payment plan. It only takes effect when the other side
    agrees. state: pending, agreed, declined, or withdrawn (the asker took it back)."""

    __tablename__ = "payment_plan_change"

    id: str = Field(primary_key=True)
    job_id: str = Field(foreign_key="job.id", index=True)
    proposed_by: str
    method: str
    deposit_rands: int = 0
    state: str
    created_at: dt.datetime = Field(sa_type=UtcDateTime)
    decided_at: dt.datetime | None = Field(default=None, sa_type=UtcDateTime)


class Payment(SQLModel, table=True):
    """One in-app payment: a deposit, a balance, or the full amount. The card details never
    reach Fixa: the customer types them on the payment company's own page (gateway), which
    tells us the result. A paid payment is the customer's receipt.

    state: pending (sent to checkout), paid, failed (the amounts didn't match) or cancelled.

    refund_state, for a paid payment on a job that was cancelled (see payment_plans.py):
    refunded (given back), refund_owed (the team pays it back from the payment company's
    dashboard) or under_review (work had started, so the team decides). None: not refunded.
    """

    id: str = Field(primary_key=True)
    job_id: str = Field(foreign_key="job.id", index=True)
    kind: str  # deposit, balance or full
    amount_rands: int
    state: str
    gateway: str  # mock or payfast
    gateway_reference: str | None = None
    created_at: dt.datetime = Field(sa_type=UtcDateTime)
    paid_at: dt.datetime | None = Field(default=None, sa_type=UtcDateTime)
    refund_state: str | None = None
    refund_at: dt.datetime | None = Field(default=None, sa_type=UtcDateTime)
