"""Shared test fixtures: a fresh in-memory database per test, so tests never touch fixa.db."""

from collections import OrderedDict

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from fixa_api.db import IN_MEMORY_DATABASE_URL, create_database_engine, get_session
from fixa_api.main import app
from fixa_api.seed import SEED_TABLES, create_rows_from_seed_file


@pytest.fixture(autouse=True)
def fake_translation_backend(monkeypatch):
    """Translate with the fake backend in every test, whatever .env says.

    fixa_api.db loads .env, so a laptop set to TRANSLATION_BACKEND=azure would otherwise make
    paid calls from the tests, and the chat tests couldn't find the fake's "[en]" language tags.
    The translation cache starts empty too, so no test sees another test's translations.
    """
    monkeypatch.setenv("TRANSLATION_BACKEND", "fake")
    monkeypatch.setattr("lang.translation._translation_cache", OrderedDict())


@pytest.fixture(autouse=True)
def push_turned_off(monkeypatch):
    """No real push notifications from the tests, whatever VAPID keys .env has. The push tests
    turn it back on with fake keys."""
    monkeypatch.delenv("VAPID_PRIVATE_KEY", raising=False)


@pytest.fixture(autouse=True)
def mock_payments(monkeypatch):
    """Pay through the test checkout in every test, whatever PAYMENT_PROVIDER .env has."""
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")


@pytest.fixture
def session():
    """Yield a session on a new, empty in-memory database. Each test gets its own."""
    test_engine = create_database_engine(IN_MEMORY_DATABASE_URL)
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as test_session:
        yield test_session


@pytest.fixture
def seeded_session(session):
    """The test session with every seed file loaded, for tests that need the demo data."""
    for file_name, model in SEED_TABLES:
        create_rows_from_seed_file(session, file_name, model)
    session.commit()
    return session


@pytest.fixture
def client(session):
    """Yield a TestClient whose routes use the test session instead of fixa.db."""
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_client(client, seeded_session):
    """A test client on a database that has the demo data loaded."""
    return client


@pytest.fixture
def log_in(seeded_client):
    """log_in("082 000 0001") returns the Authorization header for that demo user."""

    def sign_in(phone: str) -> dict[str, str]:
        response = seeded_client.post("/api/auth/verify", json={"phone": phone, "otp": "123456"})
        return {"Authorization": f"Bearer {response.json()['token']}"}

    return sign_in
