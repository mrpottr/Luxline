# Broker Panel - Shared Code Touchpoints Log

Per rule: "You may touch shared code only at: route registry, navigation registry, permission or role registry (additive values only), environment schema (new optional variables with safe defaults), migration folder (new files only), event bus (new subscribers only), i18n catalogs (new broker namespace). If a seam doesn’t exist, create the smallest possible one. Log every shared file you edit in docs/broker/TOUCHPOINTS.md with the reason and what changed."

---

## Logged Touchpoints

| File | Seam Category | Milestone | Reason & What Changed |
| :--- | :--- | :--- | :--- |
| `backend/app/core/config.py` | Environment schema | M0 | Added optional `broker_panel_enabled: bool = os.getenv("BROKER_PANEL_ENABLED", "false").lower() in {"1", "true", "yes", "on"}` (Default: `false`). |
| `backend/app/main.py` | Route registry | M0 | Conditionally included broker base router: `if getattr(settings, "broker_panel_enabled", False): from backend.app.broker.api import broker_router; app.include_router(broker_router, prefix="/api/broker/v1")`. |
| `frontend/index.jsx` | Route registry | M0 | Registered `<Route path="/broker/*" element={<BrokerApp />} />`. `BrokerApp` checks `VITE_BROKER_PANEL_ENABLED` and displays offline fallback if disabled. |
| `frontend/components/HomePage.jsx` | Navigation registry | M0 | Additive spread into `AGENT_NAV_LINKS`: added `{ path: '/broker', label: 'Broker Portal' }` conditionally if `VITE_BROKER_PANEL_ENABLED === 'true'`. Empty otherwise. |
| `frontend/index.jsx` | Route registry | M4 seam correction | Mount `/broker/*` only when `VITE_BROKER_PANEL_ENABLED === 'true'`, so the off state has no broker route. |
| `frontend/components/HomePage.jsx` | Navigation registry | M4 seam correction | Show Broker Portal only when the flag is on and the JWT role is `business_account`. |
| `frontend/components/HomePage.jsx` | Route/navigation registry | Found issue 2 | Derive page state from React Router location and navigate through the router so browser history stays synchronized. |
| `backend/.env.example` | Environment schema | M4 | Added optional broker flag, listing price floors/media/import limits, rate limits, and mock upload provider settings with safe defaults. |
| `backend/app/core/config.py` | Environment schema | Found issue 4 | Added optional monitoring service base URLs with localhost defaults. |
| `docker-compose.yml` | Environment schema | Found issue 4 | Configured the backend container to use Prometheus/Grafana service DNS defaults while allowing explicit environment overrides. |
| `backend/app/routers/admin.py` | Admin integration | Found issue 4 | Monitoring requests now use configured internal service URLs; response fields and status behavior are unchanged. |
| `frontend/package.json` | Developer tooling | Found issue 3 | Added Node test and ESLint scripts; ESLint is a development dependency. |
| `frontend/package-lock.json` | Developer tooling | Found issue 3 | Locked the ESLint development dependency. |
| `backend/app/services/ingestion/service.py` | Existing worker correctness | Found issue 1 | Flush the newly added listing before assigning its generated ID to the ingestion row. |
| `backend/app/broker/api/dependencies.py` | Broker authorization context | Found issue 6 | Resolve organization membership and assigned broker role through the application access use case. |
| `backend/app/broker/api/router.py` | Route registry | Found issue 9 | Mounted broker media upload and signed-read routes under the feature-flagged broker router. |
| `frontend/components/broker/i18n/catalog.mjs` | i18n catalog | Found issue 7 | Added the broker namespace catalog for English, Sinhala, and Tamil with safe English fallback. |
| `frontend/components/broker/i18n/withBrokerTranslations.jsx` | Broker UI seam | Found issue 7 | Routed broker screen text and accessible text attributes through the broker catalog. |
| `frontend/eslint.config.mjs` | Developer tooling | Found issue 3 | Added focused lint checks for the frontend entry point, HomePage, and broker components. |
| `backend/app/broker/api/router.py` | Broker route registry | M5 | Registered tenant-scoped broker leads, inbox, and authenticated buyer conversation endpoints under the existing flag-guarded `/api/broker/v1` router. |
| `backend/app/broker/config.py` | Broker optional config | M5 | Added configurable `BROKER_MESSAGES_PER_MINUTE` with a safe bounded default for messaging throttling. |
| `backend/.env.example` | Environment schema | M5 | Documented the optional broker messaging rate limit setting. |
| `backend/app/broker/api/router.py` | Broker route registry | M6 | Registered analytics summary, CSV, public listing view, and public impression routes under the existing feature-flagged broker API. |
| `frontend/components/HomePage.jsx` | Approved public listing tracking hook | M6 | When `VITE_BROKER_PANEL_ENABLED=true`, count session-deduplicated impressions after 50% of a live listing card is visible and detail views after an eligible listing opens; failures are best-effort and the flag-off path sends no tracking requests. |

---

## Planned Touchpoints for Milestones M1 - M10

| File | Seam Category | Reason & Planned Additive Change |
| :--- | :--- | :--- |
| None | — | Broker entities remain in `backend/app/broker/models/`; no existing model registry changes are planned. |

### M4 Listing Management

No shared files were changed for listing persistence, routes, schemas, use cases, or screens. Broker listings and revisions use new `broker_` collections. The two frontend seam corrections above close M0 flag-off and role-visibility gaps found during M4 verification. M4 continuation adds listing media metadata and one optional environment example file; existing listing APIs remain unchanged.

### M5 Leads and Inbox

The only shared route seam change is broker-router registration. The existing `/api/v1/leads/.../inquire` endpoint and its schemas remain unchanged. Broker lead sync reads inquiries attached to the organization's own listing extensions and materializes them in new `broker_` collections. Buyer reads and replies require authentication, the selected organization, matching buyer ownership, and the original seller-contact intent. No background job is added; synchronization occurs when the broker lead list is requested.

### M6 Dashboard and Analytics

The broker route registry is the only backend route seam changed. Analytics events are derived from organization-scoped broker leads/messages, phone-reveal records, and new anonymous view/impression events for this broker's listings, then materialized in new broker collections with daily rollups. The approved `HomePage.jsx` hook sends tracking only while the frontend flag is on; existing marketplace listing APIs and response shapes are untouched. CTR is detail views divided by visible-card impressions and is null without impressions.
### M7 Shared seam additions

| File | Seam Category | Milestone | Reason & What Changed |
| :--- | :--- | :--- | :--- |
| `backend/app/broker/api/router.py` | Broker route registry | M7 | Added broker plans, billing, credits, promotions, and platform-admin plan routes under the existing flag guard. |
| `backend/.env.example` | Environment schema | M7 | Documented `BROKER_PAYMENT_PROVIDER=mock` as an optional safe-default provider and removed its duplicate example entry. |
| `frontend/index.jsx` | Route registry | M7 | Routed broker imports through the public broker module entry point; route is still absent while the flag is off. |
| `frontend/components/HomePage.jsx` | Navigation registry | M7 | Imported the broker navigation predicate through the public module entry point without changing its flag and role behavior. |
| `frontend/components/AdminDashboard.jsx` | Navigation registry | M7 | Added a broker plan editor tab only when the frontend feature flag is enabled, inside the existing super-admin portal. |

### M8 Shared seam additions

| File | Seam Category | Milestone | Reason & What Changed |
| :--- | :--- | :--- | :--- |
| `backend/app/broker/api/router.py` | Broker route registry | M8 | Registered broker, authenticated buyer, public profile review, and platform moderation routes under the existing backend flag guard. |
| `frontend/components/AdminDashboard.jsx` | Navigation registry | M8 | Added a broker trust moderation tab within the existing admin portal, visible only with the frontend flag. |
| `frontend/components/broker/BrokerApp.jsx` | Broker navigation registry | M8 | Added reviews/badges and audit navigation for owners and managers; use-cases enforce permissions independently. |
| `frontend/components/broker/index.jsx` | Broker public module entry | M8 | Exported buyer review and admin trust screens for route/admin wiring through the feature module entry point. |
| `frontend/index.jsx` | Route registry | M8 | Added `/buyer/reviews` only when the existing broker frontend flag is enabled. |
| `frontend/components/broker/i18n/catalog.mjs` | i18n catalog | M8 | Added trust navigation labels to the English, Sinhala, and Tamil broker catalogs. |
