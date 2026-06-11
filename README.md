# Luxline

Luxline is a luxury marketplace platform in active development. The current system already supports luxury listings, user accounts, seller workflows, buyer inquiries, saved searches, admin moderation, and monitoring. The next product direction is to evolve the platform into an AI-assisted real-estate advisory system for luxury villas and mansions.

## Project Vision

Luxline will help buyers evaluate whether a luxury villa or mansion is worth the asking price before they commit to a purchase. A user will be able to describe or submit a property they are considering, then interact with an AI chatbot that reviews the property, compares it against market signals, and explains whether the price appears justified.

If the target property is not worth the price, the system will recommend better villa or mansion options in any country or location. The recommendation flow is planned to combine an advanced AI assistant with n8n automation so the platform can orchestrate property research, valuation checks, lead capture, notifications, and recommendation workflows.

## Current Development State

The current application is a full-stack luxury marketplace prototype with:

- React and Vite frontend for browsing luxury inventory and account workflows.
- FastAPI backend with versioned API routes under `/api/v1`.
- PostgreSQL database models for users, agencies, listings, listing media, inquiries, saved searches, saved listings, subscriptions, blog posts, and audit logs.
- Authentication, registration, email verification, role-based access, and optional two-factor verification flows.
- Buyer features such as listing search, saved assets, saved searches, inquiries, account preferences, and alert preferences.
- Seller and business account features for creating listings and importing listing feeds.
- Admin features for overview metrics, moderation queues, user management, and audit logs.
- Prometheus and Grafana monitoring services configured through Docker Compose.

The frontend already includes an early AI-style entry point through the "Ask from AI..." search box. At the moment, that input routes users into listing discovery. Future development can expand this into a real conversational AI assistant for valuation and personalized recommendations.

## Planned AI Chatbot and n8n Workflow

The planned AI-powered workflow is:

1. A buyer enters property details, a listing URL, or a purchase question through the AI chatbot.
2. The backend stores the user intent and relevant property data.
3. n8n automations collect or normalize supporting data such as location, price, features, comparable properties, currency, seller details, and buyer preferences.
4. The AI system evaluates whether the villa or mansion appears worth the price.
5. The chatbot explains the reasoning in plain language, including strengths, risks, and price concerns.
6. If the property is overpriced or unsuitable, the system recommends better luxury villas or mansions from any country or location that match the buyer's goals.
7. The user can save recommendations, contact sellers, or continue refining the search through the chatbot.

## Tech Stack

- Frontend: React 18, Vite, React Router
- Backend: FastAPI, SQLAlchemy, Pydantic
- Database: PostgreSQL
- Authentication: JWT-based auth with role controls
- Monitoring: Prometheus and Grafana
- Deployment/dev orchestration: Docker Compose
- Planned automation: n8n
- Planned intelligence layer: AI chatbot and property valuation/recommendation logic

## Main Services

When run through Docker Compose, the project includes:

- `frontend`: serves the React application on port `5173`
- `backend`: serves the FastAPI application on port `8000`
- `db`: PostgreSQL database on port `5432`
- `prometheus`: metrics collection on port `9090`
- `grafana`: dashboards on port `3000`

## Local Development

Build and start the main services:

```bash
docker compose up --build -d backend frontend
```

Start the full stack, including monitoring:

```bash
docker compose up --build -d
```

Useful local URLs:

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`

## Development Notes

This repository is currently moving from a broad luxury marketplace toward an AI-first luxury real-estate decision system. Existing marketplace features remain useful because the future chatbot can use listings, saved searches, inquiries, buyer preferences, agencies, and admin moderation as the operational foundation for AI recommendations.
