"""A job's day (check-in, check-out, done or no-show) and the two-week "still working?" check."""

import datetime as dt

import pytest
from sqlmodel import select

from fixa_api.models import Job, JobEvent

LINDIWE = "082 000 0001"  # cust_001
OTHER_CUSTOMER = "082 000 0002"
PLUMBER = "071 000 0001"  # prov_001, has a long history
NEWCOMER = "071 000 0002"  # prov_002, no app jobs yet
OTHER_PLUMBER = "071 000 0003"
TODAY = dt.datetime.now(dt.UTC).date()
QUOTE_TIME = "2026-10-01T10:00:00+02:00"


@pytest.fixture
def lindiwe(log_in):
    return log_in(LINDIWE)


def confirmed_job(client, log_in, provider_phone=PLUMBER) -> str:
    """Lindiwe posts a job, the provider quotes, she accepts and they confirm."""
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
    return job_id


def finish(client, headers, job_id, completed=True):
    return client.post(f"/api/jobs/{job_id}/done", json={"completed": completed}, headers=headers)


def events(session, job_id) -> list[str]:
    session.expire_all()
    rows = session.exec(select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.at))
    return [row.kind for row in rows]


def backdate(session, job_id, days):
    session.expire_all()
    job = session.get(Job, job_id)
    job.finished_on = TODAY - dt.timedelta(days=days)
    session.add(job)
    session.commit()


# --- check-in and check-out -----------------------------------------------------------------


def test_the_provider_checks_in_and_the_job_is_in_progress(seeded_client, seeded_session, log_in):
    job_id = confirmed_job(seeded_client, log_in)

    response = seeded_client.post(f"/api/jobs/{job_id}/check-in", headers=log_in(PLUMBER))

    assert response.status_code == 200
    assert response.json()["state"] == "in_progress"
    assert events(seeded_session, job_id) == ["check_in"]


def test_only_the_jobs_provider_can_check_in(seeded_client, log_in, lindiwe):
    job_id = confirmed_job(seeded_client, log_in)

    assert seeded_client.post(f"/api/jobs/{job_id}/check-in", headers=lindiwe).status_code == 403
    other = seeded_client.post(f"/api/jobs/{job_id}/check-in", headers=log_in(OTHER_PLUMBER))
    assert other.status_code == 404
    assert seeded_client.post(f"/api/jobs/{job_id}/check-in").status_code == 401


def test_checking_in_twice_is_refused(seeded_client, log_in):
    job_id = confirmed_job(seeded_client, log_in)
    provider = log_in(PLUMBER)
    seeded_client.post(f"/api/jobs/{job_id}/check-in", headers=provider)

    assert seeded_client.post(f"/api/jobs/{job_id}/check-in", headers=provider).status_code == 409


def test_check_out_needs_a_check_in_first_and_changes_no_state(
    seeded_client, seeded_session, log_in
):
    job_id = confirmed_job(seeded_client, log_in)
    provider = log_in(PLUMBER)

    assert seeded_client.post(f"/api/jobs/{job_id}/check-out", headers=provider).status_code == 409
    seeded_client.post(f"/api/jobs/{job_id}/check-in", headers=provider)
    response = seeded_client.post(f"/api/jobs/{job_id}/check-out", headers=provider)

    assert response.status_code == 200
    assert response.json()["state"] == "in_progress"  # only the customer can finish the job
    assert events(seeded_session, job_id) == ["check_in", "check_out"]


# --- done and no-show -----------------------------------------------------------------------


def test_the_customer_marks_the_job_done(seeded_client, seeded_session, log_in, lindiwe):
    job_id = confirmed_job(seeded_client, log_in)
    seeded_client.post(f"/api/jobs/{job_id}/check-in", headers=log_in(PLUMBER))

    response = finish(seeded_client, lindiwe, job_id)

    assert response.status_code == 200
    assert response.json()["state"] == "done"
    job = seeded_session.get(Job, job_id)
    assert (job.completed, job.finished_on) == (True, TODAY)
    assert "marked_done" in events(seeded_session, job_id)


def test_done_works_even_if_the_provider_forgot_to_check_in(seeded_client, log_in, lindiwe):
    job_id = confirmed_job(seeded_client, log_in)

    assert finish(seeded_client, lindiwe, job_id).json()["state"] == "done"


def test_the_customer_keeps_seeing_the_details_after_the_job_is_done(
    seeded_client, log_in, lindiwe
):
    job_id = confirmed_job(seeded_client, log_in)

    job = finish(seeded_client, lindiwe, job_id).json()

    assert job["provider_phone"] == PLUMBER


def test_a_finished_job_counts_as_evidence_for_the_provider(seeded_client, log_in, lindiwe):
    provider = log_in(PLUMBER)
    before = seeded_client.get("/api/providers/prov_001", headers=lindiwe).json()["evidence"][
        "jobs"
    ]
    job_id = confirmed_job(seeded_client, log_in)

    finish(seeded_client, lindiwe, job_id)

    after = seeded_client.get("/api/providers/prov_001", headers=provider).json()["evidence"][
        "jobs"
    ]
    assert after == before + 1


def test_a_no_show_ends_the_job_locks_the_details_and_counts_against_the_provider(
    seeded_client, seeded_session, log_in, lindiwe
):
    job_id = confirmed_job(seeded_client, log_in, NEWCOMER)
    assert seeded_client.get("/api/providers/prov_002", headers=lindiwe).json()["is_newcomer"]

    response = finish(seeded_client, lindiwe, job_id, completed=False)

    assert response.json()["state"] == "cancelled"
    assert "provider_phone" not in response.json()
    job = seeded_session.get(Job, job_id)
    assert (job.completed, job.finished_on) == (False, TODAY)
    assert events(seeded_session, job_id) == ["no_show"]
    profile = seeded_client.get("/api/providers/prov_002", headers=lindiwe).json()
    assert profile["is_newcomer"] is False  # a no-show ends the newcomer protection


def test_only_the_customer_can_finish_a_job(seeded_client, log_in):
    job_id = confirmed_job(seeded_client, log_in)

    assert finish(seeded_client, log_in(PLUMBER), job_id).status_code == 403
    assert finish(seeded_client, log_in(OTHER_CUSTOMER), job_id).status_code == 404
    assert finish(seeded_client, {}, job_id).status_code == 401


def test_a_job_can_only_be_finished_once_it_is_confirmed(seeded_client, log_in, lindiwe):
    body = {
        "description": "My tap drips",
        "lang": "en",
        "trade": "plumbing",
        "urgency": "normal",
        "size": "small",
        "suburb": "Braamfontein",
    }
    posted = seeded_client.post("/api/jobs", json=body, headers=lindiwe).json()["id"]
    done = confirmed_job(seeded_client, log_in)
    finish(seeded_client, lindiwe, done)

    assert finish(seeded_client, lindiwe, posted).status_code == 409
    assert finish(seeded_client, lindiwe, done).status_code == 409


# --- "still working?" -----------------------------------------------------------------------


def test_it_is_not_asked_right_after_the_job(seeded_client, seeded_session, log_in, lindiwe):
    job_id = confirmed_job(seeded_client, log_in)
    finish(seeded_client, lindiwe, job_id)

    assert seeded_client.get("/api/follow-ups", headers=lindiwe).json() == []
    early = seeded_client.post(
        f"/api/jobs/{job_id}/still-working", json={"still_working": True}, headers=lindiwe
    )
    assert early.status_code == 409


def test_it_is_asked_two_weeks_after_the_job(seeded_client, seeded_session, log_in, lindiwe):
    job_id = confirmed_job(seeded_client, log_in)
    finish(seeded_client, lindiwe, job_id)

    backdate(seeded_session, job_id, 13)
    assert seeded_client.get("/api/follow-ups", headers=lindiwe).json() == []
    backdate(seeded_session, job_id, 14)
    due = seeded_client.get("/api/follow-ups", headers=lindiwe).json()

    assert [job["id"] for job in due] == [job_id]


@pytest.mark.parametrize("answer", [True, False])
def test_the_answer_is_saved_and_the_job_is_followed_up(
    seeded_client, seeded_session, log_in, lindiwe, answer
):
    job_id = confirmed_job(seeded_client, log_in)
    finish(seeded_client, lindiwe, job_id)
    backdate(seeded_session, job_id, 15)

    response = seeded_client.post(
        f"/api/jobs/{job_id}/still-working", json={"still_working": answer}, headers=lindiwe
    )

    assert response.status_code == 200
    assert response.json()["state"] == "followed_up"
    seeded_session.expire_all()
    assert seeded_session.get(Job, job_id).still_working is answer
    assert events(seeded_session, job_id)[-1] == "still_working_answer"
    assert seeded_client.get("/api/follow-ups", headers=lindiwe).json() == []


def test_the_question_can_be_answered_only_once(seeded_client, seeded_session, log_in, lindiwe):
    job_id = confirmed_job(seeded_client, log_in)
    finish(seeded_client, lindiwe, job_id)
    backdate(seeded_session, job_id, 15)
    url = f"/api/jobs/{job_id}/still-working"
    seeded_client.post(url, json={"still_working": True}, headers=lindiwe)

    assert (
        seeded_client.post(url, json={"still_working": False}, headers=lindiwe).status_code == 409
    )


def test_a_job_that_is_not_finished_cannot_be_followed_up(seeded_client, log_in, lindiwe):
    job_id = confirmed_job(seeded_client, log_in)

    response = seeded_client.post(
        f"/api/jobs/{job_id}/still-working", json={"still_working": True}, headers=lindiwe
    )

    assert response.status_code == 409


def test_follow_ups_are_private_to_the_customer(seeded_client, seeded_session, log_in, lindiwe):
    job_id = confirmed_job(seeded_client, log_in)
    finish(seeded_client, lindiwe, job_id)
    backdate(seeded_session, job_id, 15)
    url = f"/api/jobs/{job_id}/still-working"

    others = seeded_client.get("/api/follow-ups", headers=log_in(OTHER_CUSTOMER)).json()
    assert job_id not in [job["id"] for job in others]  # only their own jobs, never Lindiwe's
    assert seeded_client.get("/api/follow-ups", headers=log_in(PLUMBER)).status_code == 403
    assert (
        seeded_client.post(url, json={"still_working": True}, headers=log_in(PLUMBER)).status_code
        == 403
    )
    other = seeded_client.post(url, json={"still_working": True}, headers=log_in(OTHER_CUSTOMER))
    assert other.status_code == 404
    assert seeded_client.get("/api/follow-ups").status_code == 401
