"""build_record and verify_record: the work record PDF, and the check behind /verify/{code}.

STUB (step 0): a one-page PDF with a summary, the verify code and the SHA-256 of the
record's contents. Step 6 lays it out to follow the sections of the merSETA ARPL trade test
application form, and adds jobs by trade task, photos, vouches, the experience timeline and
a QR code linking to /verify/{code}.

The SHA-256 is taken over the record's contents (canonical JSON of the evidence and mode),
not over the PDF bytes: a PDF can't print its own hash, and this way the hash printed on
the paper is the one the verify page checks.
"""

import hashlib
import json
import secrets
from typing import get_args

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from record.models import RecordDoc, RecordEvidence, RecordMode, StoredRecord, VerifyResult

RECORD_MODES = get_args(RecordMode)

# Trades with an ARPL toolkit, by trade id in data/glossary.json. Add carpentry,
# bricklaying and the other toolkit trades once P3 adds their ids to the glossary.
ARPL_TRADES = frozenset({"plumbing", "electrical"})

VERIFY_CODE_LENGTH = 6
# No 0/O or 1/I, so a code copied off paper can't be mistyped.
VERIFY_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

TITLES = {"arpl": "Fixa work record", "statement": "Fixa work statement"}
DISCLAIMERS = {
    "arpl": (
        "This record supports an ARPL application. It is not a qualification: the NAMB "
        "technical panel reviews every application, and the trade test is still required."
    ),
    "statement": "Customer-confirmed, not a bank statement.",
}

PDF_FONT = "Helvetica"
TITLE_FONT_SIZE_PT = 16
BODY_FONT_SIZE_PT = 11
LINE_HEIGHT_MM = 7


class ArplTradeError(ValueError):
    """Raised for an ARPL export when none of the provider's trades has an ARPL toolkit."""


def build_record(evidence: RecordEvidence, mode: RecordMode) -> RecordDoc:
    """Builds a work record PDF with a verify code and the SHA-256 of its contents.

    Args:
        evidence: the provider's confirmed jobs. It has no customer names, numbers or
            addresses, by design.
        mode: "arpl" to support an ARPL application (toolkit trades only), or "statement"
            for credit or renting (every trade, including cleaning and gardening).

    Returns:
        RecordDoc(pdf_bytes, verify_code, sha256). P2 saves a StoredRecord with the same
        code and hash so the verify page can check the record later.

    Raises:
        ValueError: mode is not "arpl" or "statement".
        ArplTradeError: mode is "arpl" and none of the provider's trades has an ARPL toolkit.
    """
    check_mode_allowed(evidence, mode)
    verify_code = create_verify_code()
    sha256 = hash_record(evidence, mode)
    lines = build_record_lines(evidence, mode, verify_code, sha256)
    pdf_bytes = render_pdf(TITLES[mode], lines)
    return RecordDoc(pdf_bytes=pdf_bytes, verify_code=verify_code, sha256=sha256)


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
    return VerifyResult(
        status="genuine" if is_unchanged else "changed",
        display_name=stored.evidence.display_name,
        mode=stored.mode,
        n_jobs=len(stored.evidence.jobs),
        issued_on=stored.issued_on,
        sha256=stored.sha256,
    )


def check_mode_allowed(evidence: RecordEvidence, mode: str) -> None:
    """Raises if the mode is unknown, or if it's ARPL for a provider with no ARPL trade."""
    if mode not in RECORD_MODES:
        raise ValueError(f"Unknown record mode {mode!r}; expected one of {RECORD_MODES}")
    if mode == "arpl" and not ARPL_TRADES.intersection(evidence.trades):
        raise ArplTradeError(f"No ARPL toolkit for trades {evidence.trades}")


def create_verify_code() -> str:
    """Creates a random verify code such as "FX7K2Q".

    Uses the secrets module, not a seeded rng: the code is what lets a stranger open the
    verify page, so it must not be guessable.
    """
    return "".join(secrets.choice(VERIFY_CODE_ALPHABET) for _ in range(VERIFY_CODE_LENGTH))


def hash_record(evidence: RecordEvidence, mode: str) -> str:
    """Returns the SHA-256 (hex) of the record's contents as canonical JSON.

    The same evidence and mode always give the same hash, and changing any job changes it.
    The verify code and issue date are left out, so re-exporting unchanged evidence gives
    the same hash.
    """
    contents = {"mode": mode, "evidence": evidence.model_dump(mode="json")}
    canonical_json = json.dumps(contents, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def build_record_lines(
    evidence: RecordEvidence, mode: str, verify_code: str, sha256: str
) -> list[str]:
    """Builds the text lines of the record, below the title. STUB: a short summary."""
    return [
        f"Provider: {evidence.display_name}",
        f"Trades: {', '.join(evidence.trades)}",
        f"Confirmed jobs: {len(evidence.jobs)}",
        f"Verify code: {verify_code} (check it at /verify/{verify_code})",
        f"SHA-256: {sha256}",
        DISCLAIMERS[mode],
    ]


def render_pdf(title: str, lines: list[str]) -> bytes:
    """Writes a title and lines of text onto an A4 page and returns the PDF's bytes."""
    pdf = FPDF(format="A4")
    pdf.add_page()
    pdf.set_font(PDF_FONT, style="B", size=TITLE_FONT_SIZE_PT)
    write_paragraph(pdf, title, LINE_HEIGHT_MM * 2)
    pdf.set_font(PDF_FONT, size=BODY_FONT_SIZE_PT)
    for line in lines:
        write_paragraph(pdf, line, LINE_HEIGHT_MM)
    return bytes(pdf.output())


def write_paragraph(pdf: FPDF, text: str, line_height_mm: float) -> None:
    """Writes text across the page width, wrapping as needed, then moves to the next line."""
    pdf.multi_cell(0, line_height_mm, make_latin1_safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def make_latin1_safe(text: str) -> str:
    """Replaces characters the built-in PDF font can't draw with "?".

    The built-in Helvetica covers Latin-1 only. Step 6 embeds a Unicode font instead.
    """
    return text.encode("latin-1", errors="replace").decode("latin-1")
