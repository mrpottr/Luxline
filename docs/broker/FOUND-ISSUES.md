# Found Issues and Resolution Status

### 1. Ingestion Worker Row-to-Listing ID Assignment — fixed

- **Location:** `backend/app/services/ingestion/service.py`
- **Resolution:** The worker flushes the new listing before assigning its generated ID to the staging row.
- **Verification:** `tests/test_ingestion_worker.py` checks that ordering and the assigned ID.

### 2. Frontend History and Routing Synchronization — fixed

- **Location:** `frontend/components/HomePage.jsx`
- **Resolution:** Page state follows React Router `useLocation()` and navigation uses `useNavigate()`.

### 3. Missing Frontend Quality Scripts — fixed

- **Location:** `frontend/package.json`, `frontend/eslint.config.mjs`
- **Resolution:** Added `npm test` with Node's built-in runner and `npm run lint` with ESLint. No test or lint framework was added beyond the linter itself.
- **Scope:** The frontend is JavaScript-only; a TypeScript typecheck is not applicable. ESLint currently reports pre-existing unused-variable warnings, while syntax and undefined-name errors fail the command.

### 4. Monitoring Service URLs — fixed

- **Location:** `backend/app/routers/admin.py`, `backend/app/core/config.py`, `docker-compose.yml`
- **Resolution:** Prometheus and Grafana internal URLs are configurable. Local defaults use localhost; Compose uses service DNS. Existing response shapes and public dashboard links are preserved.

### 5. Multi-File Configuration Sync — not reproduced

- **Location:** `backend/app/core/config.py`, `backend/.env`, `.env.monitoring`
- **Finding:** The path resolves to `backend/.env`; process environment values take precedence. `.env.monitoring` configures monitoring containers separately. No runtime drift was reproduced, so no fix was needed.

### 6. Legacy Broker Context Role and Tenant Resolution — fixed

- **Location:** `backend/app/broker/api/dependencies.py`
- **Resolution:** Broker routes resolve a real organization and active membership role, honor `X-Broker-Organization-Id`, and reject platform admins from the broker panel.

### 7. Broker i18n Catalogs — fixed

- **Location:** `frontend/components/broker/i18n/`
- **Resolution:** Added an English, Sinhala, and Tamil broker namespace catalog, a locale selector, and a translation boundary used by the broker layout and screens. Untranslated phrases safely fall back to English.

### 8. Shared Rate Limiting — fixed for broker bulk and uploads

- **Location:** `backend/app/broker/services/mongo_bulk_rate_limiter.py`
- **Resolution:** Atomic MongoDB counters in `broker_bulk_rate_limits` are keyed by organization and actor and shared across workers. Bulk actions and media uploads use configured limits.
- **Limit:** Counters use fixed 60-second windows, so requests near a boundary can span adjacent windows.

### 9. Binary Media Upload and Scanning — fixed with mock providers

- **Location:** `backend/app/broker/api/media.py`, `backend/app/broker/application/media_upload_use_cases.py`, `backend/app/broker/services/mongo_media_storage.py`
- **Resolution:** Added 8 MiB upload caps, MIME allow-listing, file-signature sniffing, an injectable scanner interface, organization-scoped Mongo storage, and expiring HMAC signed reads. The default mock scanner detects the EICAR test marker only; production launch needs a real scanner adapter.

### 10. MongoDB Integration and Migration Checks — resolved for this stack

- **Location:** `tests/test_broker_mongo_integration.py`
- **Resolution:** Opt-in integration tests require a `broker_test_*` database and cover tenant isolation, rate limits, and signed media isolation. They were run against a fresh isolated database. MongoEngine creates collections on demand and this repository has no migration framework, so schema migration up/down commands do not apply.
