"""Currency conversion helpers with fallback exchange rates."""

from decimal import Decimal, ROUND_HALF_UP


# Production should pull daily rates from a provider like ECB, OpenExchangeRates, or FXAPI.
FALLBACK_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "CHF": 0.88,
    "AED": 3.67,
}


def convert_currency(amount: float, from_code: str, to_code: str) -> float:
    """Convert an amount between supported currencies using fallback rates."""
    from_rate = FALLBACK_RATES.get(from_code.upper())
    to_rate = FALLBACK_RATES.get(to_code.upper())
    if from_rate is None or to_rate is None:
        raise ValueError("Unsupported currency code")

    usd_amount = amount / from_rate
    converted = usd_amount * to_rate
    return float(Decimal(converted).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
