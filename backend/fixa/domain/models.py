"""Data models shared by the store, the services and the API.

Python code uses snake_case; the JSON the frontend sees is camelCase (see ApiModel).
These are a starting point for Role 3's Day 2 data model, not a final design.

Safety rule baked into the shape: phone numbers and addresses are NOT on User.
They live in ContactDetails, which only the unlock flow may read.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from fixa.domain.job_states import JobState


class ApiModel(BaseModel):
    """Base for every model the API sends or receives: snake_case in Python, camelCase in JSON."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class UserRole(StrEnum):
    """Whether a user hires (customer) or does the work (provider)."""

    CUSTOMER = "customer"
    PROVIDER = "provider"


class JobSize(StrEnum):
    """Rough job size. Newcomers are offered small jobs first."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class User(ApiModel):
    """A customer or provider, without contact details. Safe to send to anyone.

    Provider-only fields keep their defaults for customers.
    """

    id: str
    display_name: str
    role: UserRole
    preferred_language: str
    area: str
    trades: list[str] = []
    service_areas: list[str] = []
    badges: list[str] = []
    completed_job_count: int = 0
    rating_sum: float = 0.0
    rating_count: int = 0


class ContactDetails(ApiModel):
    """Private details. Only returned once a job is unlocked (see job_states)."""

    user_id: str
    phone_number: str
    street_address: str | None = None


class NewJob(ApiModel):
    """What a customer sends to post a job (the request body for POST /api/jobs)."""

    trade: str
    size: JobSize
    description: str
    description_language: str
    area: str
    photo_id: str | None = None


class NewQuote(ApiModel):
    """What a provider sends to quote (the request body for POST /api/jobs/{id}/quotes)."""

    amount_in_rand: int
    proposed_start_at: datetime


class Job(ApiModel):
    """A job a customer posted.

    TODO (Role 3, Day 2): confirm these fields with Role 2's screens.
    """

    id: str
    customer_id: str
    trade: str
    size: JobSize
    description: str
    description_language: str
    area: str
    photo_id: str | None = None
    state: JobState = JobState.POSTED
    offered_provider_ids: list[str] = []
    accepted_quote_id: str | None = None
    assigned_provider_id: str | None = None
    created_at: datetime


class Quote(ApiModel):
    """A provider's price and time for a job.

    Price and time are structured fields, never free text, so translation can't change them.
    """

    id: str
    job_id: str
    provider_id: str
    amount_in_rand: int
    proposed_start_at: datetime
    created_at: datetime


class Message(ApiModel):
    """One chat message, stored after masking and translation.

    `original_text` is already masked, so "See original" can never leak a phone number.
    """

    id: str
    job_id: str
    sender_id: str
    recipient_id: str
    original_text: str
    original_language: str
    translated_text: str
    translated_language: str
    translation_flags: list[str] = []
    scam_warnings: list[str] = []
    contains_masked_contact: bool = False
    created_at: datetime
