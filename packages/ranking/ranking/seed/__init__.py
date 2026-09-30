"""Demo seed data for data/seed/: providers, customers, jobs, quotes and off-app jobs (P4).

Run from the repo root. It overwrites the files in data/seed/:

    node scripts/run-python.mjs -m ranking.seed

Everything is made up and comes from one random seed, so a rerun gives the same files.
Trade ids come from data/glossary.json, so rerun it after P3 adds trades. The file format
is described in data/seed/README.md.
"""

import json
from datetime import date
from pathlib import Path

import numpy as np

from ranking.seed.common import SeedTables, Trade, remove_internal_fields
from ranking.seed.jobs import add_random_open_jobs, add_random_past_jobs
from ranking.seed.off_app import add_random_off_app_jobs
from ranking.seed.people import add_random_customers, add_random_providers
from ranking.seed.story import add_story_people, add_story_work

REPO_ROOT_PATH = Path(__file__).resolve().parents[4]
GLOSSARY_PATH = REPO_ROOT_PATH / "data" / "glossary.json"
SEED_DIR_PATH = REPO_ROOT_PATH / "data" / "seed"

DEFAULT_SEED = 2026
DEFAULT_TODAY = date(2026, 9, 29)  # the day the fixtures' demo happens
PROVIDER_COUNT = 60
CUSTOMER_COUNT = 80
RANDOM_PAST_JOB_COUNT = 400
RANDOM_OPEN_JOB_COUNT = 12
APP_TABLE_NAMES = ["providers", "customers", "jobs", "quotes", "off_app_jobs"]
# The demo's trades. The people and jobs made for them stay the same as the glossary grows,
# because the tests and the demo name them; other trades get their own people and jobs
# afterwards, from a separate random stream.
CORE_TRADE_IDS = ["plumbing", "electrical"]
MORE_TRADES_STREAM = 1  # which random stream, beside the seed, the other trades use
MORE_TRADES_PROVIDER_COUNT = 40
MORE_TRADES_PAST_JOB_COUNT = 250
MORE_TRADES_OPEN_JOB_COUNT = 8


def read_trades(glossary_path: Path = GLOSSARY_PATH) -> list[Trade]:
    """Reads the trade ids and English labels from data/glossary.json."""
    glossary = json.loads(glossary_path.read_text(encoding="utf-8"))
    return [Trade(id=trade["id"], label=trade["labels"]["en"]) for trade in glossary["trades"]]


def generate_seed(
    trades: list[Trade], seed: int = DEFAULT_SEED, today: date = DEFAULT_TODAY
) -> dict[str, list[dict]]:
    """Generates every seed table.

    Args:
        trades: the trades in data/glossary.json, from read_trades().
        seed: the random seed. The same seed, trades and today give the same data.
        today: the demo's "today": past jobs end before it and open jobs are just before it.

    Returns:
        {table name: rows} for providers, customers, jobs, quotes and off_app_jobs (what the
        app loads), plus hidden_truth: each provider's true skill and first language, for
        the fairness check only.
    """
    rng = np.random.default_rng(seed)
    trades_by_id = {trade.id: trade for trade in trades}
    core_trades = [
        trades_by_id[trade_id] for trade_id in CORE_TRADE_IDS if trade_id in trades_by_id
    ]
    more_trades = [trade for trade in trades if trade.id not in CORE_TRADE_IDS]
    tables = SeedTables()
    add_story_people(tables, today)
    add_random_providers(tables, rng, core_trades, today, PROVIDER_COUNT - len(tables.providers))
    add_random_customers(tables, rng, CUSTOMER_COUNT - len(tables.customers))
    add_story_work(tables, rng, trades_by_id, today)
    add_random_past_jobs(tables, rng, core_trades, today, RANDOM_PAST_JOB_COUNT)
    add_random_off_app_jobs(tables, rng, trades_by_id, tables.providers)
    add_random_open_jobs(tables, rng, core_trades, today, RANDOM_OPEN_JOB_COUNT)
    if more_trades:
        more_trades_rng = np.random.default_rng([seed, MORE_TRADES_STREAM])
        add_more_trades_work(tables, more_trades_rng, more_trades, trades_by_id, today)
    return build_output_tables(tables)


def add_more_trades_work(
    tables: SeedTables,
    rng: np.random.Generator,
    trades: list[Trade],
    trades_by_id: dict[str, Trade],
    today: date,
) -> None:
    """Adds providers, past jobs, off-app jobs and open jobs for the trades beyond the core ones.

    They come after the core rows, so the core rows keep their ids. The customers are the ones
    already in the table.
    """
    first_new_provider = len(tables.providers)
    add_random_providers(tables, rng, trades, today, MORE_TRADES_PROVIDER_COUNT)
    add_random_past_jobs(tables, rng, trades, today, MORE_TRADES_PAST_JOB_COUNT)
    add_random_off_app_jobs(tables, rng, trades_by_id, tables.providers[first_new_provider:])
    add_random_open_jobs(tables, rng, trades, today, MORE_TRADES_OPEN_JOB_COUNT)


def build_output_tables(tables: SeedTables) -> dict[str, list[dict]]:
    """Builds the tables to write: the app's tables without internal fields, and hidden_truth."""
    output_tables = {
        table_name: [remove_internal_fields(row) for row in getattr(tables, table_name)]
        for table_name in APP_TABLE_NAMES
    }
    output_tables["hidden_truth"] = [build_hidden_truth(row) for row in tables.providers]
    return output_tables


def build_hidden_truth(provider: dict) -> dict:
    """Builds a provider's hidden_truth row: known to the fairness check, never to the app."""
    return {
        "provider_id": provider["id"],
        "true_skill": provider["_true_skill"],
        "first_language": provider["_first_language"],
    }


def write_seed(tables_by_name: dict[str, list[dict]], seed_dir_path: Path = SEED_DIR_PATH) -> None:
    """Writes each table to <table name>.json in seed_dir_path.

    Each file is a JSON array with one row per line, so it stays small and git diffs stay
    readable. Line endings are always \\n, so the files are the same on every OS.
    """
    seed_dir_path.mkdir(parents=True, exist_ok=True)
    for table_name, rows in tables_by_name.items():
        row_lines = ",\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
        seed_file_path = seed_dir_path / f"{table_name}.json"
        seed_file_path.write_text(f"[\n{row_lines}\n]\n", encoding="utf-8", newline="\n")
