"""MongoEngine documents and enums for the Luxline domain."""

from datetime import datetime
from enum import Enum

from mongoengine import (
    BooleanField,
    DateTimeField,
    DictField,
    Document,
    EnumField,
    FloatField,
    IntField,
    ListField,
    StringField,
)

from backend.app.db.base import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


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
    meta = {
        "collection": "users",
        "indexes": ["email", "role", "created_at"],
    }

    email = StringField(required=True, unique=True)
    password_hash = StringField(required=True)
    first_name = StringField(required=True, max_length=80)
    last_name = StringField(required=True, max_length=80)
    phone = StringField(max_length=32)
    role = EnumField(UserRole, required=True, default=UserRole.standard_user)
    is_active = BooleanField(default=True)
    is_email_verified = BooleanField(default=False)
    is_verified_business = BooleanField(default=False)
    is_2fa_enabled = BooleanField(default=False)
    preferred_currency = StringField(default="USD", max_length=8)
    preferred_language = StringField(default="en", max_length=8)
    measurement_system = StringField(default="imperial", max_length=16)
    created_at = DateTimeField(default=_utcnow)
    updated_at = DateTimeField(default=_utcnow)

    @property
    def agency_profile(self):
        return AgencyProfile.objects(owner_id=self.id).first()

    @property
    def team_members(self):
        return list(AgencyTeamMember.objects(agency_owner_id=self.id))

    @property
    def listings(self):
        return list(Listing.objects(seller_id=self.id))

    @property
    def saved_listings(self):
        return list(SavedListing.objects(user_id=self.id))

    @property
    def saved_searches(self):
        return list(SavedSearch.objects(user_id=self.id))

    @property
    def inquiries_sent(self):
        return list(Inquiry.objects(buyer_id=self.id))

    @property
    def inquiries_received(self):
        return list(Inquiry.objects(seller_id=self.id))

    @property
    def subscriptions(self):
        return list(Subscription.objects(business_user_id=self.id))

    @property
    def audit_logs(self):
        return list(AuditLog.objects(actor_user_id=self.id))

    @property
    def social_accounts(self):
        return list(SocialAccount.objects(user_id=self.id))

    @property
    def two_factor_challenges(self):
        return list(TwoFactorChallenge.objects(user_id=self.id))

    @property
    def email_verification_challenges(self):
        return list(EmailVerificationChallenge.objects(user_id=self.id))


class AgencyProfile(Base):
    meta = {"collection": "agency_profiles", "indexes": ["owner_id"]}

    owner_id = IntField(required=True, unique=True)
    name = StringField(required=True, max_length=200)
    logo_url = StringField(max_length=500)
    bio = StringField()
    website = StringField(max_length=255)
    contact_email = StringField(max_length=255)
    contact_phone = StringField(max_length=32)
    address = StringField(max_length=255)
    created_at = DateTimeField(default=_utcnow)
    updated_at = DateTimeField(default=_utcnow)

    @property
    def owner(self):
        return User.objects(id=self.owner_id).first()

    @property
    def team_members(self):
        return list(AgencyTeamMember.objects(agency_id=self.id))


class AgencyTeamMember(Base):
    meta = {"collection": "agency_team_members", "indexes": ["agency_id", "agency_owner_id"]}

    agency_id = IntField(required=True)
    agency_owner_id = IntField(required=True)
    full_name = StringField(required=True, max_length=120)
    title = StringField(max_length=120)
    email = StringField(max_length=255)
    phone = StringField(max_length=32)

    @property
    def agency(self):
        return AgencyProfile.objects(id=self.agency_id).first()

    @property
    def agency_owner(self):
        return User.objects(id=self.agency_owner_id).first()


class Listing(Base):
    meta = {
        "collection": "listings",
        "indexes": [
            "seller_id",
            "agency_id",
            "slug",
            "category",
            "status",
            "moderation_status",
            "location_country",
            "location_city",
            "price",
            "year",
            "make",
            "model",
            "condition",
            "is_featured",
            "created_at",
        ],
    }

    seller_id = IntField(required=True)
    agency_id = IntField()
    title = StringField(required=True, max_length=255)
    slug = StringField(required=True, unique=True, max_length=300)
    description = StringField()
    category = EnumField(ListingCategory, required=True)
    status = EnumField(ListingStatus, required=True, default=ListingStatus.draft)
    moderation_status = EnumField(ModerationStatus, required=True, default=ModerationStatus.pending)
    location_country = StringField(max_length=100)
    location_city = StringField(max_length=100)
    location_address = StringField(max_length=255)
    latitude = FloatField()
    longitude = FloatField()
    currency = StringField(default="USD", max_length=8)
    price = FloatField(required=True)
    year = IntField()
    make = StringField(max_length=120)
    model = StringField(max_length=120)
    condition = StringField(max_length=50)
    bedrooms = IntField()
    bathrooms = FloatField()
    square_footage = FloatField()
    mileage = FloatField()
    draft_depth = FloatField()
    beam_width = FloatField()
    attributes = DictField(default=dict)
    is_featured = BooleanField(default=False)
    published_at = DateTimeField()
    created_at = DateTimeField(default=_utcnow)
    updated_at = DateTimeField(default=_utcnow)

    @property
    def seller(self):
        return User.objects(id=self.seller_id).first()

    @property
    def agency(self):
        return AgencyProfile.objects(id=self.agency_id).first() if self.agency_id else None

    @property
    def media_items(self):
        return list(ListingMedia.objects(listing_id=self.id).order_by("sort_order", "id"))

    @property
    def inquiries(self):
        return list(Inquiry.objects(listing_id=self.id))

    @property
    def real_estate_details(self):
        return RealEstateListing.objects(listing_id=self.id).first()

    @property
    def vehicle_details(self):
        return VehicleListing.objects(listing_id=self.id).first()

    @property
    def vessel_aircraft_details(self):
        return VesselAircraftListing.objects(listing_id=self.id).first()

    @property
    def watch_jewelry_details(self):
        return WatchJewelryListing.objects(listing_id=self.id).first()

    @property
    def rental_terms(self):
        return RentalTerms.objects(listing_id=self.id).first()

    @property
    def details(self) -> dict:
        """Return category-specific fields from additive subtype collections."""
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
    meta = {
        "collection": "taxonomy_terms",
        "indexes": [
            "taxonomy",
            "parent_id",
            "is_active",
            {"fields": ("taxonomy", "parent_id", "slug"), "unique": True},
        ],
    }

    taxonomy = StringField(required=True, max_length=50)
    parent_id = IntField()
    name = StringField(required=True, max_length=160)
    slug = StringField(required=True, max_length=180)
    metadata_json = DictField(default=dict)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=_utcnow)
    updated_at = DateTimeField(default=_utcnow)


class RealEstateListing(Document):
    meta = {"collection": "listing_real_estate"}

    listing_id = IntField(primary_key=True)
    area_value = FloatField()
    area_unit = StringField(max_length=8)
    acreage = FloatField()
    bedrooms = IntField()
    bathrooms = FloatField()
    property_type_id = IntField()

    @property
    def listing(self):
        return Listing.objects(id=self.listing_id).first()

    def as_dict(self) -> dict:
        return {
            "area_value": self.area_value,
            "area_unit": self.area_unit,
            "acreage": self.acreage,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "property_type_id": self.property_type_id,
        }


class VehicleListing(Document):
    meta = {"collection": "listing_vehicle"}

    listing_id = IntField(primary_key=True)
    make_id = IntField()
    model_id = IntField()
    make = StringField(max_length=120)
    model = StringField(max_length=120)
    year = IntField()
    mileage_value = FloatField()
    mileage_unit = StringField(max_length=8)
    vin_ciphertext = StringField()
    steering_side = StringField(max_length=8)

    @property
    def listing(self):
        return Listing.objects(id=self.listing_id).first()

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


class VesselAircraftListing(Document):
    meta = {"collection": "listing_vessel_aircraft"}

    listing_id = IntField(primary_key=True)
    asset_type = StringField(required=True, max_length=16)
    builder_id = IntField()
    builder = StringField(max_length=120)
    year = IntField()
    length_value = FloatField()
    length_unit = StringField(max_length=8)
    cabins = IntField()
    engine_hours = IntField()

    @property
    def listing(self):
        return Listing.objects(id=self.listing_id).first()

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


class WatchJewelryListing(Document):
    meta = {"collection": "listing_watch_jewelry"}

    listing_id = IntField(primary_key=True)
    asset_type = StringField(required=True, max_length=16)
    brand_id = IntField()
    brand = StringField(max_length=120)
    reference_number = StringField(max_length=120)
    case_material_id = IntField()
    movement_id = IntField()
    case_material = StringField(max_length=120)
    movement = StringField(max_length=120)

    @property
    def listing(self):
        return Listing.objects(id=self.listing_id).first()

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


class RentalTerms(Document):
    meta = {"collection": "listing_rental_terms"}

    listing_id = IntField(primary_key=True)
    available_from = DateTimeField()
    available_until = DateTimeField()
    min_nights = IntField()
    pricing_tiers = DictField(default=dict)

    @property
    def listing(self):
        return Listing.objects(id=self.listing_id).first()

    def as_dict(self) -> dict:
        return {
            "available_from": self.available_from,
            "available_until": self.available_until,
            "min_nights": self.min_nights,
            "pricing_tiers": self.pricing_tiers,
        }


class ListingMedia(Base):
    meta = {"collection": "listing_media", "indexes": ["listing_id"]}

    listing_id = IntField(required=True)
    media_type = StringField(required=True, max_length=32)
    url = StringField(required=True, max_length=600)
    sort_order = IntField(default=0)

    @property
    def listing(self):
        return Listing.objects(id=self.listing_id).first()


class SavedListing(Base):
    meta = {
        "collection": "saved_listings",
        "indexes": [
            "user_id",
            "listing_id",
            {"fields": ("user_id", "listing_id"), "unique": True},
        ],
    }

    user_id = IntField(required=True)
    listing_id = IntField(required=True)
    created_at = DateTimeField(default=_utcnow)

    @property
    def user(self):
        return User.objects(id=self.user_id).first()

    @property
    def listing(self):
        return Listing.objects(id=self.listing_id).first()


class SavedSearch(Base):
    meta = {"collection": "saved_searches", "indexes": ["user_id"]}

    user_id = IntField(required=True)
    name = StringField(required=True, max_length=120)
    filters = DictField(default=dict)
    alert_enabled = BooleanField(default=True)
    created_at = DateTimeField(default=_utcnow)

    @property
    def user(self):
        return User.objects(id=self.user_id).first()


class AlertPreference(Base):
    meta = {"collection": "alert_preferences", "indexes": ["user_id"]}

    user_id = IntField(required=True)
    channel = StringField(required=True, max_length=32)
    enabled = BooleanField(default=True)


class Inquiry(Base):
    meta = {
        "collection": "inquiries",
        "indexes": ["listing_id", "buyer_id", "seller_id", "status", "created_at"],
    }

    listing_id = IntField(required=True)
    buyer_id = IntField()
    seller_id = IntField(required=True)
    name = StringField(required=True, max_length=120)
    email = StringField(required=True, max_length=255)
    phone = StringField(max_length=32)
    message = StringField(required=True)
    status = StringField(default="sent", max_length=24)
    viewed_at = DateTimeField()
    replied_at = DateTimeField()
    created_at = DateTimeField(default=_utcnow)

    @property
    def listing(self):
        return Listing.objects(id=self.listing_id).first()

    @property
    def buyer(self):
        return User.objects(id=self.buyer_id).first() if self.buyer_id else None

    @property
    def seller(self):
        return User.objects(id=self.seller_id).first()


class PhoneRevealEvent(Base):
    meta = {"collection": "phone_reveal_events", "indexes": ["listing_id", "user_id"]}

    listing_id = IntField(required=True)
    user_id = IntField()
    created_at = DateTimeField(default=_utcnow)


class Subscription(Base):
    meta = {"collection": "subscriptions", "indexes": ["business_user_id", "starts_at"]}

    business_user_id = IntField(required=True)
    plan_code = StringField(required=True, max_length=50)
    status = EnumField(SubscriptionStatus, required=True, default=SubscriptionStatus.trial)
    stripe_customer_id = StringField(max_length=100)
    stripe_subscription_id = StringField(max_length=100)
    starts_at = DateTimeField(default=_utcnow)
    ends_at = DateTimeField()

    @property
    def business_user(self):
        return User.objects(id=self.business_user_id).first()


class FeaturedPlacement(Base):
    meta = {"collection": "featured_placements", "indexes": ["listing_id"]}

    listing_id = IntField(required=True, unique=True)
    starts_at = DateTimeField(default=_utcnow)
    ends_at = DateTimeField()
    priority = IntField(default=100)


class BlogPost(Base):
    meta = {"collection": "blog_posts", "indexes": ["slug", "published", "created_at"]}

    title = StringField(required=True, max_length=255)
    slug = StringField(required=True, unique=True, max_length=300)
    excerpt = StringField(max_length=500)
    content_markdown = StringField(required=True)
    cover_image_url = StringField(max_length=600)
    podcast_embed_url = StringField(max_length=600)
    published = BooleanField(default=False)
    created_at = DateTimeField(default=_utcnow)
    updated_at = DateTimeField(default=_utcnow)


class AuditLog(Base):
    meta = {"collection": "audit_logs", "indexes": ["actor_user_id", "event_type", "created_at"]}

    actor_user_id = IntField()
    event_type = StringField(required=True, max_length=80)
    details = DictField(default=dict)
    created_at = DateTimeField(default=_utcnow)

    @property
    def actor(self):
        return User.objects(id=self.actor_user_id).first() if self.actor_user_id else None


class ApiKey(Base):
    meta = {"collection": "api_keys", "indexes": ["owner_user_id", "key_hash"]}

    owner_user_id = IntField(required=True)
    name = StringField(required=True, max_length=120)
    key_hash = StringField(required=True, unique=True, max_length=128)
    scopes = ListField(StringField(), default=list)
    last_used_at = DateTimeField()
    revoked_at = DateTimeField()
    created_at = DateTimeField(default=_utcnow)


class BrokerFeed(Base):
    meta = {"collection": "broker_feeds", "indexes": ["owner_user_id", "status", "created_at"]}

    owner_user_id = IntField(required=True)
    name = StringField(required=True, max_length=120)
    source_type = StringField(required=True, max_length=20)
    pull_url = StringField(max_length=600)
    mapping_json = DictField(default=dict)
    schedule_cron = StringField(max_length=80)
    status = StringField(default="active", max_length=24)
    created_at = DateTimeField(default=_utcnow)
    updated_at = DateTimeField(default=_utcnow)


class IngestionJob(Base):
    meta = {"collection": "ingestion_jobs", "indexes": ["owner_user_id", "feed_id", "status", "created_at"]}

    owner_user_id = IntField(required=True)
    feed_id = IntField()
    source_type = StringField(required=True, max_length=20)
    status = StringField(default="queued", max_length=24)
    total_rows = IntField(default=0)
    success_rows = IntField(default=0)
    failed_rows = IntField(default=0)
    error_json = DictField(default=dict)
    created_at = DateTimeField(default=_utcnow)
    started_at = DateTimeField()
    finished_at = DateTimeField()


class IngestionRow(Base):
    meta = {"collection": "ingestion_rows", "indexes": ["job_id", "external_id", "status"]}

    job_id = IntField(required=True)
    external_id = StringField(max_length=160)
    row_payload = DictField(default=dict)
    status = StringField(default="staged", max_length=24)
    error_json = DictField(default=dict)
    created_at = DateTimeField(default=_utcnow)


class ListingExternalId(Base):
    meta = {
        "collection": "listing_external_ids",
        "indexes": [
            "owner_user_id",
            "listing_id",
            {"fields": ("owner_user_id", "source", "external_id"), "unique": True},
        ],
    }

    owner_user_id = IntField(required=True)
    source = StringField(required=True, max_length=80)
    external_id = StringField(required=True, max_length=160)
    listing_id = IntField(required=True)
    created_at = DateTimeField(default=_utcnow)


class OutboxEvent(Base):
    meta = {"collection": "outbox_events", "indexes": ["aggregate_type", "aggregate_id", "event_type"]}

    aggregate_type = StringField(required=True, max_length=80)
    aggregate_id = StringField(required=True, max_length=120)
    event_type = StringField(required=True, max_length=120)
    payload = DictField(default=dict)
    created_at = DateTimeField(default=_utcnow)
    published_at = DateTimeField()


class FraudSignal(Base):
    meta = {"collection": "fraud_signals", "indexes": ["listing_id", "user_id", "signal_type", "severity", "status", "created_at"]}

    listing_id = IntField()
    user_id = IntField()
    signal_type = StringField(required=True, max_length=80)
    severity = StringField(default="medium", max_length=20)
    status = StringField(default="open", max_length=24)
    details = DictField(default=dict)
    created_at = DateTimeField(default=_utcnow)
    resolved_at = DateTimeField()


class SocialAccount(Base):
    meta = {
        "collection": "social_accounts",
        "indexes": [
            "user_id",
            {"fields": ("provider", "provider_user_id"), "unique": True},
        ],
    }

    user_id = IntField(required=True)
    provider = StringField(required=True, max_length=20)
    provider_user_id = StringField(required=True, max_length=255)
    email = StringField(max_length=255)
    created_at = DateTimeField(default=_utcnow)

    @property
    def user(self):
        return User.objects(id=self.user_id).first()


class TwoFactorChallenge(Base):
    meta = {"collection": "two_factor_challenges", "indexes": ["user_id", "expires_at"]}

    user_id = IntField(required=True)
    code_hash = StringField(required=True, max_length=128)
    expires_at = DateTimeField(required=True)
    consumed_at = DateTimeField()
    created_at = DateTimeField(default=_utcnow)

    @property
    def user(self):
        return User.objects(id=self.user_id).first()


class EmailVerificationChallenge(Base):
    meta = {"collection": "email_verification_challenges", "indexes": ["user_id", "expires_at"]}

    user_id = IntField(required=True)
    code_hash = StringField(required=True, max_length=128)
    expires_at = DateTimeField(required=True)
    consumed_at = DateTimeField()
    created_at = DateTimeField(default=_utcnow)

    @property
    def user(self):
        return User.objects(id=self.user_id).first()
