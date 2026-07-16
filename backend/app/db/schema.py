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

LISTING_COLUMN_UPGRADES = (
    ColumnUpgrade("agency_id", "INTEGER", "NULL", "NULL", nullable=True),
    ColumnUpgrade("slug", "VARCHAR(300)", "'listing-' || id", "''"),
    ColumnUpgrade("moderation_status", "VARCHAR(20)", "'pending'", "'pending'"),
    ColumnUpgrade("location_address", "VARCHAR(255)", "NULL", "NULL", nullable=True),
    ColumnUpgrade("latitude", "FLOAT", "NULL", "NULL", nullable=True),
    ColumnUpgrade("longitude", "FLOAT", "NULL", "NULL", nullable=True),
    ColumnUpgrade("condition", "VARCHAR(50)", "NULL", "NULL", nullable=True),
    ColumnUpgrade("draft_depth", "FLOAT", "NULL", "NULL", nullable=True),
    ColumnUpgrade("beam_width", "FLOAT", "NULL", "NULL", nullable=True),
    ColumnUpgrade("is_featured", "BOOLEAN", "FALSE", "FALSE"),
    ColumnUpgrade("published_at", "TIMESTAMP", "NULL", "NULL", nullable=True),
)

LISTING_MEDIA_COLUMN_UPGRADES = (
    ColumnUpgrade("sort_order", "INTEGER", "0", "0"),
)

BLOG_POST_COLUMN_UPGRADES = (
    ColumnUpgrade("excerpt", "VARCHAR(500)", "NULL", "NULL", nullable=True),
    ColumnUpgrade("cover_image_url", "VARCHAR(600)", "NULL", "NULL", nullable=True),
    ColumnUpgrade("podcast_embed_url", "VARCHAR(600)", "NULL", "NULL", nullable=True),
)

ENUM_VALUE_UPGRADES = {
    "listingcategory": (
        "real_estate",
        "car",
        "hypercar",
        "yacht",
        "jet",
        "watch",
        "jewelry",
        "rental",
    ),
    "listingstatus": ("draft", "active", "pending", "sold"),
    "moderationstatus": ("pending", "approved", "rejected"),
    "userrole": ("standard_user", "private_seller", "business_account", "super_admin"),
    "subscriptionstatus": ("trial", "active", "past_due", "canceled"),
}


def ensure_schema_compatibility(engine: Engine) -> None:
    """Apply additive schema fixes for persistent databases from older app versions."""
    _ensure_postgresql_enum_values(engine)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    _ensure_table_columns(engine, inspector, table_names, "users", USER_COLUMN_UPGRADES)
    _ensure_table_columns(engine, inspector, table_names, "inquiries", INQUIRY_COLUMN_UPGRADES)
    _ensure_table_columns(engine, inspector, table_names, "listings", LISTING_COLUMN_UPGRADES)
    _ensure_table_columns(engine, inspector, table_names, "listing_media", LISTING_MEDIA_COLUMN_UPGRADES)
    _ensure_table_columns(engine, inspector, table_names, "blog_posts", BLOG_POST_COLUMN_UPGRADES)


def _ensure_postgresql_enum_values(engine: Engine) -> None:
    if engine.dialect.name != "postgresql":
        return

    with engine.begin() as connection:
        enum_names = tuple(ENUM_VALUE_UPGRADES)
        existing_types = {
            row[0]
            for row in connection.execute(
                text(
                    """
                    SELECT typname
                    FROM pg_type
                    WHERE typtype = 'e'
                      AND typname = ANY(:enum_names)
                    """
                ),
                {"enum_names": list(enum_names)},
            )
        }
        for enum_name, values in ENUM_VALUE_UPGRADES.items():
            if enum_name not in existing_types:
                continue
            quoted_enum_name = _quote(engine, enum_name)
            for value in values:
                connection.execute(text(f"ALTER TYPE {quoted_enum_name} ADD VALUE IF NOT EXISTS '{value}'"))


def backfill_listing_subtype_rows(engine: Engine) -> None:
    """Populate additive listing subtype rows from legacy wide listing columns."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    required_tables = {
        "listings",
        "listing_real_estate",
        "listing_vehicle",
        "listing_vessel_aircraft",
        "listing_watch_jewelry",
        "listing_rental_terms",
    }
    if not required_tables.issubset(table_names):
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO listing_real_estate (
                    listing_id, area_value, area_unit, bedrooms, bathrooms
                )
                SELECT
                    listings.id,
                    listings.square_footage,
                    CASE WHEN listings.square_footage IS NOT NULL THEN 'sqft' ELSE NULL END,
                    listings.bedrooms,
                    listings.bathrooms
                FROM listings
                WHERE listings.category = 'real_estate'
                  AND NOT EXISTS (
                    SELECT 1
                    FROM listing_real_estate
                    WHERE listing_real_estate.listing_id = listings.id
                  )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO listing_vehicle (
                    listing_id, make, model, year, mileage_value, mileage_unit
                )
                SELECT
                    listings.id,
                    listings.make,
                    listings.model,
                    listings.year,
                    listings.mileage,
                    CASE WHEN listings.mileage IS NOT NULL THEN 'mi' ELSE NULL END
                FROM listings
                WHERE listings.category IN ('car', 'hypercar')
                  AND NOT EXISTS (
                    SELECT 1
                    FROM listing_vehicle
                    WHERE listing_vehicle.listing_id = listings.id
                  )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO listing_vessel_aircraft (
                    listing_id, asset_type, builder, year
                )
                SELECT listings.id, listings.category, listings.make, listings.year
                FROM listings
                WHERE listings.category IN ('yacht', 'jet')
                  AND NOT EXISTS (
                    SELECT 1
                    FROM listing_vessel_aircraft
                    WHERE listing_vessel_aircraft.listing_id = listings.id
                  )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO listing_watch_jewelry (
                    listing_id, asset_type, brand, reference_number
                )
                SELECT listings.id, listings.category, listings.make, listings.model
                FROM listings
                WHERE listings.category IN ('watch', 'jewelry')
                  AND NOT EXISTS (
                    SELECT 1
                    FROM listing_watch_jewelry
                    WHERE listing_watch_jewelry.listing_id = listings.id
                  )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO listing_rental_terms (
                    listing_id, pricing_tiers
                )
                SELECT listings.id, '{}'
                FROM listings
                WHERE listings.category = 'rental'
                  AND NOT EXISTS (
                    SELECT 1
                    FROM listing_rental_terms
                    WHERE listing_rental_terms.listing_id = listings.id
                  )
                """
            )
        )


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
