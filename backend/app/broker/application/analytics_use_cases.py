"""Permission-checked analytics queries and CSV exports."""

import csv
import io
from datetime import date

from backend.app.broker.application.analytics_ports import AnalyticsProvider
from backend.app.broker.domain.analytics import (
    aggregate_daily_rollups, aggregate_events, build_daily_rollups, validate_date_range,
)
from backend.app.broker.domain.roles import BrokerPermission


class AnalyticsUseCases:
    def __init__(self, provider: AnalyticsProvider, permissions: set[BrokerPermission], *, role=None, actor_user_id: int | None = None):
        self.provider = provider
        self.permissions = permissions
        self.role = role
        self.actor_user_id = actor_user_id

    def report(self, *, start: date, end: date, listing_id: int | None = None, agent_id: int | None = None):
        if BrokerPermission.ANALYTICS_VIEW not in self.permissions:
            raise PermissionError("Missing required broker analytics permission")
        if not self.provider.is_broker_approved():
            raise PermissionError("An approved broker profile is required to view analytics")
        validate_date_range(start, end)
        if getattr(self.role, "value", self.role) == "broker_agent":
            if agent_id is not None and agent_id != self.actor_user_id:
                raise PermissionError("Agents can only view their own analytics")
            agent_id = self.actor_user_id
        self.provider.capture_source_events(start=start, end=end)
        source_events = self.provider.list_events(start=start, end=end, listing_id=None, agent_id=None)
        self.provider.save_daily_rollups(build_daily_rollups(source_events))
        events = source_events if listing_id is None and agent_id is None else self.provider.list_events(
            start=start, end=end, listing_id=listing_id, agent_id=agent_id,
        )
        report = aggregate_events(events, start=start, end=end)
        report["daily"] = aggregate_daily_rollups(
            self.provider.list_daily_rollups(start=start, end=end, listing_id=listing_id, agent_id=agent_id),
            start=start,
            end=end,
        )
        if listing_id is not None:
            report["by_listing"] = [row for row in report["by_listing"] if row["listing_id"] == listing_id]
        if agent_id is not None:
            report["by_agent"] = [row for row in report["by_agent"] if row["agent_id"] == agent_id]
        return report

    def export_csv(self, *, start: date, end: date, dimension: str, limit: int, offset: int) -> str:
        if dimension not in {"listing", "agent"}:
            raise ValueError("Unsupported analytics dimension")
        if self.role and getattr(self.role, "value", self.role) == "broker_agent":
            return self._export_agent_csv(start=start, end=end, dimension=dimension, limit=limit, offset=offset)
        report = self.report(start=start, end=end)
        records = report["by_listing"] if dimension == "listing" else report["by_agent"]
        dimension_id = "listing_id" if dimension == "listing" else "agent_id"
        output = io.StringIO()
        columns = [dimension_id, "impressions", "views", "click_through_rate", "leads", "replies", "phone_reveals", "average_response_seconds", "conversion_rate"]
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        for row in records[offset:offset + limit]:
            writer.writerow({column: row.get(column) if row.get(column) is not None else "" for column in columns})
        return output.getvalue()

    def _export_agent_csv(self, *, start: date, end: date, dimension: str, limit: int, offset: int) -> str:
        report = self.report(start=start, end=end, agent_id=self.actor_user_id)
        records = report["by_listing"] if dimension == "listing" else report["by_agent"]
        dimension_id = "listing_id" if dimension == "listing" else "agent_id"
        output = io.StringIO()
        columns = [dimension_id, "impressions", "views", "click_through_rate", "leads", "replies", "phone_reveals", "average_response_seconds", "conversion_rate"]
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        for row in records[offset:offset + limit]:
            writer.writerow({column: row.get(column) if row.get(column) is not None else "" for column in columns})
        return output.getvalue()
