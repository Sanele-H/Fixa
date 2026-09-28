"""Shared test fixtures: a fresh in-memory database per test, so tests never touch fixa.db."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from fixa_api.db import IN_MEMORY_DATABASE_URL, create_database_engine, get_session
from fixa_api.main import app
from fixa_api.seed import SEED_TABLES, create_rows_from_seed_file


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
