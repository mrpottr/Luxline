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


# --- Team & Branch Schemas ---

class BrokerMemberCreate(BaseModel):
    user_id: int
    role: BrokerRole = BrokerRole.broker_agent
    branch_id: int | None = None
    title: str | None = Field(default=None, max_length=120)
    display_name: str = Field(max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    whatsapp: str | None = Field(default=None, max_length=50)
    photo_url: str | None = Field(default=None, max_length=500)
    specialties: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)


class BrokerMemberUpdate(BaseModel):
    role: BrokerRole | None = None
    branch_id: int | None = None
    title: str | None = None
    display_name: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    photo_url: str | None = None
    specialties: list[str] | None = None
    languages: list[str] | None = None
    is_active: bool | None = None


class BrokerMemberOut(BaseModel):
    id: int
    organization_id: int
    user_id: int
    branch_id: int | None = None
    role: BrokerRole
    title: str | None = None
    display_name: str | None = None
    email: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    photo_url: str | None = None
    specialties: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BrokerBranchCreate(BaseModel):
    name: str = Field(max_length=150)
    code: str = Field(max_length=30)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None


class BrokerBranchUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    phone: str | None = None
    email: EmailStr | None = None


class BrokerBranchOut(BaseModel):
    id: int
    organization_id: int
    name: str
    code: str
    address: str | None = None
    city: str | None = None
    country: str | None = None
    phone: str | None = None
    email: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
