# Luxline Broker Panel: Phase 0 Architecture Audit

**Author:** Senior Staff Engineer  
**Date:** 2026-11-03  
**Status:** Complete  
**Scope:** Read-only inspection of the Luxline codebase prior to designing and implementing the Broker Panel.

---

## 1. Stack, Versions, Folder Layout, Naming Conventions, and Formatting

### Stack & Versions
* **Backend:**
  * Python: 3.13
  * Framework: FastAPI 0.129.0
  * ASGI Server: Uvicorn 0.40.0
  * ODM / Database Client: MongoEngine 0.29.1, PyMongo 4.10.1
  * Auth / Cryptography: PyJWT 2.10.1, Passlib 1.7.4, Bcrypt 4.0.1
  * Validation: Pydantic 2.12.3 (with email validator)
  * Metrics: Prometheus Client 0.20.0
  * HTTP Client: Requests 2.32.3
* **Frontend:**
  * Library: React 18.2.0, React-DOM 18.2.0
  * Router: React Router DOM 6.30.6
  * Bundler: Vite 5.4.21
* **Database & Infrastructure:**
  * Database: MongoDB 7.0 (Docker container `luxline-mongodb`, default port `27017`)
  * Monitoring: Prometheus (`localhost:9090`), Grafana (`localhost:3000`)
  * Containerization: Docker & Docker Compose

### Folder Layout
```text
Luxline/
├── backend/
│   ├── app/
│   │   ├── core/           # Configuration, security, email
│   │   ├── db/             # Base document, MongoEngine connection/session facade
│   │   ├── routers/        # FastAPI endpoint routers (auth, listings, agencies, admin, etc.)
│   │   ├── services/       # Domain and business services (inventory, leads, fraud, search)
│   │   ├── dependencies.py # Auth and role dependency injection
│   │   ├── main.py         # App factory, middleware, router wiring
│   │   ├── models.py       # MongoEngine Document models
│   │   ├── schemas.py      # Pydantic request/response models
│   │   └── utils.py        # String and slug helpers
│   ├── database.py         # Compatibility shim
│   ├── Dockerfile
│   └── main.py             # ASGI entrypoint compatibility shim
├── frontend/
│   ├── components/         # React components (HomePage, AdminDashboard)
│   ├── public/             # Static assets (image directory)
│   ├── index.html
│   ├── index.jsx           # App entrypoint and top-level router
│   ├── nginx.conf
│   └── package.json
├── docs/                   # Architecture and technical documentation
├── grafana/                # Provisioned dashboards and datasources
├── docker-compose.yml
├── prometheus.yml
├── test_endpoints.py       # Integration audit script
└── verify_monitoring.py    # Monitoring health verification
```

### Naming Conventions & Code Style
* **Python:** Follows PEP 8.
  * Snake_case for file names, methods, functions, variables (`admin_moderation.py`, `create_access_token`).
  * PascalCase for classes, MongoEngine documents, Pydantic models (`AgencyProfile`, `ListingOut`).
  * UPPER_CASE for constants and global environment defaults (`DEFAULT_DATABASE`, `PLANS`).
* **JavaScript / React:**
  * CamelCase for helper functions and hooks (`callApi`, `getRoleFromJwt`).
  * PascalCase for React component files and functions (`AdminDashboard.jsx`, `HomePage.jsx`).
  * CSS: BEM-adjacent semantic class names (`.admin-dashboard`, `.admin-btn-primary`, `.luxury-card`).

---

## 2. Authentication & Authorization Architecture

### How Sessions and Tokens Work
* **Mechanism:** Stateless JSON Web Tokens (JWT) signed with HMAC-SHA256 (`PyJWT`).
* **Token Creation:** `backend/app/core/security.py:create_access_token(subject, extra_claims)`.
* **Token Lifetime:** Default 120 minutes (`JWT_EXP_MINUTES`).
* **Subject:** User ID integer string (`sub: str(user.id)`). Extra claims can include `role` and `email`.
* **Storage:** Client-side in `localStorage.getItem('luxline_token')`.
* **Transport:** Standard HTTP Authorization header (`Authorization: Bearer <token>`).

### Roles and Permission Checks
* **User Roles:** Enum `UserRole`:
  * `standard_user` (Buyer)
  * `private_seller` (Individual seller)
  * `business_account` (Verified seller / agency / broker organization)
  * `super_admin` (Platform administrator)
* **Backend Route Guards:**
  * `get_current_user`: Validates token, retrieves active user, raises HTTP 401 if invalid.
  * `get_optional_current_user`: Returns `User | None` without throwing 401 for public or hybrid endpoints.
  * `require_roles(*roles)`: Fast-fails with HTTP 403 Forbidden if `current_user.role not in roles`.
* **Two-Factor & Verification Challenges:**
  * Email OTP verification required on signup (`EmailVerificationChallenge`).
  * 2FA required by default for `business_account` users (`TwoFactorChallenge`).

---

## 3. Existing Roles and Entities

| Entity | Collection | Key Fields | Ownership / Relations |
| :--- | :--- | :--- | :--- |
| **User** | `users` | `id`, `email`, `password_hash`, `role`, `is_active`, `is_verified_business` | Root user entity. Can own agency profiles, listings, subscriptions, searches, inquiries. |
| **AgencyProfile** | `agency_profiles` | `id`, `owner_id`, `name`, `logo_url`, `bio`, `website`, `contact_email`, `address` | 1-to-1 with `User` where `role == business_account`. Enforces `owner_id` uniqueness. |
| **AgencyTeamMember** | `agency_team_members` | `id`, `agency_id`, `agency_owner_id`, `full_name`, `title`, `email`, `phone` | Belongs to `AgencyProfile`. Managed by the agency owner. |
| **Subscription** | `subscriptions` | `id`, `business_user_id`, `plan_code`, `status`, `starts_at`, `ends_at` | Tracks tier and subscription period per business user. |
| **AuditLog** | `audit_logs` | `id`, `actor_user_id`, `event_type`, `details`, `created_at` | Append-only system activity log for compliance and admin oversight. |

### Domain Extension Rules for Broker
* A **Broker Organization** is an existing `AgencyProfile` (or business user organization) with broker capabilities enabled.
* We will **not** duplicate the organization table. We will extend it via relational reference (`broker_profiles.organization_id -> agency_profiles.id`).
* Scoped broker roles (`broker_owner`, `broker_manager`, `broker_agent`, `broker_viewer`) will be mapped through an additive membership collection (`broker_members`).
* Tenant isolation will be enforced strictly in the repository layer using `organization_id`.

---

## 4. Existing Listing, Product Model, Media, and Search

### Listing Model
* Collection `listings` acts as the durable base item:
  * `id` (SequenceField integer primary key)
  * `seller_id` (User ID FK)
  * `agency_id` (AgencyProfile ID FK, optional)
  * `title`, `slug` (unique)
  * `category` (`ListingCategory` enum: `real_estate`, `car`, `hypercar`, `yacht`, `jet`, `watch`, `jewelry`, `rental`)
  * `status` (`ListingStatus` enum: `draft`, `active`, `pending`, `sold`)
  * `moderation_status` (`ModerationStatus` enum: `pending`, `approved`, `rejected`)
  * `price`, `currency`, `location_country`, `location_city`, `latitude`, `longitude`
  * `attributes` (DictField)
* **Vertical Subtypes (Class Table Inheritance / CTI):**
  * `RealEstateListing` (`listing_real_estate`)
  * `VehicleListing` (`listing_vehicle`)
  * `VesselAircraftListing` (`listing_vessel_aircraft`)
  * `WatchJewelryListing` (`listing_watch_jewelry`)
  * `RentalTerms` (`listing_rental_terms`)

### Media Storage
* Collection `listing_media`:
  * `listing_id`, `media_type` (`image`, `video`), `url`, `sort_order`.
  * Public media served from `/image_directory/` or external cloud URLs.

### Search and Filtering
* Implemented in `backend/app/services/search_indexer/service.py`:
  * Full-text filtering via MongoEngine `Q` regex (`icontains`) on `title`, `description`, `location_city`, `location_country`, `make`, `model`.
  * Facet extraction for categories, price bands, condition, year, and location.

---

## 5. Frontend UI, Routing, Styling, and Patterns

* **Routing:** `frontend/index.jsx` sets up a top-level `BrowserRouter` with:
  * `/admin` -> `AdminDashboard`
  * `/*` -> `HomePage` (manages internal pages: `/`, `/listings`, `/agencies`, `/journal`, `/concierge`, `/dashboard`, `/account`, `/listing/:id`).
* **UI Kit & Theming:**
  * Bespoke luxury design system using pure CSS.
  * Palette: Obsidian `#0a0b0d` / `#121418`, Dark Steel `#1a1d24`, Gold accents `#d4af37` / `#c5a059`, Platinum borders `#262930`, Slate text `#9da3af`, Crisp White `#ffffff`.
  * Consistent typography, card elevations, button styles, badges, and modal overlays.
* **API Client Pattern:**
  * Reusable `callApi(path, token, options)` returning parsed JSON or throwing standard `Error` containing `data.detail` and `res.status`.
* **State Management:** React hooks (`useState`, `useEffect`, `useMemo`).
* **i18n:** No i18n package or locale catalogs are present. Existing UI strings are inline English text; locale-aware display is done selectively with `Intl`.

---

## 6. Background Jobs, Email, Payments, and Integrations

* **Background Processing:**
  * `IngestionWorker.process_job_background(job_id)` processes queued imports asynchronously.
  * `OutboxEvent` collection logs state transitions for event-driven patterns.
* **Email / Notifications:**
  * Python `smtplib` and `email.message.EmailMessage` in `backend/app/core/email.py`.
  * In dev mode (`APP_ENV != "production"`), OTP codes are returned directly in response payloads for ease of automated testing and developer experience.
* **Payments & Subscriptions:**
  * Stripe secret key configured via `STRIPE_SECRET_KEY`.
  * Subscription plans (`starter`, `professional`, `elite`, `enterprise`) with credit allocations and limits.
* **Feeds & Integrations:**
  * `BrokerFeed`, `IngestionJob`, `IngestionRow`, and `ListingExternalId` models already exist in the database layer.

---

## 7. Test Setup and Quality Assurance

* **Current Baseline:**
  * Python backend compilation: `python -m compileall backend` passes with exit code 0.
  * Frontend production build: `npm run build --prefix frontend` passes with exit code 0 (Vite build ~3.1s).
  * API integration test script: `test_endpoints.py` covers 35+ routes (health, auth, users, listings, search, agencies, monetization, admin).
* **Test Framework Strategy for Broker Panel:**
  * Because `pytest` is not pre-installed in the virtual environment, tests can run via Python's standard library `unittest` (`python -m unittest discover`) or standalone test runners without requiring foreign package installations.
  * Custom regression tests will verify that existing endpoints and pages remain 100% frozen when `BROKER_PANEL_ENABLED=false`.

---

## 8. Safe Extension Seams & Risk Analysis

### Safe Extension Seams
1. **Feature Flag:** New setting in `backend/app/core/config.py`:
   `broker_panel_enabled: bool = os.getenv("BROKER_PANEL_ENABLED", "false").lower() in {"1", "true", "yes", "on"}`
   Default is strictly `False`.
2. **API Router Seam:** In `backend/app/main.py`:
   Conditionally mount `/api/broker/v1` routes only if `settings.broker_panel_enabled` is active.
3. **Database Seam:** All new MongoEngine models will be prefixed with `broker_` (e.g. `broker_profiles`, `broker_members`, `broker_listings`, etc.) in a dedicated module `backend/app/broker/`. No modifications to existing collections.
4. **Frontend Route Seam:** In `frontend/index.jsx`, conditionally register route `/broker/*` -> `BrokerDashboard` when feature flag is enabled.
5. **Frontend Nav Seam:** Add a Broker Panel entry point in `frontend/components/HomePage.jsx` visible only to authorized broker roles when the feature flag is enabled.

### Risk Analysis & Mitigations
* **Risk 1: Cross-Tenant Data Leakage.**
  * *Mitigation:* Absolute tenant isolation enforced at the repository layer. Every query must take `organization_id` as a mandatory parameter, verified by cross-tenant integration tests.
* **Risk 2: Accidental Mutation of Existing Tables.**
  * *Mitigation:* Strict additive-only design. No alterations to `users`, `listings`, or `agency_profiles` schema. Broker-specific attributes attach through relational pointers.
* **Risk 3: Feature Flag Leakage.**
  * *Mitigation:* With `BROKER_PANEL_ENABLED=false`, all `/api/broker/v1/*` routes return 404/disabled, and no broker UI elements are rendered.

## 9. Resumption Baseline (2026-11-03)

The working branch at resumption was `feature/broker-panel`, with M0–M3 commits present and a partially implemented, uncommitted M4 in the working tree. Baseline results before this continuation:

| Check | Result |
| --- | --- |
| Python `compileall backend` | Pass |
| Full Python `unittest` discovery | Pass, 26 tests |
| Frontend Vite production build | Pass |
| Lint | Not configured in the repository |
| Typecheck | Not configured in the repository |

The frontend has only `start` and `build` npm scripts. Backend dependencies are listed in the root `requirements.txt`; there is no pytest, lint, or typecheck configuration. The M4 worktree build was directed to a temporary output directory so the pre-existing dirty `frontend/dist/index.html` was not changed by verification.

## 10. M4 Resumption Verification

| Check | Result |
| --- | --- |
| Full Python `unittest` discovery | Pass, 42 tests |
| Python `compileall backend tests` | Pass |
| Frontend Vite production build | Pass, 40 modules transformed |
| FastAPI route registration with flag off | No `/api/broker/v1` routes registered |
| FastAPI route registration with flag on | Broker listing routes registered |
| Lint / typecheck | Not available; no scripts/configuration |
| Database migrations / real Mongo integration | No migration framework or Mongo-backed M4 integration tests configured |

The suite includes mocked API/use-case and tenant repository tests. It does not prove cross-tenant isolation against a running MongoDB instance. No commit was made because the repository-required lint, typecheck, and fresh/existing database migration checks cannot currently be run.

