"""Off-app jobs: logging one, the customer's SMS reply, and the rules against fakes."""

import datetime as dt

import pytest
from sqlmodel import select

from fixa_api import off_app
from fixa_api.main import app
from fixa_api.models import OffAppConfirmation, OffAppJob
from fixa_api.off_app import parse_reply
from fixa_api.sms import OutboxSender, get_sms_sender

THABO = "071 000 0001"  # prov_001, English
SIPHO = "071 000 0002"  # prov_002, isiZulu
NOSIPHO = "071 000 0003"  # prov_003
CUSTOMER_PHONE = "083 555 0001"  # nobody in the database
LINDIWE = "082 000 0001"  # cust_001, English
TODAY = dt.datetime.now(dt.UTC).date()
LAST_MONTH = (TODAY - dt.timedelta(days=30)).isoformat()


@pytest.fixture
def outbox():
    box = OutboxSender()
    app.dependency_overrides[get_sms_sender] = lambda: box
    yield box
    app.dependency_overrides.pop(get_sms_sender, None)


def log_job(client, headers, **changes):
    body = {
        "customer_phone": CUSTOMER_PHONE,
        "trade_task": "Replace geyser valve",
        "date": LAST_MONTH,
        "suburb": "Soweto",
        "amount_rands": 380,
    } | changes
    return client.post("/api/off-app-jobs", json=body, headers=headers)


def reply(client, from_phone, text, **query):
    return client.post("/api/sms/inbound", data={"from": from_phone, "text": text}, params=query)


def code_for(session, job_id: str) -> str:
    return session.get(OffAppConfirmation, job_id).code


@pytest.fixture
def thabo(log_in):
    return log_in(THABO)


@pytest.fixture
def logged(seeded_client, seeded_session, thabo, outbox):
    """A job Thabo logged, awaiting the customer's reply. Returns (job id, code)."""
    job_id = log_job(seeded_client, thabo).json()["id"]
    return job_id, code_for(seeded_session, job_id)


# --- logging a job --------------------------------------------------------------------------


def test_logging_a_job_texts_the_customer_and_waits_for_the_reply(seeded_client, thabo, outbox):
    response = log_job(seeded_client, thabo)

    assert response.status_code == 201
    job = response.json()
    assert set(job) == {"id", "state", "trade_task", "date", "suburb", "amount_rands"}
    assert job["state"] == "awaiting_sms_reply"
    ((number, text),) = outbox.sent
    assert number == "+27835550001"
    assert "Thabo" in text and "YES" in text and "REF" in text


def test_the_customers_number_is_never_sent_back_to_the_provider(seeded_client, thabo, outbox):
    text = log_job(seeded_client, thabo).text

    assert "555" not in text


def test_the_text_is_in_the_customers_language_when_we_know_them(seeded_client, log_in, outbox):
    log_job(seeded_client, log_in(THABO), customer_phone=LINDIWE)  # Lindiwe reads English
    log_job(
        seeded_client, log_in(SIPHO), customer_phone="083 555 0002"
    )  # unknown: provider's language

    (_, english), (_, zulu) = outbox.sent
    assert "Reply YES" in english
    assert "Phendula YEBO" in zulu


def test_a_pending_job_does_not_count_as_evidence_yet(seeded_client, seeded_session, thabo, outbox):
    before = seeded_client.get("/api/providers/prov_001", headers=thabo).json()["evidence"]
    log_job(seeded_client, thabo)

    after = seeded_client.get("/api/providers/prov_001", headers=thabo).json()["evidence"]

    assert after == before


def test_contact_details_in_the_task_are_hidden_from_the_customers_text(
    seeded_client, thabo, outbox
):
    job = log_job(seeded_client, thabo, trade_task="Fix geyser, call 082 123 4567").json()

    assert "082 123 4567" not in job["trade_task"]
    assert "082 123 4567" not in outbox.sent[0][1]


def test_the_job_is_saved_with_a_trade_and_a_formatted_number(
    seeded_client, seeded_session, thabo, outbox
):
    job_id = log_job(seeded_client, thabo, customer_phone="0835550001").json()["id"]

    saved = seeded_session.get(OffAppJob, job_id)

    assert (saved.trade, saved.customer_phone) == ("plumbing", CUSTOMER_PHONE)


def test_only_a_provider_can_log_a_job(seeded_client, log_in):
    assert log_job(seeded_client, log_in(LINDIWE)).status_code == 403
    assert log_job(seeded_client, {}).status_code == 401


@pytest.mark.parametrize(
    "changes",
    [
        {"trade_task": ""},
        {"suburb": ""},
        {"amount_rands": 0},
        {"date": "not a date"},
        {"customer_phone": "12345"},
    ],
)
def test_a_bad_job_is_refused(seeded_client, thabo, outbox, changes):
    assert log_job(seeded_client, thabo, **changes).status_code == 422
    assert outbox.sent == []


# --- the rules against fakes ----------------------------------------------------------------


def error_of(response) -> str:
    return response.json()["detail"]["error"]


def test_a_provider_cannot_confirm_their_own_job(seeded_client, thabo, outbox):
    for own_number in (THABO, "+27 71 000 0001", "0710000001"):
        response = log_job(seeded_client, thabo, customer_phone=own_number)

        assert response.status_code == 422
        assert error_of(response) == "self_confirmation"
    assert outbox.sent == []


def test_the_same_customer_and_date_cannot_be_logged_twice(seeded_client, thabo, outbox, logged):
    again = log_job(seeded_client, thabo, customer_phone="0835550001")

    assert again.status_code == 409
    assert error_of(again) == "duplicate"


def test_a_repeat_customer_needs_a_different_date(seeded_client, thabo, outbox, logged):
    other_date = (TODAY - dt.timedelta(days=60)).isoformat()

    assert log_job(seeded_client, thabo, date=other_date).status_code == 201


def test_a_declined_job_can_be_logged_again(seeded_client, seeded_session, thabo, outbox, logged):
    job_id, code = logged
    reply(seeded_client, CUSTOMER_PHONE, f"NO {code}")

    assert log_job(seeded_client, thabo).status_code == 201


@pytest.mark.parametrize("days", [-1, 3700])
def test_the_date_must_be_a_past_date_within_ten_years(seeded_client, thabo, outbox, days):
    date = (TODAY - dt.timedelta(days=days)).isoformat()

    response = log_job(seeded_client, thabo, date=date)

    assert response.status_code == 422
    assert error_of(response) == "invalid_date"


def test_a_provider_can_log_only_ten_jobs_a_month(seeded_client, thabo, outbox):
    for index in range(off_app.MAX_LOGS_PER_MONTH):
        phone = f"083 555 {index:04d}"
        assert log_job(seeded_client, thabo, customer_phone=phone).status_code == 201

    over = log_job(seeded_client, thabo, customer_phone="083 555 9999")

    assert over.status_code == 429
    assert error_of(over) == "monthly_cap"


def test_one_phone_gets_only_three_requests_a_day_from_anyone(seeded_client, log_in, outbox):
    for index in range(off_app.MAX_REQUESTS_PER_PHONE_PER_DAY):
        provider = log_in(f"071 000 000{index + 1}")
        assert log_job(seeded_client, provider).status_code == 201

    fourth = log_job(seeded_client, log_in("071 000 0004"))

    assert fourth.status_code == 429
    assert error_of(fourth) == "customer_busy"


def test_if_the_text_cannot_be_sent_nothing_is_saved(seeded_client, seeded_session, thabo):
    class Down:
        def send(self, to, message):
            raise RuntimeError("down")

    app.dependency_overrides[get_sms_sender] = lambda: Down()
    try:
        response = log_job(seeded_client, thabo)
    finally:
        app.dependency_overrides.pop(get_sms_sender, None)

    assert response.status_code == 502
    assert error_of(response) == "sms_failed"
    assert list(seeded_session.exec(select(OffAppConfirmation))) == []
    assert (
        len(
            [
                j
                for j in seeded_session.exec(select(OffAppJob))
                if j.id.startswith("offapp_") and len(j.id) == 15
            ]
        )
        == 0
    )


# --- the customer's reply -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "said_yes", "reference"),
    [
        ("YES 123456", True, False),
        ("yes 123456", True, False),
        ("Yes 123456 REF", True, True),
        ("YEBO 123456", True, False),
        ("ewe 123456 ref", True, True),
        ("NO 123456", False, False),
        ("cha 123456", False, False),
        ("HAYI 123456", False, False),
        ("  YES   123456.  ", True, False),
        ("123456 YES", True, False),
    ],
)
def test_replies_are_read_in_three_languages(text, said_yes, reference):
    parsed = parse_reply(text)

    assert (parsed.said_yes, parsed.code, parsed.agrees_to_be_reference) == (
        said_yes,
        "123456",
        reference,
    )


@pytest.mark.parametrize(
    "text",
    [
        "",
        "hello",
        "YES",
        "123456",
        "YES NO 123456",
        "YES 1234",
        "YES 123456 654321",
        "maybe 123456",
    ],
)
def test_anything_else_is_not_understood(text):
    assert parse_reply(text) is None


def state_of(session, job_id: str) -> OffAppJob:
    session.expire_all()
    return session.get(OffAppJob, job_id)


def test_a_yes_with_the_code_confirms_the_job(seeded_client, seeded_session, logged):
    job_id, code = logged

    response = reply(seeded_client, "+27835550001", f"YES {code}")

    assert response.status_code == 200
    job = state_of(seeded_session, job_id)
    assert (job.state, job.confirmed_via, job.reference_agreed) == ("confirmed", "sms", False)


def test_adding_ref_records_that_the_customer_agrees_to_be_a_reference(
    seeded_client, seeded_session, logged
):
    job_id, code = logged

    reply(seeded_client, CUSTOMER_PHONE, f"YES {code} REF")

    assert state_of(seeded_session, job_id).reference_agreed is True


def test_a_no_declines_the_job(seeded_client, seeded_session, logged):
    job_id, code = logged

    reply(seeded_client, CUSTOMER_PHONE, f"NO {code}")

    assert state_of(seeded_session, job_id).state == "declined"


def test_a_confirmed_job_shows_up_as_evidence_on_the_profile(
    seeded_client, seeded_session, thabo, logged, log_in
):
    before = seeded_client.get("/api/providers/prov_001", headers=thabo).json()["evidence"]
    job_id, code = logged

    reply(seeded_client, CUSTOMER_PHONE, f"YES {code}")

    after = seeded_client.get("/api/providers/prov_001", headers=thabo).json()["evidence"]
    assert after["off_app_confirmed"] == before["off_app_confirmed"] + 1


def test_a_reply_from_a_different_number_does_nothing(seeded_client, seeded_session, logged):
    job_id, code = logged

    reply(seeded_client, "083 555 7777", f"YES {code}")

    assert state_of(seeded_session, job_id).state == "awaiting_sms_reply"


def test_a_wrong_code_does_nothing_and_five_wrong_codes_end_the_request(
    seeded_client, seeded_session, logged
):
    job_id, code = logged
    wrong = "000000" if code != "000000" else "111111"

    for _ in range(off_app.MAX_WRONG_CODES - 1):
        reply(seeded_client, CUSTOMER_PHONE, f"YES {wrong}")
    assert state_of(seeded_session, job_id).state == "awaiting_sms_reply"
    reply(seeded_client, CUSTOMER_PHONE, f"YES {wrong}")

    assert state_of(seeded_session, job_id).state == "expired"
    reply(seeded_client, CUSTOMER_PHONE, f"YES {code}")  # too late: the right code no longer works
    assert state_of(seeded_session, job_id).state == "expired"


def test_a_reply_after_a_week_is_too_late(seeded_client, seeded_session, logged):
    job_id, code = logged
    confirmation = seeded_session.get(OffAppConfirmation, job_id)
    confirmation.expires_at = dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1)
    seeded_session.add(confirmation)
    seeded_session.commit()

    reply(seeded_client, CUSTOMER_PHONE, f"YES {code}")

    assert state_of(seeded_session, job_id).state == "expired"


def test_a_code_works_only_once(seeded_client, seeded_session, logged):
    job_id, code = logged
    reply(seeded_client, CUSTOMER_PHONE, f"YES {code}")
    reply(seeded_client, CUSTOMER_PHONE, f"NO {code}")

    assert state_of(seeded_session, job_id).state == "confirmed"


def test_the_webhook_answers_the_same_whatever_happens(seeded_client, logged):
    job_id, code = logged

    answers = [
        reply(seeded_client, CUSTOMER_PHONE, f"YES {code}"),
        reply(seeded_client, CUSTOMER_PHONE, "nonsense"),
        reply(seeded_client, "083 111 2222", "YES 123456"),
    ]

    assert [(a.status_code, a.json()) for a in answers] == [(200, {"status": "ok"})] * 3


def test_the_webhook_needs_its_secret_when_one_is_set(
    seeded_client, seeded_session, logged, monkeypatch
):
    monkeypatch.setenv("SMS_WEBHOOK_SECRET", "s3cret")
    job_id, code = logged

    assert reply(seeded_client, CUSTOMER_PHONE, f"YES {code}").status_code == 403
    assert reply(seeded_client, CUSTOMER_PHONE, f"YES {code}", secret="wrong").status_code == 403
    assert state_of(seeded_session, job_id).state == "awaiting_sms_reply"
    assert reply(seeded_client, CUSTOMER_PHONE, f"YES {code}", secret="s3cret").status_code == 200
    assert state_of(seeded_session, job_id).state == "confirmed"


# --- rings ----------------------------------------------------------------------------------


def log_and_confirm(client, session, headers, phone, date=LAST_MONTH):
    job_id = log_job(client, headers, customer_phone=phone, date=date).json()["id"]
    reply(client, phone, f"YES {code_for(session, job_id)}")
    return state_of(session, job_id)


def test_a_number_that_confirms_for_five_providers_is_flagged(
    seeded_client, seeded_session, log_in, monkeypatch
):
    monkeypatch.setattr(off_app, "MAX_REQUESTS_PER_PHONE_PER_DAY", 99)
    app.dependency_overrides[get_sms_sender] = lambda: OutboxSender()
    try:
        states = [
            log_and_confirm(
                seeded_client, seeded_session, log_in(f"071 000 000{index}"), CUSTOMER_PHONE
            ).state
            for index in range(1, 6)
        ]
    finally:
        app.dependency_overrides.pop(get_sms_sender, None)

    assert states == ["confirmed"] * 4 + ["flagged"]


def test_two_providers_confirming_each_other_are_flagged(
    seeded_client, seeded_session, log_in, outbox
):
    first = log_and_confirm(seeded_client, seeded_session, log_in(THABO), "071 000 0002")
    second = log_and_confirm(seeded_client, seeded_session, log_in(SIPHO), "071 000 0001")

    assert first.state == "confirmed"  # nothing yet says the other way round
    assert second.state == "flagged"


def test_a_provider_confirming_a_stranger_provider_one_way_is_fine(
    seeded_client, seeded_session, log_in, outbox
):
    assert (
        log_and_confirm(seeded_client, seeded_session, log_in(THABO), "071 000 0002").state
        == "confirmed"
    )


def test_flagged_jobs_do_not_count_as_evidence(seeded_client, seeded_session, log_in, outbox):
    thabo = log_in(THABO)

    def confirmed(provider_id: str) -> int:
        profile = seeded_client.get(f"/api/providers/{provider_id}", headers=thabo).json()
        return profile["evidence"]["off_app_confirmed"]

    thabo_before, sipho_before = confirmed("prov_001"), confirmed("prov_002")
    log_and_confirm(seeded_client, seeded_session, thabo, "071 000 0002")
    log_and_confirm(seeded_client, seeded_session, log_in(SIPHO), "071 000 0001")  # the flagged one

    assert confirmed("prov_001") == thabo_before + 1
    assert confirmed("prov_002") == sipho_before
