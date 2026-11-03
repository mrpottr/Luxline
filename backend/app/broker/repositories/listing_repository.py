"""Tenant-scoped broker listing repository."""

from typing import Any

from backend.app.broker.models.listing_extension import BrokerListing
from backend.app.broker.repositories.base_repository import BaseTenantRepository


class BrokerListingRepository(BaseTenantRepository[BrokerListing]):
    def __init__(self, organization_id: int):
        super().__init__(BrokerListing, organization_id)

    def find_listing(self, listing_id: int, assigned_agent_id: int | None = None) -> BrokerListing | None:
        filters = {"listing_id": listing_id}
        if assigned_agent_id is not None:
            filters["assigned_agent_id"] = assigned_agent_id
        return self._scoped_query(**filters).first()

    def find_by_idempotency_key(self, key: str) -> BrokerListing | None:
        return self._scoped_query(include_deleted=True, idempotency_key=key).first()

    def list_filtered(self, *, filters: dict[str, Any], limit: int, offset: int, sort: str) -> list[BrokerListing]:
        allowed_sort = {"created_at", "-created_at", "quality_score", "-quality_score"}
        order_by = sort if sort in allowed_sort else "-created_at"
        filters = dict(filters)
        category = filters.pop("category", None)
        if category:
            from backend.app.models import Listing
            listing_ids = [row.id for row in Listing.objects(agency_id=self.organization_id, category=category)]
            filters["listing_id__in"] = listing_ids
        return list(self._scoped_query(**filters).order_by(order_by).skip(offset).limit(limit))
