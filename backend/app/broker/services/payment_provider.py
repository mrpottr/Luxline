"""Mock broker payment adapter; no external provider calls are made."""

from hashlib import sha256


class MockBrokerPaymentProvider:
    def charge(self, *, organization_id: int, amount: str, currency: str, idempotency_key: str) -> str:
        """Return a stable mock receipt for repeat requests with the same key."""
        material = f"{organization_id}:{amount}:{currency}:{idempotency_key}"
        return f"mock_{sha256(material.encode('utf-8')).hexdigest()[:32]}"
