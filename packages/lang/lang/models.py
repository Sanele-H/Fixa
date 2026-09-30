"""Return types for the lang package. P2's API builds its JSON from these, so field names match
contracts/api.md (snake_case)."""

from typing import Literal

from pydantic import BaseModel

Lang = Literal["en", "zu", "xh"]
Trade = str  # One of the 11 trade ids in data/glossary.json, for example "plumbing"
Urgency = Literal["low", "normal", "urgent"]
JobSize = Literal["small", "medium", "large"]
FindingKind = Literal["phone", "email", "link", "address"]


class Translation(BaseModel):
    """A message in the reader's language, with the original kept for "See original"."""

    text: str
    original: str
    source_lang: Lang  # The sender's language: the contract's Message calls it original_lang
    flagged: bool  # True shows "This may not have translated well"
    flag_reason: str | None = None


class JobIntent(BaseModel):
    """What a customer's job description means. Matches contracts/fixtures/job_intent.json."""

    trade: Trade
    urgency: Urgency
    size: JobSize
    confidence: float  # 0 to 1
    # None when the text is fine, else the category of illegal electricity work it asks for
    prohibited: str | None = None


class Finding(BaseModel):
    """One piece of contact detail found in a message, by character position in the original."""

    kind: FindingKind
    start: int
    end: int


class SafetyResult(BaseModel):
    """A chat message that is safe to show, plus what was hidden and why."""

    safe_text: str
    findings: list[Finding]
    scam_warnings: list[str]
    # None when the text is fine, else illegal_connection, infrastructure_tampering,
    # meter_tampering or illegal_vouchers. A flagged text must not be published or delivered.
    prohibited: str | None = None


class Quote(BaseModel):
    """A price and time pulled out of a chat message."""

    amount_rands: int
    when: str | None  # The time as written, for example "Tuesday 10:00". P2 turns it into a date.


class Transcript(BaseModel):
    """A voice note turned into text. PROPOSAL: not in contracts/api.md yet."""

    text: str
    lang: Lang
    confidence: float  # 0 to 1. Low confidence flags the message like a doubtful translation.
