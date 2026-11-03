"""Short-lived persisted counters for cross-worker broker bulk throttling."""

from mongoengine import DateTimeField, Document, IntField, StringField


class BrokerBulkRateLimit(Document):
    meta = {
        "collection": "broker_bulk_rate_limits",
        "indexes": [{"fields": ["expires_at"], "expireAfterSeconds": 0}],
    }

    id = StringField(primary_key=True)
    organization_id = IntField(required=True)
    user_id = IntField(required=True)
    window_id = IntField(required=True)
    request_count = IntField(required=True, default=0)
    created_at = DateTimeField(required=True)
    updated_at = DateTimeField(required=True)
    expires_at = DateTimeField(required=True)
