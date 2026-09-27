"""Shared pieces of the seed generator: the tables being built, ids, times and random picks.

Rows are plain dicts, ready to write as JSON. Fields starting with "_" are for the
generator only (such as a provider's hidden true skill) and are never written to the files
the app loads.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import NamedTuple, TypeVar

import numpy as np

SAST = timezone(timedelta(hours=2))  # South African time, as in the fixtures
ID_DIGITS = 3  # ids look like "job_001", as in the fixtures
INTERNAL_FIELD_PREFIX = "_"
APP_HISTORY_DAYS = 270  # the demo pretends the app has been running for about 9 months

Item = TypeVar("Item")


class Trade(NamedTuple):
    """A trade from data/glossary.json."""

    id: str
    label: str  # the English label, such as "Plumbing"


@dataclass
class SeedTables:
    """The rows being built, one list per output file."""

    providers: list[dict] = field(default_factory=list)
    customers: list[dict] = field(default_factory=list)
    jobs: list[dict] = field(default_factory=list)
    quotes: list[dict] = field(default_factory=list)
    off_app_jobs: list[dict] = field(default_factory=list)


def format_id(prefix: str, number: int) -> str:
    """Formats an id such as "prov_001"."""
    return f"{prefix}_{number:0{ID_DIGITS}d}"


def create_id(prefix: str, rows: list[dict]) -> str:
    """Creates the id for the next row of a table, such as "job_001" for its first row."""
    return format_id(prefix, len(rows) + 1)


def pick(rng: np.random.Generator, items: Sequence[Item]) -> Item:
    """Picks one item at random. Returns the item itself, never a numpy copy of it."""
    return items[int(rng.integers(len(items)))]


def pick_weighted(
    rng: np.random.Generator, items: Sequence[Item], weights: Sequence[float]
) -> Item:
    """Picks one item at random, in proportion to its weight."""
    probabilities = np.asarray(weights, dtype=float)
    return items[int(rng.choice(len(items), p=probabilities / probabilities.sum()))]


def pick_from_weights(rng: np.random.Generator, weights_by_item: dict[Item, float]) -> Item:
    """Picks one key of a {item: weight} dict at random, in proportion to its weight."""
    return pick_weighted(rng, list(weights_by_item), list(weights_by_item.values()))


def pick_date_before(rng: np.random.Generator, today: date, low_days: int, high_days: int) -> date:
    """Picks a random date from low_days (inclusive) to high_days (exclusive) before today."""
    return today - timedelta(days=int(rng.integers(low_days, high_days)))


def spread_dates(
    rng: np.random.Generator, first_day: date, last_day: date, count: int
) -> list[date]:
    """Picks count random dates from first_day to last_day (both inclusive), in order."""
    span_days = (last_day - first_day).days
    offsets_days = sorted(int(offset) for offset in rng.integers(0, span_days + 1, size=count))
    return [first_day + timedelta(days=offset_days) for offset_days in offsets_days]


def format_timestamp(day: date, hour: int, minute: int = 0) -> str:
    """Formats a South African time the way the fixtures do: 2026-09-29T08:00:00+02:00."""
    return datetime.combine(day, time(hour, minute), tzinfo=SAST).isoformat()


def remove_internal_fields(row: dict) -> dict:
    """Returns a copy of a row without the generator-only fields that start with "_"."""
    return {key: value for key, value in row.items() if not key.startswith(INTERNAL_FIELD_PREFIX)}
