"""build_record and verify_record: modes, hashing, the verify link, and what's never printed."""

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
    RecordPhoto,
    StoredRecord,
    Vouch,
    build_record,
    verify_record,
)

FIXTURES_PATH = Path(__file__).resolve().parents[3] / "contracts" / "fixtures"
VERIFY_CODE_PATTERN = re.compile(r"[A-HJ-NP-Z2-9]{6}")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
ISSUED_ON = date(2026, 9, 29)
BASE_URL = "https://fixa.example"


def make_job(trade: str = "plumbing", **fields) -> RecordJob:
    """Makes a confirmed job; any RecordJob field can be passed in."""
    job_fields = {
        "done_on": date(2026, 8, 14),
        "suburb": "Soweto",
        "trade": trade,
        "trade_task": "Replace geyser valve",
        "confirmed_via": "sms",
        "amount_rands": 380,
    }
    return RecordJob(**{**job_fields, **fields})


def make_evidence(trades: list[str] | None = None, **fields) -> RecordEvidence:
    """Makes a record with two confirmed jobs in the first trade (plumbing by default)."""
    trades = trades or ["plumbing"]
    fields.setdefault(
        "jobs",
        [make_job(trades[0]), make_job(trades[0], done_on=date(2026, 9, 2), confirmed_via="app")],
    )
    return RecordEvidence(provider_id="prov_002", display_name="Sipho", trades=trades, **fields)


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


def test_empty_optional_fields_and_photo_bytes_leave_the_hash_alone():
    plain = make_evidence()
    with_empty_fields = make_evidence(vouches=[], arpl_trade=None)
    assert build_record(plain, "arpl").sha256 == build_record(with_empty_fields, "arpl").sha256
    with_photo = make_evidence(jobs=[make_job(photos=[RecordPhoto(photo_id="p1", kind="after")])])
    without_bytes = build_record(with_photo, "arpl").sha256
    assert build_record(with_photo, "arpl", photos={"p1": b"not an image"}).sha256 == without_bytes


def test_arpl_mode_needs_a_trade_with_an_arpl_toolkit():
    with pytest.raises(ArplTradeError):
        build_record(make_evidence(["cleaning"]), "arpl")


def test_arpl_trade_must_be_one_of_the_providers_toolkit_trades():
    with pytest.raises(ArplTradeError):
        build_record(make_evidence(["plumbing"], arpl_trade="electrical"), "arpl")
    assert build_record(make_evidence(["plumbing"], arpl_trade="plumbing"), "arpl").pdf_bytes


def test_statement_mode_works_for_every_trade():
    assert build_record(make_evidence(["cleaning"]), "statement").pdf_bytes


def test_unknown_mode_is_refused():
    with pytest.raises(ValueError):
        build_record(make_evidence(), "loan")


@pytest.mark.parametrize("customer_field", ["customer_name", "customer_phone", "address"])
def test_jobs_and_vouches_refuse_customer_details(customer_field):
    with pytest.raises(ValidationError):
        make_job(**{customer_field: "x"})
    with pytest.raises(ValidationError):
        Vouch(text="Great work", suburb="Soweto", given_on=ISSUED_ON, **{customer_field: "x"})


def test_the_verify_link_is_in_the_pdf_when_there_is_a_base_url():
    doc = build_record(make_evidence(), "arpl", verify_base_url=BASE_URL + "/")
    assert f"{BASE_URL}/verify/{doc.verify_code}".encode() in doc.pdf_bytes


def test_no_absolute_link_without_a_base_url():
    doc = build_record(make_evidence(), "arpl")
    assert BASE_URL.encode() not in doc.pdf_bytes


def test_verify_confirms_an_unchanged_record():
    stored = store(make_evidence(), "arpl")
    result = verify_record(stored.verify_code.lower(), stored)
    assert result.status == "genuine"
    assert (result.display_name, result.n_jobs, result.issued_on) == ("Sipho", 2, ISSUED_ON)
    assert (result.first_job_on, result.last_job_on) == (date(2026, 8, 14), date(2026, 9, 2))


def test_verify_spots_a_changed_record():
    stored = store(make_evidence(), "arpl")
    stored.evidence.jobs[0].amount_rands = 3800
    assert verify_record(stored.verify_code, stored).status == "changed"


def test_verify_reports_an_unknown_code():
    stored = store(make_evidence(), "arpl")
    assert verify_record("ABC234", None).status == "unknown"
    assert verify_record("ABC234", stored).status == "unknown"
