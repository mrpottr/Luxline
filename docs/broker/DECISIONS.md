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
- Bulk throttling uses atomic MongoDB counters in `broker_bulk_rate_limits`, keyed by organization and actor. Fixed windows are shared by workers; requests at a window boundary may span adjacent windows.
- Bulk idempotency keys are SHA-256-derived per row so the accepted request header length cannot overflow the broker listing key field, and retrying the same import can resume rows already created.
- Broker sequence counters use the new `broker_sequences` collection. Initial counter values are seeded from the maximum existing ID per broker collection to avoid collisions with earlier records.

## M5: Leads, assignment, and conversations

- Preserve the existing inquiry endpoint and response contract. Broker lead refresh imports legacy inquiries only when the referenced listing has a live `broker_listings` extension for the selected organization; `organization_id` is applied on broker lead and conversation repositories.
- A submitted seller inquiry is treated as buyer intent to receive a response through that seller's broker organization. Buyer conversations are only available to authenticated account holders whose `buyer_id` matches; anonymous inquiries remain in the broker pipeline but cannot receive a platform-account message.
- Lead assignment follows listing agent, matching routing rule, least-loaded active agent (stable user ID tie-break), then active manager/owner queue. No routing-rule store exists yet, so the rule-match input remains an empty seam for M9.
- Lead scores use only submitted phone presence, account presence, and inquiry message length, with a deterministic 0–100 score. Spam labels are manual in M5; no opaque classifier is introduced.
- Broker messages are stored as Luxline conversation records with `delivery_status=stored`; no external messaging vendor is called. Replies are available to the authenticated buyer through the new broker buyer-inbox endpoints.
- Create endpoints require `Idempotency-Key`; message, activity, and template persistence uses tenant/actor-scoped unique keys and payload hashes. Message writes share the configured Mongo-backed per-actor rate limiter.
- Lead stage, assignment, spam changes, and notes create activity history. No background job was introduced; inquiry synchronization runs when an authorized broker loads leads.

## M6: Analytics and available event sources

- Build analytics from this organization's `broker_leads`, agent-authored `broker_messages`, and existing phone-reveal records restricted to this organization's `broker_listings`. Materialize source events with unique source keys, then refresh daily rollups idempotently when an authorized report is requested; no analytics worker is added.
- The conversion metric is qualified-or-closed leads divided by all leads created in the selected period. It is a current-stage cohort measure and can change as leads progress. Response-time and per-agent attribution use the lead's current assignment because existing records do not preserve assignment history.
- Agents can only query/export their own assigned lead and response data; managers, owners, and analytics viewers use organization scope.
- Add anonymous, session-deduplicated public listing detail views and visible-card impressions through two flag-guarded broker analytics routes. The approved HomePage hook sends only listing IDs, never buyer identity; impressions require 50% visibility and are counted once per listing per browser session. Public events are accepted only for active, moderation-approved listings with an approved broker profile and are throttled per visitor/listing. CTR is detail views divided by impressions and remains unavailable when a report has no impressions. Existing marketplace endpoint contracts remain unchanged.

---

## M7: Plans, wallet, promotions, and transactions

- Store plans and billing in new `broker_` collections. Admin-configured values are the only source of prices, currencies, listing limits, entitlements, credit packs, and promotion rates; an empty configuration means no broker plan or paid promotion is available.
- Use `BROKER_PAYMENT_PROVIDER=mock` by default. The mock emits deterministic idempotent receipts and makes no external call. Unsupported provider values fail closed rather than silently charging through another provider.
- Keep credit balance adjustments, append-only ledger rows, subscription replacement, and promotion creation inside MongoDB transactions. Never fall back to multiple standalone writes if the database cannot transact.
- The existing Compose Mongo service is standalone and its persistent volume must stay untouched. `docker-compose.broker-replica.yml` is an explicit opt-in overlay with its own volume for local transaction work; it is not started automatically.
- Plan subscriptions and credit pack purchases use stable request keys. Credit debit plus ledger row plus promotion row commit atomically. Future-dated promotions start as `scheduled`; this milestone does not add an activation worker.
- Existing marketplace subscriptions continue to satisfy existing publish checks. A broker plan adds plan limits and entitlements without changing marketplace subscription documents or endpoints.
- The admin plan screen is nested in the current admin portal and guarded by the frontend feature flag; broker owners alone see billing, while owners and managers see promotion tools. API use cases and routes enforce permissions independently.


## Independent property broker account

- Add a separate broker_account signup role, shown only while the broker feature flag is enabled. Keep the existing business_account role and organization-scoped broker_owner/manager/agent/viewer roles distinct.
- Create the broker's existing AgencyProfile as their brokerage organization; it represents their business, not ownership of any listed property. Preserve broker profile approval, region licence checks, and explicit owner consent before publishing.
- Record the seller-agreed commission terms on each broker listing as bounded text. Do not calculate, collect, or distribute money in this milestone.
- Property-broker publish requires a recorded owner name, mandate reference, explicit owner-consent confirmation, and agreed commission terms. The reference records external authorization metadata only; Luxline does not issue mandates or calculate/pay commissions.
