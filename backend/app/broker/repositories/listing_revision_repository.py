"""Tenant-scoped repository for broker listing revisions."""

from backend.app.broker.models.listing_revision import BrokerListingRevision


class BrokerListingRevisionRepository:
    def __init__(self, organization_id: int):
        self.organization_id = organization_id

    def list_for_listing(self, listing_id: int, limit: int = 50) -> list[BrokerListingRevision]:
        return list(BrokerListingRevision.objects(
            organization_id=self.organization_id,
            listing_id=listing_id,
            is_deleted=False,
        ).order_by("-version").limit(limit))
