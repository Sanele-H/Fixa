"""The ranked list, nearby list, provider profile and price range, built on P4's ranking package."""

import json

import pytest
from sqlmodel import select

from fixa_api.fixtures import FIXTURES_PATH
from fixa_api.models import Job, OffAppJob, Provider, Quote
from fixa_api.trades import known_trades
from ranking import PriceRange

LINDIWE = "082 000 0001"  # cust_001, Braamfontein
PLUMBER = "071 000 0001"  # prov_001 (Thabo): 9 app jobs, 2 repeat customers, 3 off-app
NEWCOMER = "071 000 0002"  # prov_002 (Sipho): no app jobs, confirmed off-app work


def fixture_keys(file_name: str) -> set[str]:
    data = json.loads((FIXTURES_PATH / file_name).read_text(encoding="utf-8"))
    return set(data[0] if isinstance(data, list) else data)


@pytest.fixture
def lindiwe(log_in):
    return log_in(LINDIWE)


@pytest.fixture
def new_job_id(seeded_client, lindiwe):
    body = {
        "description": "Geyser leaking",
        "lang": "en",
        "trade": "plumbing",
        "urgency": "urgent",
        "size": "small",
        "suburb": "Braamfontein",
    }
    return seeded_client.post("/api/jobs", json=body, headers=lindiwe).json()["id"]


# --- the ranked list ------------------------------------------------------------------------


def test_the_ranked_list_has_the_contract_shape_and_only_plumbers(
    seeded_client, lindiwe, new_job_id
):
    response = seeded_client.get(f"/api/jobs/{new_job_id}/providers", headers=lindiwe)

    assert response.status_code == 200
    ranked = response.json()
    assert len(ranked) > 5
    assert all(set(row) == fixture_keys("ranked_providers.json") for row in ranked)
    assert all("plumbing" in row["trades"] for row in ranked)
    assert all(set(row["trust"]) == {"score", "low", "high", "label"} for row in ranked)


def test_a_newcomer_is_always_in_the_top_five(seeded_client, lindiwe, new_job_id):
    """The newcomer slot: on a small job, one of the top 5 has fewer than 3 completed jobs."""
    for _ in range(5):  # ranking draws random numbers, so try several searches
        ranked = seeded_client.get(f"/api/jobs/{new_job_id}/providers", headers=lindiwe).json()

        assert any(row["is_newcomer"] for row in ranked[:5])


def test_newcomers_are_shown_as_new_without_a_score(seeded_client, lindiwe, new_job_id):
    ranked = seeded_client.get(f"/api/jobs/{new_job_id}/providers", headers=lindiwe).json()

    for row in ranked:
        if row["is_newcomer"]:
            assert row["trust"] == {
                "score": None,
                "low": None,
                "high": None,
                "label": "New, building a record",
            }


def test_a_provider_at_the_open_quote_cap_is_left_out(
    seeded_client, seeded_session, lindiwe, new_job_id
):
    jobs = list(seeded_session.exec(select(Job).limit(5)))
    for index, job in enumerate(jobs):
        seeded_session.add(
            Quote(
                id=f"quote_cap_{index}",
                job_id=job.id,
                provider_id="prov_003",
                amount_rands=300,
                when=job.created_at,
                state="open",
                created_at=job.created_at,
            )
        )
    seeded_session.commit()

    ranked = seeded_client.get(f"/api/jobs/{new_job_id}/providers", headers=lindiwe).json()

    assert "prov_003" not in [row["provider_id"] for row in ranked]


def test_only_the_jobs_customer_can_see_the_ranked_list(seeded_client, log_in, new_job_id):
    url = f"/api/jobs/{new_job_id}/providers"

    assert seeded_client.get(url).status_code == 401
    assert seeded_client.get(url, headers=log_in(PLUMBER)).status_code == 403
    assert seeded_client.get(url, headers=log_in("082 000 0002")).status_code == 404
    assert (
        seeded_client.get("/api/jobs/job_nope/providers", headers=log_in(LINDIWE)).status_code
        == 404
    )


# --- the provider profile -------------------------------------------------------------------


def test_an_established_provider_shows_evidence_and_a_trust_range(seeded_client, lindiwe):
    profile = seeded_client.get("/api/providers/prov_001", headers=lindiwe).json()

    assert set(profile) == fixture_keys("provider_profile.json")
    assert profile["is_newcomer"] is False
    assert profile["evidence"]["jobs"] == 9
    assert profile["evidence"]["repeat_customers"] == 2
    assert profile["evidence"]["off_app_confirmed"] == 3
    trust = profile["trust"]
    assert trust["low"] <= trust["score"] <= trust["high"]
    assert trust["label"] != "New, building a record"


def test_a_newcomer_profile_says_new_building_a_record(seeded_client, lindiwe, seeded_session):
    confirmed_off_app = len(
        list(
            seeded_session.exec(
                select(OffAppJob).where(
                    OffAppJob.provider_id == "prov_002", OffAppJob.state == "confirmed"
                )
            )
        )
    )

    profile = seeded_client.get("/api/providers/prov_002", headers=lindiwe).json()

    assert profile["is_newcomer"] is True
    assert profile["trust"]["label"] == "New, building a record"
    assert profile["trust"]["score"] is None
    assert profile["evidence"]["jobs"] == 0
    assert profile["evidence"]["off_app_confirmed"] == confirmed_off_app > 0


def test_a_profile_never_holds_contact_details(seeded_client, lindiwe, seeded_session):
    provider = seeded_session.get(Provider, "prov_001")

    text = seeded_client.get("/api/providers/prov_001", headers=lindiwe).text

    assert provider.phone not in text
    assert str(provider.lat) not in text
    assert "phone" not in text


def test_the_distance_is_rounded_and_from_the_viewers_home(seeded_client, lindiwe):
    distance = seeded_client.get("/api/providers/prov_001", headers=lindiwe).json()["distance_km"]

    assert distance == round(distance, 1) > 0


def test_a_profile_needs_sign_in_and_an_existing_provider(seeded_client, lindiwe):
    assert seeded_client.get("/api/providers/prov_001").status_code == 401
    assert seeded_client.get("/api/providers/prov_nope", headers=lindiwe).status_code == 404


# --- who works near you ---------------------------------------------------------------------


def test_the_nearby_list_is_nearest_first_and_has_no_trust(seeded_client, lindiwe):
    rows = seeded_client.get("/api/providers?trade=plumbing", headers=lindiwe).json()

    assert rows
    assert all(set(row) == fixture_keys("nearby_providers.json") for row in rows)
    assert all("trust" not in row for row in rows)
    distances = [row["distance_km"] for row in rows]
    assert distances == sorted(distances)
    assert max(distances) <= 10


def test_the_language_filter_keeps_only_providers_who_speak_it(seeded_client, lindiwe):
    rows = seeded_client.get("/api/providers?trade=plumbing&lang=zu", headers=lindiwe).json()

    assert rows
    assert all("zu" in row["langs"] for row in rows)


def test_a_wider_radius_finds_more_providers(seeded_client, lindiwe):
    near = seeded_client.get("/api/providers?trade=plumbing&radius_km=2", headers=lindiwe).json()
    far = seeded_client.get("/api/providers?trade=plumbing&radius_km=30", headers=lindiwe).json()

    assert len(near) < len(far)


@pytest.mark.parametrize(
    "query",
    [
        "trade=plumbing&radius_km=0",
        "trade=plumbing&radius_km=31",
        "trade=astrology",
        "trade=plumbing&lang=fr",
    ],
)
def test_a_bad_nearby_search_is_a_422(seeded_client, lindiwe, query):
    assert seeded_client.get(f"/api/providers?{query}", headers=lindiwe).status_code == 422


def test_only_a_customer_can_browse_nearby_providers(seeded_client, log_in):
    assert seeded_client.get("/api/providers?trade=plumbing").status_code == 401
    assert (
        seeded_client.get("/api/providers?trade=plumbing", headers=log_in(PLUMBER)).status_code
        == 403
    )


# --- price range ----------------------------------------------------------------------------


def test_the_price_range_is_built_from_accepted_quotes_only(
    seeded_client, seeded_session, lindiwe, monkeypatch
):
    seen = {}

    def fake_price_range(trade, size, area, accepted_quotes):
        seen.update(trade=trade, size=size, area=area, quotes=accepted_quotes)
        return PriceRange(
            trade=trade, size=size, suburb=area, low_rands=350, high_rands=600, n_quotes=12
        )

    monkeypatch.setattr("fixa_api.routes.providers.price_range", fake_price_range)

    response = seeded_client.get(
        "/api/price-range?trade=plumbing&size=small&suburb=Braamfontein", headers=lindiwe
    )

    assert response.json() == {
        "trade": "plumbing",
        "size": "small",
        "suburb": "Braamfontein",
        "low_rands": 350,
        "high_rands": 600,
        "n_quotes": 12,
    }
    accepted_in_database = len(
        list(seeded_session.exec(select(Quote).where(Quote.state == "accepted")))
    )
    assert len(seen["quotes"]) == accepted_in_database > 0
    assert {quote.trade for quote in seen["quotes"]} <= known_trades()


def test_the_price_range_is_null_when_there_is_not_enough_data(seeded_client, lindiwe, monkeypatch):
    monkeypatch.setattr("fixa_api.routes.providers.price_range", lambda *args: None)

    response = seeded_client.get(
        "/api/price-range?trade=plumbing&size=small&suburb=Braamfontein", headers=lindiwe
    )

    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.parametrize(
    "query",
    ["trade=astrology&size=small&suburb=Yeoville", "trade=plumbing&size=huge&suburb=Yeoville"],
)
def test_a_bad_price_range_search_is_a_422(seeded_client, lindiwe, query):
    assert seeded_client.get(f"/api/price-range?{query}", headers=lindiwe).status_code == 422


def test_the_price_range_needs_sign_in(seeded_client):
    url = "/api/price-range?trade=plumbing&size=small&suburb=Yeoville"

    assert seeded_client.get(url).status_code == 401
