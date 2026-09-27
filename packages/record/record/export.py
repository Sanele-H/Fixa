"""build_record and verify_record: the work record PDF, and the check behind /verify/{code}.

Two kinds of record:
- "arpl": evidence for an ARPL trade test application, following the merSETA form's
  sections (see arpl_record.py). Only for trades with an ARPL toolkit.
- "statement": confirmed jobs and agreed amounts for credit or renting, in any trade,
  labelled "Customer-confirmed, not a bank statement" (see statement_record.py).

The SHA-256 is taken over the record's contents (canonical JSON of the evidence and mode),
not over the PDF bytes: a PDF can't print its own hash, and this way the hash printed on
the paper is the one the verify page checks.
"""

import hashlib
import json
import secrets
from collections.abc import Mapping
from datetime import date
from typing import get_args

from record.arpl_record import write_arpl_record
from record.experience import choose_arpl_trade
from record.models import RecordDoc, RecordEvidence, RecordMode, StoredRecord, VerifyResult
from record.pdf_layout import RecordPdf
from record.sections import RecordCover
from record.statement_record import STATEMENT_LABEL, write_statement_record

RECORD_MODES = get_args(RecordMode)
VERIFY_CODE_LENGTH = 6
# No 0/O or 1/I, so a code copied off paper can't be mistyped.
VERIFY_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
VERIFY_PATH = "/verify/"
TITLES = {"arpl": "Fixa work record", "statement": "Fixa work statement"}


def build_record(
    evidence: RecordEvidence,
    mode: RecordMode,
    *,
    verify_base_url: str | None = None,
    photos: Mapping[str, bytes] | None = None,
) -> RecordDoc:
    """Builds a work record PDF with a verify code and the SHA-256 of its contents.

    Args:
        evidence: the provider's confirmed jobs. It has no customer names, numbers or
            addresses, by design.
        mode: "arpl" to support an ARPL application (toolkit trades only), or "statement"
            for credit or renting (every trade, including cleaning and gardening).
        verify_base_url: the site's address, such as "https://fixa.example". With it, the
            PDF gets a QR code for {verify_base_url}/verify/{code}; without it, just the path.
        photos: image bytes by photo id, for the jobs' before/after photos. Photos not
            passed in are left out of the PDF (they don't change the hash).

    Returns:
        RecordDoc(pdf_bytes, verify_code, sha256). P2 saves a StoredRecord with the same
        code and hash so the verify page can check the record later.

    Raises:
        ValueError: mode is not "arpl" or "statement".
        ArplTradeError: mode is "arpl" and the provider has no trade with an ARPL toolkit.
    """
    check_mode_allowed(evidence, mode)
    verify_code = create_verify_code()
    cover = RecordCover(
        verify_code=verify_code,
        sha256=hash_record(evidence, mode),
        issued_on=date.today(),
        verify_url=build_verify_url(verify_base_url, verify_code),
    )
    pdf = render_record(evidence, mode, cover, photos or {})
    return RecordDoc(pdf_bytes=bytes(pdf.output()), verify_code=verify_code, sha256=cover.sha256)


def render_record(
    evidence: RecordEvidence, mode: str, cover: RecordCover, photos: Mapping[str, bytes]
) -> RecordPdf:
    """Lays out the record for its mode. Its text_log holds every piece of text written."""
    footer_label = STATEMENT_LABEL if mode == "statement" else "Not a qualification"
    footer_text = f"{TITLES[mode]}  ·  {footer_label}  ·  Verify code {cover.verify_code}"
    pdf = RecordPdf(footer_text=footer_text, title=TITLES[mode])
    if mode == "arpl":
        write_arpl_record(pdf, evidence, cover, photos)
    else:
        write_statement_record(pdf, evidence, cover)
    return pdf


def verify_record(verify_code: str, stored: StoredRecord | None) -> VerifyResult:
    """Checks a record against the hash stored when it was issued.

    Args:
        verify_code: the code from the link or the paper, in any letter case.
        stored: the StoredRecord P2 looked up by that code, or None if there is none.

    Returns:
        A VerifyResult: "genuine" if the stored record still matches its hash, "changed" if
        it doesn't, and "unknown" if there is no record with this code.
    """
    if stored is None or stored.verify_code != verify_code.strip().upper():
        return VerifyResult(status="unknown")
    is_unchanged = hash_record(stored.evidence, stored.mode) == stored.sha256
    job_dates = [job.done_on for job in stored.evidence.jobs]
    return VerifyResult(
        status="genuine" if is_unchanged else "changed",
        display_name=stored.evidence.display_name,
        mode=stored.mode,
        n_jobs=len(stored.evidence.jobs),
        issued_on=stored.issued_on,
        sha256=stored.sha256,
        first_job_on=min(job_dates, default=None),
        last_job_on=max(job_dates, default=None),
    )


def check_mode_allowed(evidence: RecordEvidence, mode: str) -> None:
    """Raises if the mode is unknown, or if it's ARPL for a provider with no ARPL trade."""
    if mode not in RECORD_MODES:
        raise ValueError(f"Unknown record mode {mode!r}; expected one of {RECORD_MODES}")
    if mode == "arpl":
        choose_arpl_trade(evidence)


def create_verify_code() -> str:
    """Creates a random verify code such as "FX7K2Q".

    Uses the secrets module, not a seeded rng: the code is what lets a stranger open the
    verify page, so it must not be guessable.
    """
    return "".join(secrets.choice(VERIFY_CODE_ALPHABET) for _ in range(VERIFY_CODE_LENGTH))


def build_verify_url(verify_base_url: str | None, verify_code: str) -> str | None:
    """Returns the absolute verify link for the QR code, or None without a base URL."""
    if not verify_base_url:
        return None
    return f"{verify_base_url.rstrip('/')}{VERIFY_PATH}{verify_code}"


def hash_record(evidence: RecordEvidence, mode: str) -> str:
    """Returns the SHA-256 (hex) of the record's contents as canonical JSON.

    The same evidence and mode always give the same hash, and changing any job changes it.
    Fields left at their defaults are left out, so adding an optional field later doesn't
    change the hash of records issued before. The verify code and issue date are left out
    too, so re-exporting unchanged evidence gives the same hash.
    """
    contents = {"mode": mode, "evidence": evidence.model_dump(mode="json", exclude_defaults=True)}
    canonical_json = json.dumps(contents, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
