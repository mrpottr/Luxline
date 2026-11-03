"""MongoDB-backed mock storage with expiring HMAC signed read URLs."""

import hashlib
import hmac
import time
from urllib.parse import urlencode

from backend.app.broker.models.media_asset import BrokerMediaAsset
from backend.app.core.config import settings


class MongoMockMediaStorage:
    SIGNED_URL_TTL_SECONDS = 24 * 60 * 60

    def __init__(self, public_base_url: str):
        self.public_base_url = public_base_url.rstrip("/")

    @staticmethod
    def _signature(asset_id: str, organization_id: int, expires: int) -> str:
        message = f"{asset_id}:{organization_id}:{expires}".encode("utf-8")
        return hmac.new(settings.jwt_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

    def store(self, *, organization_id: int, content: bytes, content_type: str, media_type: str, alt_text: str) -> dict:
        asset = BrokerMediaAsset(
            organization_id=organization_id,
            content=content,
            content_type=content_type,
            media_type=media_type,
            alt_text=alt_text,
            moderation_state="pending",
        ).save()
        expires = int(time.time()) + self.SIGNED_URL_TTL_SECONDS
        token = self._signature(str(asset.id), organization_id, expires)
        url = f"{self.public_base_url}/api/broker/v1/media/{asset.id}?{urlencode({'organization_id': organization_id, 'expires': expires, 'token': token})}"
        return {
            "asset_id": asset.id,
            "organization_id": organization_id,
            "url": url,
            "content_type": content_type,
            "media_type": media_type,
            "alt_text": alt_text,
            "moderation_state": "pending",
            "expires_at": expires,
        }

    def read_signed(self, *, asset_id: int, organization_id: int, expires: int, token: str):
        if expires < int(time.time()):
            return None
        expected = self._signature(str(asset_id), organization_id, expires)
        if not hmac.compare_digest(expected, token):
            return None
        asset = BrokerMediaAsset.objects(
            id=asset_id,
            organization_id=organization_id,
            is_deleted=False,
        ).first()
        return asset
