"""Data shapes for the work record and its exports.

No model here has a field for a customer's name, phone number or address, and the input
models use extra="forbid", so passing one in is an error rather than a leak. Fields added
after step 0 all have defaults, so older calls keep working.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RecordMode = Literal["arpl", "statement"]
ConfirmationMethod = Literal["app", "sms", "ussd"]
PhotoKind = Literal["before", "after"]
VerifyStatus = Literal["genuine", "changed", "unknown"]


class RecordPhoto(BaseModel):
    """A before or after photo of a job, by P2's photo id. The image bytes come separately."""

    model_config = ConfigDict(extra="forbid")

    photo_id: str  # for example "photo_001", as in contracts/fixtures/photo.json
    kind: PhotoKind


class RecordJob(BaseModel):
    """One confirmed job on the record: when, where (suburb only), what, and how confirmed."""

    model_config = ConfigDict(extra="forbid")

    done_on: date
    suburb: str
    trade: str
    trade_task: str  # for example "Replace geyser valve"
    confirmed_via: ConfirmationMethod  # "app" for in-app jobs; "sms" or "ussd" for off-app jobs
    amount_rands: int | None = None  # the agreed amount, shown in statement mode
    photos: list[RecordPhoto] = Field(default_factory=list)
    reference_agreed: bool = False  # the customer said yes to being listed as a reference


class Vouch(BaseModel):
    """A customer's own words about the work, shown with suburb and date only.

    P2 runs the text through lang.scan_message first. The export also hides anything that
    looks like a phone number, in case one slips through.
    """

    model_config = ConfigDict(extra="forbid")

    text: str
    suburb: str
    given_on: date


class RecordEvidence(BaseModel):
    """Everything an export is built from. P2 assembles it from confirmed jobs only."""

    model_config = ConfigDict(extra="forbid")

    provider_id: str
    display_name: str
    trades: list[str]
    jobs: list[RecordJob] = Field(default_factory=list)
    vouches: list[Vouch] = Field(default_factory=list)
    # The trade an ARPL record is for. None picks the provider's ARPL trade with most jobs.
    arpl_trade: str | None = None


class RecordDoc(BaseModel):
    """A finished export: the PDF, its verify code and the SHA-256 of its contents."""

    pdf_bytes: bytes
    verify_code: str
    sha256: str


class StoredRecord(BaseModel):
    """What P2 saves when a record is exported, so /verify/{code} can check it later."""

    verify_code: str
    sha256: str
    mode: RecordMode
    evidence: RecordEvidence
    issued_on: date


class VerifyResult(BaseModel):
    """What the verify page shows. The detail fields are None when the code is unknown.

    status is "genuine" when the stored record still matches its hash, "changed" when it
    doesn't, and "unknown" when there is no record with that code.
    """

    status: VerifyStatus
    display_name: str | None = None
    mode: RecordMode | None = None
    n_jobs: int | None = None
    issued_on: date | None = None
    sha256: str | None = None
    first_job_on: date | None = None
    last_job_on: date | None = None
