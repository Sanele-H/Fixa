"""The parts of the API that already work. These must stay green."""

from fixa.api.dependencies import DEMO_USER_HEADER


def test_health_says_ok(api_client):
    response = api_client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_users_list_includes_the_demo_pair_without_contact_details(api_client):
    response = api_client.get("/api/users")

    users_by_id = {user["id"]: user for user in response.json()}
    assert {"customer-van-wyk", "provider-nomsa"} <= users_by_id.keys()
    assert "phoneNumber" not in users_by_id["provider-nomsa"]


def test_json_uses_camel_case(api_client):
    nomsa = api_client.get("/api/users/me", headers={DEMO_USER_HEADER: "provider-nomsa"}).json()

    assert nomsa["preferredLanguage"] == "zu"


def test_requests_without_a_demo_user_are_rejected(api_client):
    assert api_client.get("/api/users/me").status_code == 401


def test_changing_language_is_saved(api_client):
    headers = {DEMO_USER_HEADER: "customer-van-wyk"}

    api_client.patch("/api/users/me", json={"preferredLanguage": "en"}, headers=headers)

    assert api_client.get("/api/users/me", headers=headers).json()["preferredLanguage"] == "en"


def test_unbuilt_endpoints_answer_501_not_500(api_client):
    response = api_client.get("/api/jobs", headers={DEMO_USER_HEADER: "customer-van-wyk"})

    # Role 3: once list_jobs_for_user works, change this to expect 200.
    assert response.status_code == 501
