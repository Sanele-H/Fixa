"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from fixa.api.dependencies import get_store
from fixa.api.main import app
from fixa.storage.memory_store import MemoryStore


@pytest.fixture
def store() -> MemoryStore:
    """A fresh store with the demo data, so tests never affect each other."""
    return MemoryStore()


@pytest.fixture
def api_client(store: MemoryStore):
    """An HTTP client for the app, wired to the fresh `store`."""
    app.dependency_overrides[get_store] = lambda: store
    yield TestClient(app)
    app.dependency_overrides.clear()
