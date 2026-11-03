"""Base document model for all Broker collection entities."""

from datetime import datetime, timezone
from mongoengine import BooleanField, DateTimeField, Document, IntField, SequenceField
from mongoengine.connection import get_db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class BrokerBaseDocument(Document):
    """Abstract base document for Broker entities.

    Enforces:
    1. Integer sequence primary key.
    2. Tenant isolation via mandatory `organization_id`.
    3. Auto-updating audit timestamps.
    4. Soft-delete support (`is_deleted`).
    """

    meta = {
        "abstract": True,
        "allow_inheritance": True,
    }

    id = SequenceField(collection_name="broker_sequences", primary_key=True)
    organization_id = IntField(required=True)
    created_at = DateTimeField(default=_utcnow)
    updated_at = DateTimeField(default=_utcnow)
    is_deleted = BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.updated_at = _utcnow()
        if self.id is None:
            # Preserve sequence continuity for broker documents created before the
            # counter collection was namespaced, while keeping counters broker-only.
            field = self._fields["id"]
            sequence_id = f"{self._get_collection_name()}.id"
            counters = get_db(alias=field.db_alias)[field.collection_name]
            if counters.find_one({"_id": sequence_id}) is None:
                collection = self._get_collection()
                current = collection.find_one(sort=[("id", -1)])
                highest_id = int(current.get("id", 0)) if current else 0
                counters.update_one(
                    {"_id": sequence_id},
                    {"$setOnInsert": {"next": highest_id}},
                    upsert=True,
                )
        return super().save(*args, **kwargs)

