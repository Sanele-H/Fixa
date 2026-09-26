"""The people the fixtures and the demo are about, with their histories.

- Lindiwe (cust_001): the demo customer in Braamfontein, who posts job_001.
- Thabo (prov_001): an established plumber with 9 app jobs, 2 repeat customers and 3
  confirmed off-app jobs, as in ranked_providers.json.
- Sipho (prov_002): a plumber with 6 years' experience who is new to the app: no app jobs
  yet, 1 confirmed off-app job and 1 awaiting the customer's reply (off_app_job.json).
- Nosipho (prov_003): a plumber with about 4 years of confirmed work, for the ARPL demo.

They are added first, so their ids match the fixtures, and fields the fixtures show are
copied from them. job_001, quote_001 and offapp_001 keep the fixtures' dates whatever
"today" is. Story providers never appear in random jobs, so their records stay exact.
"""

from datetime import date, timedelta

import numpy as np

from ranking.seed.common import APP_HISTORY_DAYS, SeedTables, Trade, spread_dates
from ranking.seed.jobs import (
    MAX_DAYS_TO_DO_JOB,
    MIN_PAST_JOB_DAYS_AGO,
    add_past_job,
    list_random_customers,
)
from ranking.seed.off_app import CUSTOMER_PHONE_FORMAT, add_logged_history, add_off_app_job
from ranking.seed.places import (
    DEMO_SUBURB,
    SUBURB_CENTRES,
    calculate_distance_km,
    get_location,
    move_location,
)
from ranking.seed.work import pick_task

PLUMBING = "plumbing"
DEMO_LOCATION = SUBURB_CENTRES[DEMO_SUBURB]  # Lindiwe's home, where job_001 is
# Distances from job_001 as in ranked_providers.json. Sipho is far enough that established
# plumbers are nearer, so the demo shows the newcomer slot lifting him into the top 5.
THABO_DISTANCE_KM = 1.8
SIPHO_DISTANCE_KM = 3.1

THABO_APP_JOBS = 9
THABO_REPEAT_CUSTOMERS = 2
THABO_OFF_APP_JOBS = 3
SIPHO_JOINED_DAYS_AGO = 5
SIPHO_CONFIRMED_OFF_APP_JOBS = 1
NOSIPHO_JOINED_DAYS_AGO = 240
NOSIPHO_APP_JOBS = 16
NOSIPHO_REPEAT_CUSTOMERS = 2
NOSIPHO_HISTORY_YEARS = 4  # her first confirmed job is this long ago
NOSIPHO_CONFIRMED_OFF_APP_JOBS = 70
NOSIPHO_AWAITING_REPLY_JOBS = 2
DAYS_PER_YEAR = 365


def add_story_people(tables: SeedTables, today: date) -> None:
    """Adds Lindiwe and the three story providers. Call it first, so their ids match."""
    tables.customers.append(create_lindiwe())
    tables.providers.extend([create_thabo(today), create_sipho(today), create_nosipho(today)])


def add_story_work(
    tables: SeedTables, rng: np.random.Generator, trades_by_id: dict[str, Trade], today: date
) -> None:
    """Adds the demo job and the story providers' histories.

    Call it after the random customers exist (story jobs are for customers living nearby)
    and before any other job, quote or off-app job, so the fixtures' ids line up.
    """
    plumbing = trades_by_id[PLUMBING]
    thabo, sipho, nosipho = tables.providers[:3]
    tables.jobs.append(create_demo_job())
    tables.quotes.append(create_demo_quote())
    tables.off_app_jobs.append(create_sipho_pending_off_app_job())
    add_logged_history(tables, rng, sipho, trades_by_id, SIPHO_CONFIRMED_OFF_APP_JOBS)
    add_story_app_jobs(tables, rng, thabo, plumbing, THABO_APP_JOBS, THABO_REPEAT_CUSTOMERS, today)
    add_logged_history(tables, rng, thabo, trades_by_id, THABO_OFF_APP_JOBS)
    add_story_app_jobs(
        tables, rng, nosipho, plumbing, NOSIPHO_APP_JOBS, NOSIPHO_REPEAT_CUSTOMERS, today
    )
    add_long_off_app_history(tables, rng, nosipho, plumbing, today)


def add_story_app_jobs(
    tables: SeedTables,
    rng: np.random.Generator,
    provider: dict,
    trade: Trade,
    job_count: int,
    repeat_customer_count: int,
    today: date,
) -> None:
    """Adds a story provider's app jobs: all completed, spread over their time on the app.

    The customers are the ones living nearest. The first repeat_customer_count of them hire
    the provider a second time, later on.
    """
    customers = find_nearest_customers(
        tables, get_location(provider), job_count - repeat_customer_count
    )
    customer_order = customers + customers[:repeat_customer_count]
    first_day = date.fromisoformat(provider["joined_on"]) + timedelta(days=MAX_DAYS_TO_DO_JOB)
    last_day = today - timedelta(days=MIN_PAST_JOB_DAYS_AGO)
    done_dates = spread_dates(rng, first_day, last_day, job_count)
    for customer, done_on in zip(customer_order, done_dates, strict=True):
        task = pick_task(rng, trade, provider["licensed"])
        add_past_job(tables, rng, provider, customer, trade, task, done_on, today, completed=True)


def add_long_off_app_history(
    tables: SeedTables, rng: np.random.Generator, provider: dict, trade: Trade, today: date
) -> None:
    """Adds Nosipho's confirmed work, from NOSIPHO_HISTORY_YEARS ago until she joined.

    The first job is exactly that long ago, so her record spans the full time. She also
    has a few jobs whose customers haven't replied to the SMS yet.
    """
    joined_on = date.fromisoformat(provider["joined_on"])
    first_day = today - timedelta(days=NOSIPHO_HISTORY_YEARS * DAYS_PER_YEAR)
    later_days = spread_dates(
        rng, first_day + timedelta(days=1), joined_on, NOSIPHO_CONFIRMED_OFF_APP_JOBS - 1
    )
    for done_on in [first_day, *later_days]:
        task = pick_task(rng, trade, provider["licensed"])
        add_off_app_job(tables, rng, provider, trade, task, done_on, "confirmed")
    for done_on in spread_dates(
        rng, joined_on - timedelta(days=DAYS_PER_YEAR), joined_on, NOSIPHO_AWAITING_REPLY_JOBS
    ):
        task = pick_task(rng, trade, provider["licensed"])
        add_off_app_job(tables, rng, provider, trade, task, done_on, "awaiting_sms_reply")


def find_nearest_customers(
    tables: SeedTables, location: tuple[float, float], count: int
) -> list[dict]:
    """Finds the count random customers who live nearest to a location, nearest first."""
    customers = list_random_customers(tables)
    customers.sort(key=lambda customer: calculate_distance_km(location, get_location(customer)))
    return customers[:count]


def create_lindiwe() -> dict:
    """Creates Lindiwe, the demo customer, with the fields in me.json and job_unlocked.json."""
    latitude, longitude = DEMO_LOCATION
    return {
        "id": "cust_001",
        "role": "customer",
        "display_name": "Lindiwe",
        "phone": "082 000 0001",
        "lang": "en",
        "suburb": "Braamfontein",
        "address": "12 Example Street, Braamfontein",
        "lat": latitude,
        "lng": longitude,
        "id_badge": "none",
        "_story": True,
    }


def create_thabo(today: date) -> dict:
    """Creates Thabo, the established plumber, 1.8 km from the demo job."""
    latitude, longitude = move_location(DEMO_LOCATION, north_km=THABO_DISTANCE_KM, east_km=0.0)
    return {
        "id": "prov_001",
        "role": "provider",
        "display_name": "Thabo",
        "phone": "071 000 0001",
        "lang": "en",
        "langs": ["en", "zu"],
        "suburb": "Parktown",
        "lat": latitude,
        "lng": longitude,
        "trades": ["plumbing"],
        "licensed": True,
        "id_badge": "id_number",
        "bio": "Plumber, 11 years' experience.",
        "joined_on": (today - timedelta(days=APP_HISTORY_DAYS)).isoformat(),
        "_true_skill": 0.86,
        "_first_language": "st",
        "_price_factor": 1.05,
        "_story": True,
    }


def create_sipho(today: date) -> dict:
    """Creates Sipho, the experienced newcomer, with the fields in provider_profile.json."""
    latitude, longitude = move_location(DEMO_LOCATION, north_km=0.0, east_km=-SIPHO_DISTANCE_KM)
    return {
        "id": "prov_002",
        "role": "provider",
        "display_name": "Sipho",
        "phone": "071 000 0002",
        "lang": "zu",
        "langs": ["zu", "en"],
        "suburb": "Braamfontein",
        "lat": latitude,
        "lng": longitude,
        "trades": ["plumbing"],
        "licensed": False,
        "id_badge": "home_affairs",
        "bio": "Plumber, 6 years fixing geysers and leaks.",
        "joined_on": (today - timedelta(days=SIPHO_JOINED_DAYS_AGO)).isoformat(),
        "_true_skill": 0.9,
        "_first_language": "zu",
        "_price_factor": 0.95,
        "_story": True,
    }


def create_nosipho(today: date) -> dict:
    """Creates Nosipho, the plumber with about 4 years of confirmed work, for the ARPL demo.

    She isn't licensed: an ARPL trade test is her route to a qualification.
    """
    latitude, longitude = SUBURB_CENTRES["Yeoville"]
    return {
        "id": "prov_003",
        "role": "provider",
        "display_name": "Nosipho",
        "phone": "071 000 0003",
        "lang": "xh",
        "langs": ["xh", "en"],
        "suburb": "Yeoville",
        "lat": latitude,
        "lng": longitude,
        "trades": ["plumbing"],
        "licensed": False,
        "id_badge": "id_number",
        "bio": "Plumber, 4 years of leaks, drains, taps and geysers.",
        "joined_on": (today - timedelta(days=NOSIPHO_JOINED_DAYS_AGO)).isoformat(),
        "_true_skill": 0.92,
        "_first_language": "xh",
        "_price_factor": 1.0,
        "_story": True,
    }


def create_demo_job() -> dict:
    """Creates job_001 as in job_public.json: Lindiwe's leaking geyser, with quotes coming in.

    photo_url is None because no photo file exists yet; the fixture's photo_001 is P1's mock.
    """
    latitude, longitude = DEMO_LOCATION
    return {
        "id": "job_001",
        "customer_id": "cust_001",
        "provider_id": None,
        "state": "quoting",
        "trade": "plumbing",
        "trade_task": "Fix leaking geyser",
        "size": "small",
        "urgency": "urgent",
        "needs_licence": False,
        "suburb": "Braamfontein",
        "address": "12 Example Street, Braamfontein",
        "lat": latitude,
        "lng": longitude,
        "problem": "My geyser is leaking through the ceiling",
        "problem_lang": "en",
        "photo_url": None,
        "created_at": "2026-09-29T08:00:00+02:00",
        "finished_on": None,
        "completed": None,
        "still_working": None,
    }


def create_demo_quote() -> dict:
    """Creates quote_001 exactly as in quote.json: Sipho's R450 quote for job_001."""
    return {
        "id": "quote_001",
        "job_id": "job_001",
        "provider_id": "prov_002",
        "amount_rands": 450,
        "when": "2026-09-29T10:00:00+02:00",
        "message": "Ngingafika ngoLwesibili, R450.",
        "state": "open",
        "created_at": "2026-09-29T08:20:00+02:00",
    }


def create_sipho_pending_off_app_job() -> dict:
    """Creates offapp_001 as in off_app_job.json: logged by Sipho, awaiting the SMS reply."""
    return {
        "id": "offapp_001",
        "provider_id": "prov_002",
        "state": "awaiting_sms_reply",
        "trade": "plumbing",
        "trade_task": "Replace geyser valve",
        "date": "2026-08-14",
        "suburb": "Soweto",
        "amount_rands": 380,
        "customer_phone": CUSTOMER_PHONE_FORMAT.format(1),
        "confirmed_via": None,
        "reference_agreed": None,
    }
