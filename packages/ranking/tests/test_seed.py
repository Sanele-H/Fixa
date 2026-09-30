"""The demo seed data: reproducible, consistent, private, and in line with the fixtures."""

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

import pytest

from ranking.seed import APP_TABLE_NAMES, generate_seed, read_trades, write_seed

REPO_ROOT_PATH = Path(__file__).resolve().parents[3]
FIXTURES_PATH = REPO_ROOT_PATH / "contracts" / "fixtures"
TODAY = date(2026, 9, 29)
APP_LANGUAGES = {"en", "zu", "xh"}
MADE_UP_PHONE_PATTERN = re.compile(r"0\d\d 000 \d{4}")  # the fixtures' pattern, e.g. 082 000 0001
HIDDEN_FIELD_NAMES = {"true_skill", "first_language"}
ARPL_EXPERIENCE_YEARS = 3
DAYS_PER_YEAR = 365


@pytest.fixture(scope="module")
def trades():
    return read_trades()


@pytest.fixture(scope="module")
def seed(trades):
    return generate_seed(trades, today=TODAY)


def read_fixture(file_name: str):
    """Reads one JSON fixture from contracts/fixtures/."""
    return json.loads((FIXTURES_PATH / file_name).read_text(encoding="utf-8"))


def find_row(rows: list[dict], row_id: str) -> dict:
    """Finds the row with the given id."""
    return next(row for row in rows if row["id"] == row_id)


def list_completed_app_jobs(seed: dict, provider_id: str) -> list[dict]:
    """Lists a provider's completed in-app jobs."""
    return [job for job in seed["jobs"] if job["provider_id"] == provider_id and job["completed"]]


def list_off_app_jobs(seed: dict, provider_id: str, state: str) -> list[dict]:
    """Lists a provider's off-app jobs in the given state."""
    return [
        job
        for job in seed["off_app_jobs"]
        if job["provider_id"] == provider_id and job["state"] == state
    ]


def count_repeat_customers(jobs: list[dict]) -> int:
    """Counts customers who appear on more than one of these jobs."""
    job_counts_by_customer = Counter(job["customer_id"] for job in jobs)
    return sum(1 for job_count in job_counts_by_customer.values() if job_count > 1)


def test_same_seed_gives_the_same_data(trades, seed):
    assert generate_seed(trades, today=TODAY) == seed


def test_another_seed_gives_other_data(trades, seed):
    assert generate_seed(trades, seed=1, today=TODAY)["jobs"] != seed["jobs"]


@pytest.mark.parametrize("table_name", APP_TABLE_NAMES)
def test_ids_are_unique(seed, table_name):
    ids = [row["id"] for row in seed[table_name]]
    assert len(ids) == len(set(ids))


def test_every_reference_points_to_an_existing_row(seed):
    provider_ids = {provider["id"] for provider in seed["providers"]}
    customer_ids = {customer["id"] for customer in seed["customers"]}
    job_ids = {job["id"] for job in seed["jobs"]}
    assert {job["customer_id"] for job in seed["jobs"]} <= customer_ids
    assert {job["provider_id"] for job in seed["jobs"]} - {None} <= provider_ids
    assert {quote["job_id"] for quote in seed["quotes"]} <= job_ids
    assert {quote["provider_id"] for quote in seed["quotes"]} <= provider_ids
    assert {job["provider_id"] for job in seed["off_app_jobs"]} <= provider_ids
    assert [row["provider_id"] for row in seed["hidden_truth"]] == [
        provider["id"] for provider in seed["providers"]
    ]


def test_codes_are_the_agreed_ones(trades, seed):
    trade_ids = {trade.id for trade in trades}
    users = seed["providers"] + seed["customers"]
    assert {user["lang"] for user in users} <= APP_LANGUAGES
    assert {lang for provider in seed["providers"] for lang in provider["langs"]} <= APP_LANGUAGES
    assert {user["id_badge"] for user in users} <= {"none", "id_number", "home_affairs"}
    assert {trade for provider in seed["providers"] for trade in provider["trades"]} <= trade_ids
    assert {job["trade"] for job in seed["jobs"] + seed["off_app_jobs"]} <= trade_ids
    assert {job["size"] for job in seed["jobs"]} <= {"small", "medium", "large"}
    assert {job["urgency"] for job in seed["jobs"]} <= {"low", "normal", "urgent"}
    job_states = {"posted", "quoting", "done", "followed_up", "cancelled"}
    assert {job["state"] for job in seed["jobs"]} <= job_states
    assert {quote["state"] for quote in seed["quotes"]} <= {"open", "accepted", "declined"}


@pytest.mark.parametrize("table_name", APP_TABLE_NAMES)
def test_hidden_fields_stay_out_of_the_app_tables(seed, table_name):
    for row in seed[table_name]:
        assert not any(field_name.startswith("_") for field_name in row)
        assert not HIDDEN_FIELD_NAMES & row.keys()


def test_hidden_truth_has_a_skill_and_group_for_every_provider(seed):
    for row in seed["hidden_truth"]:
        assert 0 <= row["true_skill"] <= 1
        assert row["first_language"]


def test_phone_numbers_are_made_up_in_the_fixtures_pattern(seed):
    phones = [user["phone"] for user in seed["providers"] + seed["customers"]]
    phones += [job["customer_phone"] for job in seed["off_app_jobs"]]
    assert all(MADE_UP_PHONE_PATTERN.fullmatch(phone) for phone in phones)
    assert len(phones) == len(set(phones))


def test_licensed_work_goes_only_to_licensed_providers(seed):
    licensed_ids = {provider["id"] for provider in seed["providers"] if provider["licensed"]}
    licensed_jobs = [job for job in seed["jobs"] if job["needs_licence"] and job["provider_id"]]
    assert licensed_jobs
    assert {job["provider_id"] for job in licensed_jobs} <= licensed_ids


def test_every_finished_job_has_its_providers_accepted_quote(seed):
    accepted = {(q["job_id"], q["provider_id"]) for q in seed["quotes"] if q["state"] == "accepted"}
    finished_jobs = [job for job in seed["jobs"] if job["finished_on"]]
    assert all((job["id"], job["provider_id"]) in accepted for job in finished_jobs)


def test_open_jobs_have_open_quotes_only_once_quoting(seed):
    open_quote_counts = Counter(q["job_id"] for q in seed["quotes"] if q["state"] == "open")
    for job in seed["jobs"]:
        if job["state"] == "quoting":
            assert open_quote_counts[job["id"]] >= 1
        if job["state"] == "posted":
            assert open_quote_counts[job["id"]] == 0


def test_app_jobs_happen_after_joining_and_before_today(seed):
    joined_on_by_id = {provider["id"]: provider["joined_on"] for provider in seed["providers"]}
    for job in seed["jobs"]:
        if job["finished_on"]:
            assert joined_on_by_id[job["provider_id"]] <= job["finished_on"] < TODAY.isoformat()


def test_demo_users_match_the_fixtures(seed):
    lindiwe = find_row(seed["customers"], "cust_001")
    assert {key: lindiwe[key] for key in read_fixture("me.json")} == read_fixture("me.json")
    profile = read_fixture("provider_profile.json")
    sipho = find_row(seed["providers"], "prov_002")
    for key in ["display_name", "trades", "id_badge", "suburb", "langs", "bio"]:
        assert sipho[key] == profile[key]


def test_demo_job_quote_and_off_app_job_match_the_fixtures(seed):
    job = find_row(seed["jobs"], "job_001")
    job_fixture = read_fixture("job_public.json")
    for key in ["state", "trade", "size", "urgency", "suburb", "problem", "problem_lang"]:
        assert job[key] == job_fixture[key]
    assert job["created_at"] == job_fixture["created_at"]
    assert job["address"] == read_fixture("job_unlocked.json")["address"]
    quote_fixture = read_fixture("quote.json")
    quote = find_row(seed["quotes"], "quote_001")
    # The seed has no payment columns: its quotes get the model's defaults, as in the fixture.
    payment_keys = {"payment_methods", "deposit_rands"}
    seeded_keys = [key for key in quote_fixture if key not in payment_keys]
    assert {key: quote[key] for key in seeded_keys} == {
        key: quote_fixture[key] for key in seeded_keys
    }
    assert quote_fixture["payment_methods"] == ["in_app_after", "cash"]
    off_app_fixture = read_fixture("off_app_job.json")
    off_app_job = find_row(seed["off_app_jobs"], "offapp_001")
    assert {key: off_app_job[key] for key in off_app_fixture} == off_app_fixture


def test_thabo_has_the_evidence_in_the_fixture(seed):
    evidence = read_fixture("ranked_providers.json")[0]["evidence"]
    jobs = list_completed_app_jobs(seed, "prov_001")
    assert len(jobs) == evidence["jobs"]
    assert count_repeat_customers(jobs) == evidence["repeat_customers"]
    assert len(list_off_app_jobs(seed, "prov_001", "confirmed")) == evidence["off_app_confirmed"]


def test_sipho_is_new_to_the_app_with_one_confirmed_off_app_job(seed):
    assert list_completed_app_jobs(seed, "prov_002") == []
    assert len(list_off_app_jobs(seed, "prov_002", "confirmed")) == 1
    assert len(list_off_app_jobs(seed, "prov_002", "awaiting_sms_reply")) == 1


def test_nosipho_has_over_three_years_of_confirmed_work(seed):
    work_dates = [job["date"] for job in list_off_app_jobs(seed, "prov_003", "confirmed")]
    work_dates += [job["finished_on"] for job in list_completed_app_jobs(seed, "prov_003")]
    span_days = (date.fromisoformat(max(work_dates)) - date.fromisoformat(min(work_dates))).days
    assert span_days >= ARPL_EXPERIENCE_YEARS * DAYS_PER_YEAR
    assert not find_row(seed["providers"], "prov_003")["licensed"]


def test_write_seed_writes_one_json_array_per_table(seed, tmp_path):
    write_seed(seed, tmp_path)
    for table_name, rows in seed.items():
        written_rows = json.loads((tmp_path / f"{table_name}.json").read_text(encoding="utf-8"))
        assert written_rows == rows
