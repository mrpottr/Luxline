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
    hypercar = "hypercar"
    yacht = "yacht"
    jet = "jet"
    watch = "watch"


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
