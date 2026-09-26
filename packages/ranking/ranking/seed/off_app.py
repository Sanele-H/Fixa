"""Off-app jobs for the seed: past work a provider logged, confirmed by the customer.

Rows follow contracts/fixtures/off_app_job.json, plus the fields P2 stores alongside:
provider_id, trade, customer_phone, confirmed_via and reference_agreed.
"""

from datetime import date, timedelta

import numpy as np

from ranking.seed.common import SeedTables, Trade, create_id, pick
from ranking.seed.places import get_location, list_nearby_suburbs
from ranking.seed.work import TradeTask, create_amount_rands, pick_task

CUSTOMER_PHONE_FORMAT = "083 000 {:04d}"  # made up, in the pattern the fixtures use
LOGGING_PROVIDER_SHARE = 0.3  # share of random providers who logged work from before the app
MAX_JOBS_PER_PROVIDER = 5
MAX_DAYS_BEFORE_JOINING = 730  # how far back logged work goes
NEARBY_WORK_KM = 5.0  # off-app work happens in suburbs this close to the provider's home
AMOUNT_GIVEN_RATE = 0.8  # the amount is optional when logging a job
USSD_SHARE = 0.2  # the rest confirm by SMS
REFERENCE_AGREED_RATE = 0.5  # customers who agree to be listed as a reference


def add_random_off_app_jobs(
    tables: SeedTables, rng: np.random.Generator, trades_by_id: dict[str, Trade]
) -> None:
    """Adds a few confirmed off-app jobs for some random providers, from before they joined."""
    for provider in tables.providers:
        if not provider.get("_story") and rng.random() < LOGGING_PROVIDER_SHARE:
            job_count = int(rng.integers(1, MAX_JOBS_PER_PROVIDER + 1))
            add_logged_history(tables, rng, provider, trades_by_id, job_count)


def add_logged_history(
    tables: SeedTables,
    rng: np.random.Generator,
    provider: dict,
    trades_by_id: dict[str, Trade],
    job_count: int,
) -> None:
    """Adds job_count confirmed off-app jobs a provider did before joining, in their trades."""
    joined_on = date.fromisoformat(provider["joined_on"])
    for _ in range(job_count):
        trade = trades_by_id[pick(rng, provider["trades"])]
        task = pick_task(rng, trade, provider["licensed"])
        done_on = joined_on - timedelta(days=int(rng.integers(1, MAX_DAYS_BEFORE_JOINING)))
        add_off_app_job(tables, rng, provider, trade, task, done_on, "confirmed")


def add_off_app_job(
    tables: SeedTables,
    rng: np.random.Generator,
    provider: dict,
    trade: Trade,
    task: TradeTask,
    done_on: date,
    state: str,
) -> None:
    """Adds one off-app job in a suburb near the provider.

    state is "confirmed" or "awaiting_sms_reply". Only confirmed jobs have confirmed_via
    and reference_agreed. Each job gets its own customer number, so P2's rule of one
    count per number per provider holds.
    """
    is_confirmed = state == "confirmed"
    nearby_suburbs = list_nearby_suburbs(get_location(provider), NEARBY_WORK_KM)
    amount_rands = create_amount_rands(rng, task, provider)
    is_amount_given = rng.random() < AMOUNT_GIVEN_RATE
    confirmed_via = pick_confirmation_method(rng) if is_confirmed else None
    reference_agreed = bool(rng.random() < REFERENCE_AGREED_RATE) if is_confirmed else None
    tables.off_app_jobs.append(
        {
            "id": create_id("offapp", tables.off_app_jobs),
            "provider_id": provider["id"],
            "state": state,
            "trade": trade.id,
            "trade_task": task.name,
            "date": done_on.isoformat(),
            "suburb": pick(rng, nearby_suburbs),
            "amount_rands": amount_rands if is_amount_given else None,
            "customer_phone": CUSTOMER_PHONE_FORMAT.format(len(tables.off_app_jobs) + 1),
            "confirmed_via": confirmed_via,
            "reference_agreed": reference_agreed,
        }
    )


def pick_confirmation_method(rng: np.random.Generator) -> str:
    """Picks how the customer confirmed: SMS reply, or USSD from a feature phone."""
    return "ussd" if rng.random() < USSD_SHARE else "sms"
