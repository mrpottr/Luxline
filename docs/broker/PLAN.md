# Luxline Broker Panel: Milestone Implementation Plan

**Branch:** `main`
**Feature Flag:** `BROKER_PANEL_ENABLED` (Default: `false`)  
**Status:** M0 through M7 are implemented. M8 trust, reviews, badges, moderation, and audit integration are implemented on `main`; marketplace ranking integration remains pending. Broker flags remain off by default.

This milestone plan adapts the Broker Panel specification to Luxline's architecture (FastAPI + MongoEngine + React + Vite). Implementation will strictly follow the safety rules: additive-only, frozen existing APIs, absolute tenant isolation, and verification before committing.

---

## Shared Touchpoints Summary

All modifications to existing files are strictly confined to safe seams and logged in `docs/broker/TOUCHPOINTS.md`:

| Shared File | Seam Type | Description of Additive Change |
| :--- | :--- | :--- |
| `backend/app/core/config.py` | Config / Env | Add `broker_panel_enabled: bool = os.getenv("BROKER_PANEL_ENABLED", "false").lower() in {"1", "true", "yes", "on"}` |
| `backend/app/main.py` | Router Registry | Add conditional inclusion: `if settings.broker_panel_enabled: app.include_router(broker_router, prefix="/api/broker/v1")` |
| `frontend/index.jsx` | Route Registry | Conditionally mount `<Route path="/broker/*" element={<BrokerApp />} />` when feature flag is active |
| `frontend/components/HomePage.jsx` | Navigation Seam | Add an additive link "Broker Portal" to `AGENT_NAV_LINKS` visible when user has broker capability and flag is on |
| `backend/app/broker/api/router.py` | Broker route registry | Register flag-guarded trust, review, public review, buyer review, and platform moderation routes. |
| `frontend/components/AdminDashboard.jsx` | Navigation registry | Add a feature-flagged moderation view inside the existing admin portal. |
| `frontend/components/broker/BrokerApp.jsx` | Broker navigation registry | Add owner/manager-only review, badge, and audit screens. |
| `frontend/components/broker/index.jsx` | Broker public module entry | Export only the flag-guarded buyer review and admin moderation screens to app routes. |
| `frontend/index.jsx` | Route registry | Add a buyer review route only when the frontend flag is enabled. |
| `frontend/components/broker/i18n/catalog.mjs` | i18n catalog | Add broker trust navigation labels in English, Sinhala, and Tamil. |

---

## Milestone Breakdown

### Milestone 0: Scaffold & Seams
* **Goal:** Establish feature flag, clean modular directory structure, permission keys, and minimal placeholder routes and navigation.
* **New Files to Create:**
  * `backend/app/broker/__init__.py`
  * `backend/app/broker/config.py` (broker module config, feature flag accessor)
  * `backend/app/broker/domain/` (pure Python domain entities, roles, permission constants)
  * `backend/app/broker/api/__init__.py`
  * `backend/app/broker/api/router.py` (base router for `/api/broker/v1`)
  * `backend/app/broker/api/dependencies.py` (broker tenant and permission guards)
  * `frontend/components/broker/BrokerApp.jsx` (top-level broker layout and router placeholder)
  * `frontend/components/broker/BrokerApp.css` (broker styles using existing design tokens)
  * `tests/test_broker_m0_scaffold.py` (contract tests proving flag OFF = 0 changes, flag ON = scaffold active)
* **Shared Files Touched:**
  * `backend/app/core/config.py`
  * `backend/app/main.py`
  * `frontend/index.jsx`
* **Success Criteria:**
  * Flag OFF: Application is 100% indistinguishable from baseline; `/api/broker/v1` returns 404; `/broker` routes render standard 404 or redirect.
  * Flag ON: `/api/broker/v1/health` returns status ok; `/broker` displays placeholder shell with brand styling.

---

### Milestone 1: Data Foundation & Tenant Isolation
* **Goal:** Create the core additive database models (prefixed with `broker_`), base repository pattern with automatic tenant filtering, database seeds, and cross-tenant isolation tests.
* **New Files to Create:**
  * `backend/app/broker/models/`
    * `base.py` (Base broker document enforcing `organization_id`, timestamps, soft-delete)
    * `profile.py` (`broker_profiles` extending `agency_profiles`)
    * `member.py` (`broker_members` mapping users to broker roles)
    * `branch.py` (`broker_branches`)
  * `backend/app/broker/repositories/`
    * `base_repository.py` (Enforces `organization_id` on all read/write queries)
    * `profile_repository.py`
    * `member_repository.py`
  * `backend/app/broker/scripts/seed_demo_broker.py` (Creates demo broker tenant, agents, and sample state)
  * `tests/test_broker_tenant_isolation.py` (Proves Broker A cannot view, modify, or leak Broker B records)
* **Shared Files Touched:** None.
* **Success Criteria:**
  * All collections prefixed `broker_`.
  * Zero cross-tenant data leakage in automated tests.
  * Demo seed script creates a functional organization without side effects on standard users.

---

### Milestone 2: Onboarding & Branded Public Profile
* **Goal:** Business application and review lifecycle (draft, submitted, approved, rejected, suspended), admin review integration, and public branded profile view. The signup flow includes a separate `broker_account` persona when the broker feature flag is on. A property broker represents owners and does not claim property ownership; their account owns an existing AgencyProfile that serves as the brokerage organization.
* **New Files to Create:**
  * `backend/app/broker/domain/onboarding.py` (Verification state machine and rules)
  * `backend/app/broker/api/onboarding.py` (Apply, submit documents, check status)
  * `backend/app/broker/api/public_profile.py` (Public read-only profile by slug/ID)
  * `frontend/components/broker/screens/OnboardingScreen.jsx`
  * `frontend/components/broker/screens/PublicProfileEditor.jsx`
  * `frontend/components/broker/screens/PublicBrokerProfile.jsx` (Customer-facing showcase)
  * `tests/test_broker_onboarding.py`
* **Shared Files Touched:** None.
* **Success Criteria:**
  * Unapproved business accounts cannot access operational tools.
  * Property brokers can register only while the broker flag is enabled, complete 2FA, and submit broker profile/licence details for review.
  * Broker listings require the owner's name, a mandate reference, explicit consent, and recorded commission terms before publishing; commission terms are records only and no money is calculated or transferred.
  * Public profile renders logo, banner, bio, licenses, and verified badges.
* **Additional Files Touched:** `backend/app/models.py`, `backend/app/routers/auth.py`, `backend/app/routers/admin.py`, `backend/app/broker/application/access_use_cases.py`, `backend/app/broker/models/listing_extension.py`, `backend/app/broker/schemas.py`, `backend/app/broker/services/listing_provider.py`, `backend/app/broker/domain/listing_rules.py`, `backend/app/broker/application/listing_use_cases.py`, `backend/app/broker/api/listings.py`, `frontend/components/HomePage.jsx`, `frontend/components/AdminDashboard.jsx`, `frontend/components/broker/featureFlag.mjs`, `frontend/components/broker/BrokerApp.jsx`, `frontend/components/broker/screens/ListingEditorScreen.jsx`, `frontend/components/broker/i18n/catalog.mjs`, `frontend/Dockerfile`, `docker-compose.yml`, `tests/test_broker_m0_scaffold.py`, `frontend/tests/brokerFeatureFlag.test.mjs`, `tests/test_broker_listings.py`, and `docs/broker/{API,DECISIONS,TOUCHPOINTS}.md`.

**Property broker account extension verification:** Frontend tests: 3 passed; lint: 0 errors and 21 existing warnings; Vite production build passed; Python compileall passed; `docker compose config -q` passed with Docker config access warnings. Backend pytest could not run because pytest is absent from the available local Python environment. New listing fields are optional nullable fields on the additive `broker_listings` collection; no existing listing or user records were migrated. No database writes were made.

---

### Milestone 3: Team, Branches, Roles & Permissions
* **Goal:** Manage team members (`broker_owner`, `broker_manager`, `broker_agent`, `broker_viewer`), invitation flows, branches, and fine-grained permission enforcement.
* **New Files to Create:**
  * `backend/app/broker/domain/permissions.py` (Role-to-permission mapping)
  * `backend/app/broker/api/team.py` (CRUD members, assign roles, invitation codes)
  * `backend/app/broker/api/branches.py` (Branch offices and locations)
  * `frontend/components/broker/screens/TeamScreen.jsx`
  * `frontend/components/broker/screens/BranchesScreen.jsx`
  * `tests/test_broker_team_permissions.py`
* **Shared Files Touched:** None.
* **Success Criteria:**
  * Owner has full access; Manager can manage listings/leads; Agent is restricted to own listings/leads; Viewer has read-only analytics.

---

### Milestone 4: Listings Management, Quality Score & Bulk Import
* **Goal:** Broker inventory management (CRUD, publish, pause, archive, revisions), category rules, configurable price floors, rich media ordering, listing quality scoring, and CSV bulk import/export.
* **New Files to Create:**
  * `backend/app/broker/application/ports.py` and `application/listing_use_cases.py` (provider boundary and permission-checked operations)
  * `backend/app/broker/application/access_use_cases.py` (organization membership resolution)
  * `backend/app/broker/api/listing_dependencies.py` (JWT-backed listing context)
  * `backend/app/broker/config.py` (price floors and media/import limits from optional environment config)
  * `backend/app/broker/models/listing_extension.py` (`broker_listings` linking to base `listings`)
  * `backend/app/broker/models/listing_revision.py` (`broker_listing_revisions`)
  * `backend/app/broker/domain/quality_score.py` (Algorithmic quality score: Green/Orange/Red with fix suggestions)
  * `backend/app/broker/domain/listing_rules.py` (Minimum price validation, media count rules)
  * `backend/app/broker/repositories/listing_repository.py` and `listing_revision_repository.py` (tenant-scoped listing and revision access)
  * `backend/app/broker/repositories/organization_access_repository.py` (tenant membership lookup)
  * `backend/app/broker/services/bulk_import.py` and `services/listing_provider.py` (CSV validation/import and Mongo adapter)
  * `backend/app/broker/api/listings.py`
  * `frontend/components/broker/screens/ListingsListScreen.jsx` (Table & cards, filters, bulk actions)
  * `frontend/components/broker/screens/ListingEditorScreen.jsx` (Multi-step editor, quality score widget)
  * `frontend/components/broker/screens/BulkImportScreen.jsx`
  * `tests/test_broker_listings.py`
  * `docs/broker/API.md` and `docs/broker/DECISIONS.md`
* **Shared Files Touched:** `frontend/index.jsx` (conditional route registry, flag-off behavior); `frontend/components/HomePage.jsx` (role-gated navigation). These M0 seam corrections were identified while verifying M4.
* **Success Criteria:**
  * Quality score updates dynamically.
  * Bulk import provides a validation dry-run before persistence.
  * Base listings remain compatible with existing public search.

**Resumption status:** Listing CRUD, publish checks, assignment scoping, CSV import/export, revision snapshots, media metadata and upload, MongoDB-backed bulk/upload throttling, broker namespace catalogs, docs, and API/use-case tests are implemented. Upload scanning and storage currently use the configured mock adapters. The opt-in MongoDB tenant, rate-limit, and signed-media tests passed against a newly created isolated broker_test_* database.

---

### Milestone 5: Leads, Routing & Direct Inbox
* **Goal:** Lead capture, automated agent assignment, lead pipeline stages (new, contacted, qualified, lost, closed), CRM notes/tasks, threaded inbox with reply templates, and spam controls.
* **New Files to Create:**
  * `backend/app/broker/models/lead.py` (`broker_leads`, `broker_activities`, `broker_messages`, `broker_templates`)
  * `backend/app/broker/domain/lead_routing.py` (Assignment order: listing agent -> rules -> round-robin -> manager)
  * `backend/app/broker/api/leads.py`
  * `backend/app/broker/api/inbox.py`
  * `frontend/components/broker/screens/LeadsKanbanScreen.jsx` (Kanban & list views)
  * `frontend/components/broker/screens/InboxScreen.jsx` (Threads, quick replies, templates)
  * `tests/test_broker_leads_inbox.py`
* **Shared Files Touched:** None.
* **Success Criteria:**
  * Real-time lead creation from public inquiries.
  * Direct communication thread between assigned agent and buyer.

---

**Completion status:** Existing seller-directed inquiries are imported idempotently into tenant-owned lead records when broker lead/inbox views load; no existing inquiry endpoint or response schema was changed. Leads support pipeline stages, explainable rule-based scoring, assignment priority, spam flags, activities, reply templates, and consent-linked authenticated buyer conversations. The lead list refresh is the synchronization trigger; no background poller is introduced. Anonymous inquiries remain visible to their broker team as submitted, but direct platform conversations require a buyer account so replies have an authenticated recipient.

### Milestone 6: Dashboard, Performance & Analytics
* **Goal:** Business overview dashboard, key metrics (views, leads, CTR, first-response time), per-listing and per-agent analytics, and CSV exports.
* **New Files to Create:**
  * `backend/app/broker/models/analytics.py` (`broker_analytics_events`, daily rollups)
  * `backend/app/broker/services/analytics_service.py` (Rollup calculator, metrics aggregator)
  * `backend/app/broker/api/analytics.py`
  * `frontend/components/broker/screens/DashboardOverviewScreen.jsx`
  * `frontend/components/broker/screens/AnalyticsScreen.jsx` (Charts, time range picker, export)
  * `tests/test_broker_analytics.py`
* **Shared Files Touched:** None.
* **Success Criteria:**
  * Responsive metrics cards and trend charts matching the dark luxury aesthetic.
  * Accurate calculation of available lead, phone-reveal, response-time, and conversion metrics.
  * Listing-view and CTR metrics use additive detail-view and visible-impression events; existing marketplace API contracts remain unchanged.

**Completion status:** Dashboard and date-range analytics report tenant-scoped leads, replies, phone reveals, response times, listing views, impressions, CTR, per-listing/per-agent breakdowns, deterministic daily rollups, and CSV exports. Agents are restricted to their own metrics. Public engagement events are anonymous, session-deduplicated in the browser, rate-limited, and accepted only for live, moderation-approved listings owned by approved broker organizations. CTR is null until eligible impressions exist.

---

### Milestone 7: Promotions, Credits Wallet & Plans
* **Goal:** Visibility boosts (featured, premium, urgent tag, geo-targeting), append-only credit ledger with atomic balance checks, and plan entitlement enforcement.
* **New Files to Create:**
  * `backend/app/broker/models/monetization.py` (`broker_plans`, `broker_subscriptions`, `broker_credit_accounts`, `broker_credit_ledger`, `broker_promotions`)
  * `backend/app/broker/domain/monetization.py` (Price validation, configured promotion cost and idempotency digest)
  * `backend/app/broker/application/monetization_use_cases.py` and `monetization_ports.py`
  * `backend/app/broker/repositories/monetization_repository.py` (Tenant repositories and Mongo transaction boundary)
  * `backend/app/broker/api/monetization.py` and `admin_monetization.py`
  * `backend/app/broker/services/payment_provider.py` (Deterministic offline payment mock)
  * `docker-compose.broker-replica.yml` (Opt-in isolated replica set for Mongo transactions)
  * `frontend/components/broker/screens/PromotionsScreen.jsx` (Boost calendar, cost preview)
  * `frontend/components/broker/screens/BillingPlansScreen.jsx` (Ledger statement, plan limits)
  * `frontend/components/broker/BrokerPlanAdminScreen.jsx` and `frontend/components/broker/index.jsx`
  * `tests/test_broker_monetization.py`
* **Shared Files Touched:** `backend/app/broker/api/router.py`, `backend/.env.example`, `frontend/index.jsx`, `frontend/components/HomePage.jsx`, `frontend/components/AdminDashboard.jsx`.
* **Success Criteria:**
  * Negative balance prevention via atomic transaction.
  * Clear append-only audit trail of credit movements.

**Completion status:** Plans and entitlements are managed in the existing super-admin portal. Broker owners can subscribe and purchase configured credit packs using the deterministic mock provider. Promotion estimates use configured geography, placement, and duration prices; promotion creation atomically debits the tenant wallet, appends a ledger row, and creates a scheduled or active promotion. Multi-document operations require the opt-in broker replica-set Compose overlay. Existing marketplace subscriptions remain valid and their APIs are unchanged. The scheduled promotion activation/expiry worker and marketplace ranking integration are deferred; this milestone does not claim that a paid boost has changed search ranking.

**Verification:** Backend suite: 101 passed, 5 skipped (isolated Mongo integration URL not configured). Frontend suite: 3 passed. Frontend lint: 0 errors, 21 existing warnings. Production builds passed with `VITE_BROKER_PANEL_ENABLED` both false and true. Compose overlay configuration and Python syntax checks passed. No typecheck script or Mongo migration framework exists in this repository; no database was started or modified.

---

### Milestone 8: Trust, Reviews, Badges & Audit Trail
* **Goal:** Deterministic badge engine (Verified Seller, Responsive Agent, Quality Lister), review collection with replies and dispute handling, anti-manipulation checks, and tenant audit log.
* **New Files Created:**
  * `backend/app/broker/models/trust.py` (`broker_badges`, `broker_reviews`, `broker_moderation_cases`, `broker_audit_logs`)
  * `backend/app/broker/domain/trust.py` (review validation and deterministic, explainable, versioned badge rules)
  * `backend/app/broker/application/trust_ports.py` and `trust_use_cases.py`
  * `backend/app/broker/api/trust.py` and `trust_dependencies.py`
  * `backend/app/broker/repositories/trust_repository.py`
  * `frontend/components/broker/screens/ReviewsScreen.jsx`, `AuditLogScreen.jsx`, `BuyerReviewScreen.jsx`, and `TrustModerationAdminScreen.jsx`
  * `tests/test_broker_trust.py`
* **Broker feature files extended:** `backend/app/broker/api/onboarding.py`, `api/team.py`, `api/analytics.py`, `api/dependencies.py`, `application/monetization_ports.py`, `application/monetization_use_cases.py`, and `repositories/monetization_repository.py` add approval, role, export, credit, subscription, and promotion audit data.
* **Shared Files Touched:** `backend/app/broker/api/router.py`, `frontend/components/AdminDashboard.jsx`, `frontend/components/broker/BrokerApp.jsx`, `frontend/components/broker/index.jsx`, `frontend/components/broker/i18n/catalog.mjs`, `frontend/index.jsx`.
* **Success Criteria:**
  * Self-reviews and duplicate reviews blocked.
  * Every badge displays clear justification criteria.

**Safety decisions:** Buyer reviews require the authenticated owner of a closed, consented broker lead; one review per buyer/listing is enforced by a unique index and repository check. Reviews are pending moderation and only explicitly consented, published reviews are public. Integrity violations open platform moderation cases. Badge rules use fixed version 1 thresholds and persist criteria snapshots/explanations. Broker repositories always require an organization ID; the platform-admin moderation use case is super-admin gated and performs global moderation only through its dedicated methods. The user-facing review response schema omits buyer identifiers.

**Limitations:** Existing organization approval and team changes append audit after their existing write, so those multi-collection operations are not atomic. Credit, subscription, and promotion audit inserts share their existing Mongo transaction. Badge refresh is request-driven; no worker was added. Review moderation is visible in the admin portal. Repository/database integration and replica-set transaction tests require `BROKER_TEST_DATABASE_URL` and remain skipped when it is unset.

---

### Milestone 9: Growth, Automation, Valuation & Syndication
* **Goal:** CRM follow-up rules, automated valuation requests and reports, outbound syndication feeds (JSON/XML), hashed API keys, and webhooks with HMAC signatures.
* **New Files to Create:**
  * `backend/app/broker/models/integrations.py` (`broker_api_keys`, `broker_webhooks`, `broker_feeds`, `broker_valuations`)
  * `backend/app/broker/services/feed_syndication.py` (Generates JSON/XML feeds)
  * `backend/app/broker/services/webhook_dispatcher.py` (HMAC signatures and retry queue)
  * `backend/app/broker/api/valuation.py`
  * `backend/app/broker/api/integrations.py`
  * `frontend/components/broker/screens/ValuationScreen.jsx`
  * `frontend/components/broker/screens/IntegrationsScreen.jsx`
  * `tests/test_broker_integrations.py`
* **Shared Files Touched:** None.
* **Success Criteria:**
  * API keys generated once and stored only as hashes.
  * Webhook payloads signed with HMAC-SHA256.

---

### Milestone 10: Provider Seams, Mocks, Hardening & Final Documentation
* **Goal:** Clean pluggable provider interfaces (Messaging, Storage, AI, Telephony, CRM) with complete mock adapters for local and offline execution; accessibility (a11y) pass, performance audit, and complete documentation in `docs/broker/API.md`.
* **New Files to Create:**
  * `backend/app/broker/providers/` (Interface definitions and mock implementations for AI, WhatsApp, Cloud Storage, CRM)
  * `docs/broker/API.md` (Full API reference for `/api/broker/v1/*`)
  * `tests/test_broker_regression_complete.py` (Full regression pass with flag OFF and flag ON)
* **Shared Files Touched:** `docs/broker/TOUCHPOINTS.md`
* **Success Criteria:**
  * Entire suite runs offline using mock providers.
  * All new endpoints documented.
  * Regression tests confirm 0 breakage in existing marketplace and admin functionalities.

---

## Working Protocol Reminder
1. Phase 0 concludes upon user approval of this `PLAN.md`.
2. Each milestone will be preceded by a list of files to be created and touched.
3. Every milestone will conclude with automated tests, `TOUCHPOINTS.md` updates, and a concise status report.



**Completion status:** M8 trust models and routes are implemented behind the existing broker flag, including authenticated buyer review submission, tenant reviews/replies/appeals, public consented reviews, versioned explainable badges, platform moderation cases, and audit entries. Member and verification decisions plus analytics exports now add audit events; M7 money and promotion audit events are included in their Mongo transactions. UI screens are exposed only through the feature flag and existing admin portal. Marketplace/public-profile page review loading is best-effort so a trust endpoint outage does not block the profile.

**Verification:** Frontend tests: 3 passed; lint: 0 errors and 21 existing warnings; Vite builds passed with `VITE_BROKER_PANEL_ENABLED` false and true; Python compileall, Compose config, and `git diff --check` passed. Backend unit tests could not run because FastAPI and project dependencies are absent from local Python environments (`No module named fastapi`); full-suite regression remains unverified in this environment. No typecheck script or migration framework exists. No Mongo instance was started or changed. Audit writes after existing profile/team writes remain non-atomic.
