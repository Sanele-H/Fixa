"""The plain-HTML work record and verify pages: no JavaScript, escaped, and private."""

from datetime import date

import pytest

from record import (
    RecordEvidence,
    RecordJob,
    StoredRecord,
    Vouch,
    build_record,
    render_verify_page,
    render_work_record_page,
    verify_record,
)

ISSUED_ON = date(2026, 9, 29)


def make_evidence(**fields) -> RecordEvidence:
    """Makes a plumber's record with two confirmed jobs and an agreed amount on each."""
    jobs = [
        RecordJob(
            done_on=date(2022, 9, 30),
            suburb="Newtown",
            trade="plumbing",
            trade_task="Replace geyser valve",
            confirmed_via="ussd",
            amount_rands=4870,
        ),
        RecordJob(
            done_on=date(2026, 9, 19),
            suburb="Yeoville",
            trade="plumbing",
            trade_task="Unblock drain",
            confirmed_via="app",
            amount_rands=330,
        ),
    ]
    return RecordEvidence(
        provider_id="prov_003", display_name="Nosipho", trades=["plumbing"], jobs=jobs, **fields
    )


def make_stored(evidence: RecordEvidence, mode: str = "arpl") -> StoredRecord:
    """Exports a record and returns what P2 would save for it."""
    doc = build_record(evidence, mode)
    return StoredRecord(
        verify_code=doc.verify_code,
        sha256=doc.sha256,
        mode=mode,
        evidence=evidence,
        issued_on=ISSUED_ON,
    )


def test_work_record_page_shows_the_work_and_its_span():
    html = render_work_record_page(make_evidence())
    assert "<h1>Nosipho</h1>" in html
    assert (
        "2 confirmed jobs, confirmed work from 30/09/2022 to 19/09/2026 (3 years 11 months)" in html
    )
    assert "Replace geyser valve" in html and "by customer USSD" in html


def test_work_record_page_has_no_javascript_and_no_agreed_amounts():
    html = render_work_record_page(make_evidence()).lower()
    assert "<script" not in html and "javascript:" not in html and "onclick" not in html
    assert "4870" not in html and "4 870" not in html


def test_customers_words_are_escaped_and_numbers_hidden():
    vouch = Vouch(
        text='<script>alert("x")</script> call 082 555 1234', suburb="Berea", given_on=ISSUED_ON
    )
    html = render_work_record_page(make_evidence(vouches=[vouch]))
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "[number hidden]" in html and "555 1234" not in html


def test_a_new_provider_gets_a_page_without_tables():
    html = render_work_record_page(make_evidence().model_copy(update={"jobs": []}))
    assert "0 confirmed jobs." in html and "<table>" not in html


@pytest.mark.parametrize("mode", ["arpl", "statement"])
def test_verify_page_confirms_a_genuine_record(mode):
    stored = make_stored(make_evidence(), mode)
    html = render_verify_page(stored.verify_code, verify_record(stored.verify_code, stored))
    assert "This record is genuine and unchanged" in html
    assert stored.sha256 in html and "30/09/2022 to 19/09/2026" in html
    expected_note = "It is not a qualification" if mode == "arpl" else "not a bank statement"
    assert expected_note in html


def test_verify_page_warns_about_a_changed_record():
    stored = make_stored(make_evidence())
    stored.evidence.jobs[0].trade_task = "Install new geyser"
    html = render_verify_page(stored.verify_code, verify_record(stored.verify_code, stored))
    assert "no longer matches what Fixa issued" in html


def test_verify_page_handles_an_unknown_code():
    html = render_verify_page(" abc234 ", verify_record("abc234", None))
    assert "Fixa has no record with this code" in html and "ABC234" in html
    assert "<table>" not in html
