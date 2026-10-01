"""A customer deleting a job from their list: posted (no quotes) or cancelled jobs only."""

import pytest

from fixa_api.models import Job, Payment

LINDIWE = "082 000 0001"
OTHER_CUSTOMER = "082 000 0002"
PLUMBER = "071 000 0001"
QUOTE_TIME = "2026-10-01T10:00:00+02:00"


def post_job(client, headers, trade="groundskeeping") -> str:
    body = {
        "description": "I need my trees trimmed",
        "lang": "en",
        "trade": trade,
        "urgency": "normal",
        "size": "medium",
        "suburb": "Braamfontein",
    }
    return client.post("/api/jobs", json=body, headers=headers).json()["id"]


def list_my_job_ids(client, headers) -> set[str]:
    return {job["id"] for job in client.get("/api/jobs", headers=headers).json()}


@pytest.fixture
def lindiwe(log_in):
    return log_in(LINDIWE)


def test_a_posted_job_is_deleted_and_taken_off_the_feed(seeded_client, seeded_session, lindiwe):
    job_id = post_job(seeded_client, lindiwe)
    assert seeded_client.delete(f"/api/jobs/{job_id}", headers=lindiwe).status_code == 204
    assert job_id not in list_my_job_ids(seeded_client, lindiwe)
    job = seeded_session.get(Job, job_id)
    assert job.state == "cancelled"  # no provider can still quote on it
    assert job.deleted_at is not None


def test_a_cancelled_job_can_be_deleted(seeded_client, lindiwe):
    job_id = post_job(seeded_client, lindiwe)
    seeded_client.post(f"/api/jobs/{job_id}/cancel", headers=lindiwe)
    assert seeded_client.delete(f"/api/jobs/{job_id}", headers=lindiwe).status_code == 204
    assert job_id not in list_my_job_ids(seeded_client, lindiwe)


def test_a_job_with_quotes_must_be_cancelled_first(seeded_client, lindiwe, log_in):
    job_id = post_job(seeded_client, lindiwe, trade="plumbing")
    quote = seeded_client.post(
        f"/api/jobs/{job_id}/quotes",
        json={"amount_rands": 300, "when": QUOTE_TIME},
        headers=log_in(PLUMBER),
    )
    assert quote.status_code == 201
    response = seeded_client.delete(f"/api/jobs/{job_id}", headers=lindiwe)
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "job_in_use"
    assert job_id in list_my_job_ids(seeded_client, lindiwe)


def test_a_job_with_a_refund_waiting_stays(seeded_client, seeded_session, lindiwe):
    job_id = post_job(seeded_client, lindiwe)
    seeded_client.post(f"/api/jobs/{job_id}/cancel", headers=lindiwe)
    seeded_session.add(
        Payment(
            id="pay_waiting",
            job_id=job_id,
            kind="deposit",
            amount_rands=150,
            state="paid",
            gateway="payfast",
            refund_state="refund_owed",
            created_at=seeded_session.get(Job, job_id).created_at,
        )
    )
    seeded_session.commit()
    response = seeded_client.delete(f"/api/jobs/{job_id}", headers=lindiwe)
    assert response.json()["detail"]["error"] == "refund_pending"


def test_only_the_jobs_customer_can_delete_it(seeded_client, lindiwe, log_in):
    job_id = post_job(seeded_client, lindiwe)
    assert (
        seeded_client.delete(f"/api/jobs/{job_id}", headers=log_in(OTHER_CUSTOMER)).status_code
        == 404
    )
    assert seeded_client.delete(f"/api/jobs/{job_id}", headers=log_in(PLUMBER)).status_code == 403


def test_deleting_twice_says_not_found(seeded_client, lindiwe):
    job_id = post_job(seeded_client, lindiwe)
    seeded_client.delete(f"/api/jobs/{job_id}", headers=lindiwe)
    assert seeded_client.delete(f"/api/jobs/{job_id}", headers=lindiwe).status_code == 404
