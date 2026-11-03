"""Rate-limited public listing-view capture."""

from backend.app.broker.application.analytics_ports import AnalyticsProvider
from backend.app.broker.application.ports import RateLimiter


class ListingViewRateLimitExceeded(Exception):
    """Raised when a visitor exceeds the public listing view capture limit."""


class RecordPublicListingView:
    def __init__(self, provider: AnalyticsProvider, rate_limiter: RateLimiter):
        self.provider = provider
        self.rate_limiter = rate_limiter

    def execute(self, *, listing_id: int, visitor_key: int, event_type: str) -> bool:
        if event_type not in {"listing_view", "listing_impression"}:
            raise ValueError("Unsupported public listing analytics event")
        if not self.provider.is_public_listing_eligible(listing_id):
            return False
        if not self.rate_limiter.consume(
            f"{listing_id}:{visitor_key}", maximum=30, window_seconds=60,
        ):
            raise ListingViewRateLimitExceeded("Listing view tracking rate limit exceeded")
        return self.provider.record_public_listing_event(listing_id, event_type)
