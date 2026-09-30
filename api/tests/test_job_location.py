"""Where a job is: the customer's home by default, or a pin on the map, named by the server."""

import httpx
import pytest

from fixa_api import geocoding
from fixa_api.geocoding import NominatimGeocoder, Place, PlaceLookupError, read_place
from fixa_api.models import Customer, Job
from ranking.seed.places import SUBURB_CENTRES

LINDIWE = "082 000 0001"  # cust_001, lives in Braamfontein
PLUMBER = "071 000 0001"
SOWETO_PIN = {"lat": -26.2500, "lng": 27.8550}  # her mother's house, say
LONDON_PIN = {"lat": 51.5, "lng": -0.12}


def post_job(client, headers, **changes):
    body = {
        "description": "The kitchen tap won't stop dripping",
        "lang": "en",
        "trade": "plumbing",
        "urgency": "normal",
        "size": "small",
        "suburb": "Braamfontein",
    } | changes
    return client.post("/api/jobs", json=body, headers=headers)


@pytest.fixture
def lindiwe(log_in):
    return log_in(LINDIWE)


def test_a_job_is_at_the_customers_home_by_default(seeded_client, seeded_session, lindiwe):
    job = post_job(seeded_client, lindiwe).json()
    customer = seeded_session.get(Customer, "cust_001")
    stored = seeded_session.get(Job, job["id"])
    assert job["suburb"] == customer.suburb
    assert (stored.lat, stored.lng, stored.address) == (
        customer.lat,
        customer.lng,
        customer.address,
    )


def test_a_pinned_job_gets_the_pins_place_and_coordinates(seeded_client, seeded_session, lindiwe):
    job = post_job(seeded_client, lindiwe, location=SOWETO_PIN).json()
    stored = seeded_session.get(Job, job["id"])
    assert job["suburb"] == "Soweto"
    assert (stored.lat, stored.lng) == (SOWETO_PIN["lat"], SOWETO_PIN["lng"])
    assert stored.address == "Pinned spot in Soweto"


def test_the_phones_suburb_is_ignored(seeded_client, lindiwe):
    job = post_job(seeded_client, lindiwe, suburb="Sandton", location=SOWETO_PIN).json()
    assert job["suburb"] == "Soweto"


def test_a_pin_outside_south_africa_is_refused(seeded_client, lindiwe):
    response = post_job(seeded_client, lindiwe, location=LONDON_PIN)
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "place_not_found"


def test_a_failed_lookup_says_try_again(seeded_client, lindiwe, monkeypatch):
    def fail(*_args):
        raise PlaceLookupError

    monkeypatch.setattr(geocoding.NearestSuburbGeocoder, "find_place", fail)
    response = post_job(seeded_client, lindiwe, location=SOWETO_PIN)
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "place_lookup_failed"


def test_providers_are_ranked_by_distance_from_the_pin(seeded_client, lindiwe):
    at_home = post_job(seeded_client, lindiwe).json()["id"]
    in_soweto = post_job(seeded_client, lindiwe, location=SOWETO_PIN).json()["id"]
    home_list = seeded_client.get(f"/api/jobs/{at_home}/providers", headers=lindiwe).json()
    soweto_list = seeded_client.get(f"/api/jobs/{in_soweto}/providers", headers=lindiwe).json()
    home_distances = {p["provider_id"]: p["distance_km"] for p in home_list}
    soweto_distances = {p["provider_id"]: p["distance_km"] for p in soweto_list}
    assert home_distances != soweto_distances


def test_a_provider_sees_the_pins_suburb_and_distance_but_no_address(
    seeded_client, lindiwe, log_in
):
    job_id = post_job(seeded_client, lindiwe, location=SOWETO_PIN).json()["id"]
    seen = seeded_client.get(f"/api/jobs/{job_id}", headers=log_in(PLUMBER)).json()
    assert seen["suburb"] == "Soweto"
    assert seen["distance_km"] > 0
    assert "address" not in seen
    assert "Pinned spot" not in str(seen)


def test_my_area_is_rounded_to_about_a_kilometre(seeded_client, seeded_session, lindiwe):
    area = seeded_client.get("/api/me/area", headers=lindiwe).json()
    customer = seeded_session.get(Customer, "cust_001")
    assert area == {
        "suburb": customer.suburb,
        "lat": round(customer.lat, 2),
        "lng": round(customer.lng, 2),
    }


def test_reverse_lookup_names_a_pin(seeded_client, lindiwe):
    params = {"lat": SUBURB_CENTRES["Tembisa"][0], "lng": SUBURB_CENTRES["Tembisa"][1]}
    place = seeded_client.get("/api/places/reverse", params=params, headers=lindiwe).json()
    assert place == {"suburb": "Tembisa", "label": "Pinned spot in Tembisa"}


def test_providers_cant_look_up_places(seeded_client, log_in):
    response = seeded_client.get("/api/places/reverse", params=SOWETO_PIN, headers=log_in(PLUMBER))
    assert response.status_code == 403


# --- Nominatim, with the network replaced


NOMINATIM_ANSWER = {
    "address": {
        "house_number": "8115",
        "road": "Vilakazi Street",
        "suburb": "Orlando West",
        "city": "Johannesburg",
        "country_code": "za",
    }
}


def test_nominatim_answers_become_a_suburb_and_street():
    assert read_place(NOMINATIM_ANSWER) == Place(
        suburb="Orlando West", label="8115 Vilakazi Street, Orlando West"
    )


def test_a_pin_without_a_road_is_named_by_suburb_and_town():
    answer = {"address": {"suburb": "Orlando West", "city": "Johannesburg", "country_code": "za"}}
    assert read_place(answer).label == "Orlando West, Johannesburg"


def test_a_ward_number_is_skipped_for_the_city():
    answer = {
        "address": {
            "road": "Ngakane Street",
            "suburb": "Johannesburg Ward 39",
            "city": "Johannesburg",
            "country_code": "za",
        }
    }
    assert read_place(answer) == Place(suburb="Johannesburg", label="Ngakane Street, Johannesburg")


def test_a_pin_in_another_country_has_no_place():
    assert read_place({"address": {"town": "Maseru", "country_code": "ls"}}) is None


@pytest.fixture
def fresh_nominatim(monkeypatch):
    """An empty cache and no waiting, so tests are fast and don't share answers."""
    monkeypatch.setattr(NominatimGeocoder, "_cache", type(NominatimGeocoder._cache)())
    monkeypatch.setattr(geocoding, "SECONDS_BETWEEN_REQUESTS", 0.0)


def fake_nominatim(requests: list[httpx.Request], status_code: int = 200) -> httpx.Client:
    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status_code, json=NOMINATIM_ANSWER)

    return httpx.Client(transport=httpx.MockTransport(answer))


def test_nominatim_is_asked_once_per_spot_and_told_who_we_are(fresh_nominatim):
    requests: list[httpx.Request] = []
    geocoder = NominatimGeocoder("Fixa-test/1.0", fake_nominatim(requests))
    first = geocoder.find_place(-26.23901, 27.90822)
    second = geocoder.find_place(-26.23902, 27.90823)  # about a metre away: same cached answer
    assert first == second
    assert len(requests) == 1
    assert requests[0].headers["User-Agent"] == "Fixa-test/1.0"


def test_nominatim_requests_are_spaced_a_second_apart(fresh_nominatim, monkeypatch):
    monkeypatch.setattr(geocoding, "SECONDS_BETWEEN_REQUESTS", 1.0)
    monkeypatch.setattr(NominatimGeocoder, "_last_request_at", 0.0)
    sleeps: list[float] = []
    clock = iter([100.0, 100.0, 100.2, 101.0])  # the second request comes 0.2 s after the first
    monkeypatch.setattr(geocoding.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(geocoding.time, "sleep", sleeps.append)
    geocoder = NominatimGeocoder("Fixa-test/1.0", fake_nominatim([]))
    geocoder.find_place(-26.1, 28.0)
    geocoder.find_place(-26.2, 28.1)
    assert sleeps == [pytest.approx(0.8)]


def test_a_nominatim_failure_is_not_cached(fresh_nominatim):
    requests: list[httpx.Request] = []
    geocoder = NominatimGeocoder("Fixa-test/1.0", fake_nominatim(requests, status_code=503))
    for _ in range(2):
        with pytest.raises(PlaceLookupError):
            geocoder.find_place(-26.1, 28.0)
    assert len(requests) == 2
