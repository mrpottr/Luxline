"""SQLAlchemy ORM models and enums for the Luxline domain."""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class UserRole(str, Enum):
    standard_user = "standard_user"
    private_seller = "private_seller"
    business_account = "business_account"
    super_admin = "super_admin"


class ListingCategory(str, Enum):
    real_estate = "real_estate"
    car = "car"
    hypercar = "hypercar"
    yacht = "yacht"
    jet = "jet"
    watch = "watch"
    jewelry = "jewelry"
    rental = "rental"


class ListingStatus(str, Enum):
    draft = "draft"
    active = "active"
    pending = "pending"
    sold = "sold"


class ModerationStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class SubscriptionStatus(str, Enum):
    trial = "trial"
    active = "active"
    past_due = "past_due"
    canceled = "canceled"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified_business: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_2fa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    preferred_currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    measurement_system: Mapped[str] = mapped_column(String(16), default="imperial", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    agency_profile: Mapped["AgencyProfile | None"] = relationship(back_populates="owner", uselist=False)
    team_members: Mapped[list["AgencyTeamMember"]] = relationship(back_populates="agency_owner")
    listings: Mapped[list["Listing"]] = relationship(back_populates="seller")
    saved_listings: Mapped[list["SavedListing"]] = relationship(back_populates="user")
    saved_searches: Mapped[list["SavedSearch"]] = relationship(back_populates="user")
    inquiries_sent: Mapped[list["Inquiry"]] = relationship(
        back_populates="buyer", foreign_keys="Inquiry.buyer_id"
    )
    inquiries_received: Mapped[list["Inquiry"]] = relationship(
        back_populates="seller", foreign_keys="Inquiry.seller_id"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="business_user")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="actor")
    social_accounts: Mapped[list["SocialAccount"]] = relationship(back_populates="user")
    two_factor_challenges: Mapped[list["TwoFactorChallenge"]] = relationship(back_populates="user")
    email_verification_challenges: Mapped[list["EmailVerificationChallenge"]] = relationship(back_populates="user")


class AgencyProfile(Base):
    __tablename__ = "agency_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    bio: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(String(255))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    address: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    owner: Mapped["User"] = relationship(back_populates="agency_profile")
    team_members: Mapped[list["AgencyTeamMember"]] = relationship(back_populates="agency")


class AgencyTeamMember(Base):
    __tablename__ = "agency_team_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agency_profiles.id"), nullable=False, index=True)
    agency_owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))

    agency: Mapped["AgencyProfile"] = relationship(back_populates="team_members")
    agency_owner: Mapped["User"] = relationship(back_populates="team_members")


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    agency_id: Mapped[int | None] = mapped_column(ForeignKey("agency_profiles.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(300), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[ListingCategory] = mapped_column(SQLEnum(ListingCategory), nullable=False, index=True)
    status: Mapped[ListingStatus] = mapped_column(SQLEnum(ListingStatus), default=ListingStatus.draft, nullable=False)
    moderation_status: Mapped[ModerationStatus] = mapped_column(
        SQLEnum(ModerationStatus), default=ModerationStatus.pending, nullable=False, index=True
    )
    location_country: Mapped[str | None] = mapped_column(String(100), index=True)
    location_city: Mapped[str | None] = mapped_column(String(100), index=True)
    location_address: Mapped[str | None] = mapped_column(String(255))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    price: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, index=True)
    year: Mapped[int | None] = mapped_column(Integer, index=True)
    make: Mapped[str | None] = mapped_column(String(120), index=True)
    model: Mapped[str | None] = mapped_column(String(120), index=True)
    condition: Mapped[str | None] = mapped_column(String(50), index=True)
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    bathrooms: Mapped[float | None] = mapped_column(Float)
    square_footage: Mapped[float | None] = mapped_column(Float)
    mileage: Mapped[float | None] = mapped_column(Float)
    draft_depth: Mapped[float | None] = mapped_column(Float)
    beam_width: Mapped[float | None] = mapped_column(Float)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    seller: Mapped["User"] = relationship(back_populates="listings")
    media_items: Mapped[list["ListingMedia"]] = relationship(back_populates="listing")
    inquiries: Mapped[list["Inquiry"]] = relationship(back_populates="listing")
    real_estate_details: Mapped["RealEstateListing | None"] = relationship(
        back_populates="listing", uselist=False, cascade="all, delete-orphan"
    )
    vehicle_details: Mapped["VehicleListing | None"] = relationship(
        back_populates="listing", uselist=False, cascade="all, delete-orphan"
    )
    vessel_aircraft_details: Mapped["VesselAircraftListing | None"] = relationship(
        back_populates="listing", uselist=False, cascade="all, delete-orphan"
    )
    watch_jewelry_details: Mapped["WatchJewelryListing | None"] = relationship(
        back_populates="listing", uselist=False, cascade="all, delete-orphan"
    )
    rental_terms: Mapped["RentalTerms | None"] = relationship(
        back_populates="listing", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def details(self) -> dict:
        """Return category-specific fields from additive subtype tables."""
        if self.real_estate_details:
            return self.real_estate_details.as_dict()
        if self.vehicle_details:
            return self.vehicle_details.as_dict()
        if self.vessel_aircraft_details:
            return self.vessel_aircraft_details.as_dict()
        if self.watch_jewelry_details:
            return self.watch_jewelry_details.as_dict()
        if self.rental_terms:
            return self.rental_terms.as_dict()
        return self.attributes or {}


class TaxonomyTerm(Base):
    __tablename__ = "taxonomy_terms"
    __table_args__ = (UniqueConstraint("taxonomy", "parent_id", "slug", name="uq_taxonomy_parent_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    taxonomy: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("taxonomy_terms.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class RealEstateListing(Base):
    __tablename__ = "listing_real_estate"

    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True)
    area_value: Mapped[float | None] = mapped_column(Float)
    area_unit: Mapped[str | None] = mapped_column(String(8))
    acreage: Mapped[float | None] = mapped_column(Float)
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    bathrooms: Mapped[float | None] = mapped_column(Float)
    property_type_id: Mapped[int | None] = mapped_column(ForeignKey("taxonomy_terms.id"), nullable=True)

    listing: Mapped["Listing"] = relationship(back_populates="real_estate_details")

    def as_dict(self) -> dict:
        return {
            "area_value": self.area_value,
            "area_unit": self.area_unit,
            "acreage": self.acreage,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "property_type_id": self.property_type_id,
        }


class VehicleListing(Base):
    __tablename__ = "listing_vehicle"

    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True)
    make_id: Mapped[int | None] = mapped_column(ForeignKey("taxonomy_terms.id"), nullable=True, index=True)
    model_id: Mapped[int | None] = mapped_column(ForeignKey("taxonomy_terms.id"), nullable=True, index=True)
    make: Mapped[str | None] = mapped_column(String(120), index=True)
    model: Mapped[str | None] = mapped_column(String(120), index=True)
    year: Mapped[int | None] = mapped_column(Integer, index=True)
    mileage_value: Mapped[float | None] = mapped_column(Float)
    mileage_unit: Mapped[str | None] = mapped_column(String(8))
    vin_ciphertext: Mapped[str | None] = mapped_column(Text)
    steering_side: Mapped[str | None] = mapped_column(String(8))

    listing: Mapped["Listing"] = relationship(back_populates="vehicle_details")

    def as_dict(self) -> dict:
        return {
            "make_id": self.make_id,
            "model_id": self.model_id,
            "make": self.make,
            "model": self.model,
            "year": self.year,
            "mileage_value": self.mileage_value,
            "mileage_unit": self.mileage_unit,
            "steering_side": self.steering_side,
        }


class VesselAircraftListing(Base):
    __tablename__ = "listing_vessel_aircraft"

    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True)
    asset_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    builder_id: Mapped[int | None] = mapped_column(ForeignKey("taxonomy_terms.id"), nullable=True, index=True)
    builder: Mapped[str | None] = mapped_column(String(120), index=True)
    year: Mapped[int | None] = mapped_column(Integer, index=True)
    length_value: Mapped[float | None] = mapped_column(Float)
    length_unit: Mapped[str | None] = mapped_column(String(8))
    cabins: Mapped[int | None] = mapped_column(Integer)
    engine_hours: Mapped[int | None] = mapped_column(Integer)

    listing: Mapped["Listing"] = relationship(back_populates="vessel_aircraft_details")

    def as_dict(self) -> dict:
        return {
            "asset_type": self.asset_type,
            "builder_id": self.builder_id,
            "builder": self.builder,
            "year": self.year,
            "length_value": self.length_value,
            "length_unit": self.length_unit,
            "cabins": self.cabins,
            "engine_hours": self.engine_hours,
        }


class WatchJewelryListing(Base):
    __tablename__ = "listing_watch_jewelry"

    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True)
    asset_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("taxonomy_terms.id"), nullable=True, index=True)
    brand: Mapped[str | None] = mapped_column(String(120), index=True)
    reference_number: Mapped[str | None] = mapped_column(String(120), index=True)
    case_material_id: Mapped[int | None] = mapped_column(ForeignKey("taxonomy_terms.id"), nullable=True)
    movement_id: Mapped[int | None] = mapped_column(ForeignKey("taxonomy_terms.id"), nullable=True)
    case_material: Mapped[str | None] = mapped_column(String(120))
    movement: Mapped[str | None] = mapped_column(String(120))

    listing: Mapped["Listing"] = relationship(back_populates="watch_jewelry_details")

    def as_dict(self) -> dict:
        return {
            "asset_type": self.asset_type,
            "brand_id": self.brand_id,
            "brand": self.brand,
            "reference_number": self.reference_number,
            "case_material_id": self.case_material_id,
            "movement_id": self.movement_id,
            "case_material": self.case_material,
            "movement": self.movement,
        }


class RentalTerms(Base):
    __tablename__ = "listing_rental_terms"

    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True)
    available_from: Mapped[datetime | None] = mapped_column(DateTime)
    available_until: Mapped[datetime | None] = mapped_column(DateTime)
    min_nights: Mapped[int | None] = mapped_column(Integer)
    pricing_tiers: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    listing: Mapped["Listing"] = relationship(back_populates="rental_terms")

    def as_dict(self) -> dict:
        return {
            "available_from": self.available_from,
            "available_until": self.available_until,
            "min_nights": self.min_nights,
            "pricing_tiers": self.pricing_tiers,
        }


class ListingMedia(Base):
    __tablename__ = "listing_media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), nullable=False, index=True)
    media_type: Mapped[str] = mapped_column(String(32), nullable=False)
    url: Mapped[str] = mapped_column(String(600), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    listing: Mapped["Listing"] = relationship(back_populates="media_items")


class SavedListing(Base):
    __tablename__ = "saved_listings"
    __table_args__ = (UniqueConstraint("user_id", "listing_id", name="uq_saved_listing_user_listing"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="saved_listings")


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    filters: Mapped[dict] = mapped_column(JSON, nullable=False)
    alert_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="saved_searches")


class AlertPreference(Base):
    __tablename__ = "alert_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Inquiry(Base):
    __tablename__ = "inquiries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), nullable=False, index=True)
    buyer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="sent", nullable=False, index=True)
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    listing: Mapped["Listing"] = relationship(back_populates="inquiries")
    buyer: Mapped["User"] = relationship(back_populates="inquiries_sent", foreign_keys=[buyer_id])
    seller: Mapped["User"] = relationship(back_populates="inquiries_received", foreign_keys=[seller_id])


class PhoneRevealEvent(Base):
    __tablename__ = "phone_reveal_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    plan_code: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        SQLEnum(SubscriptionStatus), default=SubscriptionStatus.trial, nullable=False
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(100))
    starts_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime)

    business_user: Mapped["User"] = relationship(back_populates="subscriptions")


class FeaturedPlacement(Base):
    __tablename__ = "featured_placements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), nullable=False, index=True, unique=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), unique=True, nullable=False, index=True)
    excerpt: Mapped[str | None] = mapped_column(String(500))
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    cover_image_url: Mapped[str | None] = mapped_column(String(600))
    podcast_embed_url: Mapped[str | None] = mapped_column(String(600))
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    actor: Mapped["User | None"] = relationship(back_populates="audit_logs")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class BrokerFeed(Base):
    __tablename__ = "broker_feeds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    pull_url: Mapped[str | None] = mapped_column(String(600))
    mapping_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    schedule_cron: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(24), default="active", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    feed_id: Mapped[int | None] = mapped_column(ForeignKey("broker_feeds.id"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="queued", nullable=False, index=True)
    total_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class IngestionRow(Base):
    __tablename__ = "ingestion_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("ingestion_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(160), index=True)
    row_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="staged", nullable=False, index=True)
    error_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ListingExternalId(Base):
    __tablename__ = "listing_external_ids"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "source", "external_id", name="uq_listing_external_owner_source_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    external_id: Mapped[str] = mapped_column(String(160), nullable=False)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    aggregate_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    aggregate_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)


class FraudSignal(Base):
    __tablename__ = "fraud_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int | None] = mapped_column(ForeignKey("listings.id"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    signal_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), default="open", nullable=False, index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)


class SocialAccount(Base):
    __tablename__ = "social_accounts"
    __table_args__ = (UniqueConstraint("provider", "provider_user_id", name="uq_social_provider_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="social_accounts")


class TwoFactorChallenge(Base):
    __tablename__ = "two_factor_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="two_factor_challenges")


class EmailVerificationChallenge(Base):
    __tablename__ = "email_verification_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="email_verification_challenges")
