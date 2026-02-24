"""Localization endpoints for currencies, languages, and unit systems."""

from fastapi import APIRouter, Query

from backend.app.services.currency import FALLBACK_RATES, convert_currency


router = APIRouter(prefix="/localization", tags=["localization"])


SUPPORTED_LANGUAGES = ["en", "fr", "es", "de", "it"]
MEASUREMENT_SYSTEMS = ["imperial", "metric"]


@router.get("/currencies")
def currencies():
    """Return the base currency and supported fallback exchange rates."""
    return {"base": "USD", "rates": FALLBACK_RATES}


@router.get("/convert")
def convert(amount: float, from_code: str = Query(alias="from"), to_code: str = Query(alias="to")):
    """Convert an amount between two supported currencies."""
    converted = convert_currency(amount, from_code, to_code)
    return {"amount": amount, "from": from_code.upper(), "to": to_code.upper(), "converted": converted}


@router.get("/languages")
def languages():
    """Return supported interface language codes."""
    return {"languages": SUPPORTED_LANGUAGES}


@router.get("/measurement-systems")
def measurement_systems():
    """Return supported unit systems for UI preferences."""
    return {"systems": MEASUREMENT_SYSTEMS}
