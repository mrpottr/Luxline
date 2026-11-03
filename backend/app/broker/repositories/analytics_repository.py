"""Tenant-scoped repository for broker analytics events and daily rollups."""

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from mongoengine.errors import NotUniqueError
from uuid import uuid4

from backend.app.broker.models.analytics import BrokerAnalyticsDailyRollup, BrokerAnalyticsEvent
from backend.app.broker.repositories.base_repository import BaseTenantRepository


class BrokerAnalyticsRepository(BaseTenantRepository[BrokerAnalyticsEvent]):
    def __init__(self, organization_id: int):
        super().__init__(BrokerAnalyticsEvent, organization_id)

    def record_source_event(
        self, *, source_type: str, source_id: int, event_type: str, listing_id: int,
        agent_user_id: int | None, occurred_at: datetime, response_seconds: int | None = None,
        lead_stage: str | None = None,
    ) -> None:
        query = self._scoped_query(source_type=source_type, source_id=source_id)
        event = query.first()
        if event:
            event.agent_user_id = agent_user_id
            event.response_seconds = response_seconds
            event.lead_stage = lead_stage
            event.save()
            return
        try:
            self.create(
                source_type=source_type, source_id=source_id, event_type=event_type,
                listing_id=listing_id, agent_user_id=agent_user_id, occurred_at=occurred_at,
                response_seconds=response_seconds, lead_stage=lead_stage,
            )
        except NotUniqueError:
            event = query.first()
            if not event:
                raise
            event.agent_user_id = agent_user_id
            event.response_seconds = response_seconds
            event.lead_stage = lead_stage
            event.save()

    def record_listing_event(self, *, listing_id: int, event_type: str, occurred_at: datetime) -> None:
        try:
            self.create(
                source_type=event_type, source_id=uuid4().int % 2_000_000_000,
                event_type=event_type, listing_id=listing_id, agent_user_id=None,
                occurred_at=occurred_at,
            )
        except NotUniqueError:
            self.record_listing_event(listing_id=listing_id, event_type=event_type, occurred_at=occurred_at)

    def list_events(self, *, start: date, end: date, listing_id: int | None, agent_id: int | None) -> list[Any]:
        filters: dict[str, Any] = {
            "occurred_at__gte": datetime.combine(start, time.min),
            "occurred_at__lt": datetime.combine(end + timedelta(days=1), time.min),
        }
        if listing_id is not None:
            filters["listing_id"] = listing_id
        if agent_id is not None:
            filters["agent_user_id"] = agent_id
        query = self._scoped_query(**filters).order_by("occurred_at")
        if query.count() > 100_000:
            raise ValueError("Analytics query exceeds 100,000 events; narrow the date range")
        return list(query.limit(100_000))

    def list_rollups(self, *, start: date, end: date, listing_id: int | None, agent_id: int | None) -> list[Any]:
        filters: dict[str, Any] = {"day__gte": start, "day__lte": end}
        if listing_id is None and agent_id is None:
            filters.update(listing_id=0, agent_user_id=0)
        elif listing_id is not None:
            filters["listing_id"] = listing_id
            if agent_id is not None:
                filters["agent_user_id"] = agent_id
        else:
            filters["agent_user_id"] = agent_id
        return list(BrokerAnalyticsDailyRollup.objects(
            organization_id=self.organization_id, is_deleted=False, **filters,
        ).order_by("day").limit(366))

    def save_rollups(self, rows: list[dict[str, Any]]) -> None:
        generated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        for row in rows:
            identity = {key: row[key] for key in ("day", "listing_id", "agent_user_id")}
            query = BrokerAnalyticsDailyRollup.objects(
                organization_id=self.organization_id, **identity, is_deleted=False,
            )
            rollup = query.first()
            if not rollup:
                rollup = BrokerAnalyticsDailyRollup(
                    organization_id=self.organization_id, **identity,
                    leads=row["leads"], replies=row["replies"],
                    phone_reveals=row["phone_reveals"],
                    views=row["views"],
                    impressions=row["impressions"],
                    response_count=row["response_count"],
                    response_seconds_total=row["response_seconds_total"],
                    average_response_seconds=row["average_response_seconds"],
                    generated_at=generated_at,
                )
                try:
                    rollup.save()
                    continue
                except NotUniqueError:
                    rollup = query.first()
                    if not rollup:
                        raise
            rollup.leads = row["leads"]
            rollup.replies = row["replies"]
            rollup.phone_reveals = row["phone_reveals"]
            rollup.views = row["views"]
            rollup.impressions = row["impressions"]
            rollup.response_count = row["response_count"]
            rollup.response_seconds_total = row["response_seconds_total"]
            rollup.average_response_seconds = row["average_response_seconds"]
            rollup.generated_at = generated_at
            rollup.save()
