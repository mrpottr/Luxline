"""Broker listing application use cases."""

from typing import Any
import csv
import hashlib
import io

from backend.app.broker.application.ports import ListingProvider, RateLimiter
from backend.app.broker.domain.listing_rules import ListingRules
from backend.app.broker.services.bulk_import import BulkImportService


class ListingUseCases:
    """Application boundary for listing actions and permission enforcement."""

    def __init__(
        self,
        provider: ListingProvider,
        permissions: set[Any],
        config: Any,
        role: Any,
        actor_user_id: int,
        rate_limiter: RateLimiter | None = None,
        organization_id: int | None = None,
        require_commission_terms: bool = False,
    ):
        self.provider = provider
        self.permissions = permissions
        self.config = config
        self.role = role
        self.actor_user_id = actor_user_id
        self.rate_limiter = rate_limiter
        self.organization_id = organization_id
        self.require_commission_terms = require_commission_terms

    def _require(self, permission: Any) -> None:
        if permission not in self.permissions:
            raise PermissionError("Missing required broker permission")

    def _require_operational(self) -> None:
        if not self.provider.is_broker_approved():
            raise PermissionError("An approved broker profile is required to use listing operations")

    def list_listings(self, *, permission: Any, filters: dict[str, Any], limit: int, offset: int, sort: str):
        self._require(permission)
        self._require_operational()
        if filters.get("category") and filters["category"] not in self.config.categories:
            raise ValueError("Unsupported listing category")
        if filters.get("quality_rating") and filters["quality_rating"] not in {"green", "orange", "red"}:
            raise ValueError("Unsupported quality rating")
        if sort not in {"created_at", "-created_at", "quality_score", "-quality_score"}:
            raise ValueError("Unsupported listing sort")
        if self.role.value == "broker_agent":
            filters = {**filters, "assigned_agent_id": self.actor_user_id}
        return self.provider.list_listings(filters=filters, limit=limit, offset=offset, sort=sort)

    def list_categories(self, *, permission: Any) -> list[str]:
        self._require(permission)
        self._require_operational()
        return self.provider.list_categories()

    def create_listing(self, *, permission: Any, payload: dict[str, Any], user_id: int, idempotency_key: str):
        self._require(permission)
        self._require_operational()
        if payload.get("category") not in self.config.categories:
            raise ValueError("Unsupported listing category")
        if self.role.value == "broker_agent":
            payload = {**payload, "assigned_agent_id": user_id}
        return self.provider.create_listing(payload=payload, user_id=user_id, idempotency_key=idempotency_key)

    def update_listing(self, *, permission: Any, listing_id: int, changes: dict[str, Any], actor_user_id: int):
        self._require(permission)
        self._require_operational()
        if self.role.value == "broker_agent" and changes.get("assigned_agent_id", actor_user_id) != actor_user_id:
            raise PermissionError("Agents cannot reassign listings to another team member")
        return self.provider.update_listing(
            listing_id=listing_id,
            changes=changes,
            actor_user_id=actor_user_id,
            restrict_to_assigned_agent=self.role.value == "broker_agent",
        )

    def set_listing_status(self, *, permission: Any, listing_id: int, target_status: str):
        self._require(permission)
        self._require_operational()
        if target_status == "active":
            context = self.provider.get_publish_context(
                listing_id=listing_id,
                actor_user_id=self.actor_user_id,
                restrict_to_assigned_agent=self.role.value == "broker_agent",
            )
            if context is None:
                return None
            valid, reasons = ListingRules.validate_publish_eligibility(
                is_approved_broker=context["is_approved_broker"],
                has_active_plan=context["has_active_plan"],
                valid_region_licence=context["valid_region_licence"],
                owner_consent=context["owner_consent"],
                category=context["category"],
                currency=context["currency"],
                price=context["price"],
                quality_score=context["quality_score"],
                media_count=context["media_count"],
                minimum_media_count=self.config.minimum_media_count,
                price_floors=self.config.price_floors,
                commission_terms=context.get("commission_terms"),
                require_commission_terms=self.require_commission_terms,
                owner_name=context.get("owner_name"),
                owner_mandate_reference=context.get("owner_mandate_reference"),
                require_owner_mandate=self.require_commission_terms,
            )
            if not valid:
                raise ValueError("Cannot publish listing: " + "; ".join(reasons))
        return self.provider.set_listing_status(
            listing_id=listing_id,
            status=target_status,
            actor_user_id=self.actor_user_id,
            restrict_to_assigned_agent=self.role.value == "broker_agent",
        )

    def list_revisions(self, *, permission: Any, listing_id: int, limit: int):
        self._require(permission)
        self._require_operational()
        return self.provider.list_revisions(
            listing_id=listing_id,
            actor_user_id=self.actor_user_id,
            restrict_to_assigned_agent=self.role.value == "broker_agent",
            limit=limit,
        )

    def validate_bulk_import(self, *, permission: Any, csv_content: str, user_id: int, idempotency_key: str, commit: bool):
        self._require(permission)
        self._require_operational()
        if self.rate_limiter and not self.rate_limiter.consume(
            f"{self.organization_id}:{user_id}",
            maximum=self.config.bulk_requests_per_minute,
            window_seconds=60,
        ):
            raise TooManyBulkRequests("Broker bulk request limit exceeded; retry later")
        report = BulkImportService.validate_csv(
            csv_content,
            price_floors=self.config.price_floors,
            maximum_rows=self.config.maximum_bulk_rows,
            allowed_categories=set(self.config.categories),
        )
        if not commit or not report["is_valid"]:
            return report
        if len(idempotency_key) < 8:
            raise ValueError("An Idempotency-Key with at least 8 characters is required to commit an import")
        imported = []
        for index, row in enumerate(BulkImportService.parse_rows(csv_content), start=1):
            payload = {
                "title": row["title"].strip(),
                "category": row["category"].strip().lower(),
                "price": float(row["price"]),
                "currency": row["currency"].strip().upper(),
                "location_country": row["location_country"].strip(),
                "location_city": row["location_city"].strip(),
            }
            item = self.provider.create_listing(
                payload=payload,
                user_id=user_id,
                idempotency_key=hashlib.sha256(f"{idempotency_key}:{index}".encode("utf-8")).hexdigest(),
            )
            imported.append(item["listing_id"])
        return {**report, "committed": True, "imported_listing_ids": imported}

    def export_listings(self, *, permission: Any, limit: int, offset: int) -> str:
        self._require(permission)
        self._require_operational()
        rows = self.provider.list_listings(filters={}, limit=limit, offset=offset, sort="-created_at")
        output = io.StringIO()
        columns = ["title", "category", "price", "currency", "location_country", "location_city"]
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()


class TooManyBulkRequests(Exception):
    """A broker exceeded the short-window bulk operation limit."""
