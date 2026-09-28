"""Database engine and sessions. SQLite on laptops, Supabase Postgres when live (DATABASE_URL)."""

import os
import sqlite3

from dotenv import load_dotenv
from sqlalchemy import Engine, event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

DEFAULT_DATABASE_URL = "sqlite:///./fixa.db"
IN_MEMORY_DATABASE_URL = "sqlite://"


def enable_sqlite_foreign_keys(connection: sqlite3.Connection, _connection_record: object) -> None:
    """Switch on foreign keys for a new SQLite connection. SQLite leaves them off and Postgres
    always enforces them, so without this a broken reference only fails once deployed."""
    connection.execute("PRAGMA foreign_keys=ON")


def create_database_engine(database_url: str) -> Engine:
    """Return an engine for database_url.

    Postgres: pool_pre_ping replaces connections the Supabase pooler has closed.
    SQLite: foreign keys on, and connections may cross threads (FastAPI runs sync routes in a
    thread pool). The in-memory URL shares one connection (StaticPool), because otherwise each
    new connection to "sqlite://" would be a separate, empty database.
    """
    if not database_url.startswith("sqlite"):
        return create_engine(database_url, pool_pre_ping=True)
    engine_options = {"connect_args": {"check_same_thread": False}}
    if database_url == IN_MEMORY_DATABASE_URL:
        engine_options["poolclass"] = StaticPool
    sqlite_engine = create_engine(database_url, **engine_options)
    event.listen(sqlite_engine, "connect", enable_sqlite_foreign_keys)
    return sqlite_engine


load_dotenv()
engine = create_database_engine(os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))


def get_session():
    """Yield one session per request. Use it as a FastAPI dependency; tests override it."""
    with Session(engine) as session:
        yield session
