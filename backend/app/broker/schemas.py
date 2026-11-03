"""Pydantic schemas for Broker API endpoints."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from backend.app.broker.models.profile import BrokerStatus
from backend.app.broker.domain.roles import BrokerRole


class BrokerProfileUpdate(BaseModel):
    company_name: str | None = Field(default=None, max_length=200)
    legal_name: str | None = Field(default=None, max_length=200)
    address: str | None = Field(default=None, max_length=300)
    country: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    licences: dict[str, str] = Field(default_factory=dict)
    logo_url: str | None = Field(default=None, max_length=500)
    banner_url: str | None = Field(default=None, max_length=500)
    about: str | None = None
    website: str | None = Field(default=None, max_length=255)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=50)
    whatsapp_number: str | None = Field(default=None, max_length=50)
    languages: list[str] = Field(default_factory=list)
    service_areas: list[str] = Field(default_factory=list)


class BrokerProfileOut(BrokerProfileUpdate):
    id: int
    organization_id: int
    status: BrokerStatus
    decision_notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BrokerPublicProfileOut(BaseModel):
    organization_id: int
    company_name: str | None = None
    logo_url: str | None = None
    banner_url: str | None = None
    about: str | None = None
    website: str | None = None
    city: str | None = None
    country: str | None = None
    languages: list[str] = Field(default_factory=list)
    service_areas: list[str] = Field(default_factory=list)
    whatsapp_number: str | None = None
    is_verified: bool = False

    model_config = ConfigDict(from_attributes=True)


class BrokerVerificationDecision(BaseModel):
    decision: str = Field(description="approve|reject|suspend")
    notes: str | None = None
