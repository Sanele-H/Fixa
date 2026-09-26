"""Smoke test for the API shell. Keeps CI green until P2's real tests arrive."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from fixa_api.main import app

FIXTURES_PATH = Path(__file__).resolve().parents[2] / "contracts" / "fixtures"


def test_health_matches_its_fixture():
    expected = json.loads((FIXTURES_PATH / "health.json").read_text(encoding="utf-8"))

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == expected
