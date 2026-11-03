# Broker API

All routes are mounted under `/api/broker/v1` only when backend `BROKER_PANEL_ENABLED=true`. Authentication uses the existing bearer JWT. Listing routes resolve business owners from their existing organization profile and enrolled members from `broker_members`. Send `X-Broker-Organization-Id` when selecting a specific organization or when the user belongs to multiple brokers. Platform admins use the existing admin portal. Listing use cases enforce their own broker permissions; repositories scope broker extension records to `organization_id`.

## Listings

`POST /media/upload` accepts JSON fields `content_base64`, `content_type`, `media_type`, and `alt_text`. It allows JPEG, PNG, WebP, and PDF floor plans up to 8 MiB, checks file signatures, applies the broker upload rate limit, and returns an expiring signed media URL. `GET /media/{asset_id}` serves a valid signed URL. Uploaded bytes are stored in the additive `broker_media_assets` collection. `BROKER_MEDIA_STORAGE=mock_mongo` and `BROKER_VIRUS_SCANNER=mock` select the offline mock adapters. The mock scanner only detects the EICAR test marker; production use requires replacing it with a real scanning provider.

| Method | Path | Permission | Purpose |
| --- | --- | --- | --- |
| POST | `/media/upload` | `broker:listing:create` | Validate, scan through the configured provider, store media, and return an expiring signed URL. |
| GET | `/media/{asset_id}` | Signed URL | Serve an unexpired asset after HMAC and tenant-bound signature validation. |

| Method | Path | Permission | Purpose |
| --- | --- | --- | --- |
| GET | `/listings/categories` | `broker:listing:view_own` | Return the category values supported by the existing marketplace listing model. |
| GET | `/listings` | `broker:listing:view_own` | Filter by `category`, `quality_rating`, and `agent_id`; paginate with `limit` (1–100) and `offset`; sort by `created_at` or `quality_score` (prefix `-` for descending). Agent role is restricted to assigned listings. |
| GET | `/listings/export.csv` | `broker:listing:view_own` | Export up to 500 listings as CSV; agents export only assigned listings. |
| POST | `/listings` | `broker:listing:create` | Create a draft. Requires `Idempotency-Key` (8–128 characters). |
| PATCH | `/listings/{listing_id}` | `broker:listing:edit` | Update listing fields and append a prior-state revision. |
| GET | `/listings/{listing_id}/revisions` | `broker:listing:view_own` | Read up to 50 tenant-scoped prior revisions. |
| POST | `/listings/{listing_id}/publish` | `broker:listing:publish` | Validate publish eligibility, then activate the base listing. |
| POST | `/listings/{listing_id}/pause` | `broker:listing:edit` | Return the base listing to draft. |
| DELETE | `/listings/{listing_id}` | `broker:listing:delete` | Soft-delete the broker extension and return the base listing to draft. |
| POST | `/listings/bulk/validate` | `broker:listing:create` | Validate CSV and return row-level errors without writing. |
| POST | `/listings/bulk/import` | `broker:listing:create` | Validate the full CSV, then create draft listings. Requires an `Idempotency-Key` of at least 8 characters. |

CSV columns: `title,category,price,currency,location_country,location_city`. The importer rejects unsupported categories, non-finite or non-positive prices, currencies that are not three-letter alphabetic codes, blank locations, and configured category/currency price-floor violations.

Create and update request bodies are validated by Pydantic schemas in `backend/app/broker/schemas.py`. Listing bodies accept a `media` array of HTTPS references with `media_type` (`image`, `video`, or `floor_plan`), `sort_order`, and descriptive `alt_text` for image and floor-plan entries. The legacy `photos` field remains accepted as an image-reference compatibility input. New media metadata is stored on the broker extension and base media rows continue to serve existing marketplace readers. Omitted media is retained on edit because the existing shared `ListingMedia` model has no soft-delete support.

Responses use the existing FastAPI JSON detail error format. List responses are arrays and include listing, media, and quality fields. A missing tenant-owned listing returns 404; insufficient permission returns 403; invalid fields or publish eligibility return 422. Bulk request throttling returns 429. MongoDB-backed counters allow the configured number of bulk requests per actor and organization in each fixed 60-second window and are shared across workers.

## Publish eligibility

Publishing requires an approved broker profile, an active existing subscription, a licence keyed by the listing country, owner consent, the configured minimum media count, a configured price floor for the listing category and currency if present, and quality score of at least 50.

Broker-specific optional environment settings are listed in `backend/.env.example`. The default panel flag is off. MongoEngine creates broker collections on first write; this repository has no migration framework or rollback command.

## Leads and inbox

All endpoints below require `BROKER_PANEL_ENABLED=true` and a bearer token. Broker endpoints also require an active broker membership, an approved broker profile, and the listed use-case permission. Broker leads and supporting records are stored in tenant-owned `broker_leads`, `broker_activities`, `broker_messages`, and `broker_templates` collections. List endpoints accept bounded pagination and the documented stage/sort filters. Create endpoints require an `Idempotency-Key` header (8–128 characters). Messaging is throttled by `BROKER_MESSAGES_PER_MINUTE` using shared Mongo-backed counters.

| Method | Path | Permission / identity | Purpose |
| --- | --- | --- | --- |
| GET | `/leads` | `broker:lead:view_all` or assigned agent `broker:lead:view_own` | Import seller-directed inquiries for this organization's listings, then list by `stage`, `limit`, `offset`, and `sort` (`created_at`, `score`, optionally prefixed with `-`). |
| PATCH | `/leads/{lead_id}/stage` | Lead view permission | Set stage to `new`, `contacted`, `qualified`, `lost`, or `closed`. |
| POST | `/leads/{lead_id}/assign` | `broker:lead:assign` | Assign to an active member in the selected organization. |
| PATCH | `/leads/{lead_id}/spam` | `broker:lead:view_all` | Set or clear the manual spam flag. |
| GET, POST | `/leads/{lead_id}/activities` | Lead view permission | Read with `limit`/`offset` or add a note, task, or reminder. Create requires an idempotency key. |
| GET, POST | `/inbox/{lead_id}/messages` | `broker:lead:view_all` or assigned agent `broker:lead:view_own`; send additionally requires `broker:lead:message` | Read with `limit`/`offset` or add a buyer-visible message. Send requires a buyer account linked to the inquiry and an idempotency key. Stored messages are available to the authenticated buyer through the buyer inbox; no external messaging provider is called. |
| GET, POST | `/inbox/templates` | `broker:lead:message` | List or create organization-scoped saved replies. Create requires an idempotency key. Supported UI variables are `{buyer_name}` and `{listing_id}`. |
| GET | `/buyer/inbox?organization_id={id}` | Authenticated buyer | List only consented leads whose `buyer_id` matches the current user, scoped to the selected organization; supports `limit`/`offset`. |
| GET, POST | `/buyer/inbox/{lead_id}/messages?organization_id={id}` | Authenticated buyer owning that lead | Read with `limit`/`offset` or add messages to the buyer's own conversation. Create requires an idempotency key and is rate-limited. |

Lead assignment uses listing assignment first, a future routing-rule match second, least-loaded active-agent selection third, and manager/owner queue last. Lead scores are deterministic and use contact/account completeness and inquiry text length only. Inquiry sync happens on the lead-list request, not in a background job. A seller-directed public inquiry is treated as consent to receive a response from that broker; anonymous inquiries do not support platform messaging because no authenticated buyer identity exists.

## Analytics

Public engagement capture is also available at `POST /analytics/views` and `POST /analytics/impressions`. Each accepts `{"listing_id": 123}`, is feature-flagged, anonymous, and rate-limited per visitor/listing. Views count an eligible listing detail open; impressions count a listing card once it is at least 50% visible in the discovery grid. CTR is views divided by impressions and is null when no impressions exist.

Analytics routes require the feature flag, bearer authentication, selected organization, active membership, an approved broker profile, and `broker:analytics:view`. The maximum query window is 366 calendar days. Reports are limited to 100,000 source events per query; narrow the date range if the cap is exceeded. Event materialization and daily rollups are tenant-scoped and refreshed on report requests.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/analytics` | Return totals, daily series, and per-listing/per-agent impression, view, CTR, lead, reply, phone-reveal, response-time, and qualified-conversion metrics. Optional filters: `date_from`, `date_to`, `listing_id`, `agent_id`. |
| GET | `/analytics/export.csv` | Export a paginated listing or agent breakdown with `date_from`, `date_to`, `dimension`, `limit` (1–500), and `offset`. |

Qualified conversion means qualified or closed leads divided by all leads created in the requested period. Click-through rate is detail views divided by visible listing impressions and is null when no impressions exist. Impressions are counted once per listing per browser session after at least 50% visibility. Response-time and agent attribution follow the lead’s current assignment; listing engagement follows its current assigned agent. Existing marketplace endpoint contracts remain unchanged.
---

## Plans, billing, credits, and promotions

These routes require the backend feature flag, bearer authentication, an active organization membership, and an approved broker profile. Broker plan, wallet, subscription, and promotion records use new `broker_` collections. Application use cases check each permission; tenant repository methods include `organization_id`. Plan settings are global and writable only by a platform `super_admin`. Configure plan prices, currencies, listing limits, entitlements, credit packs, and geographic placement rates in the broker plan admin screen; an empty database has no purchasable plans and no promotion rates.

| Method | Path | Permission / identity | Purpose |
| --- | --- | --- | --- |
| GET | `/plans?limit={n}&offset={n}&sort={code|-code}` | `broker:promotion:view` | List active global broker plans (limit 1–100, default 50), sorted by code. |
| GET | `/billing/subscription` | `broker:billing:manage` | Read the active tenant broker subscription. |
| POST | `/billing/subscribe?plan_code={code}` | `broker:billing:manage` | Subscribe through the configured payment provider; requires `Idempotency-Key` (8–128 characters). |
| GET | `/credits?limit={n}&offset={n}` | `broker:billing:manage` | Read tenant balance and paginated credit ledger (limit 1–100). |
| GET | `/credits/balance` | `broker:promotion:view` | Read tenant promotion credit balance. |
| POST | `/credits/purchase?plan_code={code}&pack_code={code}` | `broker:billing:manage` | Purchase a configured credit pack; requires `Idempotency-Key`. |
| GET | `/promotions?status={status}&limit={n}&offset={n}` | `broker:promotion:view` | Read tenant promotions with bounded pagination and optional status. |
| POST | `/promotions/estimate` | `broker:promotion:manage` | Validate eligibility and calculate credits from configured scope, placement, and duration. |
| POST | `/promotions` | `broker:promotion:manage` | Create scheduled or active promotion and atomically debit credits and append a ledger entry; requires `Idempotency-Key`. |
| GET | `/admin/plans?is_active={bool}&limit={n}&offset={n}&sort={code|-code}` | Platform `super_admin` | List configured plans, optionally filtered by active state (limit 1–100, default 50). |
| POST | `/admin/plans` | Platform `super_admin` | Create a validated plan and entitlements; requires `Idempotency-Key` (8–128 characters). Repeating the same key and body returns the created plan. |
| PUT | `/admin/plans/{code}` | Platform `super_admin` | Update plan configuration and increment its version. |

Promotion request fields: `listing_id`, `scope` (`city`, `locality`, `province`, `country`), configured `location_code`, `placement_type` (`featured`, `premium`, `urgent`), and timezone-aware `starts_at`/`ends_at`. Promotion requires an approved broker, a live and moderation-approved organization listing, an active plan, owner consent, a licence matching the listing's country, and promotion entitlement. Future-dated promotions are stored as `scheduled`; automatic activation and expiry workers are not part of M7. Invalid request or business rules return the existing FastAPI `detail` error envelope with 422; permission failures return 403; insufficient credits or reused idempotency keys with different payloads return 409; unsupported Mongo transactions return 503.

`BROKER_PAYMENT_PROVIDER` defaults to `mock`, which produces deterministic receipts and makes no external calls. Transactional subscription, credit, and promotion operations require a MongoDB replica set. The optional `docker-compose.broker-replica.yml` overlay uses its own named volume and does not modify or reuse the standard Mongo volume. The default standalone Mongo configuration fails closed with 503 for these operations. No automatic charge refund is applicable to the mock provider; production adapters must add a compensating refund before they are enabled.




## Reviews, badges, moderation, and audit

Trust routes are under the same feature-flagged `/api/broker/v1` router. Broker routes require an authenticated active organization membership, approved broker profile, and the permission shown below. Public reviews expose only published reviews with explicit public consent. Buyer review creation requires authentication and ownership of the eligible closed lead; the organization ID is selected by query parameter and all lead/listing/review reads remain scoped to that organization. Review response schemas omit buyer identifiers. Platform moderation routes require the existing `super_admin` role.

| Method | Path | Permission / identity | Purpose |
| --- | --- | --- | --- |
| GET | `/reviews?status={pending|published|rejected}&limit={n}&offset={n}` | `broker:reviews:manage` | List tenant reviews with bounded pagination. |
| POST | `/reviews/{review_id}/reply` | `broker:reviews:manage` | Add or update a public reply to a published review. Body: `{"body":"..."}`. |
| POST | `/reviews/{review_id}/appeal` | `broker:reviews:manage` | Submit one appeal for an eligible review. Body: `{"reason":"..."}`. Creates an admin moderation case. |
| GET | `/badges` | `broker:analytics:view` | Re-evaluate and return versioned organization and agent badge rules, explanations, and criteria snapshots. |
| GET | `/audit?action={action}&actor_user_id={id}&limit={n}&offset={n}` | `broker:audit:view` | Read tenant audit entries including before/after state. |
| POST | `/buyer/reviews?organization_id={id}` | Authenticated buyer owning a closed, consented lead | Submit a 1�5 rating and 10�3000 character review with `public_consent=true`; requires `Idempotency-Key` (8�128 chars). New reviews start pending moderation. |
| GET | `/public/brokers/{organization_id}/reviews?limit={n}&offset={n}` | Public | List only consented, published reviews for an approved broker. |
| GET | `/admin/moderation-cases?status={open|resolved}&limit={n}&offset={n}` | Platform `super_admin` | List integrity alerts and broker appeals across tenants. |
| POST | `/admin/moderation-cases/{case_id}/resolve` | Platform `super_admin` | Record a resolution for a moderation case. |
| POST | `/admin/reviews/{review_id}/decision` | Platform `super_admin` | Publish or reject a review; body includes `decision` and optional `notes`. |

Review integrity checks reject seller/broker self-reviews and duplicate buyer/listing reviews; detected attempts create moderation cases. Badge rule version 1 awards Verified Seller to approved broker profiles, Quality Lister for five or more approved live listings averaging quality 85+, and Responsive Agent for five or more first responses averaging at most one hour. Badge evaluations are refreshed on request. Owner/manager operations, moderation, profile decisions, member role changes, credit movements, promotions, subscriptions, and analytics exports write audit rows; money-related audit writes share their transaction. Existing profile/team writes and their additional audit records are not atomic. Validation errors use FastAPI's existing `detail` error envelope (422), permission failures return 403, duplicate integrity violations return 409, and missing resources return 404.
