"""Health and root metadata endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.session import get_db


router = APIRouter(tags=["health"])


@router.get("/")
def root():
    """Return basic API metadata for clients and operational checks."""
    return {"name": settings.app_name, "version": settings.app_version, "environment": settings.app_env}


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """Verify API and database availability with a lightweight DB ping."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
