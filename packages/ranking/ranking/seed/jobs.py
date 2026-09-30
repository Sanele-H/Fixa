"""In-app jobs and quotes for the seed: finished jobs with outcomes, and open jobs with quotes.

A finished job's "still working?" answer is yes as often as its provider's hidden true
skill, so the seed's evidence fits the hidden truth the fairness check uses. Story
providers (story.py) are kept out of random jobs, so their records match the fixtures.
"""

import math
from datetime import date, datetime, timedelta

import numpy as np

from ranking.seed.common import (
    APP_HISTORY_DAYS,
    SeedTables,
    Trade,
    create_id,
    format_timestamp,
    pick,
    pick_date_before,
    pick_from_weights,
    pick_weighted,
)
from ranking.seed.places import calculate_distance_km, get_location
from ranking.seed.work import TradeTask, create_amount_rands, pick_task, pick_trade

PROBLEM_LANGUAGE = "en"  # v1 job descriptions are in English; P3 translates them per reader
COMPLETION_RATE = 0.95  # the rest are no-shows, where the provider didn't turn up
STILL_WORKING_CHECK_DAYS = 14  # "still working?" goes out two weeks after a job
STILL_WORKING_ANSWER_RATE = 0.7
REHIRE_RATE = 0.3  # chance a customer goes back to a provider they used before for that trade
NEARBY_KM = 4.0  # nearer providers are likelier picks: weight exp(-distance_km / NEARBY_KM)
MIN_PAST_JOB_DAYS_AGO = 3
MIN_DAYS_TO_DO_JOB = 1  # days from posting a job to doing it (inclusive range)
MAX_DAYS_TO_DO_JOB = 2
MAX_DECLINED_QUOTES = 2
MAX_OPEN_QUOTES = 3
OPEN_JOB_MAX_DAYS_AGO = 3
POSTED_SHARE = 0.3  # share of open jobs with no quotes yet
FIRST_WORKING_HOUR = 7
LAST_WORKING_HOUR = 17
MIN_QUOTE_DELAY_MINUTES = 10
MAX_QUOTE_DELAY_MINUTES = 180
URGENCY_WEIGHTS = {"low": 0.2, "normal": 0.6, "urgent": 0.2}
QUOTE_MESSAGES = [
    None,
    "I can come tomorrow morning.",
    "I can fix it this week.",
    "The price includes parts.",
]
DIRECTIONS_CHANCE = 0.3  # about one in three jobs has directions for the provider
DIRECTIONS_OPTIONS = [
    "Blue gate, ring the bell",
    "Complex entrance on Main Road, flat 4B",
    "Gate code 1234",
    "Use the back door, next to the spaza",
    "Corner house with a red wall",
    "Call when you arrive, the gate is locked",
    "Third house from the corner, white palisade",
    "Security gate, intercom on the right",
]


def add_random_past_jobs(
    tables: SeedTables, rng: np.random.Generator, trades: list[Trade], today: date, count: int
) -> None:
    """Adds up to count finished jobs, done by random providers for random customers.

    A job is skipped when no provider could have taken it on its date, so slightly fewer
    than count may be added.
    """
    customers = list_random_customers(tables)
    for _ in range(count):
        trade = pick_trade(rng, trades)
        task = pick_task(rng, trade, can_do_licensed_work=True)
        done_on = pick_past_job_date(rng, today)
        customer = pick(rng, customers)
        provider = pick_provider_for_job(rng, tables, customer, trade, task, done_on)
        if provider is not None:
            completed = bool(rng.random() < COMPLETION_RATE)
            add_past_job(tables, rng, provider, customer, trade, task, done_on, today, completed)


def add_random_open_jobs(
    tables: SeedTables, rng: np.random.Generator, trades: list[Trade], today: date, count: int
) -> None:
    """Adds count jobs posted in the last few days: some with no quotes yet, most with some."""
    customers = list_random_customers(tables)
    for _ in range(count):
        trade = pick_trade(rng, trades)
        task = pick_task(rng, trade, can_do_licensed_work=True)
        created_on = pick_date_before(rng, today, 1, OPEN_JOB_MAX_DAYS_AGO + 1)
        add_open_job(tables, rng, pick(rng, customers), trade, task, created_on)


def add_past_job(
    tables: SeedTables,
    rng: np.random.Generator,
    provider: dict,
    customer: dict,
    trade: Trade,
    task: TradeTask,
    done_on: date,
    today: date,
    completed: bool,
) -> None:
    """Adds a finished job with its outcome, the provider's accepted quote and declined ones.

    completed=False is a no-show, and the job ends "cancelled". Declined quotes come from
    other providers near the customer who could have taken the job.
    """
    created_on = done_on - timedelta(days=pick_days_to_do_job(rng))
    still_working = ask_still_working(rng, provider, done_on, today) if completed else None
    job = create_job(tables, rng, customer, trade, task, created_on)
    job.update(
        provider_id=provider["id"],
        state=decide_finished_state(completed, still_working),
        finished_on=done_on.isoformat(),
        completed=completed,
        still_working=still_working,
    )
    tables.jobs.append(job)
    add_quote(tables, rng, job, provider, task, "accepted", done_on)
    other_providers = [
        other
        for other in find_eligible_providers(tables.providers, trade, task, created_on)
        if other["id"] != provider["id"]
    ]
    declined_count = int(rng.integers(0, MAX_DECLINED_QUOTES + 1))
    declined_providers = pick_nearby_providers(
        rng, other_providers, get_location(customer), declined_count
    )
    for other in declined_providers:
        add_quote(tables, rng, job, other, task, "declined", done_on)


def add_open_job(
    tables: SeedTables,
    rng: np.random.Generator,
    customer: dict,
    trade: Trade,
    task: TradeTask,
    created_on: date,
) -> None:
    """Adds a job that is still open: "posted" with no quotes, or "quoting" with open quotes."""
    job = create_job(tables, rng, customer, trade, task, created_on)
    quote_count = 0 if rng.random() < POSTED_SHARE else int(rng.integers(1, MAX_OPEN_QUOTES + 1))
    eligible_providers = find_eligible_providers(tables.providers, trade, task, created_on)
    quoting_providers = pick_nearby_providers(
        rng, eligible_providers, get_location(customer), quote_count
    )
    job["state"] = "quoting" if quoting_providers else "posted"
    tables.jobs.append(job)
    for provider in quoting_providers:
        proposed_day = created_on + timedelta(days=pick_days_to_do_job(rng))
        add_quote(tables, rng, job, provider, task, "open", proposed_day)


def create_job(
    tables: SeedTables,
    rng: np.random.Generator,
    customer: dict,
    trade: Trade,
    task: TradeTask,
    created_on: date,
) -> dict:
    """Creates a job row as the customer posted it, at the customer's address.

    It starts in state "quoting" with no provider and no outcome; callers fill those in.
    """
    return {
        "id": create_id("job", tables.jobs),
        "customer_id": customer["id"],
        "provider_id": None,
        "state": "quoting",
        "trade": trade.id,
        "trade_task": task.name,
        "size": task.size,
        "urgency": pick_from_weights(rng, URGENCY_WEIGHTS),
        "needs_licence": task.needs_licence,
        "suburb": customer["suburb"],
        "address": customer["address"],
        "lat": customer["lat"],
        "lng": customer["lng"],
        "problem": task.problem,
        "problem_lang": PROBLEM_LANGUAGE,
        "directions": pick(rng, DIRECTIONS_OPTIONS) if rng.random() < DIRECTIONS_CHANCE else None,
        "photo_url": None,
        "created_at": format_timestamp(created_on, pick_working_hour(rng)),
        "finished_on": None,
        "completed": None,
        "still_working": None,
    }


def add_quote(
    tables: SeedTables,
    rng: np.random.Generator,
    job: dict,
    provider: dict,
    task: TradeTask,
    state: str,
    proposed_day: date,
) -> None:
    """Adds a provider's quote for a job, sent within a few hours of the job being posted."""
    delay = timedelta(minutes=int(rng.integers(MIN_QUOTE_DELAY_MINUTES, MAX_QUOTE_DELAY_MINUTES)))
    tables.quotes.append(
        {
            "id": create_id("quote", tables.quotes),
            "job_id": job["id"],
            "provider_id": provider["id"],
            "amount_rands": create_amount_rands(rng, task, provider),
            "when": format_timestamp(proposed_day, pick_working_hour(rng)),
            "message": pick(rng, QUOTE_MESSAGES),
            "state": state,
            "created_at": (datetime.fromisoformat(job["created_at"]) + delay).isoformat(),
        }
    )


def list_random_customers(tables: SeedTables) -> list[dict]:
    """Lists the customers who aren't story characters."""
    return [customer for customer in tables.customers if not customer.get("_story")]


def can_take_job(provider: dict, trade: Trade, task: TradeTask, on_day: date) -> bool:
    """True if a random provider offers the trade, holds any licence needed, and had joined."""
    return (
        not provider.get("_story")
        and trade.id in provider["trades"]
        and (provider["licensed"] or not task.needs_licence)
        and date.fromisoformat(provider["joined_on"]) <= on_day
    )


def find_eligible_providers(
    providers: list[dict], trade: Trade, task: TradeTask, on_day: date
) -> list[dict]:
    """Finds the random providers who could have taken a job on a given day."""
    return [provider for provider in providers if can_take_job(provider, trade, task, on_day)]


def find_previous_providers(
    jobs: list[dict], providers: list[dict], customer: dict, trade: Trade, before_day: date
) -> list[dict]:
    """Finds which of these providers completed a job in this trade for the customer before."""
    previous_provider_ids = {
        job["provider_id"]
        for job in jobs
        if job["customer_id"] == customer["id"]
        and job["trade"] == trade.id
        and job["completed"]
        and job["finished_on"] < before_day.isoformat()
    }
    return [provider for provider in providers if provider["id"] in previous_provider_ids]


def pick_provider_for_job(
    rng: np.random.Generator,
    tables: SeedTables,
    customer: dict,
    trade: Trade,
    task: TradeTask,
    done_on: date,
) -> dict | None:
    """Picks who did a past job: sometimes a provider the customer used before, else someone near.

    Only providers who had joined by the earliest day the job could have been posted count.
    Returns None when there is no such provider.
    """
    earliest_posted_on = done_on - timedelta(days=MAX_DAYS_TO_DO_JOB)
    eligible_providers = find_eligible_providers(tables.providers, trade, task, earliest_posted_on)
    if not eligible_providers:
        return None
    previous_providers = find_previous_providers(
        tables.jobs, eligible_providers, customer, trade, done_on
    )
    if previous_providers and rng.random() < REHIRE_RATE:
        return pick(rng, previous_providers)
    return pick_nearby_provider(rng, eligible_providers, get_location(customer))


def pick_nearby_provider(
    rng: np.random.Generator, providers: list[dict], location: tuple[float, float]
) -> dict:
    """Picks one provider at random, nearer ones more often."""
    weights = [
        math.exp(-calculate_distance_km(location, get_location(provider)) / NEARBY_KM)
        for provider in providers
    ]
    return pick_weighted(rng, providers, weights)


def pick_nearby_providers(
    rng: np.random.Generator, providers: list[dict], location: tuple[float, float], count: int
) -> list[dict]:
    """Picks up to count different providers at random, nearer ones more often."""
    remaining_providers = list(providers)
    picked_providers = []
    for _ in range(min(count, len(remaining_providers))):
        provider = pick_nearby_provider(rng, remaining_providers, location)
        remaining_providers.remove(provider)
        picked_providers.append(provider)
    return picked_providers


def pick_past_job_date(rng: np.random.Generator, today: date) -> date:
    """Picks the date a past job was done, recent dates more often, as if the app has grown.

    Squaring a uniform random number pushes it towards 0, so towards recent dates.
    """
    history_days = APP_HISTORY_DAYS - MIN_PAST_JOB_DAYS_AGO
    days_ago = MIN_PAST_JOB_DAYS_AGO + int(history_days * rng.random() ** 2)
    return today - timedelta(days=days_ago)


def ask_still_working(
    rng: np.random.Generator, provider: dict, done_on: date, today: date
) -> bool | None:
    """Returns the customer's answer to "still working?", two weeks after the job.

    Yes as often as the provider's hidden true skill. None when the question isn't due yet
    or the customer didn't answer.
    """
    is_due = (today - done_on).days >= STILL_WORKING_CHECK_DAYS
    if not is_due or rng.random() >= STILL_WORKING_ANSWER_RATE:
        return None
    return bool(rng.random() < provider["_true_skill"])


def decide_finished_state(completed: bool, still_working: bool | None) -> str:
    """Returns a finished job's state: cancelled (a no-show), done, or followed_up (answered)."""
    if not completed:
        return "cancelled"
    return "done" if still_working is None else "followed_up"


def pick_days_to_do_job(rng: np.random.Generator) -> int:
    """Picks how many days after posting a job gets done."""
    return int(rng.integers(MIN_DAYS_TO_DO_JOB, MAX_DAYS_TO_DO_JOB + 1))


def pick_working_hour(rng: np.random.Generator) -> int:
    """Picks an hour of the working day."""
    return int(rng.integers(FIRST_WORKING_HOUR, LAST_WORKING_HOUR + 1))
