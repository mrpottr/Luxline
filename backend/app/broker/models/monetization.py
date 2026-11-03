"""Broker plans, tenant credit balances, append-only ledger, and promotions."""

from mongoengine import (
    BooleanField,
    DateTimeField,
    DictField,
    IntField,
    ListField,
    StringField,
)

from backend.app.broker.models.base import BrokerBaseDocument


class BrokerPlan(BrokerBaseDocument):
    meta = {
        "collection": "broker_plans",
        "indexes": [
            "organization_id", "code", "is_active", {"fields": ("code",), "unique": True},
            {"fields": ("create_idempotency_key",), "unique": True, "sparse": True},
        ],
    }

    code = StringField(required=True, max_length=50)
    name = StringField(required=True, max_length=120)
    description = StringField(default="", max_length=2000)
    price_amount = StringField(required=True, max_length=32)
    currency = StringField(required=True, max_length=3)
    billing_period_days = IntField(required=True, min_value=1)
    listing_limit = IntField(min_value=1)
    entitlements = DictField(default=dict)
    credit_packs = ListField(DictField(), default=list)
    promotion_prices = DictField(default=dict)
    is_active = BooleanField(default=True)
    version = IntField(default=1, min_value=1)
    create_idempotency_key = StringField(max_length=128)
    create_payload_hash = StringField(max_length=64)


class BrokerSubscription(BrokerBaseDocument):
    meta = {
        "collection": "broker_subscriptions",
        "indexes": ["organization_id", "status", "starts_at", "ends_at", {"fields": ("organization_id", "idempotency_key"), "unique": True}],
    }

    plan_code = StringField(required=True, max_length=50)
    status = StringField(required=True, default="active", max_length=20)
    starts_at = DateTimeField(required=True)
    ends_at = DateTimeField(required=True)
    plan_version = IntField(required=True, min_value=1)
    listing_limit_snapshot = IntField(min_value=1)
    entitlements_snapshot = DictField(default=dict)
    payment_reference = StringField(required=True, max_length=128)
    idempotency_key = StringField(required=True, max_length=128)
    idempotency_payload_hash = StringField(required=True, max_length=64)


class BrokerCreditAccount(BrokerBaseDocument):
    meta = {
        "collection": "broker_credit_accounts",
        "indexes": ["organization_id", {"fields": ("organization_id",), "unique": True}],
    }

    balance = IntField(default=0, min_value=0)


class BrokerCreditLedger(BrokerBaseDocument):
    meta = {
        "collection": "broker_credit_ledger",
        "indexes": [
            "organization_id", "created_at", "entry_type",
            {"fields": ("organization_id", "idempotency_key"), "unique": True, "sparse": True},
        ],
    }

    entry_type = StringField(required=True, max_length=24)
    amount = IntField(required=True)
    balance_after = IntField(required=True, min_value=0)
    actor_user_id = IntField()
    promotion_id = IntField()
    reference = StringField(max_length=128)
    idempotency_key = StringField(max_length=128)
    payload_hash = StringField(max_length=64)


class BrokerPromotion(BrokerBaseDocument):
    meta = {
        "collection": "broker_promotions",
        "indexes": [
            "organization_id", "listing_id", "status", "starts_at", "ends_at",
            {"fields": ("organization_id", "idempotency_key"), "unique": True},
        ],
    }

    listing_id = IntField(required=True)
    scope = StringField(required=True, max_length=20)
    location_code = StringField(required=True, max_length=120)
    placement_type = StringField(required=True, max_length=20)
    starts_at = DateTimeField(required=True)
    ends_at = DateTimeField(required=True)
    credits_spent = IntField(required=True, min_value=1)
    status = StringField(required=True, default="active", max_length=20)
    idempotency_key = StringField(required=True, max_length=128)
    payload_hash = StringField(required=True, max_length=64)
