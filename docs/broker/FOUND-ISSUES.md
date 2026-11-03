# Found Issues in Existing Codebase

During the Phase 0 audit of the Luxline codebase, the following existing issues and observations were identified. Per safety rules, these have NOT been modified or fixed.

---

### 1. Ingestion Worker Row-to-Listing ID Assignment
* **Location:** `backend/app/services/ingestion/service.py:44-48`
* **Issue:** When creating a `Listing` during background job processing, `db.add(listing)` is called without an immediate `db.flush()` or save before assigning `row.listing_id = listing.id`. If `listing.id` is not yet populated by the SequenceField generator, `row.listing_id` may be persisted as `None`.
* **Impact:** Imported listings might not link back to their staging `IngestionRow` record.

### 2. Frontend History and Routing Synchronization
* **Location:** `frontend/components/HomePage.jsx:137`
* **Issue:** `HomePage` initializes route state with `useState(parseRoute(window.location.pathname))` rather than using React Router's `useLocation()` / `useNavigate()` hooks (even though `BrowserRouter` is mounted in `frontend/index.jsx`). Internal navigation updates state or uses standard anchor/link behaviors without always syncing React Router context.
* **Impact:** Browser back/forward navigation can occasionally be out of sync with state in some flows.

### 3. Missing Linting and Test Scripts in Frontend
* **Location:** `frontend/package.json`
* **Issue:** `package.json` only defines `"start": "vite"` and `"build": "vite build"`. There is no `test`, `lint`, or `typecheck` script configured in the frontend.
* **Impact:** Frontend code quality checks rely solely on Vite production compilation (`vite build`).

### 4. Direct Host Networking in Monitoring Endpoints
* **Location:** `backend/app/routers/admin.py:131, 143-144`
* **Issue:** `get_monitoring_metrics` and `get_monitoring_health` make direct synchronous HTTP requests to `http://prometheus:9090` and `http://grafana:3000`. When running in local development outside Docker Compose, these throw unhandled exceptions or return error strings if those hostnames are unresolved.
* **Impact:** Admin monitoring tab may report connection errors if not running inside the Docker network.

### 5. Multi-File Configuration Sync
* **Location:** `backend/.env`, `backend/.env.example`, `.env.monitoring`, `backend/app/core/config.py`
* **Issue:** Configuration is loaded from `backend/.env` using `BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`. If the application is launched from the workspace root or if environment variables are set in docker-compose, there are multiple `.env` files (`.env.monitoring` at root and `.env` in `backend/`).
* **Impact:** Potential drift if variables are updated in one location and not the other.

### 6. Legacy Broker Context Grants Owner Role Without Membership
* **Location:** `backend/app/broker/api/dependencies.py:get_broker_context`
* **Issue:** The pre-existing context maps every business account and super admin to `broker_owner`, and falls back to the user ID when no organization profile is found. It does not resolve `broker_members` roles.
* **Impact:** Existing M0–M3 onboarding, team, and branch routes do not enforce the organization membership role model. M4 listing routes use the new listing-specific context in `backend/app/broker/api/listing_dependencies.py`; the legacy context remains to avoid changing existing broker behavior in this continuation.

### 7. No i18n Framework or Locale Catalogs
* **Location:** `frontend/` (repository-wide)
* **Issue:** There is no i18n package/catalog seam. New M4 listing screens still contain English literals, so the broker namespace requirement is not yet met.
* **Impact:** Broker screens, including M4 listing screens, do not yet support Sinhala or Tamil strings through catalogs. This remains an explicit product requirement and needs a broker namespace catalog.

### 8. No Shared Rate-Limiting Middleware
* **Location:** `backend/app/` (repository-wide)
* **Issue:** No shared rate-limiting dependency or middleware was found. M4 bulk requests use a thread-safe in-process sliding window.
* **Impact:** Requests are not coordinated across workers or instances; integrate a shared limiter before production scale-out.


### 9. Binary Media Upload and Scanning Seam Is Missing
* **Location:** `backend/app/` (repository-wide)
* **Issue:** No file storage provider, signed URL service, content sniffing, or virus scanning hook exists. M4 currently accepts HTTPS media references and stores ordering/alt-text metadata only.
* **Impact:** Brokers cannot upload files through the panel yet. A mock-backed storage/scanning seam is required before claiming upload support.

### 10. MongoDB Integration-Test Database Is Not Configured
* **Location:** `tests/` and local runtime
* **Issue:** No default isolated MongoDB test URI or mock MongoDB dependency is configured. An opt-in repository integration test now requires `BROKER_TEST_DATABASE_URL` to name a `broker_test_*` database and was run against a newly created isolated database.
* **Impact:** Migration-style up/down checks remain unavailable because the repository has no migration framework. Never point tests at the configured application database; provide a dedicated disposable database for integration runs.
