"""Pydantic schemas for Broker API endpoints."""

from datetime import date, datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from urllib.parse import urlsplit
from backend.app.broker.models.profile import BrokerStatus
from backend.app.broker.domain.roles import BrokerRole
from backend.app.models import ListingCategory


def _validate_media_urls(values: list[str] | None) -> list[str] | None:
    if values is None:
        return None
    for value in values:
        parsed = urlsplit(value)
        local_media_url = (
            parsed.scheme == "http"
            and parsed.hostname in {"localhost", "127.0.0.1"}
            and parsed.path.startswith("/api/broker/v1/media/")
        )
        secure_media_url = parsed.scheme == "https" and bool(parsed.hostname)
        if len(value) > 2048 or not (secure_media_url or local_media_url) or parsed.username or parsed.password:
            raise ValueError("Media references must be HTTPS URLs (or local signed mock URLs) without credentials")
    return values


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


# --- Broker Listing Schemas ---

class BrokerListingMediaInput(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    media_type: str = Field(pattern="^(image|video|floor_plan)$")
    sort_order: int = Field(ge=0, le=100)
    alt_text: str = Field(default="", max_length=300)

    @field_validator("url")
    @classmethod
    def media_url_must_use_https(cls, value: str) -> str:
        _validate_media_urls([value])
        return value

    @model_validator(mode="after")
    def images_need_alt_text(self):
        if self.media_type in {"image", "floor_plan"} and not self.alt_text.strip():
            raise ValueError("Image and floor plan media require descriptive alt text")
        return self


class BrokerListingMediaOut(BaseModel):
    url: str
    media_type: str
    sort_order: int
    alt_text: str = ""
    moderation_state: str = "pending"


class BrokerMediaUploadRequest(BaseModel):
    content_base64: str = Field(min_length=1, max_length=11_200_000)
    content_type: str = Field(pattern="^(image/jpeg|image/png|image/webp|application/pdf)$")
    media_type: str = Field(pattern="^(image|floor_plan)$")
    alt_text: str = Field(min_length=1, max_length=300)


class BrokerMediaUploadOut(BaseModel):
    asset_id: int
    organization_id: int
    url: str
    content_type: str
    media_type: str
    alt_text: str
    moderation_state: str
    expires_at: int


class BrokerLeadOut(BaseModel):
    id: int
    organization_id: int
    inquiry_id: int
    listing_id: int
    buyer_id: int | None = None
    buyer_name: str
    buyer_email: str
    buyer_phone: str | None = None
    initial_message: str
    source: str
    stage: str
    score: int
    assigned_member_id: int | None = None
    first_response_at: datetime | None = None
    first_response_seconds: int | None = None
    spam_flag: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BrokerLeadStageUpdate(BaseModel):
    stage: str = Field(pattern="^(new|contacted|qualified|lost|closed)$")


class BrokerLeadSpamUpdate(BaseModel):
    spam_flag: bool


class BrokerLeadAssign(BaseModel):
    member_user_id: int = Field(ge=1)


class BrokerLeadActivityCreate(BaseModel):
    activity_type: str = Field(pattern="^(note|task|reminder)$")
    body: str = Field(min_length=1, max_length=5000)
    due_at: datetime | None = None


class BrokerLeadActivityOut(BaseModel):
    id: int
    organization_id: int
    lead_id: int
    actor_user_id: int
    activity_type: str
    body: str
    due_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BrokerLeadBuyerOut(BaseModel):
    id: int
    organization_id: int
    listing_id: int
    stage: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BrokerMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class BrokerMessageOut(BaseModel):
    id: int
    organization_id: int
    lead_id: int
    sender_type: str
    sender_user_id: int | None = None
    body: str
    delivery_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BrokerReplyTemplateCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=2000)


class BrokerReplyTemplateOut(BaseModel):
    id: int
    organization_id: int
    title: str
    body: str
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BrokerAnalyticsOut(BaseModel):
    date_from: date
    date_to: date
    totals: dict[str, Any]
    daily: list[dict[str, Any]]
    by_listing: list[dict[str, Any]]
    by_agent: list[dict[str, Any]]


class BrokerPromotionCreate(BaseModel):
    listing_id: int = Field(ge=1)
    scope: str = Field(pattern="^(city|locality|province|country)$")
    location_code: str = Field(min_length=1, max_length=120)
    placement_type: str = Field(pattern="^(featured|premium|urgent)$")
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def promotion_dates_must_have_timezone(self):
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("Promotion timestamps must include a timezone")
        if self.ends_at <= self.starts_at:
            raise ValueError("Promotion end must be after its start")
        return self


class BrokerPlanUpsert(BaseModel):
    code: str = Field(min_length=1, max_length=50, pattern="^[a-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    price_amount: str = Field(min_length=1, max_length=32)
    currency: str = Field(pattern="^[A-Z]{3}$")
    billing_period_days: int = Field(ge=1)
    listing_limit: int | None = Field(default=None, ge=1)
    entitlements: dict[str, Any] = Field(default_factory=dict)
    credit_packs: list[dict[str, Any]] = Field(default_factory=list)
    promotion_prices: dict[str, dict[str, int]] = Field(default_factory=dict)
    is_active: bool = True


class BrokerPlanOut(BaseModel):
    id: int
    code: str
    name: str
    description: str
    price_amount: str
    currency: str
    billing_period_days: int
    listing_limit: int | None = None
    entitlements: dict[str, Any]
    credit_packs: list[dict[str, Any]]
    promotion_prices: dict[str, Any]
    is_active: bool
    version: int

    model_config = ConfigDict(from_attributes=True)


class BrokerPromotionOut(BaseModel):
    id: int
    organization_id: int
    listing_id: int
    scope: str
    location_code: str
    placement_type: str
    starts_at: datetime
    ends_at: datetime
    credits_spent: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BrokerCreditLedgerOut(BaseModel):
    id: int
    organization_id: int
    entry_type: str
    amount: int
    balance_after: int
    actor_user_id: int | None = None
    promotion_id: int | None = None
    reference: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BrokerCreditWalletOut(BaseModel):
    balance: int
    ledger: list[BrokerCreditLedgerOut]


class BrokerSubscriptionOut(BaseModel):
    id: int
    organization_id: int
    plan_code: str
    status: str
    starts_at: datetime
    ends_at: datetime
    plan_version: int
    listing_limit_snapshot: int | None = None
    entitlements_snapshot: dict[str, Any]
    payment_reference: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BrokerReviewCreate(BaseModel):
    lead_id: int = Field(ge=1)
    rating: int = Field(ge=1, le=5)
    body: str = Field(min_length=10, max_length=3000)
    public_consent: bool


class BrokerReviewReply(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class BrokerReviewAppeal(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class BrokerReviewOut(BaseModel):
    id: int
    organization_id: int
    lead_id: int
    listing_id: int
    rating: int
    body: str
    public_consent: bool
    status: str
    broker_reply: str | None = None
    replied_at: datetime | None = None
    appeal_state: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BrokerBadgeOut(BaseModel):
    id: int
    organization_id: int
    subject_type: str
    subject_id: int
    badge_code: str
    rule_version: int
    awarded: bool
    explanation: str
    criteria_snapshot: dict[str, Any]
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BrokerAuditLogOut(BaseModel):
    id: int
    organization_id: int
    actor_user_id: int | None = None
    actor_role: str | None = None
    action: str
    resource_type: str
    resource_id: int | None = None
    source_ip: str | None = None
    before_state: dict[str, Any]
    after_state: dict[str, Any]
    metadata: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BrokerModerationCaseOut(BaseModel):
    id: int
    organization_id: int
    case_type: str
    resource_type: str
    resource_id: int
    actor_user_id: int | None = None
    reason: str
    severity: str
    status: str
    resolution: str | None = None
    resolved_by: int | None = None
    resolved_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BrokerModerationResolve(BaseModel):
    resolution: str = Field(min_length=1, max_length=1000)


class BrokerReviewDecision(BaseModel):
    decision: str = Field(pattern="^(publish|reject)$")
    notes: str | None = Field(default=None, max_length=1000)


class BrokerListingCreate(BaseModel):
    title: str = Field(min_length=5, max_length=255)
    description: str | None = Field(default=None, max_length=20000)
    category: ListingCategory
    price: float = Field(gt=0, allow_inf_nan=False)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    location_country: str = Field(min_length=2, max_length=100)
    location_city: str = Field(min_length=1, max_length=100)
    location_address: str | None = Field(default=None, max_length=255)
    assigned_agent_id: int | None = None
    branch_id: int | None = None
    owner_name: str | None = Field(default=None, max_length=200)
    owner_mandate_reference: str | None = Field(default=None, max_length=200)
    owner_consent: bool = Field(default=False)
    commission_terms: str | None = Field(default=None, max_length=2000)
    urgent_flag: bool = Field(default=False)
    photos: list[str] = Field(default_factory=list, max_length=50)
    media: list[BrokerListingMediaInput] = Field(default_factory=list, max_length=50)
    attributes: dict[str, Any] = Field(default_factory=dict, max_length=100)

    @field_validator("photos")
    @classmethod
    def photos_must_use_https(cls, values: list[str]) -> list[str]:
        return _validate_media_urls(values) or []

    @model_validator(mode="after")
    def media_inputs_are_unambiguous(self):
        if self.media and self.photos:
            raise ValueError("Use either media or legacy photos, not both")
        if len(self.media) + len(self.photos) > 50:
            raise ValueError("At most 50 media items may be attached to a listing")
        return self


class BrokerListingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=255)
    description: str | None = Field(default=None, max_length=20000)
    price: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    location_country: str | None = Field(default=None, min_length=2, max_length=100)
    location_city: str | None = Field(default=None, min_length=1, max_length=100)
    location_address: str | None = None
    assigned_agent_id: int | None = None
    branch_id: int | None = None
    owner_name: str | None = Field(default=None, max_length=200)
    owner_mandate_reference: str | None = Field(default=None, max_length=200)
    owner_consent: bool | None = None
    commission_terms: str | None = Field(default=None, max_length=2000)
    urgent_flag: bool | None = None
    photos: list[str] | None = Field(default=None, max_length=50)
    media: list[BrokerListingMediaInput] | None = Field(default=None, max_length=50)
    attributes: dict[str, Any] | None = Field(default=None, max_length=100)

    @field_validator("photos")
    @classmethod
    def photos_must_use_https(cls, values: list[str] | None) -> list[str] | None:
        return _validate_media_urls(values)

    @model_validator(mode="after")
    def media_inputs_are_unambiguous(self):
        if self.media is not None and self.photos is not None:
            raise ValueError("Use either media or legacy photos, not both")
        if len(self.media or []) + len(self.photos or []) > 50:
            raise ValueError("At most 50 media items may be attached to a listing")
        return self


class BrokerListingOut(BaseModel):
    id: int
    organization_id: int
    listing_id: int
    title: str
    description: str = ""
    category: str
    price: float
    currency: str
    location_country: str
    location_city: str
    location_address: str | None = None
    status: str
    moderation_status: str
    assigned_agent_id: int | None = None
    branch_id: int | None = None
    owner_name: str | None = None
    owner_mandate_reference: str | None = None
    owner_consent: bool
    commission_terms: str | None = None
    quality_score: int
    quality_rating: str
    quality_suggestions: list[str] = Field(default_factory=list)
    urgent_flag: bool
    photos: list[str] = Field(default_factory=list)
    media: list[BrokerListingMediaOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BulkImportRequest(BaseModel):
    csv_content: str = Field(min_length=1, max_length=1_000_000)


class BrokerListingRevisionOut(BaseModel):
    id: int
    organization_id: int
    listing_id: int
    version: int
    actor_user_id: int
    snapshot: dict[str, Any]
    created_at: datetime
