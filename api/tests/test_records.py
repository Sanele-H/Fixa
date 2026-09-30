"""Work record export, the PDF download, and the /record and /verify link pages."""

import datetime as dt
import json
import re

import pytest
from sqlmodel import select

from fixa_api.fixtures import FIXTURES_PATH
from fixa_api.models import Customer, ExportedRecord, Job, OffAppJob, Provider

THABO = "071 000 0001"  # prov_001: 9 app jobs and 3 confirmed off-app jobs
NOSIPHO = "071 000 0003"  # prov_003: about 4 years of confirmed work
NO_JOBS = "071 000 0029"  # prov_029: nothing confirmed yet
LINDIWE = "082 000 0001"

PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+27|0)[\s-]?\d{2}[\s-]?\d{3}[\s-]?\d{4}(?!\d)")


def fixture_keys(file_name: str) -> set[str]:
    return set(json.loads((FIXTURES_PATH / file_name).read_text(encoding="utf-8")))


def export(client, headers, mode="arpl"):
    return client.post("/api/record/export", json={"mode": mode}, headers=headers)


@pytest.fixture
def thabo(log_in):
    return log_in(THABO)


# --- exporting ------------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["arpl", "statement"])
def test_an_export_has_the_contract_shape(seeded_client, thabo, mode):
    response = export(seeded_client, thabo, mode)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == fixture_keys("record_export.json")
    assert re.fullmatch(r"[A-Z2-9]{6}", body["verify_code"])
    assert re.fullmatch(r"[0-9a-f]{64}", body["sha256"])
    assert body["download_url"] == f"/api/record/exports/{body['verify_code']}.pdf"


def test_the_pdf_can_be_downloaded_by_its_owner(seeded_client, thabo):
    body = export(seeded_client, thabo).json()

    response = seeded_client.get(body["download_url"], headers=thabo)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_nobody_else_can_download_it(seeded_client, log_in, thabo):
    url = export(seeded_client, thabo).json()["download_url"]

    assert seeded_client.get(url, headers=log_in(NOSIPHO)).status_code == 404
    assert seeded_client.get(url, headers=log_in(LINDIWE)).status_code == 403
    assert seeded_client.get(url).status_code == 401
    assert seeded_client.get("/api/record/exports/NOPE00.pdf", headers=thabo).status_code == 404


def test_only_a_provider_can_export(seeded_client, log_in):
    assert export(seeded_client, log_in(LINDIWE)).status_code == 403
    assert export(seeded_client, {}).status_code == 401


def test_a_provider_with_no_confirmed_jobs_has_nothing_to_export(seeded_client, log_in):
    response = export(seeded_client, log_in(NO_JOBS), "statement")

    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "no_jobs"


def test_arpl_is_only_for_trades_with_a_toolkit(seeded_client, seeded_session, thabo):
    provider = seeded_session.get(Provider, "prov_001")
    provider.trades = ["cleaning"]
    seeded_session.add(provider)
    seeded_session.commit()

    arpl = export(seeded_client, thabo, "arpl")
    statement = export(seeded_client, thabo, "statement")

    assert arpl.status_code == 422
    assert arpl.json()["detail"]["error"] == "no_arpl_trade"
    assert statement.status_code == 200


def test_ten_exports_a_day_at_most(seeded_client, thabo):
    for _ in range(10):
        assert export(seeded_client, thabo, "statement").status_code == 200

    assert export(seeded_client, thabo, "statement").status_code == 429


def test_the_stored_evidence_has_only_confirmed_jobs_and_no_customer_details(
    seeded_client, seeded_session, thabo
):
    export(seeded_client, thabo)

    stored = seeded_session.exec(select(ExportedRecord)).one()
    text = json.dumps(stored.evidence)

    assert not PHONE_PATTERN.search(text)
    for address in {c.address for c in seeded_session.exec(select(Customer))}:
        assert address not in text
    expected = 9 + 3  # Thabo's app jobs and confirmed off-app jobs in the demo data
    assert len(stored.evidence["jobs"]) == expected
    assert {job["confirmed_via"] for job in stored.evidence["jobs"]} <= {"app", "sms", "ussd"}


def test_unconfirmed_off_app_jobs_are_left_out(seeded_client, seeded_session, thabo):
    pending = [
        job
        for job in seeded_session.exec(select(OffAppJob))
        if job.provider_id == "prov_001" and job.state != "confirmed"
    ]
    export(seeded_client, thabo)
    stored = seeded_session.exec(select(ExportedRecord)).one()

    assert len(stored.evidence["jobs"]) == 12
    assert all(job.state != "confirmed" for job in pending)


# --- the verify page ------------------------------------------------------------------------


def test_the_verify_page_says_a_fresh_export_is_genuine(seeded_client, thabo):
    code = export(seeded_client, thabo).json()["verify_code"]

    page = seeded_client.get(f"/verify/{code}")

    assert page.status_code == 200
    assert "genuine and unchanged" in page.text
    assert "Thabo" in page.text
    assert "<script" not in page.text.lower()
    assert page.headers["x-robots-tag"] == "noindex"


def test_the_code_works_in_any_letter_case(seeded_client, thabo):
    code = export(seeded_client, thabo).json()["verify_code"]

    assert "genuine" in seeded_client.get(f"/verify/{code.lower()}").text


def test_the_verify_page_shows_the_fingerprint_that_is_on_the_paper(seeded_client, thabo):
    body = export(seeded_client, thabo).json()

    assert body["sha256"] in seeded_client.get(f"/verify/{body['verify_code']}").text


def test_a_record_changed_after_it_was_issued_is_not_genuine(seeded_client, seeded_session, thabo):
    code = export(seeded_client, thabo).json()["verify_code"]
    row = seeded_session.get(ExportedRecord, code)
    evidence = json.loads(json.dumps(row.evidence))
    evidence["jobs"][0]["trade_task"] = "Something added later"
    row.evidence = evidence
    seeded_session.add(row)
    seeded_session.commit()

    page = seeded_client.get(f"/verify/{code}")

    assert "no longer matches" in page.text
    assert "genuine and unchanged" not in page.text


def test_an_unknown_code_is_a_404_page_that_says_so(seeded_client):
    page = seeded_client.get("/verify/ZZZZZZ")

    assert page.status_code == 404
    assert "no record with this code" in page.text


def test_the_verify_page_needs_no_sign_in_and_shows_no_customer_details(
    seeded_client, seeded_session, thabo
):
    code = export(seeded_client, thabo).json()["verify_code"]

    text = seeded_client.get(f"/verify/{code}").text

    assert not PHONE_PATTERN.search(text)
    assert "Example Street" not in text


# --- the work record page -------------------------------------------------------------------


def test_the_record_page_opens_for_anyone_once_the_provider_has_exported(seeded_client, thabo):
    export(seeded_client, thabo)

    page = seeded_client.get("/record/prov_001")

    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    assert "Thabo" in page.text
    assert "<script" not in page.text.lower()
    assert page.headers["x-robots-tag"] == "noindex"


def test_a_provider_who_never_exported_has_no_public_page(seeded_client):
    assert seeded_client.get("/record/prov_001").status_code == 404
    assert seeded_client.get("/record/prov_nope").status_code == 404


def test_the_record_page_never_shows_a_phone_or_an_address(seeded_client, seeded_session, thabo):
    export(seeded_client, thabo)
    text = seeded_client.get("/record/prov_001").text

    assert not PHONE_PATTERN.search(text)
    for address in {c.address for c in seeded_session.exec(select(Customer))} | {
        j.address for j in seeded_session.exec(select(Job))
    }:
        assert address not in text


def test_a_task_written_as_html_is_shown_as_text(seeded_client, seeded_session, thabo):
    seeded_session.add(
        OffAppJob(
            id="offapp_evil",
            provider_id="prov_001",
            state="confirmed",
            trade="plumbing",
            trade_task="<script>alert(1)</script>",
            date=dt.date(2026, 8, 1),
            suburb="Soweto",
            customer_phone="083 555 0001",
            confirmed_via="sms",
        )
    )
    seeded_session.commit()
    export(seeded_client, thabo)

    page = seeded_client.get("/record/prov_001").text

    assert "<script>alert(1)" not in page
    assert "&lt;script&gt;" in page


def test_the_export_uses_the_configured_public_address(seeded_client, thabo, monkeypatch):
    seen = {}

    def spy(evidence, mode, **kwargs):
        seen.update(kwargs)
        raise RuntimeError("stop here")

    monkeypatch.setattr("fixa_api.routes.records.build_record", spy)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://fixa.example")

    with pytest.raises(RuntimeError):
        export(seeded_client, thabo)

    assert seen["verify_base_url"] == "https://fixa.example"


# --- the summary for the "My record" screen -------------------------------------------------


def test_the_record_summary_has_the_contract_shape(seeded_client, log_in):
    summary = seeded_client.get("/api/record/summary", headers=log_in(NOSIPHO)).json()

    assert set(summary) == fixture_keys("record_summary.json")
    assert summary["arpl_trade"] == "plumbing"
    assert summary["experience_months"] > 36  # about 4 years of confirmed work
    assert summary["confirmed_jobs"] > 0


def test_a_provider_with_no_confirmed_jobs_has_an_empty_summary(seeded_client, log_in):
    summary = seeded_client.get("/api/record/summary", headers=log_in(NO_JOBS)).json()

    assert summary["experience_months"] == 0
    assert summary["confirmed_jobs"] == 0


def test_only_a_provider_has_a_record_summary(seeded_client, log_in):
    assert seeded_client.get("/api/record/summary", headers=log_in(LINDIWE)).status_code == 403
    assert seeded_client.get("/api/record/summary").status_code == 401
