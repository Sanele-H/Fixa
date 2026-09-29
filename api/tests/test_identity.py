"""The offline ID check, the verifiers, and the identity routes."""

import datetime as dt
import json

import pytest
from sqlmodel import select

from fixa_api.fixtures import FIXTURES_PATH
from fixa_api.identity import (
    MOCK_REGISTER,
    MockVerifier,
    SmileIdVerifier,
    VerifierUnavailableError,
    better_tier,
    check_id_number,
    get_verifier,
    luhn_check_digit,
)
from fixa_api.main import app
from fixa_api.models import IdentityCheck, Provider

TODAY = dt.date(2026, 9, 29)
THABO, THABO_ID = "071 000 0001", next(iter(MOCK_REGISTER))
CUSTOMER = "082 000 0001"


def make_id(birth_date: str, sequence: str = "5009", middle: str = "08") -> str:
    twelve = f"{birth_date}{sequence}{middle}"
    return twelve + luhn_check_digit(twelve)


def fixture_keys(file_name: str) -> set[str]:
    return set(json.loads((FIXTURES_PATH / file_name).read_text(encoding="utf-8")))


# --- the offline check ----------------------------------------------------------------------


def test_a_well_formed_id_is_valid_and_gives_the_birth_date():
    result = check_id_number(make_id("800101"), TODAY)

    assert result == {"valid": True, "reason": None, "date_of_birth": "1980-01-01"}


def test_the_register_ids_all_pass_the_offline_check():
    assert all(check_id_number(id_number, TODAY)["valid"] for id_number in MOCK_REGISTER)


def test_a_typo_fails_the_checksum():
    good = make_id("800101")
    typo = good[:5] + ("2" if good[5] != "2" else "3") + good[6:]

    assert check_id_number(typo, TODAY) == {
        "valid": False,
        "reason": "checksum",
        "date_of_birth": None,
    }


@pytest.mark.parametrize(
    ("id_number", "reason"),
    [
        ("", "digits"),
        ("80010150090", "length"),
        ("80010150090871", "length"),
        ("80010150090AB", "digits"),
        (make_id("801301"), "date"),  # month 13
        (make_id("800230"), "date"),  # 30 February
        (make_id("991231", "5009"), "checksum"),
    ],
)
def test_bad_ids_are_refused_with_a_reason(id_number, reason):
    if reason == "checksum":
        id_number = id_number[:-1] + str((int(id_number[-1]) + 1) % 10)

    result = check_id_number(id_number, TODAY)

    assert result["valid"] is False
    assert result["reason"] == reason


def test_spaces_and_dashes_are_ignored():
    spaced = make_id("800101")
    spaced = f"{spaced[:6]} {spaced[6:10]}-{spaced[10:]}"

    assert check_id_number(spaced, TODAY)["valid"] is True


def test_two_digit_years_are_read_as_the_nearest_past_year():
    assert check_id_number(make_id("050615"), TODAY)["date_of_birth"] == "2005-06-15"
    assert check_id_number(make_id("990615"), TODAY)["date_of_birth"] == "1999-06-15"


def test_a_birth_date_in_the_future_is_refused():
    assert check_id_number(make_id("261231"), TODAY)["reason"] == "date"  # 31 Dec 2026


# --- the verifiers --------------------------------------------------------------------------


def test_the_mock_verifier_knows_the_register_and_matches_names():
    verifier = MockVerifier()

    exact = verifier.verify(THABO_ID, "Thabo Nkosi", consent=True)
    partial = verifier.verify(THABO_ID, "thabo", consent=True)
    wrong_name = verifier.verify(THABO_ID, "Someone Else", consent=True)
    unknown = verifier.verify(make_id("700101", "1111"), "Thabo Nkosi", consent=True)

    assert (exact.verified, exact.name_match) == (True, True)
    assert (partial.verified, partial.name_match) == (True, True)
    assert (wrong_name.verified, wrong_name.name_match) == (True, False)
    assert (unknown.verified, unknown.name_match) == (False, False)
    assert exact.provider == "mock_sandbox"


class FakeSmileApi:
    """Stands in for smile_id_core.IdApi and records what it was asked."""

    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response, error, []

    def __call__(self, partner_id, api_key, server):
        self.server = server
        return self

    def submit_job(self, partner_params, id_params):
        self.calls.append((partner_params, id_params))
        if self.error:
            raise self.error
        return self.response


@pytest.fixture
def smile_keys(monkeypatch):
    monkeypatch.setenv("SMILE_ID_PARTNER_ID", "1234")
    monkeypatch.setenv("SMILE_ID_API_KEY", "not-a-real-key")


def test_smile_verifier_asks_for_a_za_national_id_and_reads_the_actions(smile_keys):
    fake = FakeSmileApi(
        {
            "SmileJobID": "job-77",
            "Actions": {"Verify_ID_Number": "Verified", "Names": "Exact Match"},
        }
    )

    result = SmileIdVerifier(api_factory=fake).verify(THABO_ID, "Thabo Nkosi", consent=True)

    partner_params, id_params = fake.calls[0]
    assert partner_params["job_type"] == 5
    assert id_params == {
        "country": "ZA",
        "id_type": "NATIONAL_ID",
        "id_number": THABO_ID,
        "first_name": "Thabo",
        "last_name": "Nkosi",
    }
    assert fake.server == 0  # the sandbox
    assert (result.verified, result.name_match) == (True, True)
    assert (result.provider, result.reference) == ("smile_id_sandbox", "job-77")


def test_smile_verifier_reads_a_not_found_result(smile_keys):
    fake = FakeSmileApi({"Actions": {"Verify_ID_Number": "Not Verified", "Names": "No Match"}})

    result = SmileIdVerifier(api_factory=fake).verify(THABO_ID, "Thabo Nkosi", consent=True)

    assert (result.verified, result.name_match) == (False, False)


def test_smile_verifier_turns_any_failure_into_unavailable(smile_keys):
    fake = FakeSmileApi(error=RuntimeError("timeout"))

    with pytest.raises(VerifierUnavailableError):
        SmileIdVerifier(api_factory=fake).verify(THABO_ID, "Thabo Nkosi", consent=True)


def test_smile_verifier_needs_keys(monkeypatch):
    monkeypatch.delenv("SMILE_ID_PARTNER_ID", raising=False)
    monkeypatch.delenv("SMILE_ID_API_KEY", raising=False)

    with pytest.raises(VerifierUnavailableError):
        SmileIdVerifier(api_factory=FakeSmileApi())


def test_the_verifier_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("IDENTITY_VERIFIER", "mock")
    assert isinstance(get_verifier(), MockVerifier)
    monkeypatch.setenv("IDENTITY_VERIFIER", "nonsense")
    with pytest.raises(VerifierUnavailableError):
        get_verifier()


def test_a_badge_is_never_lowered():
    assert better_tier("home_affairs", "id_number") == "home_affairs"
    assert better_tier("none", "id_number") == "id_number"


# --- the routes -----------------------------------------------------------------------------


@pytest.fixture
def thabo(log_in):
    return log_in(THABO)


def verify(client, headers, id_number=THABO_ID, names="Thabo Nkosi", consent=True):
    body = {"id_number": id_number, "names": names, "consent": consent}
    return client.post("/api/identity/verify", json=body, headers=headers)


def test_check_number_answers_instantly_with_the_contract_shape(seeded_client, thabo):
    ok = seeded_client.post(
        "/api/identity/check-number", json={"id_number": THABO_ID}, headers=thabo
    )
    typo = seeded_client.post(
        "/api/identity/check-number", json={"id_number": "800101500908"}, headers=thabo
    )

    assert set(ok.json()) == fixture_keys("id_number_check.json")
    assert ok.json()["valid"] is True
    assert (typo.json()["valid"], typo.json()["reason"]) == (False, "length")


def test_the_right_id_and_name_earn_the_home_affairs_badge(seeded_client, thabo):
    response = verify(seeded_client, thabo)

    assert response.status_code == 200
    result = response.json()
    assert set(result) == fixture_keys("id_result.json")
    assert (result["tier"], result["verified"], result["name_match"]) == (
        "home_affairs",
        True,
        True,
    )
    assert seeded_client.get("/api/me", headers=thabo).json()["id_badge"] == "home_affairs"


def test_the_badge_shows_on_the_profile_customers_see(seeded_client, log_in, thabo):
    verify(seeded_client, thabo)

    profile = seeded_client.get("/api/providers/prov_001", headers=log_in(CUSTOMER)).json()

    assert profile["id_badge"] == "home_affairs"


def test_a_wrong_name_earns_only_the_id_number_badge(seeded_client, log_in):
    headers = log_in("071 000 0005")

    result = verify(seeded_client, headers, names="Someone Else").json()

    assert (result["tier"], result["verified"], result["name_match"]) == ("id_number", True, False)
    assert seeded_client.get("/api/me", headers=headers).json()["id_badge"] == "id_number"


def test_an_id_the_verifier_does_not_know_earns_only_the_id_number_badge(seeded_client, log_in):
    headers = log_in("071 000 0005")

    result = verify(seeded_client, headers, id_number=make_id("700101", "1111")).json()

    assert (result["tier"], result["verified"]) == ("id_number", False)


def test_a_later_failed_check_does_not_take_a_badge_away(seeded_client, thabo):
    verify(seeded_client, thabo)

    verify(seeded_client, thabo, names="Someone Else")

    assert seeded_client.get("/api/me", headers=thabo).json()["id_badge"] == "home_affairs"


def test_a_typo_is_refused_with_the_reason_and_uses_no_attempt(
    seeded_client, seeded_session, thabo
):
    response = verify(
        seeded_client,
        thabo,
        id_number=THABO_ID[:-1] + "0" if THABO_ID[-1] != "0" else THABO_ID[:-1] + "1",
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {"error": "invalid_id_number", "reason": "checksum"}
    assert list(seeded_session.exec(select(IdentityCheck))) == []


def test_consent_is_required(seeded_client, thabo):
    assert verify(seeded_client, thabo, consent=False).status_code == 422
    no_consent_field = seeded_client.post(
        "/api/identity/verify", json={"id_number": THABO_ID, "names": "Thabo Nkosi"}, headers=thabo
    )
    assert no_consent_field.status_code == 422


def test_only_the_result_is_stored_never_the_id_number_or_names(
    seeded_client, seeded_session, thabo
):
    verify(seeded_client, thabo)

    rows = list(seeded_session.exec(select(IdentityCheck)))

    assert len(rows) == 1
    stored = json.dumps(rows[0].model_dump(), default=str)
    assert THABO_ID not in stored
    assert "Nkosi" not in stored
    assert set(rows[0].model_dump()) == {
        "id",
        "provider_id",
        "tier",
        "verified",
        "name_match",
        "provider",
        "reference",
        "checked_at",
        "consent_at",
    }


def test_the_id_number_and_names_never_come_back_in_a_response(seeded_client, thabo):
    text = verify(seeded_client, thabo).text

    assert THABO_ID not in text
    assert "Nkosi" not in text


def test_a_sixth_check_in_a_day_is_refused(seeded_client, thabo):
    for _ in range(5):
        assert verify(seeded_client, thabo).status_code == 200

    assert verify(seeded_client, thabo).status_code == 429


def test_an_unavailable_verifier_is_a_503_and_changes_nothing(seeded_client, seeded_session, thabo):
    class Down:
        def verify(self, id_number, names, consent):
            raise VerifierUnavailableError("down")

    app.dependency_overrides[get_verifier] = lambda: Down()
    try:
        response = verify(seeded_client, thabo)
    finally:
        del app.dependency_overrides[get_verifier]

    assert response.status_code == 503
    assert list(seeded_session.exec(select(IdentityCheck))) == []
    assert seeded_session.get(Provider, "prov_001").id_badge != "home_affairs"


def test_only_a_provider_can_use_the_identity_routes(seeded_client, log_in):
    customer = log_in(CUSTOMER)

    assert verify(seeded_client, customer).status_code == 403
    assert (
        seeded_client.post(
            "/api/identity/check-number", json={"id_number": THABO_ID}, headers=customer
        ).status_code
        == 403
    )
    assert verify(seeded_client, {}).status_code == 401
