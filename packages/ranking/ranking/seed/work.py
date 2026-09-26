"""The work in the seed: kinds of job per trade, how often each comes up, and prices.

Prices are made-up demo values in the right ballpark for Johannesburg. They only feed the
seed's quotes: price_range works from accepted quotes and never from these numbers.
"""

from typing import NamedTuple

import numpy as np

from ranking.seed.common import Trade, pick_weighted


class TradeTask(NamedTuple):
    """A kind of job in a trade."""

    name: str  # the trade task, as the work record groups jobs
    problem: str  # how a customer might describe it when posting the job
    size: str  # small | medium | large
    typical_price_rands: int
    needs_licence: bool = False


TRADE_TASKS = {
    "plumbing": [
        TradeTask("Fix leaking geyser", "My geyser is leaking through the ceiling", "small", 550),
        TradeTask(
            "Replace geyser valve",
            "Water keeps running out of the geyser overflow pipe",
            "small",
            450,
        ),
        TradeTask("Fix dripping tap", "The kitchen tap drips all night", "small", 350),
        TradeTask("Unblock drain", "The bathroom drain is blocked and smells bad", "small", 400),
        TradeTask("Fix running toilet", "The toilet keeps running after I flush", "small", 400),
        TradeTask(
            "Repair burst pipe",
            "A pipe burst in the yard and there is water everywhere",
            "medium",
            1200,
        ),
        TradeTask(
            "Replace bathroom pipes",
            "The bathroom pipes are old and the water pressure is very weak",
            "large",
            6500,
        ),
        TradeTask(
            "Install new geyser",
            "My geyser is finished and I need a new one installed",
            "large",
            9500,
            needs_licence=True,
        ),
    ],
    "electrical": [
        TradeTask(
            "Replace plug point", "A plug point sparks when I plug in the kettle", "small", 400
        ),
        TradeTask("Install light fitting", "I need a new light fitted in the lounge", "small", 450),
        TradeTask("Fix outside lights", "The outside lights stopped working", "small", 500),
        TradeTask(
            "Fix tripping circuit", "The power trips every time the stove is on", "medium", 950
        ),
        TradeTask("Connect stove", "I bought a new stove and need it connected", "medium", 850),
        TradeTask(
            "Issue Certificate of Compliance",
            "I am selling my house and need an electrical certificate of compliance",
            "medium",
            1800,
            needs_licence=True,
        ),
        TradeTask(
            "Rewire room",
            "The wiring in the back room is old and burnt and needs redoing",
            "large",
            5500,
            needs_licence=True,
        ),
    ],
}
# Trades without their own task list yet get one generic job per size, at these prices.
GENERIC_TASK_PRICES_RANDS = {"small": 450, "medium": 1200, "large": 4000}

# The demo trades get more providers and jobs than the others.
TRADE_WEIGHTS = {"plumbing": 3.0, "electrical": 2.5}
OTHER_TRADE_WEIGHT = 1.0
TASK_SIZE_WEIGHTS = {"small": 3.0, "medium": 2.0, "large": 1.0}  # small jobs are the most common

PRICE_SPREAD = 0.15  # how much one quote differs from the provider's usual price (log scale)
PRICE_ROUNDING_RANDS = 10


def pick_trade(rng: np.random.Generator, trades: list[Trade]) -> Trade:
    """Picks a trade, the demo trades more often than the others."""
    weights = [TRADE_WEIGHTS.get(trade.id, OTHER_TRADE_WEIGHT) for trade in trades]
    return pick_weighted(rng, trades, weights)


def list_trade_tasks(trade: Trade) -> list[TradeTask]:
    """Lists the kinds of job in a trade, with generic ones for trades without a list yet."""
    if trade.id in TRADE_TASKS:
        return TRADE_TASKS[trade.id]
    return [
        TradeTask(
            f"{trade.label} job ({size})", f"I need help with {trade.label.lower()}", size, price
        )
        for size, price in GENERIC_TASK_PRICES_RANDS.items()
    ]


def pick_task(rng: np.random.Generator, trade: Trade, can_do_licensed_work: bool) -> TradeTask:
    """Picks a kind of job in a trade, small ones most often.

    Licensed work (a geyser install, work needing a CoC) is only picked when allowed.
    """
    tasks = [
        task for task in list_trade_tasks(trade) if can_do_licensed_work or not task.needs_licence
    ]
    return pick_weighted(rng, tasks, [TASK_SIZE_WEIGHTS[task.size] for task in tasks])


def create_amount_rands(rng: np.random.Generator, task: TradeTask, provider: dict) -> int:
    """Creates a provider's price for a job: the typical price at their price level, plus noise.

    Rounded to R10, like a real quote.
    """
    amount_rands = (
        task.typical_price_rands * provider["_price_factor"] * rng.lognormal(0.0, PRICE_SPREAD)
    )
    return int(round(amount_rands / PRICE_ROUNDING_RANDS) * PRICE_ROUNDING_RANDS)
