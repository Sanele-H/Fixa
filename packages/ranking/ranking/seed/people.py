"""Random providers and customers for the seed. The story characters are in story.py.

Every name, phone number and address is made up. Hidden provider fields start with "_":
_true_skill and _first_language go only to hidden_truth.json (for the fairness check), and
_price_factor only shapes the seed's quotes.
"""

from datetime import date, timedelta

import numpy as np

from ranking.seed.common import (
    APP_HISTORY_DAYS,
    SeedTables,
    Trade,
    format_id,
    pick,
    pick_from_weights,
    pick_weighted,
)
from ranking.seed.places import DEMO_SUBURB, SUBURB_CENTRES, create_location
from ranking.seed.work import OTHER_TRADE_WEIGHT, TRADE_WEIGHTS, pick_trade

# Hidden group label: first language. "sn" is chiShona; many tradespeople in Johannesburg
# come from Zimbabwe.
PROVIDER_FIRST_LANGUAGE_WEIGHTS = {"zu": 0.35, "xh": 0.25, "st": 0.2, "sn": 0.2}
CUSTOMER_FIRST_LANGUAGE_WEIGHTS = {"zu": 0.3, "xh": 0.2, "st": 0.2, "en": 0.2, "sn": 0.1}
# The app language (en | zu | xh) each group uses, and the app languages they speak.
APP_LANGUAGE_BY_FIRST_LANGUAGE = {"zu": "zu", "xh": "xh", "st": "en", "sn": "en", "en": "en"}
SPOKEN_LANGUAGES_BY_FIRST_LANGUAGE = {
    "zu": ["zu", "en"],
    "xh": ["xh", "en"],
    "st": ["en", "zu"],
    "sn": ["en"],
    "en": ["en"],
}
FIRST_NAMES_BY_FIRST_LANGUAGE = {
    "zu": ["Sibusiso", "Nomvula", "Themba", "Zodwa", "Mandla", "Thandeka", "Bongani", "Sifiso"],
    "xh": ["Lwazi", "Luthando", "Unathi", "Anele", "Sizwe", "Ayanda", "Siphokazi", "Yonela"],
    "st": ["Lerato", "Tshepo", "Palesa", "Karabo", "Mpho", "Refilwe", "Teboho", "Dineo"],
    "sn": ["Tatenda", "Farai", "Tendai", "Rudo", "Chipo", "Tafadzwa", "Kudzai", "Nyasha"],
    "en": ["Megan", "David", "Priya", "Ashwin", "Sarah", "Johan", "Fatima", "Yusuf"],
}
SURNAME_INITIALS = "BDGHKLMNPRSTZ"
MAX_NAME_ATTEMPTS = 1000

PROVIDER_PHONE_FORMAT = "071 000 {:04d}"  # made up, in the pattern the fixtures use
CUSTOMER_PHONE_FORMAT = "082 000 {:04d}"
ADDRESS_FORMAT = "{house_number} Example Street, {suburb}"  # made up, as in job_unlocked.json
MAX_HOUSE_NUMBER = 200
DEMO_SUBURB_WEIGHT = 4.0  # more customers live where the demo happens

ID_BADGE_WEIGHTS = {"none": 0.3, "id_number": 0.4, "home_affairs": 0.3}
TRADE_PERSON_NAMES = {
    "plumbing": "Plumber",
    "electrical": "Electrician",
    "carpentry": "Carpenter",
    "welding": "Welder",
    "bricklaying": "Bricklayer",
    "mechanic": "Mechanic",
    "roofing": "Roofer",
    "tiling": "Tiler",
    "cabinetmaking": "Cabinetmaker",
    "painting": "Painter",
    "appliance_repair": "Appliance technician",
    "groundskeeping": "Groundskeeper",
    "other": "Handyman",
}
NEWCOMER_SHARE = 0.15  # share of providers who joined in the last few weeks
NEWCOMER_JOINED_WITHIN_DAYS = 21
SECOND_TRADE_SHARE = 0.2
LICENSED_SHARE = 0.25
MIN_EXPERIENCE_YEARS = 2
MAX_EXPERIENCE_YEARS = 15
TRUE_SKILL_BETA = (8.0, 2.0)  # mean 0.8: most providers are good, some much less so
TRUE_SKILL_DECIMALS = 3
PRICE_FACTOR_SPREAD = 0.12  # how much providers' price levels differ (log scale)


def add_random_providers(
    tables: SeedTables, rng: np.random.Generator, trades: list[Trade], today: date, count: int
) -> None:
    """Adds count random providers after the ones already in the table."""
    taken_names = list_taken_names(tables)
    for _ in range(count):
        number = len(tables.providers) + 1
        tables.providers.append(create_random_provider(rng, number, trades, today, taken_names))


def add_random_customers(tables: SeedTables, rng: np.random.Generator, count: int) -> None:
    """Adds count random customers after the ones already in the table."""
    taken_names = list_taken_names(tables)
    for _ in range(count):
        number = len(tables.customers) + 1
        tables.customers.append(create_random_customer(rng, number, taken_names))


def create_random_provider(
    rng: np.random.Generator, number: int, trades: list[Trade], today: date, taken_names: set[str]
) -> dict:
    """Creates provider number `number`, with a hidden true skill and first language."""
    first_language = pick_from_weights(rng, PROVIDER_FIRST_LANGUAGE_WEIGHTS)
    suburb = pick(rng, list(SUBURB_CENTRES))
    latitude, longitude = create_location(rng, suburb)
    provider_trades = pick_provider_trades(rng, trades)
    return {
        "id": format_id("prov", number),
        "role": "provider",
        "display_name": create_display_name(rng, first_language, taken_names),
        "phone": PROVIDER_PHONE_FORMAT.format(number),
        "lang": APP_LANGUAGE_BY_FIRST_LANGUAGE[first_language],
        "langs": list(SPOKEN_LANGUAGES_BY_FIRST_LANGUAGE[first_language]),
        "suburb": suburb,
        "lat": latitude,
        "lng": longitude,
        "trades": [trade.id for trade in provider_trades],
        "licensed": bool(rng.random() < LICENSED_SHARE),
        "id_badge": pick_id_badge(rng, first_language),
        "bio": create_bio(rng, provider_trades[0]),
        "joined_on": pick_joined_on(rng, today).isoformat(),
        "_true_skill": round(float(rng.beta(*TRUE_SKILL_BETA)), TRUE_SKILL_DECIMALS),
        "_first_language": first_language,
        "_price_factor": float(rng.lognormal(0.0, PRICE_FACTOR_SPREAD)),
    }


def create_random_customer(rng: np.random.Generator, number: int, taken_names: set[str]) -> dict:
    """Creates customer number `number`, living in a random suburb (often the demo one)."""
    first_language = pick_from_weights(rng, CUSTOMER_FIRST_LANGUAGE_WEIGHTS)
    suburbs = list(SUBURB_CENTRES)
    suburb_weights = [DEMO_SUBURB_WEIGHT if suburb == DEMO_SUBURB else 1.0 for suburb in suburbs]
    suburb = pick_weighted(rng, suburbs, suburb_weights)
    latitude, longitude = create_location(rng, suburb)
    return {
        "id": format_id("cust", number),
        "role": "customer",
        "display_name": create_display_name(rng, first_language, taken_names),
        "phone": CUSTOMER_PHONE_FORMAT.format(number),
        "lang": APP_LANGUAGE_BY_FIRST_LANGUAGE[first_language],
        "suburb": suburb,
        "address": create_address(rng, suburb),
        "lat": latitude,
        "lng": longitude,
        "id_badge": "none",
    }


def list_taken_names(tables: SeedTables) -> set[str]:
    """Lists the display names already used by providers and customers."""
    return {row["display_name"] for row in tables.providers + tables.customers}


def create_display_name(
    rng: np.random.Generator, first_language: str, taken_names: set[str]
) -> str:
    """Creates an unused made-up name such as "Nomvula K." and marks it as taken."""
    for _ in range(MAX_NAME_ATTEMPTS):
        first_name = pick(rng, FIRST_NAMES_BY_FIRST_LANGUAGE[first_language])
        display_name = f"{first_name} {pick(rng, SURNAME_INITIALS)}."
        if display_name not in taken_names:
            taken_names.add(display_name)
            return display_name
    raise RuntimeError(f"Ran out of made-up {first_language!r} names; add more to people.py")


def create_address(rng: np.random.Generator, suburb: str) -> str:
    """Creates a made-up street address in a suburb."""
    return ADDRESS_FORMAT.format(house_number=int(rng.integers(1, MAX_HOUSE_NUMBER)), suburb=suburb)


def create_bio(rng: np.random.Generator, trade: Trade) -> str:
    """Creates a short profile line such as "Plumber, 6 years' experience."."""
    years = int(rng.integers(MIN_EXPERIENCE_YEARS, MAX_EXPERIENCE_YEARS + 1))
    return f"{TRADE_PERSON_NAMES.get(trade.id, trade.label)}, {years} years' experience."


def pick_provider_trades(rng: np.random.Generator, trades: list[Trade]) -> list[Trade]:
    """Picks one trade for a provider, sometimes two."""
    first_trade = pick_trade(rng, trades)
    other_trades = [trade for trade in trades if trade != first_trade]
    if not other_trades or rng.random() >= SECOND_TRADE_SHARE:
        return [first_trade]
    weights = [TRADE_WEIGHTS.get(trade.id, OTHER_TRADE_WEIGHT) for trade in other_trades]
    return [first_trade, pick_weighted(rng, other_trades, weights)]


def pick_id_badge(rng: np.random.Generator, first_language: str) -> str:
    """Picks the ID check a provider has passed.

    chiShona speakers mostly come from Zimbabwe and have no SA ID, so they can't get the
    Home Affairs badge (passport and permit checks are a stretch feature). This is why ID
    badges must never feed the ranking.
    """
    if first_language == "sn":
        return "none"
    return pick_from_weights(rng, ID_BADGE_WEIGHTS)


def pick_joined_on(rng: np.random.Generator, today: date) -> date:
    """Picks when a provider joined: a few weeks ago for newcomers, earlier for the rest."""
    if rng.random() < NEWCOMER_SHARE:
        days_ago = int(rng.integers(1, NEWCOMER_JOINED_WITHIN_DAYS))
    else:
        days_ago = int(rng.integers(NEWCOMER_JOINED_WITHIN_DAYS, APP_HISTORY_DAYS + 1))
    return today - timedelta(days=days_ago)
