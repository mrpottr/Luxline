# Broker API

All routes are mounted under `/api/broker/v1` only when backend `BROKER_PANEL_ENABLED=true`. Authentication uses the existing bearer JWT. Listing routes resolve business owners from their existing organization profile and enrolled members from `broker_members`. Send `X-Broker-Organization-Id` when selecting a specific organization or when the user belongs to multiple brokers. Platform admins use the existing admin portal. Listing use cases enforce their own broker permissions; repositories scope broker extension records to `organization_id`.

## Listings

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

Responses use the existing FastAPI JSON detail error format. List responses are arrays and include listing, media, and quality fields. A missing tenant-owned listing returns 404; insufficient permission returns 403; invalid fields or publish eligibility return 422. Bulk request throttling returns 429. The default in-memory limiter allows 10 bulk requests per actor and organization per minute; it is process-local and does not coordinate across multiple workers.

## Publish eligibility

Publishing requires an approved broker profile, an active existing subscription, a licence keyed by the listing country, owner consent, the configured minimum media count, a configured price floor for the listing category and currency if present, and quality score of at least 50.

Broker-specific optional environment settings are listed in `backend/.env.example`. The default panel flag is off. MongoEngine creates broker collections on first write; this repository has no migration framework or rollback command.
