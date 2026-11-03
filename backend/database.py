"""Backward-compatible exports for database base/session objects."""

from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, get_db, get_database, init_db

__all__ = ["Base", "SessionLocal", "get_db", "get_database", "init_db"]
