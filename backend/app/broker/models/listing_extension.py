"""Broker listing extension model."""

from mongoengine import BooleanField, DictField, IntField, ListField, StringField
from backend.app.broker.models.base import BrokerBaseDocument


class BrokerListing(BrokerBaseDocument):
    """Extension document linking an existing marketplace listing to broker metadata."""

    meta = {
        "collection": "broker_listings",
        "indexes": [
            "organization_id",
            "listing_id",
            {"fields": ("organization_id", "listing_id"), "unique": True},
            {"fields": ("organization_id", "idempotency_key"), "unique": True, "sparse": True},
            "assigned_agent_id",
            "quality_rating",
            "is_deleted",
        ],
    }

    listing_id = IntField(required=True)
    assigned_agent_id = IntField()
    branch_id = IntField()
    owner_name = StringField(max_length=200)
    owner_mandate_reference = StringField(max_length=200)
    owner_consent = BooleanField(default=False)
    commission_terms = StringField(max_length=2000)
    quality_score = IntField(default=0)
    quality_rating = StringField(default="red", max_length=20)  # green | orange | red
    quality_suggestions = ListField(StringField(), default=list)
    media_items = ListField(DictField(), default=list)
    urgent_flag = BooleanField(default=False)
    version = IntField(default=1)
    idempotency_key = StringField(required=True, max_length=128)
    idempotency_payload_hash = StringField(required=True, max_length=64)

