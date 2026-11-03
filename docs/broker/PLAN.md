# Luxline Broker Panel: Milestone Implementation Plan

**Branch:** `feature/broker-panel`  
**Feature Flag:** `BROKER_PANEL_ENABLED` (Default: `false`)  
**Status:** Approved by continuation request; M0–M3 were already implemented on this branch.

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
* **Goal:** Business application and review lifecycle (draft, submitted, approved, rejected, suspended), admin review integration, and public branded profile view.
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
  * Public profile renders logo, banner, bio, licenses, and verified badges.

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

**Resumption status:** Core listing CRUD, publish checks, assignment scoping, CSV validation/import/export, revision snapshots, media metadata, process-local bulk throttling, docs, and mocked API/use-case tests are implemented. M4 remains active pending binary upload/storage scanning, broker-string i18n, and a shared multi-worker limiter. The opt-in MongoDB tenant-isolation test passed on a newly created, isolated broker_test_* database. No production upload or distributed throttle is claimed.

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
  * Accurate calculation of response times and conversion rates.

---

### Milestone 7: Promotions, Credits Wallet & Plans
* **Goal:** Visibility boosts (featured, premium, urgent tag, geo-targeting), append-only credit ledger with atomic balance checks, and plan entitlement enforcement.
* **New Files to Create:**
  * `backend/app/broker/models/monetization.py` (`broker_promotions`, `broker_credit_ledger`, `broker_plans`)
  * `backend/app/broker/domain/ledger.py` (Atomic credit debit/credit with refund logic)
  * `backend/app/broker/api/promotions.py`
  * `backend/app/broker/api/credits.py`
  * `frontend/components/broker/screens/PromotionsScreen.jsx` (Boost calendar, cost preview)
  * `frontend/components/broker/screens/BillingPlansScreen.jsx` (Ledger statement, plan limits)
  * `tests/test_broker_credits_ledger.py`
* **Shared Files Touched:** None.
* **Success Criteria:**
  * Negative balance prevention via atomic transaction.
  * Clear audit trail of credit spending and promotion expiry.

---

### Milestone 8: Trust, Reviews, Badges & Audit Trail
* **Goal:** Deterministic badge engine (Verified Seller, Responsive Agent, Quality Lister), review collection with replies and dispute handling, anti-manipulation checks, and tenant audit log.
* **New Files to Create:**
  * `backend/app/broker/models/trust.py` (`broker_badges`, `broker_reviews`, `broker_audit_logs`)
  * `backend/app/broker/domain/badges.py` (Rules-based badge awarding with explainability)
  * `backend/app/broker/api/reviews.py`
  * `backend/app/broker/api/audit.py`
  * `frontend/components/broker/screens/ReviewsScreen.jsx`
  * `frontend/components/broker/screens/AuditLogScreen.jsx`
  * `tests/test_broker_trust_badges.py`
* **Shared Files Touched:** None.
* **Success Criteria:**
  * Self-reviews and duplicate reviews blocked.
  * Every badge displays clear justification criteria.

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

