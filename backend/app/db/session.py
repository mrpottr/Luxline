"""Database engine/session configuration and request-scoped session provider."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import settings


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Yield a SQLAlchemy session for request handlers and close it afterward."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
