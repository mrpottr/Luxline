"""Tenant-owned broker lead, activity, conversation message, and reply template records."""

from mongoengine import BooleanField, DateTimeField, IntField, StringField

from backend.app.broker.models.base import BrokerBaseDocument


class BrokerLead(BrokerBaseDocument):
    meta = {
        "collection": "broker_leads",
        "indexes": [
            "organization_id", "listing_id", "assigned_member_id", "stage", "created_at",
            {"fields": ("organization_id", "inquiry_id"), "unique": True},
        ],
    }

    inquiry_id = IntField(required=True)
    listing_id = IntField(required=True)
    buyer_id = IntField()
    buyer_name = StringField(required=True, max_length=120)
    buyer_email = StringField(required=True, max_length=255)
    buyer_phone = StringField(max_length=50)
    initial_message = StringField(required=True)
    source = StringField(default="listing_inquiry", max_length=40)
    stage = StringField(default="new", max_length=24)
    score = IntField(default=0, min_value=0, max_value=100)
    assigned_member_id = IntField()
    first_response_at = DateTimeField()
    first_response_seconds = IntField(min_value=0)
    spam_flag = BooleanField(default=False)
    buyer_contact_consent = BooleanField(default=True)


class BrokerLeadActivity(BrokerBaseDocument):
    meta = {
        "collection": "broker_activities",
        "indexes": [
            "organization_id", "lead_id", "created_at",
            {"fields": ("organization_id", "idempotency_actor_id", "idempotency_key"), "unique": True},
        ],
    }

    lead_id = IntField(required=True)
    actor_user_id = IntField(required=True)
    activity_type = StringField(required=True, max_length=24)
    body = StringField(required=True)
    due_at = DateTimeField()
    completed_at = DateTimeField()
    idempotency_actor_id = IntField(required=True)
    idempotency_key = StringField(required=True, max_length=128)
    payload_hash = StringField(required=True, max_length=64)


class BrokerMessage(BrokerBaseDocument):
    meta = {
        "collection": "broker_messages",
        "indexes": [
            "organization_id", "lead_id", "created_at",
            {"fields": ("organization_id", "idempotency_actor_id", "idempotency_key"), "unique": True},
        ],
    }

    lead_id = IntField(required=True)
    sender_type = StringField(required=True, max_length=16)
    sender_user_id = IntField()
    body = StringField(required=True, max_length=5000)
    delivery_status = StringField(default="stored", max_length=24)
    source_inquiry_id = IntField()
    idempotency_actor_id = IntField(required=True)
    idempotency_key = StringField(required=True, max_length=128)
    payload_hash = StringField(required=True, max_length=64)


class BrokerReplyTemplate(BrokerBaseDocument):
    meta = {
        "collection": "broker_templates",
        "indexes": [
            "organization_id", "created_at", "is_deleted",
            {"fields": ("organization_id", "idempotency_actor_id", "idempotency_key"), "unique": True},
        ],
    }

    title = StringField(required=True, max_length=120)
    body = StringField(required=True, max_length=2000)
    created_by = IntField(required=True)
    idempotency_actor_id = IntField(required=True)
    idempotency_key = StringField(required=True, max_length=128)
    payload_hash = StringField(required=True, max_length=64)
