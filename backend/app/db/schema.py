"""Schema helpers for MongoDB.

MongoDB is schemaless, so collections and indexes are created automatically by
MongoEngine. These helpers remain as no-ops for backward compatibility.
"""


def ensure_schema_compatibility(engine=None) -> None:
    """No-op retained for compatibility with the previous relational backend."""


def backfill_listing_subtype_rows(engine=None) -> None:
    """No-op retained for compatibility with the previous relational backend."""
