"""Health and root metadata endpoints."""

from fastapi import APIRouter, Depends

from backend.app.core.config import settings
from backend.app.db.session import Session, get_database, get_db


router = APIRouter(tags=["health"])


@router.get("/")
def root():
    """Return basic API metadata for clients and operational checks."""
    return {"name": settings.app_name, "version": settings.app_version, "environment": settings.app_env}


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """Verify API and database availability with a lightweight DB ping."""
    get_database().command("ping")
    return {"status": "ok"}
