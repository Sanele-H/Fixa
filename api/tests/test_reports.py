"""The report button: jobs, providers and messages."""

import pytest
from sqlmodel import select

from fixa_api.models import Report

LINDIWE = "082 000 0001"  # cust_001
OTHER_CUSTOMER = "082 000 0002"
THABO = "071 000 0001"  # prov_001
SIPHO = "071 000 0002"  # prov_002
ELECTRICIAN = "071 000 0006"
QUOTE_TIME = "2026-10-01T10:00:00+02:00"


def report(client, headers, target_type, target_id, reason="scam", **extra):
    body = {"target_type": target_type, "target_id": target_id, "reason": reason} | extra
    return client.post("/api/reports", json=body, headers=headers)


@pytest.fixture
def chat(seeded_client, log_in):
    """A job with Thabo's quote and one message from him. Returns (job_id, message_id)."""
    customer, provider = log_in(LINDIWE), log_in(THABO)
    body = {
        "description": "My tap drips",
        "lang": "en",
        "trade": "plumbing",
        "urgency": "normal",
        "size": "small",
        "suburb": "Braamfontein",
    }
    job_id = seeded_client.post("/api/jobs", json=body, headers=customer).json()["id"]
    quote = {"amount_rands": 300, "when": QUOTE_TIME}
    seeded_client.post(f"/api/jobs/{job_id}/quotes", json=quote, headers=provider)
    sent = seeded_client.post(
        f"/api/jobs/{job_id}/messages", json={"text": "Pay me a deposit first"}, headers=provider
    )
    return job_id, sent.json()["id"]


def test_a_customer_reports_a_provider(seeded_client, seeded_session, log_in):
    response = report(
        seeded_client, log_in(LINDIWE), "provider", "prov_002", "fake_profile", note="Not real"
    )

    assert response.status_code == 201
    assert response.json()["status"] == "received"
    (saved,) = seeded_session.exec(select(Report))
    assert (saved.reporter_id, saved.target_id, saved.reason, saved.note, saved.status) == (
        "cust_001",
        "prov_002",
        "fake_profile",
        "Not real",
        "open",
    )


def test_a_provider_reports_a_job_they_can_see(seeded_client, log_in, chat):
    job_id, _ = chat

    assert report(seeded_client, log_in(SIPHO), "job", job_id, "illegal_work").status_code == 201


def test_the_customer_reports_a_message_they_received(seeded_client, log_in, chat):
    _, message_id = chat

    assert report(seeded_client, log_in(LINDIWE), "message", message_id, "scam").status_code == 201


@pytest.mark.parametrize("phone", [OTHER_CUSTOMER, ELECTRICIAN, SIPHO])
def test_you_cannot_report_a_message_you_could_not_read(seeded_client, log_in, chat, phone):
    _, message_id = chat

    assert report(seeded_client, log_in(phone), "message", message_id).status_code == 404


def test_you_cannot_report_a_job_you_cannot_see(seeded_client, log_in, chat):
    job_id, _ = chat

    assert report(seeded_client, log_in(OTHER_CUSTOMER), "job", job_id).status_code == 404
    assert report(seeded_client, log_in(ELECTRICIAN), "job", job_id).status_code == 404


@pytest.mark.parametrize(
    ("target_type", "target_id"),
    [("job", "job_nope"), ("provider", "prov_nope"), ("message", "msg_nope")],
)
def test_something_that_does_not_exist_is_a_404(seeded_client, log_in, target_type, target_id):
    assert report(seeded_client, log_in(LINDIWE), target_type, target_id).status_code == 404


def test_you_cannot_report_yourself(seeded_client, log_in, chat):
    job_id, message_id = chat

    assert report(seeded_client, log_in(THABO), "provider", "prov_001").status_code == 422
    assert report(seeded_client, log_in(LINDIWE), "job", job_id).status_code == 422
    assert report(seeded_client, log_in(THABO), "message", message_id).status_code == 422


def test_the_same_report_twice_is_refused_but_a_different_reason_is_fine(seeded_client, log_in):
    customer = log_in(LINDIWE)
    assert report(seeded_client, customer, "provider", "prov_002", "scam").status_code == 201

    assert report(seeded_client, customer, "provider", "prov_002", "scam").status_code == 409
    assert report(seeded_client, customer, "provider", "prov_002", "abuse").status_code == 201


@pytest.mark.parametrize(
    "changes",
    [{"reason": "annoying"}, {"target_type": "user"}, {"target_id": ""}, {"note": "x" * 501}],
)
def test_a_bad_report_is_refused(seeded_client, log_in, changes):
    body = {"target_type": "provider", "target_id": "prov_002", "reason": "scam"} | changes

    response = seeded_client.post("/api/reports", json=body, headers=log_in(LINDIWE))

    assert response.status_code == 422


def test_twenty_reports_a_day_at_most(seeded_client, log_in):
    customer = log_in(LINDIWE)
    for number in range(2, 22):
        assert report(seeded_client, customer, "provider", f"prov_{number:03d}").status_code == 201

    assert report(seeded_client, customer, "provider", "prov_030").status_code == 429


def test_reporting_needs_a_sign_in(seeded_client):
    assert report(seeded_client, {}, "provider", "prov_002").status_code == 401


def test_the_answer_shows_nothing_about_the_reported_person(seeded_client, log_in):
    text = report(
        seeded_client, log_in(LINDIWE), "provider", "prov_002", note="call 082 123 4567"
    ).text

    assert "082" not in text and "Sipho" not in text
