"""Broker-owned binary listing media for the mock storage adapter."""

from mongoengine import BinaryField, StringField

from backend.app.broker.models.base import BrokerBaseDocument


class BrokerMediaAsset(BrokerBaseDocument):
    meta = {
        "collection": "broker_media_assets",
        "indexes": ["organization_id", "created_at", "is_deleted"],
    }

    content = BinaryField(required=True)
    content_type = StringField(required=True, max_length=100)
    media_type = StringField(required=True, max_length=20)
    alt_text = StringField(default="", max_length=300)
    moderation_state = StringField(default="pending", max_length=20)
