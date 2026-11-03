"""Broker organization profile document."""

from enum import Enum
from mongoengine import DictField, EnumField, ListField, StringField

from backend.app.broker.models.base import BrokerBaseDocument


class BrokerStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"
    suspended = "suspended"


class BrokerProfile(BrokerBaseDocument):
    """Extension profile for a business organization holding broker capability."""

    meta = {
        "collection": "broker_profiles",
        "indexes": [
            "organization_id",
            "status",
            "created_at",
        ],
    }

    status = EnumField(BrokerStatus, default=BrokerStatus.draft, required=True)
    company_name = StringField(max_length=200)
    legal_name = StringField(max_length=200)
    address = StringField(max_length=300)
    country = StringField(max_length=100)
    city = StringField(max_length=100)
    licences = DictField(default=dict)  # e.g. {"region": "licence_number"}
    logo_url = StringField(max_length=500)
    banner_url = StringField(max_length=500)
    about = StringField()
    website = StringField(max_length=255)
    contact_email = StringField(max_length=255)
    contact_phone = StringField(max_length=50)
    whatsapp_number = StringField(max_length=50)
    languages = ListField(StringField(max_length=20), default=lambda: ["en"])
    service_areas = ListField(StringField(max_length=100), default=list)
    decision_notes = StringField()
