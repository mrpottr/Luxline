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

---

## Planned Touchpoints for Milestones M1 - M10

| File | Seam Category | Reason & Planned Additive Change |
| :--- | :--- | :--- |
| None | — | Broker entities remain in `backend/app/broker/models/`; no existing model registry changes are planned. |

### M4 Listing Management

No shared files were changed for listing persistence, routes, schemas, use cases, or screens. Broker listings and revisions use new `broker_` collections. The two frontend seam corrections above close M0 flag-off and role-visibility gaps found during M4 verification. M4 continuation adds listing media metadata and one optional environment example file; existing listing APIs remain unchanged.
