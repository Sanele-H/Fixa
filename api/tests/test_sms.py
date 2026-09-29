"""SMS: the Africa's Talking client, and the messages sent when a job's details unlock."""

import json

import httpx
import pytest

from fixa_api.main import app
from fixa_api.sms import (
    AFRICASTALKING_LIVE_URL,
    AFRICASTALKING_SANDBOX_URL,
    AfricasTalkingSender,
    OutboxSender,
    SmsResult,
    get_sms_sender,
    mask,
    send_safely,
    to_international,
)

LINDIWE = "082 000 0001"  # cust_001, English
SIPHO = "071 000 0002"  # prov_002, isiZulu
THABO = "071 000 0001"  # prov_001, English
QUOTE_TIME = "2026-10-01T10:00:00+02:00"


# --- numbers --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phone", ["082 000 0001", "0820000001", "+27 82 000 0001", "27820000001", "082-000-0001"]
)
def test_numbers_are_written_the_way_africas_talking_wants(phone):
    assert to_international(phone) == "+27820000001"


def test_a_masked_number_is_not_usable():
    assert mask("+27820000001") == "***001"


# --- the Africa's Talking client ------------------------------------------------------------


def africastalking_client(handler, username="sandbox"):
    transport = httpx.MockTransport(handler)
    return AfricasTalkingSender(username, "secret-key", httpx.Client(transport=transport))


def reply(status_code=101, status="Success", message_id="ATXid_1"):
    body = {
        "SMSMessageData": {
            "Message": "Sent to 1/1",
            "Recipients": [
                {
                    "statusCode": status_code,
                    "number": "+27820000001",
                    "status": status,
                    "messageId": message_id,
                }
            ],
        }
    }
    return httpx.Response(201, json=body)


def test_a_message_is_posted_to_the_sandbox_with_the_key_in_a_header():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["key"] = request.headers["apiKey"]
        seen["form"] = dict(httpx.QueryParams(request.content.decode()))
        return reply()

    result = africastalking_client(handler).send("082 000 0001", "Hello")

    assert result == SmsResult(ok=True, message_id="ATXid_1")
    assert seen["url"] == AFRICASTALKING_SANDBOX_URL
    assert seen["key"] == "secret-key"
    assert seen["form"] == {"username": "sandbox", "to": "+27820000001", "message": "Hello"}


def test_a_real_username_uses_the_live_address():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return reply()

    africastalking_client(handler, username="fixa").send("082 000 0001", "Hello")

    assert seen["url"] == AFRICASTALKING_LIVE_URL


@pytest.mark.parametrize(
    "response",
    [
        reply(status_code=403, status="InvalidPhoneNumber"),
        httpx.Response(401, json={"error": "bad key"}),
        httpx.Response(500, text="oops"),
        httpx.Response(201, text="not json"),
        httpx.Response(201, json={"SMSMessageData": {"Recipients": []}}),
    ],
)
def test_a_refusal_or_bad_answer_is_a_failed_result_not_a_crash(response):
    result = africastalking_client(lambda request: response).send("082 000 0001", "Hello")

    assert result.ok is False
    assert result.error


def test_a_network_error_is_a_failed_result():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no network")

    assert africastalking_client(handler).send("082 000 0001", "Hello").ok is False


def test_the_sender_is_the_outbox_until_keys_are_set(monkeypatch):
    monkeypatch.delenv("AFRICASTALKING_API_KEY", raising=False)
    assert isinstance(get_sms_sender(), OutboxSender)

    monkeypatch.setenv("AFRICASTALKING_API_KEY", "k")
    assert isinstance(get_sms_sender(), AfricasTalkingSender)


def test_send_safely_never_raises_and_never_logs_the_message(caplog):
    class Broken:
        def send(self, to, message):
            raise RuntimeError("boom")

    result = send_safely(Broken(), "082 000 0001", "secret address 12 Example Street", "a test")

    assert result.ok is False
    assert "12 Example Street" not in caplog.text
    assert "0820000001" not in caplog.text


# --- the unlock messages --------------------------------------------------------------------


@pytest.fixture
def outbox():
    box = OutboxSender()
    app.dependency_overrides[get_sms_sender] = lambda: box
    yield box
    app.dependency_overrides.pop(get_sms_sender, None)


def start_job(client, log_in, provider_phone):
    customer, provider = log_in(LINDIWE), log_in(provider_phone)
    body = {
        "description": "Geyser leaking",
        "lang": "en",
        "trade": "plumbing",
        "urgency": "urgent",
        "size": "small",
        "suburb": "Braamfontein",
    }
    job_id = client.post("/api/jobs", json=body, headers=customer).json()["id"]
    quote = {"amount_rands": 450, "when": QUOTE_TIME}
    quote_id = client.post(f"/api/jobs/{job_id}/quotes", json=quote, headers=provider).json()["id"]
    client.post(f"/api/quotes/{quote_id}/accept", headers=customer)
    return job_id, customer, provider


def test_no_sms_is_sent_before_the_job_is_confirmed(seeded_client, log_in, outbox):
    job_id, customer, provider = start_job(seeded_client, log_in, THABO)
    seeded_client.post(f"/api/jobs/{job_id}/decline", headers=provider)

    assert outbox.sent == []


def test_confirming_sends_both_sides_an_sms_with_the_other_persons_number(
    seeded_client, log_in, outbox
):
    job_id, customer, provider = start_job(seeded_client, log_in, THABO)

    response = seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=provider)

    assert response.status_code == 200
    by_number = dict(outbox.sent)
    assert set(by_number) == {"+27820000001", "+27710000001"}
    assert "071 000 0001" in by_number["+27820000001"]  # the customer gets the provider's number
    assert "082 000 0001" in by_number["+27710000001"]  # the provider gets the customer's number
    assert "12 Example Street, Braamfontein" in by_number["+27710000001"]
    assert "Example Street" not in by_number["+27820000001"]  # the customer knows their own address


def test_each_person_gets_their_own_language(seeded_client, log_in, outbox):
    job_id, customer, provider = start_job(seeded_client, log_in, SIPHO)

    seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=provider)

    by_number = dict(outbox.sent)
    assert "confirmed your job" in by_number["+27820000001"]  # Lindiwe reads English
    assert "uqinisekise" in by_number["+27710000002"]  # Sipho reads isiZulu


def test_a_failing_sms_never_breaks_the_confirmation(seeded_client, log_in):
    class Down:
        def send(self, to, message):
            raise RuntimeError("Africa's Talking is down")

    app.dependency_overrides[get_sms_sender] = lambda: Down()
    try:
        job_id, customer, provider = start_job(seeded_client, log_in, THABO)
        response = seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=provider)
    finally:
        app.dependency_overrides.pop(get_sms_sender, None)

    assert response.status_code == 200
    assert response.json()["state"] == "confirmed"


def test_confirming_twice_sends_no_second_sms(seeded_client, log_in, outbox):
    job_id, customer, provider = start_job(seeded_client, log_in, THABO)
    seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=provider)
    seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=provider)

    assert len(outbox.sent) == 2


def test_the_confirm_answer_does_not_carry_the_sms(seeded_client, log_in, outbox):
    job_id, customer, provider = start_job(seeded_client, log_in, THABO)

    answer = seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=provider).text

    assert "Fixa:" not in answer
    assert json.loads(answer)["state"] == "confirmed"
