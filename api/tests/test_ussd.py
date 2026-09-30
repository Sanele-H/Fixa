"""The USSD menu a customer on a feature phone uses to confirm an off-app job."""

import datetime as dt

import pytest

from fixa_api.main import app
from fixa_api.models import OffAppConfirmation, OffAppJob
from fixa_api.sms import OutboxSender, get_sms_sender

THABO = "071 000 0001"  # prov_001, English
SIPHO = "071 000 0002"  # prov_002, isiZulu
NOSIPHO = "071 000 0003"  # prov_003
CUSTOMER_PHONE = "083 555 0001"  # nobody in the database
WORK_DATE = (dt.datetime.now(dt.UTC).date() - dt.timedelta(days=30)).isoformat()


@pytest.fixture(autouse=True)
def outbox():
    box = OutboxSender()
    app.dependency_overrides[get_sms_sender] = lambda: box
    yield box
    app.dependency_overrides.pop(get_sms_sender, None)


def log_job(client, headers, phone=CUSTOMER_PHONE, task="Replace geyser valve"):
    body = {
        "customer_phone": phone,
        "trade_task": task,
        "date": WORK_DATE,
        "suburb": "Soweto",
        "amount_rands": 380,
    }
    response = client.post("/api/off-app-jobs", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def dial(client, text="", phone="+27835550001", **query):
    response = client.post(
        "/api/ussd",
        data={"sessionId": "s1", "serviceCode": "*384#", "phoneNumber": phone, "text": text},
        params=query,
    )
    assert response.status_code == 200
    return response.text


def state_of(session, job_id):
    session.expire_all()
    job = session.get(OffAppJob, job_id)
    return job.state, job.confirmed_via, job.reference_agreed


def test_nothing_waiting_ends_the_session(seeded_client):
    assert dial(seeded_client) == "END No job is waiting for your confirmation."


def test_the_first_screen_asks_about_the_job(seeded_client, log_in):
    log_job(seeded_client, log_in(THABO))

    screen = dial(seeded_client)

    assert screen.startswith("CON Fixa: Thabo says they did Replace geyser valve for you in Soweto")
    assert WORK_DATE in screen
    assert "1. Yes, that is right" in screen and "2. No" in screen


def test_yes_then_yes_confirms_with_a_reference(seeded_client, seeded_session, log_in):
    job_id = log_job(seeded_client, log_in(THABO))

    assert dial(seeded_client, "1").startswith("CON May we list you as a reference for Thabo?")
    assert dial(seeded_client, "1*1") == "END Thank you. The job is confirmed."
    assert state_of(seeded_session, job_id) == ("confirmed", "ussd", True)


def test_yes_then_no_confirms_without_a_reference(seeded_client, seeded_session, log_in):
    job_id = log_job(seeded_client, log_in(THABO))

    dial(seeded_client, "1*2")

    assert state_of(seeded_session, job_id) == ("confirmed", "ussd", False)


def test_no_declines_the_job(seeded_client, seeded_session, log_in):
    job_id = log_job(seeded_client, log_in(THABO))

    assert dial(seeded_client, "2") == "END Thank you. We marked that job as not done."
    assert state_of(seeded_session, job_id)[0] == "declined"


@pytest.mark.parametrize("typed", ["5", "0", "abc", "1*7", "1*x"])
def test_an_invalid_choice_ends_the_session_and_changes_nothing(
    seeded_client, seeded_session, log_in, typed
):
    job_id = log_job(seeded_client, log_in(THABO))

    assert dial(seeded_client, typed).startswith("END That was not a valid choice")
    assert state_of(seeded_session, job_id)[0] == "awaiting_sms_reply"


def test_with_several_jobs_waiting_the_customer_picks_one(seeded_client, seeded_session, log_in):
    first = log_job(seeded_client, log_in(THABO), task="Replace geyser valve")
    second = log_job(seeded_client, log_in(NOSIPHO), task="Unblock drain")

    menu = dial(seeded_client)
    assert menu.startswith("CON Fixa: which job?")
    assert "1. Thabo: Replace geyser valve" in menu
    assert "2. Nosipho: Unblock drain" in menu
    # each job is asked in its own language: Nosipho's jobs are in isiXhosa
    assert dial(seeded_client, "2").startswith("CON Fixa: U-Nosipho uthi wenze Unblock drain")
    assert dial(seeded_client, "2*1*1") == "END Enkosi. Umsebenzi uqinisekisiwe."

    assert state_of(seeded_session, second)[0] == "confirmed"
    assert state_of(seeded_session, first)[0] == "awaiting_sms_reply"


def test_a_job_choice_out_of_range_is_invalid(seeded_client, log_in):
    log_job(seeded_client, log_in(THABO))
    log_job(seeded_client, log_in(NOSIPHO), task="Unblock drain")

    assert dial(seeded_client, "3").startswith("END That was not a valid choice")


def test_the_menu_is_in_the_customers_language(seeded_client, log_in):
    log_job(seeded_client, log_in(SIPHO))  # the customer is unknown, so Sipho's isiZulu is used

    assert "uthi wenze" in dial(seeded_client)
    assert dial(seeded_client, "1*1").startswith("END Siyabonga")


def test_another_number_sees_nothing(seeded_client, log_in):
    log_job(seeded_client, log_in(THABO))

    assert dial(seeded_client, phone="+27835559999").startswith("END No job is waiting")


def test_an_expired_request_is_not_offered(seeded_client, seeded_session, log_in):
    job_id = log_job(seeded_client, log_in(THABO))
    confirmation = seeded_session.get(OffAppConfirmation, job_id)
    confirmation.expires_at = dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1)
    seeded_session.add(confirmation)
    seeded_session.commit()

    assert dial(seeded_client).startswith("END No job is waiting")


def test_a_job_confirmed_by_ussd_counts_as_evidence(seeded_client, log_in):
    thabo = log_in(THABO)
    path = "/api/providers/prov_001"
    before = seeded_client.get(path, headers=thabo).json()["evidence"]["off_app_confirmed"]
    log_job(seeded_client, thabo)

    dial(seeded_client, "1*1")

    assert (
        seeded_client.get(path, headers=thabo).json()["evidence"]["off_app_confirmed"] == before + 1
    )


def test_the_rules_against_fakes_apply_to_ussd_too(seeded_client, seeded_session, log_in):
    first = log_job(seeded_client, log_in(THABO), phone="071 000 0002")  # Thabo logs for Sipho
    second = log_job(seeded_client, log_in(SIPHO), phone="071 000 0001")  # Sipho logs for Thabo
    dial(seeded_client, "1*1", phone="+27710000002")  # Sipho confirms Thabo's job
    dial(seeded_client, "1*1", phone="+27710000001")  # Thabo confirms Sipho's job

    # two providers confirming each other: both jobs wait for the team instead of counting
    assert state_of(seeded_session, first)[0] == "flagged"
    assert state_of(seeded_session, second)[0] == "flagged"


def test_the_callback_needs_its_secret_when_one_is_set(
    seeded_client, seeded_session, log_in, monkeypatch
):
    monkeypatch.setenv("SMS_WEBHOOK_SECRET", "s3cret")
    job_id = log_job(seeded_client, log_in(THABO))
    body = {"phoneNumber": "+27835550001", "text": "1*1"}

    assert seeded_client.post("/api/ussd", data=body).status_code == 403
    assert seeded_client.post("/api/ussd", data=body, params={"secret": "nope"}).status_code == 403
    assert state_of(seeded_session, job_id)[0] == "awaiting_sms_reply"
    assert (
        seeded_client.post("/api/ussd", data=body, params={"secret": "s3cret"}).status_code == 200
    )
    assert state_of(seeded_session, job_id)[0] == "confirmed"


def test_the_answer_is_plain_text(seeded_client):
    response = seeded_client.post("/api/ussd", data={"phoneNumber": "+27835550001", "text": ""})

    assert response.headers["content-type"].startswith("text/plain")
