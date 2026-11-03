"""MongoEngine document base used by all Luxline models."""

from datetime import datetime

from mongoengine import Document, SequenceField


class Base(Document):
    """Abstract base document with an integer primary key and update tracking."""

    meta = {"abstract": True, "allow_inheritance": False}

    id = SequenceField(primary_key=True)

    def save(self, *args, **kwargs):
        """Refresh the update timestamp before persisting when the field exists."""
        if "updated_at" in self._fields:
            self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)
