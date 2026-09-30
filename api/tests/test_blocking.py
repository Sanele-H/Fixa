"""Illegal-request refusals: nothing flagged goes out, and repeat attempts restrict the account."""

import datetime as dt

import pytest
from sqlmodel import select

from fixa_api.blocking import BLOCK_WINDOW, MAX_BLOCKS
from fixa_api.main import app
from fixa_api.models import AccountRestriction, BlockLog, Job, Message, OffAppJob, Quote
from fixa_api.sms import OutboxSender, get_sms_sender
from lang import refusal_message

LINDIWE = "082 000 0001"  # cust_001, English
OTHER_CUSTOMER = "082 000 0002"
THABO = "071 000 0001"  # prov_001, English
SIPHO = "071 000 0002"  # prov_002, isiZulu
QUOTE_TIME = "2026-10-01T10:00:00+02:00"

ILLEGAL = "can you bypass my prepaid meter"
FINE = "my prepaid meter isn't accepting my token"


@pytest.fixture
def lindiwe(log_in):
    return log_in(LINDIWE)


def post_job(client, headers, description):
    body = {
        "description": description,
        "lang": "en",
        "trade": "plumbing",
        "urgency": "normal",
        "size": "small",
        "suburb": "Braamfontein",
    }
    return client.post("/api/jobs", json=body, headers=headers)


def quoted_job(client, log_in, provider_phone=THABO):
    """A job with an open quote from the provider. Returns (job_id, customer, provider)."""
    customer, provider = log_in(LINDIWE), log_in(provider_phone)
    job_id = post_job(client, customer, "My plug point is broken").json()["id"]
    body = {"amount_rands": 300, "when": QUOTE_TIME}
    client.post(f"/api/jobs/{job_id}/quotes", json=body, headers=provider)
    return job_id, customer, provider


def assert_refused(response, category="meter_tampering", lang="en"):
    assert response.status_code == 422
    assert response.json() == {
        "error": "prohibited_request",
        "category": category,
        "message": refusal_message(category, lang),
    }


# --- every place text is published ----------------------------------------------------------


def test_an_illegal_job_post_is_refused_and_never_created(seeded_client, seeded_session, lindiwe):
    jobs_before = len(list(seeded_session.exec(select(Job))))

    response = post_job(seeded_client, lindiwe, ILLEGAL)

    assert_refused(response)
    assert len(list(seeded_session.exec(select(Job)))) == jobs_before


def test_an_illegal_description_is_refused_before_posting_too(seeded_client, lindiwe):
    response = seeded_client.post(
        "/api/jobs/understand", json={"text": ILLEGAL, "lang": "en"}, headers=lindiwe
    )

    assert_refused(response)


def test_an_illegal_quote_note_is_refused_and_no_quote_is_saved(
    seeded_client, seeded_session, log_in
):
    customer = log_in(LINDIWE)
    job_id = post_job(seeded_client, customer, "My plug point is broken").json()["id"]

    response = seeded_client.post(
        f"/api/jobs/{job_id}/quotes",
        json={"amount_rands": 300, "when": QUOTE_TIME, "message": "R300, I sell cheap units too"},
        headers=log_in(THABO),
    )

    assert_refused(response, "illegal_vouchers")
    assert [q for q in seeded_session.exec(select(Quote)) if q.job_id == job_id] == []


@pytest.mark.parametrize("sender", ["customer", "provider"])
def test_an_illegal_chat_message_is_never_stored_or_delivered(
    seeded_client, seeded_session, log_in, sender
):
    job_id, customer, provider = quoted_job(seeded_client, log_in)
    headers = customer if sender == "customer" else provider
    extra = {"provider_id": "prov_001"} if sender == "customer" else {}

    response = seeded_client.post(
        f"/api/jobs/{job_id}/messages",
        json={"text": "I can fix your meter", **extra},
        headers=headers,
    )

    assert_refused(response)
    assert list(seeded_session.exec(select(Message))) == []
    assert seeded_client.get(f"/api/jobs/{job_id}/messages", headers=customer).json() == []


def test_a_message_is_refused_after_the_job_is_confirmed_too(seeded_client, log_in):
    job_id, customer, provider = quoted_job(seeded_client, log_in)
    quote_id = seeded_client.get(f"/api/jobs/{job_id}/quotes", headers=customer).json()[0]["id"]
    seeded_client.post(f"/api/quotes/{quote_id}/accept", headers=customer)
    seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=provider)

    response = seeded_client.post(
        f"/api/jobs/{job_id}/messages", json={"text": "selling ghost vouchers"}, headers=provider
    )

    assert_refused(response, "illegal_vouchers")


def test_an_illegal_off_app_task_is_refused_and_no_text_is_sent(
    seeded_client, seeded_session, log_in
):
    outbox = OutboxSender()
    app.dependency_overrides[get_sms_sender] = lambda: outbox
    try:
        response = seeded_client.post(
            "/api/off-app-jobs",
            json={
                "customer_phone": "083 555 0001",
                "trade_task": "Bypassed the meter",
                "date": "2026-08-01",
                "suburb": "Soweto",
            },
            headers=log_in(THABO),
        )
        illegal = seeded_client.post(
            "/api/off-app-jobs",
            json={
                "customer_phone": "083 555 0001",
                "trade_task": "bypass the meter",
                "date": "2026-08-01",
                "suburb": "Soweto",
            },
            headers=log_in(THABO),
        )
    finally:
        app.dependency_overrides.pop(get_sms_sender, None)

    assert response.status_code == 201  # past tense: "Bypassed the meter" is not a request or offer
    assert_refused(illegal)
    assert len(outbox.sent) == 1
    assert (
        len(
            [
                j
                for j in seeded_session.exec(select(OffAppJob))
                if j.id.startswith("offapp_") and len(j.id) == 15
            ]
        )
        == 1
    )


# --- language and the legal route -----------------------------------------------------------


def test_the_refusal_is_in_the_senders_language_with_the_legal_route(seeded_client, log_in):
    job_id, customer, provider = quoted_job(seeded_client, log_in, SIPHO)

    response = seeded_client.post(
        f"/api/jobs/{job_id}/messages", json={"text": "I sell cheap units"}, headers=provider
    )

    assert_refused(response, "illegal_vouchers", "zu")
    assert "Eskom" in response.json()["message"]


def test_genuine_meter_and_transformer_problems_go_through(seeded_client, lindiwe):
    for text in (FINE, "the transformer on our street is sparking, who do I call?"):
        assert post_job(seeded_client, lindiwe, text).status_code == 201


# --- the block log and account restriction --------------------------------------------------


def test_a_refused_attempt_is_logged_for_review(seeded_client, seeded_session, lindiwe):
    post_job(seeded_client, lindiwe, ILLEGAL)

    (entry,) = seeded_session.exec(select(BlockLog))

    assert (entry.user_id, entry.kind, entry.category) == (
        "cust_001",
        "job_post",
        "meter_tampering",
    )
    assert entry.text == ILLEGAL


def test_a_logged_text_is_cut_to_500_characters(seeded_client, seeded_session, lindiwe):
    post_job(seeded_client, lindiwe, ILLEGAL + " " + "x" * 800)

    (entry,) = seeded_session.exec(select(BlockLog))

    assert len(entry.text) == 500


def test_three_refusals_restrict_the_account(seeded_client, seeded_session, lindiwe):
    for _ in range(MAX_BLOCKS):
        assert post_job(seeded_client, lindiwe, ILLEGAL).status_code == 422

    assert seeded_session.get(AccountRestriction, "cust_001") is not None
    blocked = post_job(seeded_client, lindiwe, "My plug point is broken")  # even an innocent post
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["error"] == "account_restricted"


def test_a_restricted_account_cannot_quote_or_message_either(seeded_client, seeded_session, log_in):
    job_id, customer, provider = quoted_job(seeded_client, log_in)
    for _ in range(MAX_BLOCKS):
        seeded_client.post(f"/api/jobs/{job_id}/messages", json={"text": ILLEGAL}, headers=provider)

    message = seeded_client.post(
        f"/api/jobs/{job_id}/messages", json={"text": "hello"}, headers=provider
    )
    other_job = post_job(seeded_client, customer, "My plug point is broken").json()["id"]
    quote = seeded_client.post(
        f"/api/jobs/{other_job}/quotes",
        json={"amount_rands": 1, "when": QUOTE_TIME},
        headers=provider,
    )

    assert (message.status_code, quote.status_code) == (403, 403)


def test_a_restricted_account_can_still_read(seeded_client, lindiwe):
    for _ in range(MAX_BLOCKS):
        post_job(seeded_client, lindiwe, ILLEGAL)

    assert seeded_client.get("/api/me", headers=lindiwe).status_code == 200
    assert seeded_client.get("/api/jobs", headers=lindiwe).status_code == 200


def test_the_restriction_message_is_in_the_persons_language(seeded_client, log_in):
    job_id, customer, provider = quoted_job(seeded_client, log_in, SIPHO)
    for _ in range(MAX_BLOCKS):
        seeded_client.post(f"/api/jobs/{job_id}/messages", json={"text": ILLEGAL}, headers=provider)

    blocked = seeded_client.post(
        f"/api/jobs/{job_id}/messages", json={"text": "hi"}, headers=provider
    )

    assert "akhawunti" in blocked.json()["detail"]["message"]  # isiZulu


def test_two_refusals_do_not_restrict(seeded_client, seeded_session, lindiwe):
    for _ in range(MAX_BLOCKS - 1):
        post_job(seeded_client, lindiwe, ILLEGAL)

    assert seeded_session.get(AccountRestriction, "cust_001") is None
    assert post_job(seeded_client, lindiwe, "My plug point is broken").status_code == 201


def test_old_refusals_stop_counting(seeded_client, seeded_session, lindiwe):
    for _ in range(MAX_BLOCKS - 1):
        post_job(seeded_client, lindiwe, ILLEGAL)
    for entry in seeded_session.exec(select(BlockLog)):
        entry.at = dt.datetime.now(dt.UTC) - BLOCK_WINDOW - dt.timedelta(days=1)
        seeded_session.add(entry)
    seeded_session.commit()

    post_job(seeded_client, lindiwe, ILLEGAL)

    assert seeded_session.get(AccountRestriction, "cust_001") is None


def test_one_persons_refusals_never_restrict_someone_else(
    seeded_client, seeded_session, lindiwe, log_in
):
    for _ in range(MAX_BLOCKS):
        post_job(seeded_client, lindiwe, ILLEGAL)

    assert (
        post_job(seeded_client, log_in(OTHER_CUSTOMER), "My plug point is broken").status_code
        == 201
    )


def test_lifting_a_restriction_is_deleting_its_row(seeded_client, seeded_session, lindiwe):
    for _ in range(MAX_BLOCKS):
        post_job(seeded_client, lindiwe, ILLEGAL)
    seeded_session.delete(seeded_session.get(AccountRestriction, "cust_001"))
    for entry in seeded_session.exec(select(BlockLog)):
        seeded_session.delete(entry)
    seeded_session.commit()

    assert post_job(seeded_client, lindiwe, "My plug point is broken").status_code == 201
