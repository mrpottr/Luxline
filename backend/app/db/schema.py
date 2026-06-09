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


def ensure_schema_compatibility(engine: Engine) -> None:
    """Apply additive schema fixes for persistent databases from older app versions."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    missing_columns = [column for column in USER_COLUMN_UPGRADES if column.name not in existing_columns]
    if not missing_columns:
        return

    dialect_name = engine.dialect.name
    with engine.begin() as connection:
        for column in missing_columns:
            if dialect_name == "postgresql":
                _add_postgresql_column(connection, column)
            else:
                _add_portable_column(connection, column)


def _add_postgresql_column(connection, column: ColumnUpgrade) -> None:
    column_name = _quote(connection.engine, column.name)
    connection.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column.type_sql}"))
    connection.execute(text(f"UPDATE users SET {column_name} = {column.existing_value_sql} WHERE {column_name} IS NULL"))
    connection.execute(text(f"ALTER TABLE users ALTER COLUMN {column_name} SET DEFAULT {column.default_sql}"))
    if not column.nullable:
        connection.execute(text(f"ALTER TABLE users ALTER COLUMN {column_name} SET NOT NULL"))


def _add_portable_column(connection, column: ColumnUpgrade) -> None:
    column_name = _quote(connection.engine, column.name)
    connection.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column.type_sql}"))
    connection.execute(text(f"UPDATE users SET {column_name} = {column.existing_value_sql} WHERE {column_name} IS NULL"))


def _quote(engine: Engine, identifier: str) -> str:
    return engine.dialect.identifier_preparer.quote(identifier)
