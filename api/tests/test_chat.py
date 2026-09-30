"""Chat, job understanding and translation: contacts hidden, each reader in their language."""

import json
import re

import pytest
from sqlmodel import select

from fixa_api.fixtures import FIXTURES_PATH
from fixa_api.models import Message

LINDIWE = "082 000 0001"  # cust_001, English
THABO = "071 000 0001"  # prov_001 (plumber)
SIPHO = "071 000 0002"  # prov_002 (plumber, isiZulu)
NOSIPHO = "071 000 0003"  # prov_003 (plumber)
ELECTRICIAN = "071 000 0006"
OTHER_CUSTOMER = "082 000 0002"

HIDDEN = "[contact hidden until the job is confirmed]"
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+27|0)[\s-]?\d{2}[\s-]?\d{3}[\s-]?\d{4}(?!\d)")
QUOTE_TIME = "2026-10-01T10:00:00+02:00"


def fixture_keys(file_name: str) -> set[str]:
    data = json.loads((FIXTURES_PATH / file_name).read_text(encoding="utf-8"))
    return set(data[0] if isinstance(data, list) else data)


@pytest.fixture
def lindiwe(log_in):
    return log_in(LINDIWE)


@pytest.fixture
def thabo(log_in):
    return log_in(THABO)


@pytest.fixture
def sipho(log_in):
    return log_in(SIPHO)


@pytest.fixture
def job_id(seeded_client, lindiwe):
    body = {
        "description": "My geyser is leaking",
        "lang": "en",
        "trade": "plumbing",
        "urgency": "urgent",
        "size": "small",
        "suburb": "Braamfontein",
    }
    return seeded_client.post("/api/jobs", json=body, headers=lindiwe).json()["id"]


def say(client, headers, job_id, text, **extra):
    return client.post(f"/api/jobs/{job_id}/messages", json={"text": text} | extra, headers=headers)


def messages_for(client, headers, job_id, **query):
    return client.get(f"/api/jobs/{job_id}/messages", headers=headers, params=query).json()


def quote(client, headers, job_id, **changes):
    body = {"amount_rands": 450, "when": QUOTE_TIME} | changes
    return client.post(f"/api/jobs/{job_id}/quotes", json=body, headers=headers)


# --- understanding a job description --------------------------------------------------------


def test_understand_returns_a_trade_urgency_and_size(seeded_client, lindiwe):
    response = seeded_client.post(
        "/api/jobs/understand",
        json={"text": "My geyser is leaking through the ceiling", "lang": "en"},
        headers=lindiwe,
    )

    assert response.status_code == 200
    intent = response.json()
    assert set(intent) == fixture_keys("job_intent.json")
    assert intent["trade"] == "plumbing"


def test_understand_reads_isizulu_too(seeded_client, lindiwe):
    response = seeded_client.post(
        "/api/jobs/understand", json={"text": "Igiza lami liyavuza", "lang": "zu"}, headers=lindiwe
    )

    assert response.json()["trade"] == "plumbing"


def test_understand_is_for_customers_and_needs_text(seeded_client, lindiwe, thabo):
    body = {"text": "geyser", "lang": "en"}

    assert seeded_client.post("/api/jobs/understand", json=body).status_code == 401
    assert seeded_client.post("/api/jobs/understand", json=body, headers=thabo).status_code == 403
    empty = {"text": "", "lang": "en"}
    assert (
        seeded_client.post("/api/jobs/understand", json=empty, headers=lindiwe).status_code == 422
    )


# --- sending and reading messages -----------------------------------------------------------


def test_a_message_has_the_contract_shape(seeded_client, lindiwe, thabo, job_id):
    quote(seeded_client, thabo, job_id)

    response = say(seeded_client, thabo, job_id, "I can come on Tuesday, R450.")

    assert response.status_code == 201
    message = response.json()
    assert fixture_keys("message.json") <= set(message)
    assert (message["sender_id"], message["contacts_hidden"]) == ("prov_001", False)
    assert message["text"] == "I can come on Tuesday, R450."


def test_a_phone_number_is_hidden_from_the_other_side(seeded_client, lindiwe, thabo, job_id):
    quote(seeded_client, thabo, job_id)

    say(seeded_client, thabo, job_id, "Call me on 082 123 4567 please")

    seen = messages_for(seeded_client, lindiwe, job_id)
    assert len(seen) == 1
    assert seen[0]["contacts_hidden"] is True
    assert HIDDEN in seen[0]["text"]
    assert not PHONE_PATTERN.search(json.dumps(seen))


def test_disguised_numbers_are_hidden_too(seeded_client, lindiwe, thabo, job_id):
    quote(seeded_client, thabo, job_id)
    for text in (
        "call me o82 one two three four five six seven",
        "zero eight two one two three four five six seven",
        "mail me bob at gmail dot com",
    ):
        say(seeded_client, thabo, job_id, text)

    seen = messages_for(seeded_client, lindiwe, job_id)

    assert [message["contacts_hidden"] for message in seen] == [True, True, True]


@pytest.mark.xfail(reason="P3 gap: numbers split into comma-separated groups are not hidden yet")
@pytest.mark.parametrize(
    "text", ["o82, 123, 4567", "zero eight two, one two three, four five six seven"]
)
def test_numbers_split_by_commas_are_hidden(seeded_client, lindiwe, thabo, job_id, text):
    quote(seeded_client, thabo, job_id)
    say(seeded_client, thabo, job_id, text)

    assert messages_for(seeded_client, lindiwe, job_id)[0]["contacts_hidden"] is True


def test_see_original_never_shows_the_hidden_number(seeded_client, lindiwe, thabo, job_id):
    quote(seeded_client, thabo, job_id)
    say(seeded_client, thabo, job_id, "Call me on 082 123 4567 please")

    message = messages_for(seeded_client, lindiwe, job_id)[0]

    assert "082 123 4567" not in message["original"]
    assert HIDDEN in message["original"]


def test_the_raw_text_is_stored_for_review_but_never_sent(
    seeded_client, seeded_session, lindiwe, thabo, job_id
):
    quote(seeded_client, thabo, job_id)
    say(seeded_client, thabo, job_id, "Call me on 082 123 4567 please")

    stored = seeded_session.exec(select(Message)).one()

    assert "082 123 4567" in stored.original_text
    assert "082 123 4567" not in stored.safe_text
    for headers in (lindiwe, thabo):
        assert "082 123 4567" not in json.dumps(messages_for(seeded_client, headers, job_id))


def test_contact_details_are_shown_once_the_job_is_confirmed(seeded_client, lindiwe, thabo, job_id):
    quote_id = quote(seeded_client, thabo, job_id).json()["id"]
    seeded_client.post(f"/api/quotes/{quote_id}/accept", headers=lindiwe)
    seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=thabo)

    say(seeded_client, thabo, job_id, "My number is 082 123 4567")

    shown = messages_for(seeded_client, lindiwe, job_id)[0]
    assert "082 123 4567" in shown["text"]
    assert shown["contacts_hidden"] is False


def test_a_message_sent_before_confirming_stays_hidden_after(seeded_client, lindiwe, thabo, job_id):
    quote_id = quote(seeded_client, thabo, job_id).json()["id"]
    say(seeded_client, thabo, job_id, "Call me on 082 123 4567")
    seeded_client.post(f"/api/quotes/{quote_id}/accept", headers=lindiwe)
    seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=thabo)

    shown = messages_for(seeded_client, lindiwe, job_id)[0]

    assert "082 123 4567" not in shown["text"]


def test_scam_patterns_come_back_as_warnings_in_the_readers_language(
    seeded_client, log_in, lindiwe, sipho, job_id
):
    quote(seeded_client, sipho, job_id)

    say(seeded_client, sipho, job_id, "Please pay a deposit of R200 first")

    warnings = messages_for(seeded_client, lindiwe, job_id)[0]["scam_warnings"]
    assert warnings
    assert all(isinstance(warning, str) and warning for warning in warnings)


# --- translation ----------------------------------------------------------------------------


def test_each_reader_gets_the_message_in_their_own_language(seeded_client, lindiwe, sipho, job_id):
    quote(seeded_client, sipho, job_id)
    say(seeded_client, sipho, job_id, "Ngingafika ngoLwesibili, R450.")

    customer_sees = messages_for(seeded_client, lindiwe, job_id)[0]
    sender_sees = messages_for(seeded_client, sipho, job_id)[0]

    assert customer_sees["original"] == "Ngingafika ngoLwesibili, R450."
    assert customer_sees["original_lang"] == "zu"
    assert customer_sees["text"].startswith("[en]")  # the fake translator tags the language
    assert "R450" in customer_sees["text"]
    assert sender_sees["text"] == "Ngingafika ngoLwesibili, R450."


def test_a_message_is_labelled_with_the_language_it_is_written_in(
    seeded_client, lindiwe, sipho, job_id
):
    # Lindiwe's setting is English, but she writes in isiZulu.
    quote(seeded_client, sipho, job_id)
    say(seeded_client, lindiwe, job_id, "Ngizofika kusasa ekuseni.")

    provider_sees = messages_for(seeded_client, sipho, job_id)[0]
    sender_sees = messages_for(seeded_client, lindiwe, job_id)[0]

    assert provider_sees["original_lang"] == "zu"
    # Sipho reads isiZulu, so there's nothing to translate.
    assert provider_sees["text"] == "Ngizofika kusasa ekuseni."
    # Lindiwe sees her own words as she wrote them, not translated into her setting.
    assert sender_sees["text"] == "Ngizofika kusasa ekuseni."


def test_a_job_problem_is_translated_for_a_provider_with_the_original_kept(
    seeded_client, sipho, job_id
):
    job = seeded_client.get(f"/api/jobs/{job_id}", headers=sipho).json()

    assert job["problem_original"] == "My geyser is leaking"
    assert job["problem"].startswith("[zu]")
    assert job["problem_lang"] == "en"
    assert job["translation_flagged"] is False


def test_a_job_problem_is_labelled_with_the_language_it_is_written_in(
    seeded_client, lindiwe, sipho
):
    # Lindiwe's setting is English, but she describes the job in isiZulu.
    body = {
        "description": "Ngicela ungilungisele i-geyser, iyavuza.",
        "lang": "en",
        "trade": "plumbing",
        "urgency": "urgent",
        "size": "small",
        "suburb": "Braamfontein",
    }
    posted = seeded_client.post("/api/jobs", json=body, headers=lindiwe).json()

    provider_sees = seeded_client.get(f"/api/jobs/{posted['id']}", headers=sipho).json()

    assert posted["problem_lang"] == "zu"
    assert posted["problem"] == body["description"]  # her own words, as written
    assert provider_sees["problem"] == body["description"]  # Sipho reads isiZulu


def test_a_quote_note_is_translated_for_the_customer(seeded_client, lindiwe, sipho, job_id):
    quote(seeded_client, sipho, job_id, message="Ngingafika ngoLwesibili, R450.")

    shown = seeded_client.get(f"/api/jobs/{job_id}/quotes", headers=lindiwe).json()[0]

    assert shown["message"].startswith("[en]")


def test_a_quote_note_is_labelled_with_the_language_it_is_written_in(
    seeded_client, lindiwe, thabo, job_id
):
    # Thabo's setting is English, but his note is in isiZulu.
    note = "Ngingafika ngoLwesibili ekuseni."
    sent = quote(seeded_client, thabo, job_id, message=note).json()

    customer_sees = seeded_client.get(f"/api/jobs/{job_id}/quotes", headers=lindiwe).json()[0]

    assert sent["message"] == note  # his own words, as written
    assert customer_sees["message"] == f"[en] {note}"  # translated from isiZulu


# --- contact details in job posts and quote notes -------------------------------------------


def test_a_phone_number_in_a_job_post_is_hidden_from_providers(seeded_client, lindiwe, thabo):
    body = {
        "description": "Geyser leaking, call me on 082 123 4567",
        "lang": "en",
        "trade": "plumbing",
        "urgency": "urgent",
        "size": "small",
        "suburb": "Braamfontein",
    }
    posted = seeded_client.post("/api/jobs", json=body, headers=lindiwe).json()

    feed = seeded_client.get("/api/feed", headers=thabo).text
    page = seeded_client.get(f"/api/jobs/{posted['id']}", headers=thabo).text

    assert "082 123 4567" not in feed + page + json.dumps(posted)
    assert HIDDEN in page


def test_a_phone_number_in_a_quote_note_is_hidden_from_the_customer(
    seeded_client, lindiwe, thabo, job_id
):
    quote(seeded_client, thabo, job_id, message="R450. Call me on 082 123 4567")

    shown = seeded_client.get(f"/api/jobs/{job_id}/quotes", headers=lindiwe).text

    assert "082 123 4567" not in shown
    assert HIDDEN in shown


# --- who is in the chat ---------------------------------------------------------------------


def test_only_people_on_the_job_can_read_or_write(seeded_client, log_in, thabo, job_id):
    quote(seeded_client, thabo, job_id)

    for phone in (OTHER_CUSTOMER, ELECTRICIAN):
        headers = log_in(phone)
        assert seeded_client.get(f"/api/jobs/{job_id}/messages", headers=headers).status_code == 404
        assert say(seeded_client, headers, job_id, "hello").status_code == 404
    assert seeded_client.get(f"/api/jobs/{job_id}/messages").status_code == 401


def test_a_provider_never_sees_another_providers_thread(
    seeded_client, log_in, lindiwe, thabo, sipho, job_id
):
    quote(seeded_client, thabo, job_id)
    quote(seeded_client, sipho, job_id, amount_rands=500)
    say(seeded_client, thabo, job_id, "Thabo here, I can do R450")
    say(seeded_client, lindiwe, job_id, "Thabo, can you do R400?", provider_id="prov_001")

    for_sipho = messages_for(seeded_client, sipho, job_id)
    for_thabo = messages_for(seeded_client, thabo, job_id)
    for_lindiwe = messages_for(seeded_client, lindiwe, job_id)

    assert for_sipho == []
    assert len(for_thabo) == 2
    assert len(for_lindiwe) == 2


def test_a_customer_with_two_quotes_must_say_who_the_message_is_for(
    seeded_client, lindiwe, thabo, sipho, job_id
):
    quote(seeded_client, thabo, job_id)
    quote(seeded_client, sipho, job_id, amount_rands=500)

    unclear = say(seeded_client, lindiwe, job_id, "Which of you can come today?")
    unknown = say(seeded_client, lindiwe, job_id, "Hello", provider_id="prov_003")

    assert unclear.status_code == 422
    assert unknown.status_code == 422


def test_a_customer_cannot_message_before_anyone_has_quoted(seeded_client, lindiwe, job_id):
    assert say(seeded_client, lindiwe, job_id, "Anyone there?").status_code == 409


def test_once_a_provider_is_chosen_the_others_leave_the_chat(
    seeded_client, lindiwe, thabo, sipho, job_id
):
    thabo_quote = quote(seeded_client, thabo, job_id).json()["id"]
    quote(seeded_client, sipho, job_id, amount_rands=500)
    seeded_client.post(f"/api/quotes/{thabo_quote}/accept", headers=lindiwe)

    assert say(seeded_client, thabo, job_id, "Thanks!").status_code == 201
    assert say(seeded_client, sipho, job_id, "Still there?").status_code == 404
    assert seeded_client.get(f"/api/jobs/{job_id}/messages", headers=sipho).status_code == 404
    reply = say(seeded_client, lindiwe, job_id, "Great, see you then")
    assert reply.json()["recipient_id"] == "prov_001"


def test_a_cancelled_job_takes_no_more_messages(seeded_client, lindiwe, thabo, job_id):
    quote(seeded_client, thabo, job_id)
    seeded_client.post(f"/api/jobs/{job_id}/cancel", headers=lindiwe)

    assert say(seeded_client, thabo, job_id, "Hello?").status_code in (404, 409)


@pytest.mark.parametrize("text", ["", "x" * 1001])
def test_an_empty_or_huge_message_is_refused(seeded_client, lindiwe, thabo, job_id, text):
    quote(seeded_client, thabo, job_id)

    assert say(seeded_client, thabo, job_id, text).status_code == 422


def test_polling_with_after_returns_only_newer_messages(seeded_client, thabo, lindiwe, job_id):
    quote(seeded_client, thabo, job_id)
    first = say(seeded_client, thabo, job_id, "One").json()["id"]
    say(seeded_client, thabo, job_id, "Two")
    say(seeded_client, thabo, job_id, "Three")

    newer = messages_for(seeded_client, lindiwe, job_id, after=first)

    assert [message["text"] for message in newer] == ["Two", "Three"]
    assert messages_for(seeded_client, lindiwe, job_id, after=newer[-1]["id"]) == []
