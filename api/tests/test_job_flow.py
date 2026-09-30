"""Posting a job, quotes, and every state change from posted to confirmed and cancelled."""

import pytest

from fixa_api.job_states import CANCELLED, TRANSITIONS, InvalidTransitionError, check_transition

LINDIWE = "082 000 0001"  # cust_001, Braamfontein
YEVILLE = "082 000 0002"  # cust_002
PLUMBER_1 = "071 000 0001"  # prov_001
PLUMBER_2 = "071 000 0002"  # prov_002
PLUMBER_3 = "071 000 0003"  # prov_003
ELECTRICIAN = "071 000 0006"  # prov_006

CONTACT_FIELDS = {"address", "directions", "customer_phone", "provider_phone", "provider_photo_url"}
QUOTE_TIME = "2026-10-01T10:00:00+02:00"


def new_job(client, headers, **changes):
    body = {
        "description": "My geyser is leaking through the ceiling",
        "lang": "en",
        "trade": "plumbing",
        "urgency": "urgent",
        "size": "small",
        "suburb": "Braamfontein",
    } | changes
    return client.post("/api/jobs", json=body, headers=headers)


def send_quote(client, headers, job_id, amount=450, **changes):
    body = {"amount_rands": amount, "when": QUOTE_TIME} | changes
    return client.post(f"/api/jobs/{job_id}/quotes", json=body, headers=headers)


@pytest.fixture
def lindiwe(log_in):
    return log_in(LINDIWE)


@pytest.fixture
def plumber(log_in):
    return log_in(PLUMBER_1)


@pytest.fixture
def job_id(seeded_client, lindiwe):
    return new_job(seeded_client, lindiwe).json()["id"]


@pytest.fixture
def quoted(seeded_client, job_id, plumber):
    """A job with one open quote from plumber 1. Returns (job_id, quote_id)."""
    return job_id, send_quote(seeded_client, plumber, job_id).json()["id"]


@pytest.fixture
def accepted(seeded_client, quoted, lindiwe):
    """The same job after Lindiwe accepted plumber 1's quote."""
    job_id, quote_id = quoted
    seeded_client.post(f"/api/quotes/{quote_id}/accept", headers=lindiwe)
    return job_id, quote_id


# --- the state machine on its own -----------------------------------------------------------


def test_the_happy_path_is_allowed_step_by_step():
    path = [
        "posted",
        "quoting",
        "quote_accepted",
        "confirmed",
        "in_progress",
        "done",
        "followed_up",
    ]
    for current, new in zip(path, path[1:], strict=False):
        check_transition(current, new)


def test_a_decline_goes_back_to_quoting():
    check_transition("quote_accepted", "quoting")


@pytest.mark.parametrize("state", [state for state in TRANSITIONS if state != CANCELLED])
def test_any_live_state_can_be_cancelled(state):
    check_transition(state, CANCELLED)


@pytest.mark.parametrize(
    ("current", "new"),
    [
        ("posted", "confirmed"),
        ("quoting", "confirmed"),
        ("posted", "quote_accepted"),
        ("confirmed", "quoting"),
        ("done", "confirmed"),
        ("cancelled", "posted"),
        ("cancelled", "cancelled"),
    ],
)
def test_skipping_or_reversing_a_state_is_refused(current, new):
    with pytest.raises(InvalidTransitionError):
        check_transition(current, new)


# --- posting a job --------------------------------------------------------------------------


def test_a_customer_posts_a_job_that_shows_only_the_suburb_and_problem(seeded_client, lindiwe):
    response = new_job(seeded_client, lindiwe, suburb="Sandton")

    assert response.status_code == 201
    job = response.json()
    assert job["state"] == "posted"
    assert job["suburb"] == "Braamfontein"  # from Lindiwe's account, not from the phone
    assert job["problem"] == "My geyser is leaking through the ceiling"
    assert not CONTACT_FIELDS & set(job)


def test_only_a_customer_can_post_a_job(seeded_client, plumber):
    assert new_job(seeded_client, plumber).status_code == 403


def test_posting_needs_a_signed_in_user(seeded_client):
    assert new_job(seeded_client, {}).status_code == 401


@pytest.mark.parametrize(
    "changes",
    [{"trade": "astrology"}, {"description": ""}, {"lang": "fr"}, {"size": "huge"}],
)
def test_a_bad_job_is_refused(seeded_client, lindiwe, changes):
    assert new_job(seeded_client, lindiwe, **changes).status_code == 422


# --- the feed and who can see a job ---------------------------------------------------------


def test_a_plumber_sees_a_new_plumbing_job_in_the_feed(seeded_client, plumber, job_id):
    feed = seeded_client.get("/api/feed", headers=plumber).json()

    job = next(job for job in feed if job["id"] == job_id)
    assert not CONTACT_FIELDS & set(job)
    assert isinstance(job["distance_km"], float)


def test_an_electrician_does_not_see_a_plumbing_job(seeded_client, log_in, job_id):
    feed = seeded_client.get("/api/feed", headers=log_in(ELECTRICIAN)).json()

    assert job_id not in [job["id"] for job in feed]


def test_a_customer_cannot_read_the_feed(seeded_client, lindiwe):
    assert seeded_client.get("/api/feed", headers=lindiwe).status_code == 403


def test_the_job_page_is_open_to_its_customer_and_a_matching_provider(
    seeded_client, lindiwe, plumber, job_id
):
    for headers in (lindiwe, plumber):
        assert seeded_client.get(f"/api/jobs/{job_id}", headers=headers).status_code == 200


def test_another_customer_and_an_electrician_get_a_404(seeded_client, log_in, job_id):
    for phone in (YEVILLE, ELECTRICIAN):
        response = seeded_client.get(f"/api/jobs/{job_id}", headers=log_in(phone))
        assert response.status_code == 404


def test_an_unknown_job_is_the_same_404(seeded_client, lindiwe):
    assert seeded_client.get("/api/jobs/job_nope", headers=lindiwe).status_code == 404


# --- quotes ---------------------------------------------------------------------------------


def test_the_first_quote_moves_the_job_to_quoting(seeded_client, lindiwe, plumber, job_id):
    response = send_quote(seeded_client, plumber, job_id, message="Ngingafika ngoLwesibili, R450.")

    assert response.status_code == 201
    quote = response.json()
    assert (quote["state"], quote["amount_rands"], quote["provider_id"]) == (
        "open",
        450,
        "prov_001",
    )
    assert seeded_client.get(f"/api/jobs/{job_id}", headers=lindiwe).json()["state"] == "quoting"


@pytest.mark.parametrize(
    "changes",
    [{"amount": 0}, {"amount": -5}, {"amount": 2_000_000}, {"when": "2026-10-01T10:00:00"}],
)
def test_a_bad_quote_is_refused(seeded_client, plumber, job_id, changes):
    assert send_quote(seeded_client, plumber, job_id, **changes).status_code == 422


def test_a_provider_cannot_send_two_open_quotes(seeded_client, plumber, quoted):
    job_id, _ = quoted

    assert send_quote(seeded_client, plumber, job_id, 300).status_code == 409


def test_only_a_provider_of_the_right_trade_can_quote(seeded_client, log_in, lindiwe, job_id):
    assert send_quote(seeded_client, log_in(ELECTRICIAN), job_id).status_code == 404
    assert send_quote(seeded_client, lindiwe, job_id).status_code == 403


def test_the_customer_sees_every_quote_and_a_provider_only_their_own(
    seeded_client, lindiwe, plumber, log_in, quoted
):
    job_id, _ = quoted
    send_quote(seeded_client, log_in(PLUMBER_2), job_id, 500)

    everything = seeded_client.get(f"/api/jobs/{job_id}/quotes", headers=lindiwe).json()
    only_mine = seeded_client.get(f"/api/jobs/{job_id}/quotes", headers=plumber).json()

    assert {quote["provider_id"] for quote in everything} == {"prov_001", "prov_002"}
    assert [quote["provider_id"] for quote in only_mine] == ["prov_001"]


def test_another_customer_cannot_read_the_quotes(seeded_client, log_in, quoted):
    job_id, _ = quoted

    assert (
        seeded_client.get(f"/api/jobs/{job_id}/quotes", headers=log_in(YEVILLE)).status_code == 404
    )


# --- accept, confirm, decline, cancel -------------------------------------------------------


def test_accepting_a_quote_keeps_the_details_locked(seeded_client, lindiwe, plumber, quoted):
    job_id, quote_id = quoted

    response = seeded_client.post(f"/api/quotes/{quote_id}/accept", headers=lindiwe)

    assert response.status_code == 200
    assert response.json()["state"] == "quote_accepted"
    assert not CONTACT_FIELDS & set(response.json())
    assert not CONTACT_FIELDS & set(
        seeded_client.get(f"/api/jobs/{job_id}", headers=plumber).json()
    )


def test_only_the_customer_of_the_job_can_accept(seeded_client, log_in, plumber, quoted):
    _, quote_id = quoted

    assert seeded_client.post(f"/api/quotes/{quote_id}/accept", headers=plumber).status_code == 403
    other = seeded_client.post(f"/api/quotes/{quote_id}/accept", headers=log_in(YEVILLE))
    assert other.status_code == 404


def test_a_quote_cannot_be_accepted_twice(seeded_client, lindiwe, accepted):
    _, quote_id = accepted

    assert seeded_client.post(f"/api/quotes/{quote_id}/accept", headers=lindiwe).status_code == 409


def test_confirming_unlocks_the_details_for_both_sides(seeded_client, lindiwe, plumber, accepted):
    job_id, _ = accepted

    confirmed = seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=plumber)

    assert confirmed.status_code == 200
    job = confirmed.json()
    assert job["state"] == "confirmed"
    assert job["address"] == "12 Example Street, Braamfontein"
    assert (job["customer_phone"], job["provider_phone"]) == (LINDIWE, PLUMBER_1)
    for headers in (lindiwe, plumber):
        assert CONTACT_FIELDS <= set(
            seeded_client.get(f"/api/jobs/{job_id}", headers=headers).json()
        )


def test_confirming_declines_the_other_open_quotes(seeded_client, log_in, plumber, lindiwe, quoted):
    job_id, _ = quoted
    other_quote = send_quote(seeded_client, log_in(PLUMBER_2), job_id, 500).json()["id"]
    seeded_client.post(f"/api/quotes/{quoted[1]}/accept", headers=lindiwe)

    seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=plumber)

    states = {
        q["id"]: q["state"]
        for q in seeded_client.get(f"/api/jobs/{job_id}/quotes", headers=lindiwe).json()
    }
    assert states == {quoted[1]: "accepted", other_quote: "declined"}


def test_other_providers_lose_sight_of_a_confirmed_job(seeded_client, log_in, accepted, plumber):
    job_id, _ = accepted
    seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=plumber)

    assert seeded_client.get(f"/api/jobs/{job_id}", headers=log_in(PLUMBER_3)).status_code == 404


def test_only_the_accepted_provider_can_confirm(seeded_client, log_in, lindiwe, accepted, quoted):
    job_id, _ = accepted

    assert (
        seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=log_in(PLUMBER_2)).status_code
        == 404
    )
    assert seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=lindiwe).status_code == 403


def test_a_job_cannot_be_confirmed_before_a_quote_is_accepted(seeded_client, plumber, quoted):
    job_id, _ = quoted

    assert seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=plumber).status_code == 404


def test_confirming_twice_is_refused(seeded_client, plumber, accepted):
    job_id, _ = accepted
    seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=plumber)

    assert seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=plumber).status_code == 409


def test_a_decline_returns_the_job_to_quoting_and_shares_nothing(
    seeded_client, lindiwe, plumber, accepted
):
    job_id, quote_id = accepted

    response = seeded_client.post(f"/api/jobs/{job_id}/decline", headers=plumber)

    assert response.status_code == 200
    assert response.json()["state"] == "quoting"
    assert not CONTACT_FIELDS & set(response.json())
    quotes = seeded_client.get(f"/api/jobs/{job_id}/quotes", headers=lindiwe).json()
    assert [(q["id"], q["state"]) for q in quotes] == [(quote_id, "declined")]


def test_after_a_decline_the_customer_can_pick_another_quote(
    seeded_client, log_in, lindiwe, plumber, accepted
):
    job_id, _ = accepted
    seeded_client.post(f"/api/jobs/{job_id}/decline", headers=plumber)
    second = log_in(PLUMBER_2)
    quote_id = send_quote(seeded_client, second, job_id, 500).json()["id"]

    seeded_client.post(f"/api/quotes/{quote_id}/accept", headers=lindiwe)
    confirmed = seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=second)

    assert confirmed.json()["provider_phone"] == PLUMBER_2


def test_the_customer_can_cancel_and_open_quotes_are_withdrawn(
    seeded_client, lindiwe, plumber, quoted
):
    job_id, _ = quoted

    response = seeded_client.post(f"/api/jobs/{job_id}/cancel", headers=lindiwe)

    assert response.json()["state"] == "cancelled"
    quotes = seeded_client.get(f"/api/jobs/{job_id}/quotes", headers=lindiwe).json()
    assert [q["state"] for q in quotes] == ["withdrawn"]


def test_a_cancelled_job_cannot_be_cancelled_or_quoted_again(
    seeded_client, lindiwe, plumber, job_id
):
    seeded_client.post(f"/api/jobs/{job_id}/cancel", headers=lindiwe)

    assert seeded_client.post(f"/api/jobs/{job_id}/cancel", headers=lindiwe).status_code == 409
    assert send_quote(seeded_client, plumber, job_id).status_code == 404


def test_only_the_jobs_customer_can_cancel(seeded_client, log_in, plumber, job_id):
    assert seeded_client.post(f"/api/jobs/{job_id}/cancel", headers=plumber).status_code == 403
    other = seeded_client.post(f"/api/jobs/{job_id}/cancel", headers=log_in(YEVILLE))
    assert other.status_code == 404


def test_cancelling_after_confirming_locks_the_details_again(
    seeded_client, lindiwe, plumber, accepted
):
    job_id, _ = accepted
    seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=plumber)

    seeded_client.post(f"/api/jobs/{job_id}/cancel", headers=lindiwe)

    for headers in (lindiwe, plumber):
        job = seeded_client.get(f"/api/jobs/{job_id}", headers=headers).json()
        assert job["state"] == "cancelled"
        assert not CONTACT_FIELDS & set(job)


# --- a person's own jobs (GET /api/jobs) ----------------------------------------------------


def test_a_customer_lists_their_own_jobs_newest_first(seeded_client, lindiwe):
    first = new_job(seeded_client, lindiwe).json()["id"]
    second = new_job(seeded_client, lindiwe, description="The kitchen tap drips").json()["id"]

    jobs = seeded_client.get("/api/jobs", headers=lindiwe).json()

    assert [job["id"] for job in jobs[:2]] == [second, first]
    assert all(set(job) >= {"id", "state", "problem", "suburb"} for job in jobs)


def test_a_provider_lists_the_jobs_they_quoted_on(seeded_client, log_in, quoted):
    job_id, _ = quoted

    quoting_plumber_jobs = seeded_client.get("/api/jobs", headers=log_in(PLUMBER_1)).json()
    other_plumber_jobs = seeded_client.get("/api/jobs", headers=log_in(PLUMBER_2)).json()

    assert job_id in [job["id"] for job in quoting_plumber_jobs]
    assert job_id not in [job["id"] for job in other_plumber_jobs]


def test_listed_jobs_keep_the_details_locked_until_confirmed(seeded_client, plumber, accepted):
    job_id, _ = accepted

    listed = next(
        job for job in seeded_client.get("/api/jobs", headers=plumber).json() if job["id"] == job_id
    )

    assert listed["state"] == "quote_accepted"
    assert not CONTACT_FIELDS & set(listed)


def test_listing_jobs_needs_a_signed_in_user(seeded_client):
    assert seeded_client.get("/api/jobs").status_code == 401


# --- Directions ---


def test_job_stores_and_returns_directions_when_unlocked(
    seeded_client, lindiwe, plumber
):
    """Directions travel with the job and show in JobUnlocked, never in JobPublic."""
    response = new_job(
        seeded_client,
        lindiwe,
        directions="Blue gate, ring the bell",
    )
    job_id = response.json()["id"]
    assert "directions" not in response.json()  # JobPublic has no directions

    # Quote, accept, confirm to unlock
    quote_id = send_quote(seeded_client, plumber, job_id).json()["id"]
    seeded_client.post(f"/api/quotes/{quote_id}/accept", headers=lindiwe)
    unlocked = seeded_client.post(
        f"/api/jobs/{job_id}/confirm", headers=plumber
    ).json()
    assert unlocked["directions"] == "Blue gate, ring the bell"


def test_directions_are_stripped_of_phone_numbers(seeded_client, lindiwe, plumber):
    """A phone number in directions is hidden before storing, same as the problem text."""
    job_id = new_job(
        seeded_client,
        lindiwe,
        directions="Gate code 1234, call 082 555 0199 if no answer",
    ).json()["id"]
    quote_id = send_quote(seeded_client, plumber, job_id).json()["id"]
    seeded_client.post(f"/api/quotes/{quote_id}/accept", headers=lindiwe)
    unlocked = seeded_client.post(
        f"/api/jobs/{job_id}/confirm", headers=plumber
    ).json()
    assert "082 555 0199" not in (unlocked["directions"] or "")
    assert "Gate code 1234" in unlocked["directions"]


def test_job_without_directions_returns_null(seeded_client, lindiwe, plumber):
    """A job posted without directions has directions: null in JobUnlocked."""
    job_id = new_job(seeded_client, lindiwe).json()["id"]
    quote_id = send_quote(seeded_client, plumber, job_id).json()["id"]
    seeded_client.post(f"/api/quotes/{quote_id}/accept", headers=lindiwe)
    unlocked = seeded_client.post(
        f"/api/jobs/{job_id}/confirm", headers=plumber
    ).json()
    assert unlocked["directions"] is None
