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
    (
        "POST",
        "/api/off-app-jobs",
        {
            "customer_phone": "+27821234567",
            "trade_task": "geyser repair",
            "date": "2026-09-01",
            "suburb": "Braamfontein",
        },
        201,
        "off_app_job.json",
    ),
    ("POST", "/api/record/export", {"mode": "arpl"}, 200, "record_export.json"),
]


def read_fixture(file_name: str):
    return json.loads((FIXTURES_PATH / file_name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(("method", "path", "body", "status", "fixture"), ROUTES)
def test_route_returns_its_fixture(method, path, body, status, fixture):
    response = client.request(method, path, json=body)

    assert response.status_code == status
    if fixture is not None:
        assert response.json() == read_fixture(fixture)


def test_photo_upload_returns_its_fixture():
    response = client.post("/api/photos", files={"photo": ("leak.jpg", b"jpeg", "image/jpeg")})

    assert response.status_code == 200
    assert response.json() == read_fixture("photo.json")


def test_sms_webhook_accepts_form_fields():
    response = client.post("/api/sms/inbound", data={"from": "+27821234567", "text": "YES 1234"})

    assert response.status_code == 200


@pytest.mark.parametrize("path", ["/record/prov_001", "/verify/FX7K2Q"])
def test_link_pages_are_plain_html_without_scripts(path):
    response = client.get(path)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<script" not in response.text.lower()
