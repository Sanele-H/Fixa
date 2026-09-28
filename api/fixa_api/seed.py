"""Load data/seed/ into the database named by DATABASE_URL. Drops every table first.

Run from the repo root: node scripts/run-python.mjs -m fixa_api.seed
"""

import json
from pathlib import Path

from sqlmodel import Session, SQLModel

from fixa_api.db import engine
from fixa_api.models import Customer, Job, OffAppJob, Provider, Quote

SEED_DIRECTORY_PATH = Path(__file__).resolve().parents[2] / "data" / "seed"

# Listed by name, parents before children, so every foreign key finds its row.
# hidden_truth.json is left out on purpose: it must never reach the app's database.
SEED_TABLES = [
    ("providers", Provider),
    ("customers", Customer),
    ("jobs", Job),
    ("quotes", Quote),
    ("off_app_jobs", OffAppJob),
]


def reset_tables() -> None:
    """Drop and recreate every table, so each seed run starts from empty."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def create_rows_from_seed_file(session: Session, file_name: str, model: type[SQLModel]) -> int:
    """Validate each row of data/seed/<file_name>.json as model, insert it, and return the count.

    model_validate turns the seed's date strings into dates; model(**row) would not. The flush
    inserts the rows straight away, so the next file's foreign keys can find them.
    """
    seed_file_path = SEED_DIRECTORY_PATH / f"{file_name}.json"
    seed_rows = json.loads(seed_file_path.read_text(encoding="utf-8"))
    session.add_all([model.model_validate(seed_row) for seed_row in seed_rows])
    session.flush()
    return len(seed_rows)


def seed_database() -> None:
    """Reset the tables and load every seed file in one transaction."""
    reset_tables()
    with Session(engine) as session:
        for file_name, model in SEED_TABLES:
            row_count = create_rows_from_seed_file(session, file_name, model)
            print(f"{file_name}: {row_count} rows")
        session.commit()


if __name__ == "__main__":
    seed_database()
