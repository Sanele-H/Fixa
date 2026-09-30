"""The licence filter: licensed work goes only to licensed providers."""

import pytest

from fixa_api.licence import needs_licence_for

LINDIWE = "082 000 0001"
LICENSED_PLUMBER = "071 000 0001"  # prov_001
LICENSED_PLUMBER_2 = "071 000 0004"  # prov_004
UNLICENSED_PLUMBER = "071 000 0002"  # prov_002
UNLICENSED_PLUMBER_2 = "071 000 0003"  # prov_003
QUOTE_TIME = "2026-10-01T10:00:00+02:00"


# --- what counts as licensed work -----------------------------------------------------------


@pytest.mark.parametrize(
    ("trade", "text"),
    [
        ("plumbing", "My geyser is finished and I need a new one installed"),
        ("plumbing", "Geyser installation please"),
        ("plumbing", "I want to install a new geyser"),
        ("plumbing", "Ngifuna ukufaka igiza elisha"),  # isiZulu: I want to install a new geyser
        ("electrical", "I am selling my house and need an electrical certificate of compliance"),
        ("electrical", "Need a CoC for the flat"),
        ("electrical", "The whole house needs rewiring"),
        ("electrical", "Please replace my DB board"),
    ],
)
def test_licensed_work_is_recognised(trade, text):
    assert needs_licence_for(trade, text) is True


@pytest.mark.parametrize(
    ("trade", "text"),
    [
        ("plumbing", "My geyser is leaking through the ceiling"),
        ("plumbing", "Replace the geyser valve"),
        ("plumbing", "Install a new geyser element"),
        ("plumbing", "Blocked drain in the kitchen"),
        ("electrical", "My plug point is broken"),
        ("electrical", "Install a light fitting in the lounge"),
        ("electrical", "The circuit keeps tripping"),
        ("cleaning", "Install new geyser and rewire"),  # other trades have no licensed work
    ],
)
def test_ordinary_work_is_not(trade, text):
    assert needs_licence_for(trade, text) is False


# --- what the API does about it -------------------------------------------------------------


def post_job(client, headers, description="I need a new geyser installed", **changes):
    body = {
        "description": description,
        "lang": "en",
        "trade": "plumbing",
        "urgency": "normal",
        "size": "medium",
        "suburb": "Braamfontein",
    } | changes
    return client.post("/api/jobs", json=body, headers=headers)


@pytest.fixture
def lindiwe(log_in):
    return log_in(LINDIWE)


def test_a_geyser_installation_is_marked_as_needing_a_licence(seeded_client, lindiwe):
    job = post_job(seeded_client, lindiwe).json()

    assert job["needs_licence"] is True


def test_an_ordinary_job_is_not(seeded_client, lindiwe):
    job = post_job(seeded_client, lindiwe, "My tap drips").json()

    assert job["needs_licence"] is False


def test_the_customer_can_insist_on_a_licensed_provider(seeded_client, lindiwe):
    job = post_job(seeded_client, lindiwe, "My tap drips", needs_licence=True).json()

    assert job["needs_licence"] is True


def test_a_licensed_provider_sees_and_can_quote_licensed_work(seeded_client, lindiwe, log_in):
    job_id = post_job(seeded_client, lindiwe).json()["id"]
    licensed = log_in(LICENSED_PLUMBER)

    feed = seeded_client.get("/api/feed", headers=licensed).json()
    quote = seeded_client.post(
        f"/api/jobs/{job_id}/quotes",
        json={"amount_rands": 4500, "when": QUOTE_TIME},
        headers=licensed,
    )

    assert job_id in [job["id"] for job in feed]
    assert quote.status_code == 201


def test_an_unlicensed_provider_never_sees_licensed_work(seeded_client, lindiwe, log_in):
    job_id = post_job(seeded_client, lindiwe).json()["id"]
    unlicensed = log_in(UNLICENSED_PLUMBER)

    feed = seeded_client.get("/api/feed", headers=unlicensed).json()
    page = seeded_client.get(f"/api/jobs/{job_id}", headers=unlicensed)
    quote = seeded_client.post(
        f"/api/jobs/{job_id}/quotes",
        json={"amount_rands": 4500, "when": QUOTE_TIME},
        headers=unlicensed,
    )

    assert job_id not in [job["id"] for job in feed]
    assert page.status_code == 404  # the same answer as a job that doesn't exist
    assert quote.status_code == 404


def test_an_unlicensed_provider_still_sees_ordinary_work(seeded_client, lindiwe, log_in):
    job_id = post_job(seeded_client, lindiwe, "My tap drips").json()["id"]

    feed = seeded_client.get("/api/feed", headers=log_in(UNLICENSED_PLUMBER)).json()

    assert job_id in [job["id"] for job in feed]


def test_the_ranked_list_for_licensed_work_holds_only_licensed_providers(
    seeded_client, lindiwe, log_in
):
    job_id = post_job(seeded_client, lindiwe).json()["id"]

    ranked = seeded_client.get(f"/api/jobs/{job_id}/providers", headers=lindiwe).json()
    ids = {row["provider_id"] for row in ranked}

    assert ranked
    assert {"prov_002", "prov_003"}.isdisjoint(ids)  # unlicensed plumbers
    assert {"prov_001", "prov_004"} <= ids  # licensed plumbers


def test_licensed_work_is_not_in_an_unlicensed_providers_chat_either(
    seeded_client, lindiwe, log_in
):
    job_id = post_job(seeded_client, lindiwe).json()["id"]

    reply = seeded_client.post(
        f"/api/jobs/{job_id}/messages", json={"text": "Hello"}, headers=log_in(UNLICENSED_PLUMBER_2)
    )

    assert reply.status_code == 404
