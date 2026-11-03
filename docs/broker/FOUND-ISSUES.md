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

