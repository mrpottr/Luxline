"""Pydantic request/response schemas used by API endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.app.models import ListingCategory, ListingStatus, ModerationStatus, SubscriptionStatus, UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    access_token: str | None = None
    token_type: str = "bearer"
    requires_2fa: bool = False
    challenge_id: int | None = None
    otp_expires_in_seconds: int | None = None
    otp_code_dev_only: str | None = None


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str
    last_name: str
    phone: str | None = None
    role: UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TwoFactorVerifyRequest(BaseModel):
    challenge_id: int
    code: str = Field(min_length=6, max_length=6)


class SocialLoginRequest(BaseModel):
    provider: str = Field(description="google|apple")
    id_token: str = Field(min_length=10)
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None
    role: UserRole
    is_active: bool
    is_verified_business: bool
    is_2fa_enabled: bool
    preferred_currency: str
    preferred_language: str
    measurement_system: str
    created_at: datetime


class UserPreferencesUpdate(BaseModel):
    preferred_currency: str | None = None
    preferred_language: str | None = None
    measurement_system: str | None = None


class UserRoleUpdate(BaseModel):
    role: UserRole


class AgencyProfileUpsert(BaseModel):
    name: str
    logo_url: str | None = None
    bio: str | None = None
    website: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    address: str | None = None


class AgencyTeamMemberCreate(BaseModel):
    full_name: str
    title: str | None = None
    email: EmailStr | None = None
    phone: str | None = None


class AgencyTeamMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    title: str | None
    email: EmailStr | None
    phone: str | None


class AgencyProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    logo_url: str | None
    bio: str | None
    website: str | None
    contact_email: EmailStr | None
    contact_phone: str | None
    address: str | None
    team_members: list[AgencyTeamMemberOut] = Field(default_factory=list)


class ListingMediaIn(BaseModel):
    media_type: str = Field(description="image|video|virtual_tour")
    url: str
    sort_order: int = 0


class ListingMediaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    media_type: str
    url: str
    sort_order: int


class ListingCreate(BaseModel):
    title: str
    description: str | None = None
    category: ListingCategory
    status: ListingStatus = ListingStatus.draft
    location_country: str | None = None
    location_city: str | None = None
    location_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    currency: str = "USD"
    price: float = Field(gt=0)
    year: int | None = None
    make: str | None = None
    model: str | None = None
    condition: str | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    square_footage: float | None = None
    mileage: float | None = None
    draft_depth: float | None = None
    beam_width: float | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    media_items: list[ListingMediaIn] = Field(default_factory=list)


class ListingUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: ListingStatus | None = None
    moderation_status: ModerationStatus | None = None
    price: float | None = Field(default=None, gt=0)
    currency: str | None = None
    attributes: dict[str, Any] | None = None


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    seller_id: int
    agency_id: int | None
    title: str
    slug: str
    description: str | None
    category: ListingCategory
    status: ListingStatus
    moderation_status: ModerationStatus
    location_country: str | None
    location_city: str | None
    location_address: str | None
    latitude: float | None
    longitude: float | None
    currency: str
    price: float
    year: int | None
    make: str | None
    model: str | None
    condition: str | None
    bedrooms: int | None
    bathrooms: float | None
    square_footage: float | None
    mileage: float | None
    draft_depth: float | None
    beam_width: float | None
    attributes: dict[str, Any]
    is_featured: bool
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    media_items: list[ListingMediaOut] = []


class ListingImportItem(BaseModel):
    title: str
    category: ListingCategory
    price: float
    currency: str = "USD"
    location_country: str | None = None
    location_city: str | None = None
    make: str | None = None
    model: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class ListingImportRequest(BaseModel):
    source: str = Field(description="csv|xml|api")
    items: list[ListingImportItem]


class ListingFeedImportRequest(BaseModel):
    source: str = Field(description="csv|xml")
    content: str = Field(min_length=1)


class SearchResponse(BaseModel):
    total: int
    results: list[ListingOut]


class SavedSearchCreate(BaseModel):
    name: str
    filters: dict[str, Any]
    alert_enabled: bool = True


class SavedSearchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    name: str
    filters: dict[str, Any]
    alert_enabled: bool
    created_at: datetime


class AlertPreferenceUpdate(BaseModel):
    channel: str = Field(description="email|push|sms")
    enabled: bool = True


class AlertPreferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    channel: str
    enabled: bool


class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


class InquiryCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    message: str


class InquiryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    listing_id: int
    buyer_id: int | None
    seller_id: int
    name: str
    email: EmailStr
    phone: str | None
    message: str
    created_at: datetime


class SubscriptionCreate(BaseModel):
    plan_code: str


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    business_user_id: int
    plan_code: str
    status: SubscriptionStatus
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    starts_at: datetime
    ends_at: datetime | None


class BlogPostCreate(BaseModel):
    title: str
    slug: str
    excerpt: str | None = None
    content_markdown: str
    cover_image_url: str | None = None
    podcast_embed_url: str | None = None
    published: bool = False


class BlogPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    slug: str
    excerpt: str | None
    content_markdown: str
    cover_image_url: str | None
    podcast_embed_url: str | None
    published: bool
    created_at: datetime
