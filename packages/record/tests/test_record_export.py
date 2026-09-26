"""build_record and verify_record. Step 0: a summary PDF, but real hashing and verify checks."""

import json
import re
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from record import (
    ArplTradeError,
    RecordEvidence,
    RecordJob,
    StoredRecord,
    build_record,
    verify_record,
)
from record.export import build_record_lines

FIXTURES_PATH = Path(__file__).resolve().parents[3] / "contracts" / "fixtures"
VERIFY_CODE_PATTERN = re.compile(r"[A-HJ-NP-Z2-9]{6}")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
ISSUED_ON = date(2026, 9, 29)


def make_evidence(trades: list[str] | None = None) -> RecordEvidence:
    """Makes a record with two confirmed jobs in the first trade given (plumbing by default)."""
    trades = trades or ["plumbing"]
    jobs = [
        RecordJob(
            done_on=date(2026, 8, 14),
            suburb="Soweto",
            trade=trades[0],
            trade_task="Replace geyser valve",
            confirmed_via="sms",
            amount_rands=380,
        ),
        RecordJob(
            done_on=date(2026, 9, 2),
            suburb="Braamfontein",
            trade=trades[0],
            trade_task="Fix a dripping tap",
            confirmed_via="app",
            amount_rands=450,
        ),
    ]
    return RecordEvidence(provider_id="prov_002", display_name="Sipho", trades=trades, jobs=jobs)


def store(evidence: RecordEvidence, mode: str) -> StoredRecord:
    """Exports a record and returns what P2 would save for it."""
    doc = build_record(evidence, mode)
    return StoredRecord(
        verify_code=doc.verify_code,
        sha256=doc.sha256,
        mode=mode,
        evidence=evidence,
        issued_on=ISSUED_ON,
    )


def test_builds_a_pdf_with_a_verify_code_and_hash():
    doc = build_record(make_evidence(), "statement")
    assert doc.pdf_bytes.startswith(b"%PDF-")
    assert VERIFY_CODE_PATTERN.fullmatch(doc.verify_code)
    assert SHA256_PATTERN.fullmatch(doc.sha256)


def test_fixture_verify_code_fits_the_code_format():
    fixture = json.loads((FIXTURES_PATH / "record_export.json").read_text(encoding="utf-8"))
    assert VERIFY_CODE_PATTERN.fullmatch(fixture["verify_code"])


def test_same_contents_give_the_same_hash_and_a_new_code():
    first = build_record(make_evidence(), "arpl")
    second = build_record(make_evidence(), "arpl")
    assert first.sha256 == second.sha256
    assert first.verify_code != second.verify_code


def test_changing_a_job_or_the_mode_changes_the_hash():
    evidence = make_evidence()
    changed = evidence.model_copy(deep=True)
    changed.jobs[0].amount_rands = 3800
    original_hash = build_record(evidence, "arpl").sha256
    assert build_record(changed, "arpl").sha256 != original_hash
    assert build_record(evidence, "statement").sha256 != original_hash


def test_arpl_mode_needs_a_trade_with_an_arpl_toolkit():
    with pytest.raises(ArplTradeError):
        build_record(make_evidence(["cleaning"]), "arpl")


def test_statement_mode_works_for_every_trade():
    assert build_record(make_evidence(["cleaning"]), "statement").pdf_bytes


def test_unknown_mode_is_refused():
    with pytest.raises(ValueError):
        build_record(make_evidence(), "loan")


@pytest.mark.parametrize("customer_field", ["customer_name", "customer_phone", "address"])
def test_record_job_refuses_customer_details(customer_field):
    job_fields = make_evidence().jobs[0].model_dump()
    with pytest.raises(ValidationError):
        RecordJob(**job_fields, **{customer_field: "x"})


def test_arpl_record_says_it_is_not_a_qualification():
    lines = build_record_lines(make_evidence(), "arpl", "FX7K2Q", "0" * 64)
    assert any("It is not a qualification" in line for line in lines)


def test_statement_says_it_is_not_a_bank_statement():
    lines = build_record_lines(make_evidence(), "statement", "FX7K2Q", "0" * 64)
    assert any("Customer-confirmed, not a bank statement" in line for line in lines)


def test_verify_confirms_an_unchanged_record():
    stored = store(make_evidence(), "arpl")
    result = verify_record(stored.verify_code.lower(), stored)
    assert result.status == "genuine"
    assert (result.display_name, result.n_jobs, result.issued_on) == ("Sipho", 2, ISSUED_ON)


def test_verify_spots_a_changed_record():
    stored = store(make_evidence(), "arpl")
    stored.evidence.jobs[0].amount_rands = 3800
    assert verify_record(stored.verify_code, stored).status == "changed"


def test_verify_reports_an_unknown_code():
    stored = store(make_evidence(), "arpl")
    assert verify_record("ABC234", None).status == "unknown"
    assert verify_record("ABC234", stored).status == "unknown"
