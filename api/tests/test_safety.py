"""Safety during a job: trusted contact, panic button, safety timer, location at key moments, and
the inbox and push subscriptions behind the bell."""

import datetime as dt

import pytest
from sqlmodel import select

from fixa_api.main import app
from fixa_api.models import SafetyAlert, SafetyTimer
from fixa_api.sms import OutboxSender, get_sms_sender

LINDIWE = "082 000 0001"  # cust_001, English, Braamfontein
THABO = "071 000 0001"  # prov_001 (plumber)
SIPHO = "071 000 0002"  # prov_002 (plumber, isiZulu)
OTHER_CUSTOMER = "082 000 0002"
QUOTE_TIME = "2026-10-01T10:00:00+02:00"
TRUSTED = {"name": "Thandi", "phone": "083 555 0101"}
BRAAMFONTEIN = {"lat": -26.1929, "lng": 28.0305}


@pytest.fixture
def outbox(seeded_client):
    sender = OutboxSender()
    app.dependency_overrides[get_sms_sender] = lambda: sender
    return sender


@pytest.fixture
def lindiwe(log_in):
    return log_in(LINDIWE)


@pytest.fixture
def sipho(log_in):
    return log_in(SIPHO)


def post_job(client, headers):
    body = {
        "description": "My geyser is leaking",
        "lang": "en",
        "trade": "plumbing",
        "urgency": "urgent",
        "size": "small",
        "suburb": "Braamfontein",
    }
    return client.post("/api/jobs", json=body, headers=headers).json()["id"]


@pytest.fixture
def confirmed_job(seeded_client, outbox, lindiwe, sipho):
    """A job Lindiwe posted, Sipho quoted R450 on, she accepted and he confirmed. The outbox is
    emptied afterwards, so tests only see their own SMS (confirming sends two)."""
    job_id = post_job(seeded_client, lindiwe)
    quote = seeded_client.post(
        f"/api/jobs/{job_id}/quotes",
        json={"amount_rands": 450, "when": QUOTE_TIME},
        headers=sipho,
    ).json()
    seeded_client.post(f"/api/quotes/{quote['id']}/accept", headers=lindiwe)
    seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=sipho)
    outbox.sent.clear()
    return job_id


def inbox(client, headers):
    return client.get("/api/notifications", headers=headers).json()


# --- trusted contact ---------------------------------------------------------------------------


def test_a_trusted_contact_is_saved_and_read_back(seeded_client, lindiwe):
    assert seeded_client.get("/api/me/trusted-contact", headers=lindiwe).json() is None
    seeded_client.put("/api/me/trusted-contact", json=TRUSTED, headers=lindiwe)
    changed = TRUSTED | {"name": "Thandi M"}
    seeded_client.put("/api/me/trusted-contact", json=changed, headers=lindiwe)
    assert seeded_client.get("/api/me/trusted-contact", headers=lindiwe).json() == changed


# --- panic -------------------------------------------------------------------------------------


def test_panic_texts_the_trusted_contact_with_a_map_link(
    seeded_client, outbox, lindiwe, confirmed_job
):
    seeded_client.put("/api/me/trusted-contact", json=TRUSTED, headers=lindiwe)

    response = seeded_client.post(
        f"/api/jobs/{confirmed_job}/panic", json=BRAAMFONTEIN, headers=lindiwe
    )

    assert response.status_code == 201
    assert response.json()["contact"] == TRUSTED
    assert {"label": "police", "number": "10111"} in response.json()["emergency_numbers"]
    [(to, text)] = outbox.sent
    assert to == "+27835550101"
    assert "panic button" in text
    assert "maps.google.com/?q=-26.19290,28.03050" in text


def test_panic_is_never_shown_to_the_other_person(
    seeded_client, outbox, lindiwe, sipho, confirmed_job
):
    seeded_client.post(f"/api/jobs/{confirmed_job}/panic", json=BRAAMFONTEIN, headers=lindiwe)

    theirs = inbox(seeded_client, sipho)
    locations = seeded_client.get(f"/api/jobs/{confirmed_job}/locations", headers=sipho).json()

    assert not any(item["kind"].startswith("panic") for item in theirs["items"])
    assert all(ping["moment"] != "panic" for ping in locations)


def test_panic_without_a_contact_is_still_recorded(
    seeded_client, seeded_session, outbox, lindiwe, confirmed_job
):
    response = seeded_client.post(f"/api/jobs/{confirmed_job}/panic", json={}, headers=lindiwe)

    assert response.json()["contact"] is None
    assert outbox.sent == []
    assert seeded_session.exec(select(SafetyAlert)).one().kind == "panic"
    assert inbox(seeded_client, lindiwe)["items"][0]["kind"] == "panic_no_contact"


def test_only_people_on_the_job_can_press_panic(seeded_client, log_in, outbox, confirmed_job):
    stranger = log_in(OTHER_CUSTOMER)
    response = seeded_client.post(f"/api/jobs/{confirmed_job}/panic", json={}, headers=stranger)
    assert response.status_code == 404


# --- safety timer ------------------------------------------------------------------------------


def test_saying_safe_stops_the_timer(seeded_client, outbox, sipho, confirmed_job):
    started = seeded_client.post(
        f"/api/jobs/{confirmed_job}/safety-timer", json={"minutes": 60}, headers=sipho
    ).json()
    assert started["state"] == "running"

    safe = seeded_client.post(f"/api/jobs/{confirmed_job}/safety-timer/safe", headers=sipho)

    assert safe.json()["state"] == "safe"
    assert outbox.sent == []


def test_a_missed_timer_texts_the_trusted_contact(
    seeded_client, seeded_session, outbox, sipho, confirmed_job
):
    seeded_client.put("/api/me/trusted-contact", json=TRUSTED, headers=sipho)
    seeded_client.post(
        f"/api/jobs/{confirmed_job}/location",
        json={"moment": "timer_start"} | BRAAMFONTEIN,
        headers=sipho,
    )
    seeded_client.post(
        f"/api/jobs/{confirmed_job}/safety-timer", json={"minutes": 15}, headers=sipho
    )
    timer = seeded_session.exec(select(SafetyTimer)).one()
    timer.due_at = dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1)
    seeded_session.add(timer)
    seeded_session.commit()

    shown = seeded_client.get(f"/api/jobs/{confirmed_job}/safety-timer", headers=sipho).json()

    assert shown["state"] == "missed"
    [(to, text)] = outbox.sent
    assert to == "+27835550101"
    assert text.startswith("Ukuhlola ukuphepha kwa-Fixa")  # Sipho's app is in isiZulu
    assert "maps.google.com" in text
    assert inbox(seeded_client, sipho)["items"][0]["kind"] == "timer_missed"


def test_a_timer_only_takes_the_offered_lengths(seeded_client, sipho, confirmed_job):
    response = seeded_client.post(
        f"/api/jobs/{confirmed_job}/safety-timer", json={"minutes": 7}, headers=sipho
    )
    assert response.status_code == 422


# --- location at key moments -------------------------------------------------------------------


def test_locations_show_distance_from_the_job_never_coordinates(
    seeded_client, lindiwe, sipho, confirmed_job
):
    seeded_client.post(
        f"/api/jobs/{confirmed_job}/location",
        json={"moment": "check_in", "lat": -26.19, "lng": 28.03, "accuracy_m": 12},
        headers=sipho,
    )

    [ping] = seeded_client.get(f"/api/jobs/{confirmed_job}/locations", headers=lindiwe).json()

    assert ping["moment"] == "check_in"
    assert ping["role"] == "provider"
    assert isinstance(ping["distance_km"], float)
    assert "lat" not in ping and "lng" not in ping


def test_an_unknown_moment_is_refused(seeded_client, sipho, confirmed_job):
    response = seeded_client.post(
        f"/api/jobs/{confirmed_job}/location",
        json={"moment": "lunch"} | BRAAMFONTEIN,
        headers=sipho,
    )
    assert response.status_code == 422


# --- the inbox behind the bell -----------------------------------------------------------------


def test_each_step_of_a_job_lands_in_the_right_inbox(
    seeded_client, outbox, lindiwe, sipho, confirmed_job
):
    seeded_client.post(f"/api/jobs/{confirmed_job}/messages", json={"text": "Hi"}, headers=sipho)
    seeded_client.post(f"/api/jobs/{confirmed_job}/check-in", headers=sipho)

    hers = [item["kind"] for item in inbox(seeded_client, lindiwe)["items"]]
    his = [item["kind"] for item in inbox(seeded_client, sipho)["items"]]

    assert hers == ["checked_in", "message", "job_confirmed", "quote_received"]
    assert his == ["quote_accepted"]


def test_inbox_texts_are_in_the_readers_language(seeded_client, sipho, confirmed_job):
    [accepted] = inbox(seeded_client, sipho)["items"]
    assert accepted["title"] == "Intengo yakho yamukelwe"
    assert "R450" in accepted["body"]


def test_marking_read_clears_the_unread_count(seeded_client, lindiwe, confirmed_job):
    assert inbox(seeded_client, lindiwe)["unread"] == 2
    first = inbox(seeded_client, lindiwe)["items"][0]["id"]

    after_one = seeded_client.post(f"/api/notifications/{first}/read", headers=lindiwe).json()
    after_all = seeded_client.post("/api/notifications/read", headers=lindiwe).json()

    assert after_one["unread"] == 1
    assert after_all["unread"] == 0


# --- push subscriptions ------------------------------------------------------------------------


def test_push_key_is_404_when_push_is_not_set_up(seeded_client, monkeypatch):
    monkeypatch.delenv("VAPID_PRIVATE_KEY", raising=False)
    assert seeded_client.get("/api/push/key").status_code == 404


def test_a_push_goes_to_the_subscribed_browser(seeded_client, monkeypatch, lindiwe, sipho):
    sent = []
    monkeypatch.setenv("VAPID_PUBLIC_KEY", "public-key")
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "private-key")
    monkeypatch.setattr(
        "fixa_api.push._executor.submit", lambda send, user_id, payload: sent.append(user_id)
    )
    subscription = {"endpoint": "https://push.example/abc", "keys": {"p256dh": "k", "auth": "a"}}
    response = seeded_client.post("/api/push/subscriptions", json=subscription, headers=lindiwe)
    assert response.status_code == 201

    job_id = post_job(seeded_client, lindiwe)
    seeded_client.post(
        f"/api/jobs/{job_id}/quotes", json={"amount_rands": 450, "when": QUOTE_TIME}, headers=sipho
    )

    assert sent == ["cust_001"]
