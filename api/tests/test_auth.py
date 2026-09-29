"""Login with the seeded demo users, the JWT, and /api/me."""

import datetime as dt
import json
from typing import Annotated

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from fixa_api.auth import TOKEN_ALGORITHM, jwt_secret, normalise_phone, require_role
from fixa_api.db import get_session
from fixa_api.fixtures import FIXTURES_PATH
from fixa_api.models import Provider

CUSTOMER_PHONE = "082 000 0001"  # cust_001, Lindiwe
PROVIDER_PHONE = "071 000 0001"  # prov_001, Thabo


@pytest.fixture
def seeded_client(client, seeded_session):
    return client


def log_in(client: TestClient, phone: str, otp: str = "123456"):
    return client.post("/api/auth/verify", json={"phone": phone, "otp": otp})


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_verify_returns_a_token_and_the_user_shape(seeded_client):
    response = log_in(seeded_client, CUSTOMER_PHONE)

    assert response.status_code == 200
    body = response.json()
    fixture = json.loads((FIXTURES_PATH / "auth_verify.json").read_text(encoding="utf-8"))
    assert body["user"] == fixture["user"]
    assert (
        jwt.decode(body["token"], jwt_secret(), algorithms=[TOKEN_ALGORITHM])["sub"] == "cust_001"
    )


def test_a_provider_can_log_in_too(seeded_client):
    user = log_in(seeded_client, PROVIDER_PHONE).json()["user"]

    assert (user["id"], user["role"]) == ("prov_001", "provider")


@pytest.mark.parametrize("phone", ["+27 82 000 0001", "0820000001", "+27820000001"])
def test_the_phone_can_be_written_in_other_ways(seeded_client, phone):
    assert log_in(seeded_client, phone).json()["user"]["id"] == "cust_001"


def test_user_summary_never_includes_contact_details(seeded_client):
    body = log_in(seeded_client, CUSTOMER_PHONE).json()

    assert set(body["user"]) == {"id", "role", "display_name", "lang", "suburb", "id_badge"}


@pytest.mark.parametrize(
    ("phone", "otp"),
    [(CUSTOMER_PHONE, "000000"), ("082 999 9999", "123456"), ("", "123456")],
)
def test_wrong_code_or_unknown_number_is_the_same_401(seeded_client, phone, otp):
    response = log_in(seeded_client, phone, otp)

    assert response.status_code == 401
    assert response.json() == {"detail": "Wrong phone number or code"}


def test_otp_request_answers_204_for_known_and_unknown_numbers(seeded_client):
    for phone in (CUSTOMER_PHONE, "082 999 9999"):
        assert seeded_client.post("/api/auth/otp", json={"phone": phone}).status_code == 204


def test_the_otp_comes_from_the_environment(seeded_client, monkeypatch):
    monkeypatch.setenv("DEMO_OTP", "654321")

    assert log_in(seeded_client, CUSTOMER_PHONE).status_code == 401
    assert log_in(seeded_client, CUSTOMER_PHONE, "654321").status_code == 200


def test_me_returns_the_signed_in_user(seeded_client):
    token = log_in(seeded_client, PROVIDER_PHONE).json()["token"]

    response = seeded_client.get("/api/me", headers=bearer(token))

    assert response.status_code == 200
    assert response.json()["id"] == "prov_001"


def test_patch_me_changes_the_language_and_keeps_it(seeded_client):
    token = log_in(seeded_client, CUSTOMER_PHONE).json()["token"]

    changed = seeded_client.patch("/api/me", json={"lang": "zu"}, headers=bearer(token))

    assert changed.json()["lang"] == "zu"
    assert seeded_client.get("/api/me", headers=bearer(token)).json()["lang"] == "zu"


def test_patch_me_rejects_an_unknown_language(seeded_client):
    token = log_in(seeded_client, CUSTOMER_PHONE).json()["token"]

    response = seeded_client.patch("/api/me", json={"lang": "fr"}, headers=bearer(token))

    assert response.status_code == 422


def expired_token(user_id: str) -> str:
    claims = {"sub": user_id, "exp": dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1)}
    return jwt.encode(claims, jwt_secret(), algorithm=TOKEN_ALGORITHM)


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer not-a-token"},
        {"Authorization": "Basic abc"},
        bearer(jwt.encode({"sub": "cust_001"}, "another-secret", algorithm=TOKEN_ALGORITHM)),
        bearer(expired_token("cust_001")),
        bearer(jwt.encode({"sub": "ghost", "exp": 9999999999}, "change-me", algorithm="HS256")),
    ],
)
def test_me_needs_a_valid_token(seeded_client, headers):
    assert seeded_client.get("/api/me", headers=headers).status_code == 401


def test_a_token_signed_with_no_algorithm_is_refused(seeded_client):
    forged = jwt.encode({"sub": "cust_001"}, None, algorithm="none")

    assert seeded_client.get("/api/me", headers=bearer(forged)).status_code == 401


def test_normalise_phone():
    assert normalise_phone("+27 (82) 000-0001") == "0820000001"


def test_require_role_allows_only_that_role(seeded_client, session):
    """Check the guard on a tiny app of its own, so the real app's routes stay untouched."""
    small_app = FastAPI()

    @small_app.get("/only-providers")
    def only_providers(user: Annotated[Provider, Depends(require_role("provider"))]):
        return {"id": user.id}

    small_app.dependency_overrides[get_session] = lambda: session
    small_client = TestClient(small_app)
    customer = log_in(seeded_client, CUSTOMER_PHONE).json()["token"]
    provider = log_in(seeded_client, PROVIDER_PHONE).json()["token"]

    assert small_client.get("/only-providers", headers=bearer(customer)).status_code == 403
    assert small_client.get("/only-providers", headers=bearer(provider)).json() == {
        "id": "prov_001"
    }
