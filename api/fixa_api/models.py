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
    photo_url: str | None = None
    created_at: dt.datetime = Field(sa_type=UtcDateTime)
    finished_on: dt.date | None = None
    completed: bool | None = None
    still_working: bool | None = None


class Quote(SQLModel, table=True):
    """A provider's quote on a job: open, accepted or declined."""

    id: str = Field(primary_key=True)
    job_id: str = Field(foreign_key="job.id")
    provider_id: str = Field(foreign_key="provider.id")
    amount_rands: int
    when: dt.datetime = Field(sa_type=UtcDateTime)
    message: str | None = None
    state: str
    created_at: dt.datetime = Field(sa_type=UtcDateTime)


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
