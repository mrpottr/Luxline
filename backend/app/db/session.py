"""MongoDB connection/session configuration and request-scoped session provider."""

import logging

from mongoengine import connect, get_db as mongo_get_db
from pymongo.uri_parser import parse_uri

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_DATABASE = "luxline"
_initialized = False


def _database_name(db_url: str) -> str:
    try:
        parsed = parse_uri(db_url)
        return parsed.get("database") or DEFAULT_DATABASE
    except Exception:
        return DEFAULT_DATABASE


def init_db() -> None:
    """Open the process-wide MongoEngine connection once."""
    global _initialized
    if _initialized:
        return

    db_name = _database_name(settings.database_url)
    connect(db=db_name, host=settings.database_url, alias="default", uuidRepresentation="standard")
    _initialized = True
    logger.info("Connected to MongoDB database %s", db_name)


def ensure_database_exists(db_url: str | None = None) -> None:
    """Connect to MongoDB (databases/collections are created on demand)."""
    init_db()


def get_database():
    """Return the active PyMongo database handle."""
    init_db()
    return mongo_get_db()


class MongoSession:
    """Minimal session facade that persists tracked MongoEngine documents on commit."""

    def __init__(self) -> None:
        self._tracked = []

    def __enter__(self) -> "MongoSession":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def add(self, instance):
        if instance not in self._tracked:
            self._tracked.append(instance)
        return instance

    def add_all(self, instances) -> None:
        for instance in instances:
            self.add(instance)

    def flush(self, *instances) -> None:
        targets = instances or tuple(self._tracked)
        for instance in targets:
            instance.save()

    def commit(self) -> None:
        self.flush()

    def rollback(self) -> None:
        self._tracked.clear()

    def refresh(self, instance):
        instance.reload()
        return instance

    def delete(self, instance) -> None:
        if instance in self._tracked:
            self._tracked.remove(instance)
        instance.delete()

    def execute(self, *args, **kwargs):
        return None

    def close(self) -> None:
        self._tracked.clear()


Session = MongoSession
SessionLocal = MongoSession


def get_db():
    """Yield a Mongo session facade for request handlers and close it afterward."""
    init_db()
    db = MongoSession()
    try:
        yield db
    finally:
        db.close()
