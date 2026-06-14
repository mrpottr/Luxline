"""Small idempotent schema upgrades for databases created before migrations existed."""

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class ColumnUpgrade:
    name: str
    type_sql: str
    existing_value_sql: str
    default_sql: str
    nullable: bool = False


USER_COLUMN_UPGRADES = (
    ColumnUpgrade("is_email_verified", "BOOLEAN", "TRUE", "FALSE"),
    ColumnUpgrade("is_verified_business", "BOOLEAN", "FALSE", "FALSE"),
    ColumnUpgrade("is_2fa_enabled", "BOOLEAN", "FALSE", "FALSE"),
    ColumnUpgrade("preferred_currency", "VARCHAR(8)", "'USD'", "'USD'"),
    ColumnUpgrade("preferred_language", "VARCHAR(8)", "'en'", "'en'"),
    ColumnUpgrade("measurement_system", "VARCHAR(16)", "'imperial'", "'imperial'"),
)

INQUIRY_COLUMN_UPGRADES = (
    ColumnUpgrade("status", "VARCHAR(24)", "'sent'", "'sent'"),
    ColumnUpgrade("viewed_at", "TIMESTAMP", "NULL", "NULL", nullable=True),
    ColumnUpgrade("replied_at", "TIMESTAMP", "NULL", "NULL", nullable=True),
)


def ensure_schema_compatibility(engine: Engine) -> None:
    """Apply additive schema fixes for persistent databases from older app versions."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    _ensure_table_columns(engine, inspector, table_names, "users", USER_COLUMN_UPGRADES)
    _ensure_table_columns(engine, inspector, table_names, "inquiries", INQUIRY_COLUMN_UPGRADES)


def _ensure_table_columns(
    engine: Engine,
    inspector,
    table_names: set[str],
    table_name: str,
    upgrades: tuple[ColumnUpgrade, ...],
) -> None:
    if table_name not in table_names:
        return

    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    missing_columns = [column for column in upgrades if column.name not in existing_columns]
    if not missing_columns:
        return

    table_identifier = _quote(engine, table_name)
    with engine.begin() as connection:
        for column in missing_columns:
            if engine.dialect.name == "postgresql":
                _add_postgresql_column(connection, table_identifier, column)
            else:
                _add_portable_column(connection, table_identifier, column)


def _add_postgresql_column(connection, table_identifier: str, column: ColumnUpgrade) -> None:
    column_name = _quote(connection.engine, column.name)
    connection.execute(text(f"ALTER TABLE {table_identifier} ADD COLUMN {column_name} {column.type_sql}"))
    connection.execute(
        text(f"UPDATE {table_identifier} SET {column_name} = {column.existing_value_sql} WHERE {column_name} IS NULL")
    )
    connection.execute(text(f"ALTER TABLE {table_identifier} ALTER COLUMN {column_name} SET DEFAULT {column.default_sql}"))
    if not column.nullable:
        connection.execute(text(f"ALTER TABLE {table_identifier} ALTER COLUMN {column_name} SET NOT NULL"))


def _add_portable_column(connection, table_identifier: str, column: ColumnUpgrade) -> None:
    column_name = _quote(connection.engine, column.name)
    connection.execute(text(f"ALTER TABLE {table_identifier} ADD COLUMN {column_name} {column.type_sql}"))
    connection.execute(
        text(f"UPDATE {table_identifier} SET {column_name} = {column.existing_value_sql} WHERE {column_name} IS NULL")
    )


def _quote(engine: Engine, identifier: str) -> str:
    return engine.dialect.identifier_preparer.quote(identifier)
