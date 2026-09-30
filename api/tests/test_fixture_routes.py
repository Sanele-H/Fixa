"""Routes that still answer with their fixture. The real ones are tested in their own files."""

import json

import pytest
from fastapi.testclient import TestClient

from fixa_api.fixtures import FIXTURES_PATH
from fixa_api.main import app

client = TestClient(app)

# (method, path, request body, expected status, fixture file, or None for no JSON body)
ROUTES = [
    ("GET", "/api/health", None, 200, "health.json"),
    ("POST", "/api/auth/otp", {"phone": "+27821234567"}, 204, None),
]


def read_fixture(file_name: str):
    return json.loads((FIXTURES_PATH / file_name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(("method", "path", "body", "status", "fixture"), ROUTES)
def test_route_returns_its_fixture(method, path, body, status, fixture):
    response = client.request(method, path, json=body)

    assert response.status_code == status
    if fixture is not None:
        assert response.json() == read_fixture(fixture)
