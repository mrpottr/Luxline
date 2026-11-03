"""Base document model for all Broker collection entities."""

from datetime import datetime
from mongoengine import BooleanField, DateTimeField, Document, IntField, SequenceField


def _utcnow() -> datetime:
    return datetime.utcnow()


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

    id = SequenceField(primary_key=True)
    organization_id = IntField(required=True)
    created_at = DateTimeField(default=_utcnow)
    updated_at = DateTimeField(default=_utcnow)
    is_deleted = BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.updated_at = _utcnow()
        return super().save(*args, **kwargs)
