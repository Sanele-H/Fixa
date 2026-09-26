"""Command line for the seed generator. From the repo root:

    node scripts/run-python.mjs -m ranking.seed [--seed N] [--today YYYY-MM-DD]

It overwrites the files in data/seed/.
"""

import argparse
from datetime import date
from pathlib import Path

from ranking.seed import (
    DEFAULT_SEED,
    DEFAULT_TODAY,
    GLOSSARY_PATH,
    SEED_DIR_PATH,
    generate_seed,
    read_trades,
    write_seed,
)


def main() -> None:
    """Generates the seed data, writes it, and prints how many rows each file got."""
    arguments = parse_arguments()
    tables_by_name = generate_seed(read_trades(arguments.glossary), arguments.seed, arguments.today)
    write_seed(tables_by_name, arguments.out)
    for table_name, rows in tables_by_name.items():
        print(f"{arguments.out / table_name}.json: {len(rows)} rows")


def parse_arguments() -> argparse.Namespace:
    """Reads the command-line options; every one has a default."""
    parser = argparse.ArgumentParser(
        prog="python -m ranking.seed", description="Writes the Fixa demo seed data."
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="random seed")
    parser.add_argument(
        "--today", type=date.fromisoformat, default=DEFAULT_TODAY, help="the demo's today"
    )
    parser.add_argument("--glossary", type=Path, default=GLOSSARY_PATH, help="glossary.json")
    parser.add_argument("--out", type=Path, default=SEED_DIR_PATH, help="output folder")
    return parser.parse_args()


if __name__ == "__main__":
    main()
