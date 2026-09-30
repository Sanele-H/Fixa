"""add_missing_columns(): a database made before a column was added catches up on start."""

import datetime as dt

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, select

from fixa_api.db import IN_MEMORY_DATABASE_URL, create_database_engine
from fixa_api.migrations import add_missing_columns
from fixa_api.models import SafetyTimer

# safety_timer as PR #34 created it, before PR #35 added reason and alert_at
OLD_SAFETY_TIMER_TABLE = """
CREATE TABLE safety_timer (
    id VARCHAR NOT NULL PRIMARY KEY,
    job_id VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    state VARCHAR NOT NULL,
    started_at DATETIME NOT NULL,
    due_at DATETIME NOT NULL,
    ended_at DATETIME
)
"""
DUE_AT = "2026-10-01 08:00:00.000000"


def make_old_database():
    """An empty in-memory database with only the old safety_timer table and one running timer."""
    engine = create_database_engine(IN_MEMORY_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=OFF"))
        connection.execute(text(OLD_SAFETY_TIMER_TABLE))
        connection.execute(
            text(
                "INSERT INTO safety_timer (id, job_id, user_id, state, started_at, due_at) "
                "VALUES ('timer_1', 'job_1', 'prov_001', 'running', :due_at, :due_at)"
            ),
            {"due_at": DUE_AT},
        )
    return engine


def test_old_safety_timer_table_gets_the_new_columns_filled_in():
    engine = make_old_database()

    added_names = add_missing_columns(engine)

    assert added_names == ["safety_timer.reason", "safety_timer.alert_at"]
    with Session(engine) as session:
        timer = session.exec(select(SafetyTimer)).one()
    assert timer.reason == "manual"
    assert timer.alert_at == timer.due_at == dt.datetime(2026, 10, 1, 8, tzinfo=dt.UTC)


def test_running_it_again_changes_nothing():
    engine = make_old_database()
    add_missing_columns(engine)

    assert add_missing_columns(engine) == []


def test_a_new_database_needs_nothing_added():
    engine = create_database_engine(IN_MEMORY_DATABASE_URL)
    SQLModel.metadata.create_all(engine)

    assert add_missing_columns(engine) == []
    column_names = {column["name"] for column in inspect(engine).get_columns("safety_timer")}
    assert {"reason", "alert_at"} <= column_names


def test_a_job_table_without_directions_gets_the_column():
    engine = create_database_engine(IN_MEMORY_DATABASE_URL)
    SQLModel.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE job DROP COLUMN directions"))

    assert add_missing_columns(engine) == ["job.directions"]
    column_names = {column["name"] for column in inspect(engine).get_columns("job")}
    assert "directions" in column_names
