"""Append-only broker analytics events and replaceable daily aggregates."""

from datetime import date, datetime

from mongoengine import DateField, DateTimeField, IntField, StringField

from backend.app.broker.models.base import BrokerBaseDocument


class BrokerAnalyticsEvent(BrokerBaseDocument):
    meta = {
        "collection": "broker_analytics_events",
        "indexes": [
            "organization_id", "event_type", "occurred_at", "listing_id", "agent_user_id",
            {"fields": ("organization_id", "source_type", "source_id"), "unique": True},
        ],
    }

    source_type = StringField(required=True, max_length=24)
    source_id = IntField(required=True)
    event_type = StringField(required=True, max_length=32)
    listing_id = IntField(required=True)
    agent_user_id = IntField()
    occurred_at = DateTimeField(required=True)
    response_seconds = IntField(min_value=0)
    lead_stage = StringField(max_length=24)


class BrokerAnalyticsDailyRollup(BrokerBaseDocument):
    meta = {
        "collection": "broker_analytics_daily",
        "indexes": [
            "organization_id", "day", "listing_id", "agent_user_id",
            {"fields": ("organization_id", "day", "listing_id", "agent_user_id"), "unique": True},
        ],
    }

    day = DateField(required=True)
    listing_id = IntField(default=0)
    agent_user_id = IntField(default=0)
    leads = IntField(default=0, min_value=0)
    replies = IntField(default=0, min_value=0)
    phone_reveals = IntField(default=0, min_value=0)
    views = IntField(default=0, min_value=0)
    impressions = IntField(default=0, min_value=0)
    response_count = IntField(default=0, min_value=0)
    response_seconds_total = IntField(default=0, min_value=0)
    average_response_seconds = IntField(min_value=0)
    generated_at = DateTimeField(required=True)
