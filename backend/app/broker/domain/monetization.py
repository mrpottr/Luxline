"""Framework-free broker billing and promotion rules."""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json


PROMOTION_SCOPES = {"city", "locality", "province", "country"}
PLACEMENT_TYPES = {"featured", "premium", "urgent"}


def validate_plan(*, code: str, name: str, price_amount: str, currency: str, billing_period_days: int, listing_limit: int | None, entitlements: dict, credit_packs: list[dict], promotion_prices: dict, description: str = "") -> dict:
    if not code.strip() or not name.strip():
        raise ValueError("Plan code and name are required")
    if len(code) > 50 or len(currency) != 3 or not currency.isalpha() or not currency.isupper():
        raise ValueError("Plan code or ISO currency is invalid")
    try:
        price = Decimal(price_amount)
    except (InvalidOperation, TypeError):
        raise ValueError("Plan price must be a decimal amount") from None
    if not price.is_finite() or price < 0:
        raise ValueError("Plan price must be finite and non-negative")
    if billing_period_days < 1 or (listing_limit is not None and listing_limit < 1):
        raise ValueError("Plan duration and listing limit must be positive")
    pack_codes = set()
    for pack in credit_packs:
        pack_code = str(pack.get("code", ""))
        credits = pack.get("credits")
        pack_price = pack.get("price_amount")
        pack_currency = str(pack.get("currency", ""))
        try:
            parsed_price = Decimal(str(pack_price))
        except (InvalidOperation, TypeError):
            raise ValueError("Credit pack price must be a decimal amount") from None
        if (
            not pack_code or pack_code in pack_codes or len(pack_code) > 50
            or type(credits) is not int or credits < 1
            or not parsed_price.is_finite() or parsed_price < 0
            or len(pack_currency) != 3 or not pack_currency.isalpha() or not pack_currency.isupper()
        ):
            raise ValueError("Credit pack details are invalid")
        pack_codes.add(pack_code)
    for scope, placements in promotion_prices.items():
        if scope not in PROMOTION_SCOPES or not isinstance(placements, dict):
            raise ValueError("Promotion price configuration has an invalid scope")
        if set(placements) - PLACEMENT_TYPES:
            raise ValueError("Promotion price configuration has an invalid placement")
        if any(type(amount) is not int or amount < 1 for amount in placements.values()):
            raise ValueError("Promotion prices must be positive credit amounts")
    return {
        "code": code.strip().lower(), "name": name.strip(), "description": description,
        "price_amount": str(price),
        "currency": currency, "billing_period_days": billing_period_days,
        "listing_limit": listing_limit, "entitlements": dict(entitlements),
        "credit_packs": credit_packs, "promotion_prices": promotion_prices,
    }


def calculate_promotion_cost(*, promotion_prices: dict, scope: str, placement_type: str, starts_at: datetime, ends_at: datetime) -> int:
    if scope not in PROMOTION_SCOPES or placement_type not in PLACEMENT_TYPES:
        raise ValueError("Unsupported promotion scope or placement")
    if starts_at.tzinfo is None or ends_at.tzinfo is None:
        raise ValueError("Promotion timestamps must include a timezone")
    if ends_at <= starts_at:
        raise ValueError("Promotion end must be after its start")
    if ends_at <= datetime.now(ends_at.tzinfo):
        raise ValueError("Promotion end must be in the future")
    daily_cost = promotion_prices.get(scope, {}).get(placement_type)
    if not isinstance(daily_cost, int) or daily_cost < 1:
        raise ValueError("This promotion type is not configured for the selected scope")
    duration_seconds = (ends_at - starts_at).total_seconds()
    duration_days = max(1, int((duration_seconds + 86399) // 86400))
    return daily_cost * duration_days


def payload_hash(payload: dict) -> str:
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(normalized.encode("utf-8")).hexdigest()


def has_entitlement(entitlements: dict, name: str) -> bool:
    return entitlements.get(name) is True
