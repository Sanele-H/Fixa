"""Database tables (P2). One table per file in data/seed/, with the same field names."""

import datetime as dt

from sqlalchemy import JSON, Column, DateTime, Dialect, TypeDecorator
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
