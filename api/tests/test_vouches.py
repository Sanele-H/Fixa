"""Customer vouches: who can give one, what they show, and where they appear."""

import re

import pytest
from sqlmodel import select

from fixa_api.models import CustomerVouch

LINDIWE = "082 000 0001"  # cust_001, Braamfontein
OTHER_CUSTOMER = "082 000 0002"
THABO = "071 000 0001"  # prov_001
SIPHO = "071 000 0002"  # prov_002
QUOTE_TIME = "2026-10-01T10:00:00+02:00"
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+27|0)[\s-]?\d{2}[\s-]?\d{3}[\s-]?\d{4}(?!\d)")
GOOD_WORDS = "Fixed my tap quickly and cleaned up after."


def vouch(client, headers, provider_id="prov_001", text=GOOD_WORDS):
    return client.post(
        f"/api/providers/{provider_id}/vouches", json={"text": text}, headers=headers
    )


def finished_job(client, log_in, provider_phone=THABO):
    """Lindiwe's job that the provider finished."""
    customer, provider = log_in(LINDIWE), log_in(provider_phone)
    body = {
        "description": "My tap drips",
        "lang": "en",
        "trade": "plumbing",
        "urgency": "normal",
        "size": "small",
        "suburb": "Braamfontein",
    }
    job_id = client.post("/api/jobs", json=body, headers=customer).json()["id"]
    quote = {"amount_rands": 300, "when": QUOTE_TIME}
    quote_id = client.post(f"/api/jobs/{job_id}/quotes", json=quote, headers=provider).json()["id"]
    client.post(f"/api/quotes/{quote_id}/accept", headers=customer)
    client.post(f"/api/jobs/{job_id}/confirm", headers=provider)
    client.post(f"/api/jobs/{job_id}/done", json={"completed": True}, headers=customer)
    return job_id


def test_a_customer_vouches_after_a_finished_job(seeded_client, log_in):
    finished_job(seeded_client, log_in)

    response = vouch(seeded_client, log_in(LINDIWE))

    assert response.status_code == 201
    body = response.json()
    assert (body["text"], body["suburb"]) == (GOOD_WORDS, "Braamfontein")
    assert set(body) == {"id", "text", "suburb", "given_on"}  # never who wrote it


def test_you_need_a_finished_job_with_that_provider(seeded_client, log_in):
    finished_job(seeded_client, log_in, THABO)

    no_job = vouch(seeded_client, log_in(LINDIWE), "prov_002")  # a different provider
    stranger = vouch(seeded_client, log_in(OTHER_CUSTOMER), "prov_001")  # never hired Thabo

    assert no_job.status_code == 403 and stranger.status_code == 403
    assert no_job.json()["detail"]["error"] == "no_job_together"


def test_an_unfinished_job_is_not_enough(seeded_client, log_in):
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
    quote_id = seeded_client.post(
        f"/api/jobs/{job_id}/quotes", json=quote, headers=provider
    ).json()["id"]
    seeded_client.post(f"/api/quotes/{quote_id}/accept", headers=customer)
    seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=provider)

    assert vouch(seeded_client, customer).status_code == 403


def test_one_vouch_per_customer_and_provider(seeded_client, log_in):
    finished_job(seeded_client, log_in)
    customer = log_in(LINDIWE)
    vouch(seeded_client, customer)

    assert vouch(seeded_client, customer).status_code == 409


def test_only_a_customer_can_vouch(seeded_client, log_in):
    assert vouch(seeded_client, log_in(SIPHO)).status_code == 403
    assert vouch(seeded_client, {}).status_code == 401


@pytest.mark.parametrize("text", ["short", "x" * 301, ""])
def test_the_words_must_be_a_sensible_length(seeded_client, log_in, text):
    finished_job(seeded_client, log_in)

    assert vouch(seeded_client, log_in(LINDIWE), text=text).status_code == 422


def test_contact_details_are_hidden_in_a_vouch(seeded_client, seeded_session, log_in):
    finished_job(seeded_client, log_in)

    response = vouch(seeded_client, log_in(LINDIWE), text="Great plumber, call him on 082 123 4567")

    assert "082 123 4567" not in response.text
    assert "contact hidden" in response.text


def test_illegal_requests_are_refused_in_a_vouch(seeded_client, seeded_session, log_in):
    finished_job(seeded_client, log_in)

    response = vouch(seeded_client, log_in(LINDIWE), text="He can bypass my prepaid meter too")

    assert response.status_code == 422
    assert response.json()["error"] == "prohibited_request"
    assert list(seeded_session.exec(select(CustomerVouch))) == []


def test_a_provider_that_does_not_exist_is_a_404(seeded_client, log_in):
    assert vouch(seeded_client, log_in(LINDIWE), "prov_nope").status_code == 404


def test_vouches_are_listed_newest_first_without_the_writer(seeded_client, log_in):
    finished_job(seeded_client, log_in)
    vouch(seeded_client, log_in(LINDIWE), text="Fixed my tap quickly and cleaned up after.")

    listed = seeded_client.get("/api/providers/prov_001/vouches", headers=log_in(OTHER_CUSTOMER))

    assert listed.status_code == 200
    assert [item["text"] for item in listed.json()] == [GOOD_WORDS]
    assert "cust_001" not in listed.text and "Lindiwe" not in listed.text
    assert seeded_client.get("/api/providers/prov_001/vouches").status_code == 401


def test_vouches_appear_on_the_work_record_without_a_name(seeded_client, seeded_session, log_in):
    finished_job(seeded_client, log_in)
    vouch(seeded_client, log_in(LINDIWE))
    thabo = log_in(THABO)

    export = seeded_client.post("/api/record/export", json={"mode": "arpl"}, headers=thabo)
    page = seeded_client.get("/record/prov_001")

    assert export.status_code == 200
    assert GOOD_WORDS in page.text
    assert "Braamfontein" in page.text
    assert "Lindiwe" not in page.text
    assert not PHONE_PATTERN.search(page.text)
