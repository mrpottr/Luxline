"""Broker branch office document."""

from mongoengine import StringField

from backend.app.broker.models.base import BrokerBaseDocument


class BrokerBranch(BrokerBaseDocument):
    """Regional or local branch office of a broker organization."""

    meta = {
        "collection": "broker_branches",
        "indexes": [
            "organization_id",
            "code",
            {"fields": ("organization_id", "code"), "unique": True},
        ],
    }

    name = StringField(required=True, max_length=150)
    code = StringField(required=True, max_length=30)
    address = StringField(max_length=255)
    city = StringField(max_length=100)
    country = StringField(max_length=100)
    phone = StringField(max_length=50)
    email = StringField(max_length=255)
