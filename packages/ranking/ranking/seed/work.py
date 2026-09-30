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
    "carpentry": [
        TradeTask(
            "Hang a door", "A bedroom door is dragging on the floor and won't close", "small", 450
        ),
        TradeTask(
            "Fix cupboard hinge", "A kitchen cupboard door has come off its hinge", "small", 350
        ),
        TradeTask("Install shelves", "I need three shelves put up in the study", "small", 500),
        TradeTask(
            "Replace door frame",
            "The back door frame is rotten and needs replacing",
            "medium",
            2500,
        ),
        TradeTask(
            "Build a deck", "I want a small wooden deck built outside the back door", "large", 12000
        ),
        TradeTask("Build a pergola", "I need a pergola built over the patio area", "large", 15000),
    ],
    "welding": [
        TradeTask("Repair gate", "The front gate is broken and won't latch properly", "small", 550),
        TradeTask(
            "Fix burglar bars", "Two burglar bar welds have cracked on a window", "small", 500
        ),
        TradeTask("Weld a fence panel", "A panel on the steel fence has come loose", "small", 600),
        TradeTask(
            "Build a security gate",
            "I need a new steel security gate for the front door",
            "medium",
            3500,
        ),
        TradeTask(
            "Build burglar bars",
            "I need burglar bars made and fitted for three windows",
            "large",
            7500,
        ),
        TradeTask(
            "Build a carport frame",
            "I want a steel carport frame welded and erected",
            "large",
            14000,
        ),
    ],
    "bricklaying": [
        TradeTask("Repair a wall", "A section of the boundary wall has collapsed", "small", 800),
        TradeTask(
            "Plaster a room", "The lounge walls need replastering before painting", "medium", 3500
        ),
        TradeTask(
            "Build a boundary wall",
            "I need a new boundary wall built on one side of the stand",
            "large",
            18000,
        ),
        TradeTask(
            "Lay paving",
            "The front yard needs paving laid over about 30 square metres",
            "medium",
            4500,
        ),
        TradeTask("Build a braai", "I want a brick braai built on the patio", "medium", 3000),
        TradeTask(
            "Build a room", "I want to add a small room onto the back of the house", "large", 25000
        ),
    ],
    "mechanic": [
        TradeTask(
            "Change brake pads", "The car brakes are squeaking and need new pads", "small", 650
        ),
        TradeTask("Service the car", "My car is due for its 15 000 km service", "small", 850),
        TradeTask("Replace clutch", "The clutch is slipping and needs replacing", "medium", 4500),
        TradeTask("Oil change", "The engine oil and filter need changing", "small", 450),
        TradeTask(
            "Replace gearbox",
            "The gearbox is making a grinding noise and needs replacing",
            "large",
            12000,
        ),
        TradeTask(
            "Fix engine overheating",
            "The engine overheats and the temperature gauge goes into the red",
            "medium",
            3500,
        ),
    ],
    "roofing": [
        TradeTask("Fix a roof leak", "The roof leaks into the passage when it rains", "small", 850),
        TradeTask(
            "Replace roof tiles", "Several roof tiles are cracked and need replacing", "small", 650
        ),
        TradeTask(
            "Waterproof a flat roof",
            "The flat roof over the porch needs waterproofing",
            "medium",
            3500,
        ),
        TradeTask(
            "Replace gutters", "The gutters are rusted through and need replacing", "medium", 4000
        ),
        TradeTask(
            "Replace fascia boards", "The fascia boards under the eaves are rotten", "medium", 3000
        ),
        TradeTask(
            "Re-roof a house", "The whole roof needs replacing with new IBR sheets", "large", 35000
        ),
    ],
    "tiling": [
        TradeTask(
            "Replace cracked tiles", "Three floor tiles in the kitchen are cracked", "small", 550
        ),
        TradeTask(
            "Re-grout bathroom", "The grout in the shower is mouldy and needs redoing", "small", 650
        ),
        TradeTask(
            "Tile a bathroom floor", "The bathroom floor needs new tiles laid", "medium", 3500
        ),
        TradeTask(
            "Tile a kitchen splashback",
            "I want a tile splashback put in behind the kitchen counter",
            "small",
            1200,
        ),
        TradeTask(
            "Tile a whole room",
            "The lounge floor needs tiling, about 25 square metres",
            "large",
            8500,
        ),
        TradeTask(
            "Tile a shower", "A new shower needs to be tiled from floor to ceiling", "medium", 5000
        ),
    ],
    "cabinetmaking": [
        TradeTask(
            "Fix a cupboard door",
            "A kitchen cupboard door won't close and the hinge is loose",
            "small",
            350,
        ),
        TradeTask(
            "Install kitchen cupboards",
            "I need new kitchen cupboards installed in a small kitchen",
            "large",
            25000,
        ),
        TradeTask(
            "Build a wardrobe",
            "I need a built-in wardrobe made for the main bedroom",
            "large",
            12000,
        ),
        TradeTask(
            "Build a TV cabinet", "I want a custom TV cabinet built for the lounge", "medium", 4500
        ),
        TradeTask(
            "Repair a cabinet hinge",
            "Several cabinet hinges are broken and need replacing",
            "small",
            450,
        ),
        TradeTask(
            "Build a study desk",
            "I need a built-in desk with shelving for a home office",
            "medium",
            6000,
        ),
    ],
    "painting": [
        TradeTask("Paint a room", "The lounge needs repainting, walls and ceiling", "medium", 3000),
        TradeTask(
            "Paint a ceiling",
            "The bedroom ceiling has damp marks and needs repainting",
            "small",
            1200,
        ),
        TradeTask(
            "Paint a house exterior",
            "The outside walls of the house need repainting",
            "large",
            12000,
        ),
        TradeTask(
            "Paint a boundary wall",
            "The boundary wall paint is peeling and needs redoing",
            "medium",
            4000,
        ),
        TradeTask("Varnish a door", "The front door needs sanding and varnishing", "small", 800),
        TradeTask(
            "Paint a small room",
            "A small back room needs painting, walls and ceiling",
            "small",
            1800,
        ),
    ],
    "appliance_repair": [
        TradeTask(
            "Fix a washing machine",
            "The washing machine won't spin and makes a loud noise",
            "small",
            650,
        ),
        TradeTask(
            "Repair a fridge",
            "The fridge is not cooling properly and food is going off",
            "medium",
            1200,
        ),
        TradeTask(
            "Fix a stove element", "One of the stove plates doesn't heat up any more", "small", 550
        ),
        TradeTask(
            "Replace geyser element",
            "The geyser element has blown and there is no hot water",
            "small",
            850,
        ),
        TradeTask(
            "Fix an oven",
            "The oven doesn't reach temperature and the thermostat may be broken",
            "medium",
            1500,
        ),
        TradeTask(
            "Repair a microwave", "The microwave turns on but doesn't heat food", "small", 500
        ),
    ],
    "groundskeeping": [
        TradeTask("Mow the lawn", "The lawn needs mowing and edging", "small", 250),
        TradeTask(
            "Trim hedges",
            "The hedges along the boundary are overgrown and need trimming",
            "small",
            400,
        ),
        TradeTask(
            "Cut down a tree",
            "A dead tree in the yard needs cutting down and removing",
            "medium",
            2500,
        ),
        TradeTask(
            "Install irrigation",
            "I want a drip irrigation system put in for the garden",
            "medium",
            4000,
        ),
        TradeTask(
            "Lay new lawn", "The front yard is patchy and needs new lawn laid", "medium", 3500
        ),
        TradeTask(
            "Landscape a garden",
            "The whole garden needs redesigning and replanting",
            "large",
            15000,
        ),
    ],
    "other": [
        TradeTask(
            "Hang curtain rails", "I need curtain rails put up in two bedrooms", "small", 350
        ),
        TradeTask(
            "Assemble furniture", "I need a flat-pack wardrobe and a bed put together", "small", 450
        ),
        TradeTask("Mount a TV", "I want my TV mounted on the lounge wall", "small", 400),
        TradeTask("Fix a handrail", "The handrail on the outside steps is loose", "small", 400),
        TradeTask(
            "Clear out a garage",
            "The garage is full of rubble that needs taking away",
            "medium",
            1200,
        ),
    ],
}
# Trades without their own task list yet get one generic job per size, at these prices.
GENERIC_TASK_PRICES_RANDS = {"small": 450, "medium": 1200, "large": 4000}

# The demo trades get more providers and jobs than the others.
TRADE_WEIGHTS = {
    "plumbing": 3.0,
    "electrical": 2.5,
    "carpentry": 1.5,
    "welding": 1.0,
    "bricklaying": 1.0,
    "mechanic": 1.5,
    "roofing": 1.0,
    "tiling": 1.0,
    "cabinetmaking": 1.0,
    "painting": 1.5,
    "appliance_repair": 1.0,
    "groundskeeping": 1.0,
    "other": 1.5,  # the fallback trade for jobs nothing else matches
}
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
