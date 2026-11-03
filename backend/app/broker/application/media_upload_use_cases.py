"""Framework-free validation and orchestration for broker media uploads."""

from typing import Protocol

from backend.app.broker.application.ports import ListingProvider
from backend.app.broker.domain.roles import BrokerPermission


class MediaStorage(Protocol):
    def store(self, *, organization_id: int, content: bytes, content_type: str, media_type: str, alt_text: str) -> dict: ...


class VirusScanner(Protocol):
    def scan(self, content: bytes) -> bool: ...


class UploadRateLimiter(Protocol):
    def consume(self, key: str, *, maximum: int, window_seconds: int) -> bool: ...


class MediaUploadUseCases:
    MAX_BYTES = 8 * 1024 * 1024
    ALLOWED_TYPES = {
        "image/jpeg": ("image", "floor_plan"),
        "image/png": ("image", "floor_plan"),
        "image/webp": ("image", "floor_plan"),
        "application/pdf": ("floor_plan",),
    }
    SIGNATURES = {
        "image/jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
        "image/png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
        "application/pdf": lambda data: data.startswith(b"%PDF-"),
    }

    def __init__(self, storage: MediaStorage, scanner: VirusScanner, listing_provider: ListingProvider, permissions: set, rate_limiter: UploadRateLimiter, uploads_per_minute: int, actor_user_id: int):
        self.storage = storage
        self.scanner = scanner
        self.permissions = permissions
        self.rate_limiter = rate_limiter
        self.uploads_per_minute = uploads_per_minute
        self.actor_user_id = actor_user_id
        self.listing_provider = listing_provider

    def upload(self, *, organization_id: int, content: bytes, content_type: str, media_type: str, alt_text: str) -> dict:
        if BrokerPermission.LISTING_CREATE not in self.permissions:
            raise PermissionError("Missing broker listing create permission")
        if not self.listing_provider.is_broker_approved():
            raise PermissionError("An approved broker profile is required to upload listing media")
        if not self.rate_limiter.consume(
            f"{organization_id}:{self.actor_user_id}",
            maximum=self.uploads_per_minute,
            window_seconds=60,
        ):
            raise TooManyMediaUploads("Broker media upload limit exceeded; retry later")
        if not content or len(content) > self.MAX_BYTES:
            raise ValueError("Media must be between 1 byte and 8 MiB")
        if content_type not in self.ALLOWED_TYPES or media_type not in self.ALLOWED_TYPES[content_type]:
            raise ValueError("Unsupported media type for upload")
        if not self.SIGNATURES[content_type](content):
            raise ValueError("Uploaded content does not match its declared media type")
        if media_type in {"image", "floor_plan"} and not alt_text.strip():
            raise ValueError("Image and floor plan uploads require descriptive alt text")
        if not self.scanner.scan(content):
            raise ValueError("Media failed the configured virus scan")
        return self.storage.store(
            organization_id=organization_id,
            content=content,
            content_type=content_type,
            media_type=media_type,
            alt_text=alt_text.strip(),
        )


class MockVirusScanner:
    """Local mock scan hook. Replace with a production scanner before accepting uploads publicly."""

    def scan(self, content: bytes) -> bool:
        return b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE" not in content


class TooManyMediaUploads(Exception):
    """A broker exceeded the media upload rate limit."""
