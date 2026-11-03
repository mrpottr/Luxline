"""Broker reviews, explainable badges, moderation cases, and audit history."""

from mongoengine import BooleanField, DateTimeField, DictField, IntField, StringField

from backend.app.broker.models.base import BrokerBaseDocument


class BrokerReview(BrokerBaseDocument):
    meta = {
        "collection": "broker_reviews",
        "indexes": [
            "organization_id", "listing_id", "buyer_id", "status", "created_at",
            {"fields": ("organization_id", "lead_id"), "unique": True},
            {"fields": ("organization_id", "listing_id", "buyer_id"), "unique": True},
            {"fields": ("organization_id", "buyer_id", "idempotency_key"), "unique": True},
        ],
    }

    lead_id = IntField(required=True)
    listing_id = IntField(required=True)
    buyer_id = IntField(required=True)
    rating = IntField(required=True, min_value=1, max_value=5)
    body = StringField(required=True, max_length=3000)
    public_consent = BooleanField(required=True, default=False)
    status = StringField(required=True, default="pending", max_length=20)
    broker_reply = StringField(max_length=2000)
    replied_by = IntField()
    replied_at = DateTimeField()
    appeal_state = StringField(default="none", max_length=20)
    idempotency_key = StringField(required=True, max_length=128)
    payload_hash = StringField(required=True, max_length=64)


class BrokerBadge(BrokerBaseDocument):
    meta = {
        "collection": "broker_badges",
        "indexes": [
            "organization_id", "badge_code", "awarded",
            {"fields": ("organization_id", "subject_type", "subject_id", "badge_code"), "unique": True},
        ],
    }

    subject_type = StringField(required=True, max_length=16)
    subject_id = IntField(required=True)
    badge_code = StringField(required=True, max_length=40)
    rule_version = IntField(required=True, min_value=1)
    awarded = BooleanField(required=True)
    explanation = StringField(required=True, max_length=500)
    criteria_snapshot = DictField(default=dict)
    evaluated_at = DateTimeField(required=True)


class BrokerModerationCase(BrokerBaseDocument):
    meta = {
        "collection": "broker_moderation_cases",
        "indexes": ["organization_id", "status", "case_type", "created_at", "resource_id"],
    }

    case_type = StringField(required=True, max_length=40)
    resource_type = StringField(required=True, max_length=32)
    resource_id = IntField(required=True)
    actor_user_id = IntField()
    reason = StringField(required=True, max_length=1000)
    severity = StringField(default="medium", max_length=16)
    status = StringField(default="open", max_length=16)
    resolution = StringField(max_length=1000)
    resolved_by = IntField()
    resolved_at = DateTimeField()


class BrokerAuditLog(BrokerBaseDocument):
    meta = {
        "collection": "broker_audit_logs",
        "indexes": ["organization_id", "actor_user_id", "action", "resource_type", "created_at"],
    }

    actor_user_id = IntField()
    actor_role = StringField(max_length=32)
    action = StringField(required=True, max_length=64)
    resource_type = StringField(required=True, max_length=32)
    resource_id = IntField()
    source_ip = StringField(max_length=64)
    before_state = DictField(default=dict)
    after_state = DictField(default=dict)
    metadata = DictField(default=dict)
