"""Router package exports for central app registration."""

from backend.app.routers import (
    admin,
    admin_cms,
    admin_fraud,
    admin_taxonomy,
    agencies,
    api_keys,
    auth,
    health,
    ingestion,
    journal,
    leads,
    listings,
    localization,
    monetization,
    search,
    users,
)

__all__ = [
    "admin",
    "admin_cms",
    "admin_fraud",
    "admin_taxonomy",
    "agencies",
    "api_keys",
    "auth",
    "health",
    "ingestion",
    "journal",
    "leads",
    "listings",
    "localization",
    "monetization",
    "search",
    "users",
]
