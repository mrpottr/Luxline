"""Application factory and router wiring for the Luxline API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.db.base import Base
from backend.app.db.session import engine
from backend.app.routers import admin, agencies, auth, health, leads, listings, localization, monetization, search, users


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance.

    The app configures CORS, ensures tables exist, and registers all versioned routers.
    """
    app = FastAPI(title=settings.app_name, version=settings.app_version)

    origins = [origin.strip() for origin in settings.cors_origins.split(",")] if settings.cors_origins else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    Base.metadata.create_all(bind=engine)

    app.include_router(health.router)

    api_prefix = "/api/v1"
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(users.router, prefix=api_prefix)
    app.include_router(agencies.router, prefix=api_prefix)
    app.include_router(listings.router, prefix=api_prefix)
    app.include_router(search.router, prefix=api_prefix)
    app.include_router(leads.router, prefix=api_prefix)
    app.include_router(monetization.router, prefix=api_prefix)
    app.include_router(localization.router, prefix=api_prefix)
    app.include_router(admin.router, prefix=api_prefix)

    return app


app = create_app()
