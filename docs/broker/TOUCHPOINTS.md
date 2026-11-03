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
| `backend/.env.example` | Environment schema | M4 | Added optional broker flag, listing price floors/media/import limits, and bulk request limit examples with safe defaults. |

---

## Planned Touchpoints for Milestones M1 - M10

| File | Seam Category | Reason & Planned Additive Change |
| :--- | :--- | :--- |
| None | — | Broker entities remain in `backend/app/broker/models/`; no existing model registry changes are planned. |

### M4 Listing Management

No shared files were changed for listing persistence, routes, schemas, use cases, or screens. Broker listings and revisions use new `broker_` collections. The two frontend seam corrections above close M0 flag-off and role-visibility gaps found during M4 verification. M4 continuation adds listing media metadata and one optional environment example file; existing listing APIs remain unchanged.
