"""The leak test: no phone number, address or location reaches anyone who shouldn't have it.

One job is walked through every state (posted, quoting, quote_accepted, confirmed, in_progress,
done, followed_up) and through a decline and a cancel. In every state, every route that can
answer for a job is called as every kind of user, and each answer is searched for:

- any phone number, in any way of writing it (the regex), not only the ones in the database
- every address in the database
- every exact latitude and longitude in the database

Before `confirmed` nobody may see any of them. From `confirmed` on, only the job's customer and
its confirmed provider may see the two phone numbers and the job's address, and still nothing else.
"""

import json
import re

import pytest
from sqlmodel import select

from fixa_api.auth import find_user_by_phone, normalise_phone
from fixa_api.job_states import UNLOCKED_STATES
from fixa_api.main import app
from fixa_api.models import Customer, Job, Provider

CUSTOMER = "082 000 0001"  # cust_001 owns the job
OTHER_CUSTOMER = "082 000 0002"
ACCEPTED_PROVIDER = "071 000 0001"  # prov_001, plumber, quote accepted
LOSING_PROVIDER = "071 000 0002"  # prov_002, plumber, quoted but not chosen
BYSTANDER_PLUMBER = "071 000 0003"  # prov_003, never quoted
ELECTRICIAN = "071 000 0006"  # prov_006, other trade

USERS = {
    "anonymous": None,
    "customer": CUSTOMER,
    "other_customer": OTHER_CUSTOMER,
    "accepted_provider": ACCEPTED_PROVIDER,
    "losing_provider": LOSING_PROVIDER,
    "bystander_plumber": BYSTANDER_PLUMBER,
    "electrician": ELECTRICIAN,
}
# The only people who may see contact details, and only once the job is unlocked.
PARTIES = {"customer", "accepted_provider"}

# Any South African looking phone number, written with spaces, dashes or +27.
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+27|0)[\s-]?\d{2}[\s-]?\d{3}[\s-]?\d{4}(?!\d)")
QUOTE_TIME = "2026-10-01T10:00:00+02:00"


def read_routes(job_id: str, quote_id: str) -> list[tuple[str, str]]:
    """Every route that can answer for a job, as (method, path). GET routes are swept in every
    state. The change routes are checked when the walk calls them."""
    return [
        ("GET", f"/api/jobs/{job_id}"),
        ("GET", f"/api/jobs/{job_id}/quotes"),
        ("GET", f"/api/jobs/{job_id}/providers"),
        ("GET", f"/api/jobs/{job_id}/messages"),
        ("GET", "/api/feed"),
        ("GET", "/api/me"),
        ("GET", "/api/providers/prov_001"),
        ("GET", "/api/providers?trade=plumbing"),
        ("GET", "/api/price-range?trade=plumbing&size=small&suburb=Braamfontein"),
    ]


class Sensitive:
    """Everything private in the demo database."""

    def __init__(self, session):
        people = [*session.exec(select(Customer)), *session.exec(select(Provider))]
        jobs = list(session.exec(select(Job)))
        self.phones = {normalise_phone(person.phone) for person in people}
        self.addresses = {person.address for person in people if hasattr(person, "address")}
        self.addresses |= {job.address for job in jobs}
        self.coordinates = {repr(value) for person in people for value in (person.lat, person.lng)}
        self.coordinates |= {repr(value) for job in jobs for value in (job.lat, job.lng)}
        # Whole addresses only: "6 Example Street" must not match inside "46 Example Street".
        self.address_patterns = {
            address: re.compile(rf"(?<!\w){re.escape(address)}(?!\w)") for address in self.addresses
        }

    def found_in(self, text: str) -> set[str]:
        """The private values that appear in text, phones as digits."""
        found = {normalise_phone(match) for match in PHONE_PATTERN.findall(text)}
        found |= {
            address for address, pattern in self.address_patterns.items() if pattern.search(text)
        }
        found |= {coordinate for coordinate in self.coordinates if coordinate in text}
        return found


@pytest.fixture
def world(seeded_client, seeded_session, log_in):
    """Headers for each kind of user, and the private values that exist."""
    headers = {name: ({} if phone is None else log_in(phone)) for name, phone in USERS.items()}
    return seeded_client, headers, Sensitive(seeded_session), seeded_session


def allowed_values(state_is_unlocked: bool, user: str, session, job_id: str) -> set[str]:
    """What this user may legitimately see: the two phones and the address, but only when the
    job is unlocked and they are one of its two parties."""
    if not (state_is_unlocked and user in PARTIES):
        return set()
    job = session.get(Job, job_id)
    customer = session.get(Customer, job.customer_id)
    provider = session.get(Provider, job.provider_id)
    return {normalise_phone(customer.phone), normalise_phone(provider.phone), job.address}


def assert_no_leak(response, sensitive, allowed, where: str) -> None:
    assert response.status_code < 500, f"{where} crashed: {response.text}"
    leaked = sensitive.found_in(response.text) - allowed
    assert not leaked, f"{where} leaked {sorted(leaked)}"


def sweep(world, job_id, quote_id, unlocked: bool, state: str) -> None:
    """Call every read route as every user and check what comes back."""
    client, headers, sensitive, session = world
    for user, user_headers in headers.items():
        allowed = allowed_values(unlocked, user, session, job_id)
        for method, path in read_routes(job_id, quote_id):
            response = client.request(method, path, headers=user_headers)
            assert_no_leak(response, sensitive, allowed, f"{method} {path} as {user} when {state}")


def act(world, user, method, path, state, unlocked=False, **body):
    """Make one change as one user and check the answer for leaks."""
    client, headers, sensitive, session = world
    response = client.request(method, path, headers=headers[user], json=body or None)
    job_id = path.split("/")[3] if path.startswith("/api/jobs/") else None
    allowed = set()
    if unlocked and job_id:
        allowed = allowed_values(True, user, session, job_id)
    assert_no_leak(response, sensitive, allowed, f"{method} {path} as {user} in {state}")
    return response


def new_job(world) -> tuple[str, str]:
    """Lindiwe posts a job and plumber 1 quotes. Returns the job id and quote id."""
    body = {
        "description": "My geyser is leaking, call me on 082 555 0101 at 12 Fake Street",
        "lang": "en",
        "trade": "plumbing",
        "urgency": "urgent",
        "size": "small",
        "suburb": "Braamfontein",
    }
    job = act(world, "customer", "POST", "/api/jobs", "posted", **body).json()
    return job["id"], ""


def quote_as(world, user, job_id, amount) -> str:
    response = act(
        world,
        user,
        "POST",
        f"/api/jobs/{job_id}/quotes",
        "quoting",
        amount_rands=amount,
        when=QUOTE_TIME,
        message="Ngingafika ngoLwesibili, call 083 555 0102 or a@b.com",
    )
    return response.json()["id"]


def chat(world, user, job_id, text, **extra):
    """Send a chat message that tries to slip contact details through, and check the answer."""
    return act(world, user, "POST", f"/api/jobs/{job_id}/messages", "chat", text=text, **extra)


def set_state(session, job_id: str, state: str) -> None:
    """In-progress, done and followed-up have no route yet, so the walk moves the job directly."""
    job = session.get(Job, job_id)
    job.state = state
    session.add(job)
    session.commit()


def test_nothing_leaks_at_any_state_of_a_job(world):
    _, _, _, session = world
    job_id, quote_id = new_job(world)
    sweep(world, job_id, quote_id, unlocked=False, state="posted")

    first_quote = quote_as(world, "accepted_provider", job_id, 450)
    quote_as(world, "losing_provider", job_id, 500)
    sweep(world, job_id, first_quote, unlocked=False, state="quoting")

    chat(world, "accepted_provider", job_id, "Call me on 084 555 0103 or mail me at x@y.com")
    chat(world, "customer", job_id, "zero eight five 555 0104", provider_id="prov_001")
    sweep(world, job_id, first_quote, unlocked=False, state="quoting with chat")

    act(world, "customer", "POST", f"/api/quotes/{first_quote}/accept", "quote_accepted")
    sweep(world, job_id, first_quote, unlocked=False, state="quote_accepted")

    act(world, "accepted_provider", "POST", f"/api/jobs/{job_id}/confirm", "confirmed", True)
    sweep(world, job_id, first_quote, unlocked=True, state="confirmed")

    for state in ("in_progress", "done", "followed_up"):
        set_state(session, job_id, state)
        sweep(world, job_id, first_quote, unlocked=True, state=state)


def test_nothing_leaks_when_a_provider_declines(world):
    job_id, _ = new_job(world)
    quote_id = quote_as(world, "accepted_provider", job_id, 450)
    act(world, "customer", "POST", f"/api/quotes/{quote_id}/accept", "quote_accepted")

    act(world, "accepted_provider", "POST", f"/api/jobs/{job_id}/decline", "declined")

    sweep(world, job_id, quote_id, unlocked=False, state="back to quoting after a decline")


def test_details_lock_again_when_a_confirmed_job_is_cancelled(world):
    job_id, _ = new_job(world)
    quote_id = quote_as(world, "accepted_provider", job_id, 450)
    act(world, "customer", "POST", f"/api/quotes/{quote_id}/accept", "quote_accepted")
    act(world, "accepted_provider", "POST", f"/api/jobs/{job_id}/confirm", "confirmed", True)

    act(world, "customer", "POST", f"/api/jobs/{job_id}/cancel", "cancelled")

    sweep(world, job_id, quote_id, unlocked=False, state="cancelled")


def test_a_cancelled_job_that_never_reached_confirmed_leaks_nothing(world):
    job_id, _ = new_job(world)
    act(world, "customer", "POST", f"/api/jobs/{job_id}/cancel", "cancelled")

    sweep(world, job_id, "", unlocked=False, state="cancelled from posted")


def find_user_id(session, phone: str) -> str:
    return find_user_by_phone(session, phone).id


def test_the_seeded_jobs_leak_nothing_either(world):
    """The demo data has jobs in every state, so sweep each one as the customer's rivals."""
    client, headers, sensitive, session = world
    for job in session.exec(select(Job)):
        parties = {job.customer_id, job.provider_id}
        for user in ("other_customer", "bystander_plumber", "electrician", "anonymous"):
            phone = USERS[user]
            if phone and find_user_id(session, phone) in parties:
                continue  # a seeded job's real customer or provider may see their own details
            for path in (f"/api/jobs/{job.id}", f"/api/jobs/{job.id}/quotes"):
                response = client.get(path, headers=headers[user])
                assert_no_leak(response, sensitive, set(), f"GET {path} as {user}")


def own_job_allowed_values(session, job: Job, user_id: str) -> set[str]:
    """What a person may see of one of their own jobs: its phones and address, only once it's
    unlocked and only if they are its customer or its provider."""
    if job.state not in UNLOCKED_STATES or user_id not in (job.customer_id, job.provider_id):
        return set()
    customer = session.get(Customer, job.customer_id)
    provider = session.get(Provider, job.provider_id)
    return {normalise_phone(customer.phone), normalise_phone(provider.phone), job.address}


def sweep_own_jobs(world, state: str) -> None:
    """GET /api/jobs lists each person's own jobs, seeded ones included, so every job in it is
    checked on its own, rather than against the one job the walk follows."""
    client, headers, sensitive, session = world
    for user, user_headers in headers.items():
        response = client.get("/api/jobs", headers=user_headers)
        assert response.status_code < 500, f"GET /api/jobs as {user} crashed: {response.text}"
        if USERS[user] is None:
            assert response.status_code == 401
            continue
        user_id = find_user_id(session, USERS[user])
        for listed in response.json():
            allowed = own_job_allowed_values(session, session.get(Job, listed["id"]), user_id)
            leaked = sensitive.found_in(json.dumps(listed)) - allowed
            assert not leaked, (
                f"GET /api/jobs as {user} when {state}: {listed['id']} leaked {sorted(leaked)}"
            )


def test_a_persons_own_jobs_show_details_only_on_their_unlocked_jobs(world):
    client, headers, _, _ = world
    job_id, _ = new_job(world)
    first_quote = quote_as(world, "accepted_provider", job_id, 450)
    quote_as(world, "losing_provider", job_id, 500)
    sweep_own_jobs(world, "quoting")

    act(world, "customer", "POST", f"/api/quotes/{first_quote}/accept", "quote_accepted")
    sweep_own_jobs(world, "quote_accepted")

    act(world, "accepted_provider", "POST", f"/api/jobs/{job_id}/confirm", "confirmed", True)
    sweep_own_jobs(world, "confirmed")
    listed = client.get("/api/jobs", headers=headers["accepted_provider"]).json()
    assert "address" in next(job for job in listed if job["id"] == job_id)

    act(world, "customer", "POST", f"/api/jobs/{job_id}/cancel", "cancelled")
    sweep_own_jobs(world, "cancelled")


def test_every_route_is_covered_by_this_test_or_marked_as_not_about_jobs():
    """A new route fails this test until someone decides how it is leak-checked. Add job or
    contact-carrying routes to read_routes above, or to the list below with a reason."""
    covered = {path.split("?")[0] for _, path in read_routes("{job_id}", "{quote_id}")}
    covered |= {
        # change routes, checked by act() during the walks; GET /api/jobs by sweep_own_jobs()
        "/api/jobs",
        "/api/jobs/{job_id}/quotes",
        "/api/quotes/{quote_id}/accept",
        "/api/jobs/{job_id}/confirm",
        "/api/jobs/{job_id}/decline",
        "/api/jobs/{job_id}/cancel",
        "/api/jobs/{job_id}/check-in",
        "/api/jobs/{job_id}/check-out",
        "/api/jobs/{job_id}/done",
        "/api/jobs/{job_id}/still-working",
        "/api/follow-ups",
        "/api/reports",
        "/api/providers/{provider_id}/vouches",
        # carry no job data or contact details
        "/api/health",
        "/api/auth/otp",
        "/api/auth/verify",
        "/api/photos",
        "/api/photos/{photo_id}",
        "/api/jobs/understand",
        "/api/jobs/{job_id}/messages",
        "/api/providers",
        "/api/providers/{provider_id}",
        "/api/price-range",
        "/api/identity/check-number",
        "/api/identity/verify",
        "/api/off-app-jobs",
        "/api/sms/inbound",
        "/api/ussd",
        "/api/record/export",
        "/api/record/summary",
        "/api/record/exports/{filename}",
        "/record/{provider_id}",
        "/verify/{code}",
    }
    covered = {re.sub(r"\{[^}]+\}", "{}", path) for path in covered}
    # The schema lists every route, including those added through routers (app.routes doesn't).
    actual = {
        re.sub(r"\{[^}]+\}", "{}", path)
        for path in app.openapi()["paths"]
        if path.startswith(("/api", "/record", "/verify"))
    }
    assert len(actual) > 20, "the route list came back nearly empty"

    assert actual - covered == set(), f"routes the leak test doesn't know about: {actual - covered}"
