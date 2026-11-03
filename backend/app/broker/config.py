"""Broker-specific optional settings with safe defaults."""

import json
import os
from dataclasses import dataclass
from backend.app.models import ListingCategory


def _price_floors() -> dict[str, dict[str, float]]:
    raw = os.getenv("BROKER_LISTING_PRICE_FLOORS_JSON", "{}")
    try:
        values = json.loads(raw)
        if not isinstance(values, dict):
            return {}
        result: dict[str, dict[str, float]] = {}
        for category, currencies in values.items():
            if not isinstance(currencies, dict):
                continue
            parsed = {str(currency).upper(): float(value) for currency, value in currencies.items() if float(value) >= 0}
            result[str(category).lower()] = parsed
        return result
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _minimum_media_count() -> int:
    try:
        return max(0, int(os.getenv("BROKER_LISTING_MINIMUM_MEDIA_COUNT", "5")))
    except ValueError:
        return 5


def _maximum_bulk_rows() -> int:
    try:
        return min(5000, max(1, int(os.getenv("BROKER_LISTING_BULK_MAX_ROWS", "500"))))
    except ValueError:
        return 500


def _bulk_requests_per_minute() -> int:
    try:
        return min(120, max(1, int(os.getenv("BROKER_BULK_REQUESTS_PER_MINUTE", "10"))))
    except ValueError:
        return 10


def _media_uploads_per_minute() -> int:
    try:
        return min(120, max(1, int(os.getenv("BROKER_MEDIA_UPLOADS_PER_MINUTE", "20"))))
    except ValueError:
        return 20


def _messages_per_minute() -> int:
    try:
        return min(120, max(1, int(os.getenv("BROKER_MESSAGES_PER_MINUTE", "20"))))
    except ValueError:
        return 20


def _payment_provider() -> str:
    configured = os.getenv("BROKER_PAYMENT_PROVIDER", "mock").strip().lower()
    return configured if configured == "mock" else "unsupported"


@dataclass(frozen=True)
class BrokerListingConfig:
    price_floors: dict[str, dict[str, float]]
    minimum_media_count: int
    maximum_bulk_rows: int
    bulk_requests_per_minute: int
    media_uploads_per_minute: int
    messages_per_minute: int
    payment_provider: str
    categories: tuple[str, ...]


listing_config = BrokerListingConfig(
    price_floors=_price_floors(),
    minimum_media_count=_minimum_media_count(),
    maximum_bulk_rows=_maximum_bulk_rows(),
    bulk_requests_per_minute=_bulk_requests_per_minute(),
    media_uploads_per_minute=_media_uploads_per_minute(),
    messages_per_minute=_messages_per_minute(),
    payment_provider=_payment_provider(),
    categories=tuple(category.value for category in ListingCategory),
)
