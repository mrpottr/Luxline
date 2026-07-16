"""Currency conversion helpers with in-memory caching for FX rates."""

from decimal import Decimal, ROUND_HALF_UP
import time

class LocalizationService:
    _rates_cache: dict[str, float] = {
        "USD": 1.0,
        "EUR": 0.92,
        "GBP": 0.79,
        "CHF": 0.88,
        "AED": 3.67,
    }
    _last_fetched: float = 0

    @classmethod
    def refresh_rates(cls):
        """Simulate fetching from an external provider (e.g. OpenExchangeRates)."""
        # In a real scenario, make an HTTP request here.
        # requests.get("https://api.exchangeratesapi.io/latest?base=USD")
        cls._last_fetched = time.time()
        # For now, just rely on fallback cache.

    @classmethod
    def get_rate(cls, currency_code: str) -> float | None:
        if time.time() - cls._last_fetched > 3600:
            cls.refresh_rates()
        return cls._rates_cache.get(currency_code.upper())

    @classmethod
    def convert_currency(cls, amount: float, from_code: str, to_code: str) -> float:
        """Convert an amount between supported currencies using cached rates."""
        from_rate = cls.get_rate(from_code)
        to_rate = cls.get_rate(to_code)
        if from_rate is None or to_rate is None:
            raise ValueError("Unsupported currency code")

        usd_amount = amount / from_rate
        converted = usd_amount * to_rate
        return float(Decimal(converted).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
