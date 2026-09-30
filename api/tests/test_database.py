"""Checks that the database setup behaves the same on SQLite as it will on Postgres."""

import datetime as dt
import json

import pytest
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from fixa_api.db import create_database_engine
from fixa_api.models import Job, Quote
from fixa_api.seed import SEED_DIRECTORY_PATH, SEED_TABLES


def test_seed_loads_every_row_of_every_file(seeded_session):
    for file_name, model in SEED_TABLES:
        seed_file_path = SEED_DIRECTORY_PATH / f"{file_name}.json"
        expected_row_count = len(json.loads(seed_file_path.read_text(encoding="utf-8")))

        row_count = seeded_session.exec(select(func.count()).select_from(model)).one()

        assert row_count == expected_row_count, file_name


def test_datetimes_come_back_in_utc(seeded_session):
    job = seeded_session.get(Job, "job_001")

    # The seed says 2026-09-29T08:00:00+02:00, which is 06:00 UTC.
    assert job.created_at == dt.datetime(2026, 9, 29, 6, 0, tzinfo=dt.UTC)


def test_foreign_keys_are_enforced(seeded_session):
    orphan_quote = Quote(
        id="quote_orphan",
        job_id="job_does_not_exist",
        provider_id="prov_001",
        amount_rands=100,
        when=dt.datetime(2026, 9, 29, 10, 0, tzinfo=dt.UTC),
        state="open",
        created_at=dt.datetime(2026, 9, 29, 9, 0, tzinfo=dt.UTC),
    )
    seeded_session.add(orphan_quote)

    with pytest.raises(IntegrityError):
        seeded_session.commit()


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql://user:secret@db.example.com:5432/postgres",
        "postgres://user:secret@db.example.com:5432/postgres",
        "postgresql+psycopg://user:secret@db.example.com:5432/postgres",
    ],
)
def test_postgres_urls_use_the_installed_psycopg_driver(database_url):
    # Building the engine loads the driver without connecting, so a psycopg2 URL fails here.
    engine = create_database_engine(database_url)

    assert engine.dialect.driver == "psycopg"
