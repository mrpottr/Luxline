"""MongoDB-backed limiter shared by broker API workers and instances."""

from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from backend.app.broker.models.bulk_rate_limit import BrokerBulkRateLimit


class MongoBulkRateLimiter:
    def consume(self, key: str, *, maximum: int, window_seconds: int) -> bool:
        try:
            organization_id_text, user_id_text = key.split(":", maxsplit=1)
            organization_id, user_id = int(organization_id_text), int(user_id_text)
        except (AttributeError, ValueError):
            return False
        if maximum < 1 or window_seconds < 1:
            return False

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        window_id = int(now.replace(tzinfo=timezone.utc).timestamp()) // window_seconds
        record_id = f"{organization_id}:{user_id}:{window_id}"
        collection = BrokerBulkRateLimit._get_collection()
        BrokerBulkRateLimit.ensure_indexes()
        updated = collection.find_one_and_update(
            {"_id": record_id, "request_count": {"$lt": maximum}},
            {
                "$inc": {"request_count": 1},
                "$set": {"updated_at": now, "expires_at": now + timedelta(seconds=window_seconds * 2)},
            },
            return_document=ReturnDocument.AFTER,
        )
        if updated:
            return True

        try:
            collection.insert_one({
                "_id": record_id,
                "organization_id": organization_id,
                "user_id": user_id,
                "window_id": window_id,
                "request_count": 1,
                "created_at": now,
                "updated_at": now,
                "expires_at": now + timedelta(seconds=window_seconds * 2),
            })
            return True
        except DuplicateKeyError:
            updated = collection.find_one_and_update(
                {"_id": record_id, "request_count": {"$lt": maximum}},
                {
                    "$inc": {"request_count": 1},
                    "$set": {"updated_at": now, "expires_at": now + timedelta(seconds=window_seconds * 2)},
                },
                return_document=ReturnDocument.AFTER,
            )
            return updated is not None


broker_rate_limiter = MongoBulkRateLimiter()
