"""Append-only snapshots of broker listing edits."""

from mongoengine import DictField, IntField

from backend.app.broker.models.base import BrokerBaseDocument


class BrokerListingRevision(BrokerBaseDocument):
    meta = {
        "collection": "broker_listing_revisions",
        "indexes": ["organization_id", "listing_id", "version", "created_at"],
    }

    listing_id = IntField(required=True)
    version = IntField(required=True)
    actor_user_id = IntField(required=True)
    snapshot = DictField(required=True)
