"""Columns added to tables that already exist on a deployed database.

create_all() only creates missing tables; it never adds a column to a table that exists. So when a
PR adds a column to a table that's already live (the Supabase database, or a laptop's fixa.db),
list it here, and add_missing_columns() adds it when the server starts. It's safe to run on every
start: a column that's already there, or a table that doesn't exist yet (create_all makes it
whole), is skipped.
"""

import logging
from dataclasses import dataclass

from sqlalchemy import Engine, inspect, text
from sqlmodel import SQLModel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AddedColumn:
    """One column a later PR added to an existing table, and how to fill it for existing rows."""

    table_name: str
    column_name: str
    default_sql: str | None = None  # a SQL literal every existing row gets, e.g. "'manual'"
    fill_from_column: str | None = None  # or copy another column's value into existing rows


ADDED_COLUMNS = [
    # PR #35: timers started by checking in, and a grace period after "Are you OK?"
    AddedColumn("safety_timer", "reason", default_sql="'manual'"),
    AddedColumn("safety_timer", "alert_at", fill_from_column="due_at"),
]


def add_missing_columns(engine: Engine) -> list[str]:
    """Add every column in ADDED_COLUMNS that its table doesn't have yet, filling existing rows.

    The column's SQL type comes from the model, compiled for this database, so SQLite and
    Postgres each get their own type. New columns are added as nullable, since existing rows
    only get their value after the column exists. Returns the "table.column" names it added.
    """
    inspector = inspect(engine)
    added_names = []
    with engine.begin() as connection:
        for added_column in ADDED_COLUMNS:
            table_name, column_name = added_column.table_name, added_column.column_name
            if not inspector.has_table(table_name):
                continue
            existing_names = {column["name"] for column in inspector.get_columns(table_name)}
            if column_name in existing_names:
                continue
            model_column = SQLModel.metadata.tables[table_name].c[column_name]
            column_type = model_column.type.compile(dialect=engine.dialect)
            default = f" DEFAULT {added_column.default_sql}" if added_column.default_sql else ""
            connection.execute(
                text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}{default}")
            )
            if added_column.fill_from_column:
                connection.execute(
                    text(
                        f"UPDATE {table_name} SET {column_name} = {added_column.fill_from_column} "
                        f"WHERE {column_name} IS NULL"
                    )
                )
            added_names.append(f"{table_name}.{column_name}")
    for added_name in added_names:
        logger.info("Added missing column %s", added_name)
    return added_names
