"""Broker team member document."""

from mongoengine import BooleanField, EnumField, IntField, ListField, StringField

from backend.app.broker.domain.roles import BrokerRole
from backend.app.broker.models.base import BrokerBaseDocument


class BrokerMember(BrokerBaseDocument):
    """Team member mapped to a specific organization and role."""

    meta = {
        "collection": "broker_members",
        "indexes": [
            "organization_id",
            "user_id",
            {"fields": ("organization_id", "user_id"), "unique": True},
            "role",
            "is_active",
        ],
    }

    user_id = IntField(required=True)
    branch_id = IntField()
    role = EnumField(BrokerRole, default=BrokerRole.broker_agent, required=True)
    title = StringField(max_length=120)
    display_name = StringField(max_length=120)
    email = StringField(max_length=255)
    phone = StringField(max_length=50)
    whatsapp = StringField(max_length=50)
    photo_url = StringField(max_length=500)
    specialties = ListField(StringField(max_length=80), default=list)
    languages = ListField(StringField(max_length=20), default=list)
    is_active = BooleanField(default=True)

