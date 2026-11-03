# Broker Panel Decision Notes

## M4: Listing persistence and publishing

- Keep marketplace listing documents as the public inventory source and attach broker ownership/assignment through `broker_listings`.
- Scope extension lookups by organization in `BrokerListingRepository`; base listing reads and writes follow a tenant-scoped extension and also check `agency_id` before mutation.
- Route handlers only translate HTTP inputs/errors. Listing permission checks and publish rules run in the use-case layer; MongoEngine work stays in the provider adapter.
- Listing routes use a dedicated dependency that derives owners from an existing agency profile and member roles from `broker_members`; no listing tenant is synthesized from a user ID. Multi-organization members select a tenant with `X-Broker-Organization-Id`; platform admins remain in the admin portal.
- Price floors are supplied through `BROKER_LISTING_PRICE_FLOORS_JSON` as category and ISO currency keyed values. Empty configuration means no price floor is inferred. The minimum media count is configurable through `BROKER_LISTING_MINIMUM_MEDIA_COUNT`.
- Category choices come from the existing `ListingCategory` model enum through the broker categories endpoint. Currency values are entered as three-letter codes and stored on the listing with the amount.
- Creates require an organization-scoped idempotency key. Listing edits append the prior values to `broker_listing_revisions`; archive soft-deletes the broker extension and returns the base listing to draft.
- Publish requires approval, an active subscription, a licence for the listing country, owner consent, the configured media count, the configured price floor when present, and a sufficient quality score.
- MongoDB operations span existing and broker collections without assuming replica-set transactions. Create performs compensating cleanup of the newly created listing and media if extension persistence fails; this remains a limitation if the database itself also rejects cleanup.
# M4 listing completion decisions

- Rich media is represented by ordered HTTPS references plus broker-owned alt-text and moderation metadata. The existing marketplace media collection remains the source for public listing readers.
- Editing media does not remove omitted base media because the shared legacy media model has no reversible soft-delete. The editor exposes ordering and metadata changes; omitted media remains attached until a compatible public-media lifecycle exists.
- Bulk throttling uses a thread-safe in-process sliding window, keyed by organization and actor. A shared/distributed limiter adapter is still needed for multi-worker deployments.
- Bulk idempotency keys are SHA-256-derived per row so the accepted request header length cannot overflow the broker listing key field, and retrying the same import can resume rows already created.
- Broker sequence counters use the new `broker_sequences` collection. Initial counter values are seeded from the maximum existing ID per broker collection to avoid collisions with earlier records.

