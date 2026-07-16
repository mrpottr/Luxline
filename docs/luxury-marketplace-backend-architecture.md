# Luxline Global Luxury Marketplace Backend Architecture

This design extends the current Luxline FastAPI backend into a global luxury marketplace while preserving existing admin functionality:

- `GET /api/v1/admin/overview`
- `GET /api/v1/admin/audit-logs`
- `GET /api/v1/admin/moderation-queue`
- `POST /api/v1/admin/listings/{id}/approve`
- `POST /api/v1/admin/listings/{id}/reject`
- `POST /api/v1/admin/users/{id}/verify-business`
- `POST /api/v1/admin/users/{id}/reset-password`
- `PATCH /api/v1/admin/users/{id}/role`
- `GET /api/v1/admin/monitoring/metrics`
- `GET /api/v1/admin/monitoring/health`

The key architectural shift is from the current wide `listings` table to a class-table inheritance model: one durable base listing row plus one vertical-specific detail row.

## 1. Service Architecture

Keep the monolith deployable for now, but draw service boundaries inside the codebase so high-throughput pieces can be split later.

```text
frontend/
  components/
    AdminDashboard.jsx       # keep current admin cards/actions; add tabs below
    SellerDashboard.jsx
    BrokerDashboard.jsx
    SearchExperience.jsx

backend/app/
  main.py
  routers/
    auth.py
    users.py
    listings.py             # generic listing CRUD
    listings_real_estate.py
    listings_motors.py
    listings_marine_aviation.py
    listings_collectibles.py
    rentals.py
    search.py
    leads.py
    messaging.py
    agencies.py
    ingestion.py
    monetization.py
    localization.py
    journal.py
    admin.py                # preserve existing endpoints
    admin_taxonomy.py
    admin_moderation.py
    admin_fraud.py
    admin_cms.py
  services/
    inventory/
    search_indexer/
    localization/
    lead_routing/
    ingestion/
    fraud/
    payments/
```

Recommended runtime components:

```text
FastAPI API Gateway / BFF
PostgreSQL + PostGIS          source of truth, transactional writes
OpenSearch                    faceted search and autocomplete
Redis                         sessions, rate limits, short-lived FX cache
Kafka or Redpanda             outbox events, ingestion jobs, search indexing
S3-compatible object storage  listing media and feed uploads
Celery/RQ workers             XML/JSON parsing, image jobs, fraud checks
gRPC internal services        inventory, leads, search, localization
Prometheus/Grafana            keep current monitoring path
```

## 2. Polymorphic Inventory Model

### STI vs CTI decision

Single Table Inheritance is simple and matches the current code, but it becomes sparse and hard to index when real estate, cars, yachts, jets, watches, jewelry, and rentals all share one table. At 800,000+ listings, the null bloat and mixed indexes become painful.

Use Class Table Inheritance:

- `listings` stores common fields used by every vertical.
- `listing_real_estate`, `listing_vehicle`, `listing_vessel_aircraft`, `listing_watch_jewelry`, and `listing_rental_terms` store vertical fields.
- `listing_attributes` or `attributes_jsonb` is allowed only for low-value, non-faceted extras.
- Search uses a denormalized projection in OpenSearch, not live multi-table joins.

### SQLAlchemy model sketch

```python
from datetime import datetime
from enum import Enum
from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer,
    Numeric, String, Text, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geography
from backend.app.db.base import Base


class ListingCategory(str, Enum):
    real_estate = "real_estate"
    car = "car"
    yacht = "yacht"
    jet = "jet"
    watch = "watch"
    jewelry = "jewelry"
    rental = "rental"


class ListingStatus(str, Enum):
    draft = "draft"
    pending = "pending"
    active = "active"
    paused = "paused"
    sold = "sold"
    archived = "archived"


class ModerationStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    needs_review = "needs_review"


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    public_id: Mapped[str] = mapped_column(UUID(as_uuid=False), unique=True, index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    agency_id: Mapped[int | None] = mapped_column(ForeignKey("agency_profiles.id"), index=True)
    category: Mapped[ListingCategory] = mapped_column(SQLEnum(ListingCategory), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ListingStatus] = mapped_column(SQLEnum(ListingStatus), index=True)
    moderation_status: Mapped[ModerationStatus] = mapped_column(SQLEnum(ModerationStatus), index=True)
    price_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    price_currency: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    price_usd: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, index=True)
    country_code: Mapped[str | None] = mapped_column(String(2), index=True)
    region: Mapped[str | None] = mapped_column(String(120), index=True)
    city: Mapped[str | None] = mapped_column(String(120), index=True)
    address_redacted: Mapped[str | None] = mapped_column(String(255))
    geo: Mapped[object | None] = mapped_column(Geography("POINT", srid=4326))
    attributes_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    real_estate = relationship("RealEstateListing", uselist=False, back_populates="listing")
    vehicle = relationship("VehicleListing", uselist=False, back_populates="listing")
    vessel_aircraft = relationship("VesselAircraftListing", uselist=False, back_populates="listing")
    watch_jewelry = relationship("WatchJewelryListing", uselist=False, back_populates="listing")
    rental_terms = relationship("RentalTerms", uselist=False, back_populates="listing")


Index("ix_listings_public_search", Listing.status, Listing.moderation_status, Listing.category, Listing.price_usd)
Index("ix_listings_geo", Listing.geo, postgresql_using="gist")


class RealEstateListing(Base):
    __tablename__ = "listing_real_estate"

    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True)
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    bathrooms: Mapped[float | None] = mapped_column(Numeric(4, 1))
    area_value: Mapped[float | None] = mapped_column(Numeric(12, 2))
    area_unit: Mapped[str | None] = mapped_column(String(8))      # sqft|sqm
    acreage: Mapped[float | None] = mapped_column(Numeric(12, 2))
    property_type_id: Mapped[int | None] = mapped_column(ForeignKey("taxonomy_terms.id"))
    listing = relationship("Listing", back_populates="real_estate")


class VehicleListing(Base):
    __tablename__ = "listing_vehicle"

    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True)
    make_id: Mapped[int | None] = mapped_column(ForeignKey("taxonomy_terms.id"), index=True)
    model_id: Mapped[int | None] = mapped_column(ForeignKey("taxonomy_terms.id"), index=True)
    year: Mapped[int | None] = mapped_column(Integer, index=True)
    mileage_value: Mapped[float | None] = mapped_column(Numeric(12, 2))
    mileage_unit: Mapped[str | None] = mapped_column(String(8))   # mi|km
    vin_ciphertext: Mapped[str | None] = mapped_column(Text)
    steering_side: Mapped[str | None] = mapped_column(String(5))  # left|right
    listing = relationship("Listing", back_populates="vehicle")


class VesselAircraftListing(Base):
    __tablename__ = "listing_vessel_aircraft"

    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True)
    asset_type: Mapped[str] = mapped_column(String(16), index=True)  # yacht|jet
    builder_id: Mapped[int | None] = mapped_column(ForeignKey("taxonomy_terms.id"), index=True)
    year: Mapped[int | None] = mapped_column(Integer, index=True)
    length_value: Mapped[float | None] = mapped_column(Numeric(10, 2))
    length_unit: Mapped[str | None] = mapped_column(String(8))       # ft|m
    cabins: Mapped[int | None] = mapped_column(Integer)
    engine_hours: Mapped[int | None] = mapped_column(Integer)
    listing = relationship("Listing", back_populates="vessel_aircraft")


class WatchJewelryListing(Base):
    __tablename__ = "listing_watch_jewelry"

    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True)
    asset_type: Mapped[str] = mapped_column(String(16), index=True)  # watch|jewelry
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("taxonomy_terms.id"), index=True)
    reference_number: Mapped[str | None] = mapped_column(String(120), index=True)
    case_material_id: Mapped[int | None] = mapped_column(ForeignKey("taxonomy_terms.id"))
    movement_id: Mapped[int | None] = mapped_column(ForeignKey("taxonomy_terms.id"))
    listing = relationship("Listing", back_populates="watch_jewelry")


class RentalTerms(Base):
    __tablename__ = "listing_rental_terms"

    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True)
    min_nights: Mapped[int | None] = mapped_column(Integer)
    availability_calendar_id: Mapped[str | None] = mapped_column(String(120))
    pricing_tiers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    listing = relationship("Listing", back_populates="rental_terms")
```

### Shared support tables

```python
class TaxonomyTerm(Base):
    __tablename__ = "taxonomy_terms"
    __table_args__ = (UniqueConstraint("taxonomy", "parent_id", "slug"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    taxonomy: Mapped[str] = mapped_column(String(50), index=True)  # make, model, brand, builder, material
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("taxonomy_terms.id"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False)
    metadata_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ListingMedia(Base):
    __tablename__ = "listing_media"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    media_type: Mapped[str] = mapped_column(String(32))
    url: Mapped[str] = mapped_column(String(600))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Lead(Base):
    __tablename__ = "leads"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True)
    buyer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    encrypted_contact: Mapped[dict] = mapped_column(JSONB, nullable=False)
    encrypted_message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="new", index=True)
    pipeline_stage: Mapped[str] = mapped_column(String(32), default="inbox", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    key_hash: Mapped[str] = mapped_column(String(128), unique=True)
    scopes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
```

## 3. RBAC and UI Workflows

Roles should remain compatible with existing values and add explicit capabilities.

```text
standard_user       buyer account
private_seller      B2C seller, single/few listings
business_account    agent, broker, dealership, brokerage
super_admin         platform operator
```

Permission model:

```text
visitor:
  listings:read_public, search:read, journal:read, localization:read

standard_user:
  visitor permissions
  favorites:create/delete, saved_search:create, alerts:manage, leads:create, messages:read_own

private_seller:
  buyer permissions
  listings:create_own, listings:update_own, payments:create_checkout, messages:seller_inbox

business_account:
  private_seller permissions
  api_keys:manage, feeds:create, feeds:read_own, leads:pipeline_manage, company_profile:manage

super_admin:
  all permissions
  taxonomy:manage, moderation:manage, fraud:review, cms:author, users:manage, monitoring:read
```

Visitor flow:

1. `GET /search` uses OpenSearch for public active/approved inventory.
2. `GET /search/facets` returns counts for category-specific filters.
3. `GET /localization/rates` returns cached FX rates; UI converts display prices.
4. `GET /journal/posts` reads published CMS content.

Buyer flow:

1. Auth via existing `/auth`.
2. `POST /listings/{id}/save` stores favorites.
3. `POST /saved-searches` stores filters and alert cadence.
4. `POST /leads/listings/{id}/inquire` encrypts PII and emits `lead.created`.
5. Messaging uses a lead-scoped thread; buyers cannot access seller-only CRM notes.

Private seller flow:

1. Guided listing wizard selects category, then requests the subtype payload.
2. Listing starts `draft`, moves to `pending` when submitted.
3. Optional premium placement goes through `POST /monetization/checkout`.
4. Seller dashboard shows listing status, moderation notes, leads, and messages.

Broker flow:

1. Broker creates company profile and team seats.
2. `POST /api-keys` creates scoped keys: `listings:write`, `feeds:write`, `leads:read`.
3. `POST /ingestion/jobs` uploads XML/JSON/CSV feed or registers a pull URL.
4. Worker validates, upserts by external ID, and emits indexing events.
5. Lead pipeline supports stages: new, contacted, qualified, showing, negotiating, won, lost.

Super admin flow:

1. Existing dashboard remains the default admin entry.
2. Add tabs for taxonomy, moderation, fraud, ingestion health, CMS, monitoring.
3. Taxonomy changes create audit logs and trigger search reindex for affected terms.
4. Fraud queues combine rules, velocity signals, duplicate VIN/reference checks, and manual reports.
5. CMS authoring manages Journal posts, media, authors, scheduled publishing, and SEO metadata.

## 4. Search and Filtering

PostgreSQL remains the system of record. OpenSearch is the query engine.

Index one document per listing:

```json
{
  "id": 123,
  "category": "car",
  "title": "Ferrari SF90 Stradale",
  "status": "active",
  "moderation_status": "approved",
  "price_usd": 625000,
  "price_currency": "EUR",
  "location": {"lat": 43.7, "lon": 7.2},
  "country_code": "FR",
  "city": "Monaco",
  "seller_type": "business",
  "facets": {
    "make": "Ferrari",
    "model": "SF90",
    "year": 2024,
    "steering_side": "left"
  },
  "published_at": "2026-06-28T10:00:00Z",
  "is_featured": true
}
```

Search flow:

1. API validates filters and maps category-specific filters into OpenSearch DSL.
2. OpenSearch returns IDs, counts, and facet buckets.
3. API loads listing cards from Redis projection cache or PostgreSQL read replica.
4. Sort order: paid placement, quality score, recency, then deterministic ID.
5. Search events are logged asynchronously for ranking and alert matching.

For 800,000+ listings, use:

- category-specific index templates
- keyword fields for facets
- numeric fields for range filters
- geo_point for map search
- edge n-grams or completion suggester for autocomplete
- background reindex jobs via `listing.changed` outbox events

## 5. Localization Engine

Store original listing prices and a normalized `price_usd` value at write time.

Display conversion:

1. Exchange-rate worker pulls provider rates every 5 to 15 minutes.
2. Rates are written to `currency_rates` and cached in Redis.
3. Search filtering uses `price_usd` for stable ranges.
4. UI display uses requested currency, rounded according to currency rules.
5. Unit conversion is presentation-only unless users edit a listing; canonical values should be normalized per subtype.

Tables:

```text
currency_rates(base_currency, quote_currency, rate, provider, observed_at)
unit_preferences(user_id, measurement_system)
```

## 6. CRM Integration Pipeline

Do not parse feeds in request handlers. The API only accepts metadata or uploads and returns a job ID.

Flow:

1. Broker calls `POST /api/v1/ingestion/jobs` with feed URL or upload handle.
2. API writes `ingestion_jobs(status=queued)` and emits `ingestion.job.created`.
3. Worker downloads/parses feed into staging tables.
4. Worker validates taxonomy, required fields, media URLs, seller ownership, and duplicates.
5. Valid rows upsert listings and subtype rows in small batches.
6. Each batch writes outbox rows for search indexing and alert matching.
7. Errors are stored per row and exposed in broker dashboard.

Core tables:

```text
broker_feeds(id, owner_user_id, source_type, pull_url, mapping_jsonb, schedule_cron, status)
ingestion_jobs(id, feed_id, status, total_rows, success_rows, failed_rows, started_at, finished_at)
ingestion_rows(id, job_id, external_id, row_payload_jsonb, status, error_jsonb)
listing_external_ids(owner_user_id, source, external_id, listing_id)
outbox_events(id, aggregate_type, aggregate_id, event_type, payload_jsonb, published_at)
```

This avoids locking the main DB because parsing and validation happen in staging, and writes use chunked upserts with short transactions.

## 7. Optimal FastAPI Router Structure

```text
/api/v1/auth
/api/v1/users
/api/v1/me
/api/v1/listings
/api/v1/listings/{id}/media
/api/v1/listings/{id}/submit
/api/v1/listings/{id}/save
/api/v1/real-estate/listings
/api/v1/cars/listings
/api/v1/yachts/listings
/api/v1/jets/listings
/api/v1/watches/listings
/api/v1/jewelry/listings
/api/v1/rentals/listings
/api/v1/search
/api/v1/search/facets
/api/v1/search/autocomplete
/api/v1/leads
/api/v1/messages
/api/v1/agencies
/api/v1/api-keys
/api/v1/ingestion/jobs
/api/v1/monetization
/api/v1/localization
/api/v1/journal
/api/v1/admin                         # keep current admin behavior
/api/v1/admin/taxonomy
/api/v1/admin/moderation
/api/v1/admin/fraud
/api/v1/admin/cms
/api/v1/admin/monitoring
```

## 8. gRPC Proto Contracts

```proto
syntax = "proto3";

package luxline.v1;

import "google/protobuf/timestamp.proto";

enum ListingCategory {
  LISTING_CATEGORY_UNSPECIFIED = 0;
  REAL_ESTATE = 1;
  CAR = 2;
  YACHT = 3;
  JET = 4;
  WATCH = 5;
  JEWELRY = 6;
  RENTAL = 7;
}

message Money {
  string currency = 1;
  int64 amount_minor = 2;
}

message ListingSummary {
  int64 id = 1;
  string public_id = 2;
  ListingCategory category = 3;
  string title = 4;
  Money price = 5;
  string seller_id = 6;
  string status = 7;
  string moderation_status = 8;
  google.protobuf.Timestamp published_at = 9;
}

message GetListingRequest {
  int64 listing_id = 1;
  bool include_private = 2;
}

message ListingChangedEvent {
  int64 listing_id = 1;
  string change_type = 2;
  google.protobuf.Timestamp changed_at = 3;
}

service InventoryService {
  rpc GetListing(GetListingRequest) returns (ListingSummary);
  rpc StreamListingChanges(google.protobuf.Timestamp) returns (stream ListingChangedEvent);
}

message CreateLeadRequest {
  int64 listing_id = 1;
  string buyer_user_id = 2;
  string buyer_name = 3;
  string buyer_email = 4;
  string buyer_phone = 5;
  string message = 6;
  string source = 7;
}

message CreateLeadResponse {
  int64 lead_id = 1;
  string status = 2;
  string routed_to_seller_id = 3;
}

message LeadStatusChanged {
  int64 lead_id = 1;
  string status = 2;
  string pipeline_stage = 3;
  google.protobuf.Timestamp changed_at = 4;
}

service LeadGenerationService {
  rpc CreateLead(CreateLeadRequest) returns (CreateLeadResponse);
  rpc StreamLeadUpdates(google.protobuf.Timestamp) returns (stream LeadStatusChanged);
}

message SearchRequest {
  string query = 1;
  ListingCategory category = 2;
  int64 min_price_usd_minor = 3;
  int64 max_price_usd_minor = 4;
  map<string, string> facets = 5;
  int32 limit = 6;
  int32 offset = 7;
}

message FacetBucket {
  string field = 1;
  string value = 2;
  int64 count = 3;
}

message SearchResponse {
  repeated ListingSummary results = 1;
  repeated FacetBucket facets = 2;
  int64 total = 3;
}

service SearchService {
  rpc SearchListings(SearchRequest) returns (SearchResponse);
  rpc ReindexListing(GetListingRequest) returns (ListingSummary);
}

message ConvertMoneyRequest {
  Money amount = 1;
  string target_currency = 2;
}

service LocalizationService {
  rpc ConvertMoney(ConvertMoneyRequest) returns (Money);
}
```

## 9. Migration Plan From Current Code

1. Keep current endpoints and admin UI working.
2. Add subtype tables and backfill from current nullable columns:
   - `bedrooms`, `bathrooms`, `square_footage` into `listing_real_estate`
   - `year`, `make`, `model`, `mileage` into vehicle or vessel rows based on category
   - watch/jewelry fields from `attributes`
3. Update `ListingCreate` to accept a discriminated `details` payload by category.
4. Write both old columns and subtype tables for one release if needed.
5. Switch read paths to hydrate `details` from subtype tables.
6. Introduce OpenSearch indexing from outbox events.
7. Retire sparse legacy columns after frontend and ingestion paths are migrated.

