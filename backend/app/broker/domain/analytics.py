"""Framework-free broker analytics aggregation rules."""

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any


def validate_date_range(start: date, end: date, *, maximum_days: int = 366) -> None:
    if end < start:
        raise ValueError("End date must be on or after start date")
    if (end - start).days >= maximum_days:
        raise ValueError(f"Analytics date range cannot exceed {maximum_days} days")


def aggregate_events(events: list[Any], *, start: date, end: date) -> dict[str, Any]:
    """Aggregate broker events into totals, daily trend, listing, and agent views."""
    validate_date_range(start, end)
    daily = defaultdict(lambda: {"leads": 0, "replies": 0, "phone_reveals": 0, "views": 0, "impressions": 0})
    by_listing = defaultdict(lambda: {"listing_id": None, "leads": 0, "qualified_leads": 0, "replies": 0, "phone_reveals": 0, "views": 0, "impressions": 0, "response_seconds": []})
    by_agent = defaultdict(lambda: {"agent_id": None, "leads": 0, "qualified_leads": 0, "replies": 0, "phone_reveals": 0, "views": 0, "impressions": 0, "response_seconds": []})
    response_seconds = []
    totals = {"leads": 0, "replies": 0, "phone_reveals": 0, "qualified_leads": 0, "views": 0, "impressions": 0}

    for event in events:
        occurred_at = event.occurred_at
        event_date = occurred_at.date() if isinstance(occurred_at, datetime) else occurred_at
        if event_date < start or event_date > end:
            continue
        kind = event.event_type
        listing_id = event.listing_id
        agent_id = event.agent_user_id
        if kind == "lead_created":
            totals["leads"] += 1
            daily[event_date]["leads"] += 1
            by_listing[listing_id]["listing_id"] = listing_id
            by_listing[listing_id]["leads"] += 1
            if agent_id is not None:
                by_agent[agent_id]["agent_id"] = agent_id
                by_agent[agent_id]["leads"] += 1
            if event.lead_stage in {"qualified", "closed"}:
                totals["qualified_leads"] += 1
                by_listing[listing_id]["qualified_leads"] += 1
                if agent_id is not None:
                    by_agent[agent_id]["qualified_leads"] += 1
            if event.response_seconds is not None:
                response_seconds.append(event.response_seconds)
                by_listing[listing_id]["response_seconds"].append(event.response_seconds)
                if agent_id is not None:
                    by_agent[agent_id]["response_seconds"].append(event.response_seconds)
        elif kind == "broker_reply":
            totals["replies"] += 1
            daily[event_date]["replies"] += 1
            by_listing[listing_id]["listing_id"] = listing_id
            by_listing[listing_id]["replies"] += 1
            if agent_id is not None:
                by_agent[agent_id]["agent_id"] = agent_id
                by_agent[agent_id]["replies"] += 1
        elif kind == "phone_reveal":
            totals["phone_reveals"] += 1
            daily[event_date]["phone_reveals"] += 1
            by_listing[listing_id]["listing_id"] = listing_id
            by_listing[listing_id]["phone_reveals"] += 1
        elif kind == "listing_view":
            totals["views"] += 1
            daily[event_date]["views"] += 1
            by_listing[listing_id]["listing_id"] = listing_id
            by_listing[listing_id]["views"] += 1
            if agent_id is not None:
                by_agent[agent_id]["agent_id"] = agent_id
                by_agent[agent_id]["views"] += 1
        elif kind == "listing_impression":
            totals["impressions"] += 1
            daily[event_date]["impressions"] += 1
            by_listing[listing_id]["listing_id"] = listing_id
            by_listing[listing_id]["impressions"] += 1
            if agent_id is not None:
                by_agent[agent_id]["agent_id"] = agent_id
                by_agent[agent_id]["impressions"] += 1

    day_count = (end - start).days + 1
    series = []
    for delta in range(day_count):
        day = start + timedelta(days=delta)
        series.append({"date": day, **daily[day]})

    def present(rows: dict, dimension_key: str) -> list[dict[str, Any]]:
        values = []
        for item in rows.values():
            samples = item.pop("response_seconds")
            values.append({
                **item,
                "average_response_seconds": round(sum(samples) / len(samples), 2) if samples else None,
                "conversion_rate": round(item["qualified_leads"] / item["leads"], 4) if item["leads"] else 0,
                "click_through_rate": round(item["views"] / item["impressions"], 4) if item["impressions"] else None,
            })
        return sorted(values, key=lambda item: (-item["leads"], item[dimension_key]))

    totals["average_response_seconds"] = round(sum(response_seconds) / len(response_seconds), 2) if response_seconds else None
    totals["conversion_rate"] = round(totals["qualified_leads"] / totals["leads"], 4) if totals["leads"] else 0
    totals["click_through_rate"] = round(totals["views"] / totals["impressions"], 4) if totals["impressions"] else None
    return {
        "date_from": start,
        "date_to": end,
        "totals": totals,
        "daily": series,
        "by_listing": present(by_listing, "listing_id"),
        "by_agent": present(by_agent, "agent_id"),
    }


def build_daily_rollups(events: list[Any]) -> list[dict[str, Any]]:
    """Build deterministic organization, listing, and agent rollup documents."""
    rows = {}
    for event in events:
        day = event.occurred_at.date()
        agent_id = event.agent_user_id or 0
        for listing_id, dimension_agent_id in ((event.listing_id, agent_id), (0, 0)):
            key = (day, listing_id, dimension_agent_id)
            row = rows.setdefault(key, {
                "day": day, "listing_id": listing_id, "agent_user_id": dimension_agent_id,
                "leads": 0, "replies": 0, "phone_reveals": 0, "views": 0, "impressions": 0, "responses": [],
            })
            if event.event_type == "lead_created":
                row["leads"] += 1
                if event.response_seconds is not None:
                    row["responses"].append(event.response_seconds)
            elif event.event_type == "broker_reply":
                row["replies"] += 1
            elif event.event_type == "phone_reveal":
                row["phone_reveals"] += 1
            elif event.event_type == "listing_view":
                row["views"] += 1
            elif event.event_type == "listing_impression":
                row["impressions"] += 1
    return [{
        **{key: value for key, value in row.items() if key != "responses"},
        "response_count": len(row["responses"]),
        "response_seconds_total": sum(row["responses"]),
        "average_response_seconds": round(sum(row["responses"]) / len(row["responses"])) if row["responses"] else None,
    } for row in rows.values()]


def aggregate_daily_rollups(rows: list[Any], *, start: date, end: date) -> list[dict[str, Any]]:
    """Combine persisted daily rollups into a bounded date series."""
    totals = defaultdict(lambda: {"leads": 0, "replies": 0, "phone_reveals": 0, "views": 0, "impressions": 0, "response_seconds_sum": 0, "response_count": 0})
    for row in rows:
        day = row.day
        totals[day]["leads"] += row.leads
        totals[day]["replies"] += row.replies
        totals[day]["phone_reveals"] += row.phone_reveals
        totals[day]["views"] += row.views
        totals[day]["impressions"] += row.impressions
        count = row.response_count
        if count and row.response_seconds_total is not None:
            totals[day]["response_seconds_sum"] += row.response_seconds_total
            totals[day]["response_count"] += count
    series = []
    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        value = totals[day]
        response_count = value["response_count"]
        series.append({
            "date": day,
            "leads": value["leads"],
            "replies": value["replies"],
            "phone_reveals": value["phone_reveals"],
            "views": value["views"],
            "impressions": value["impressions"],
            "click_through_rate": round(value["views"] / value["impressions"], 4) if value["impressions"] else None,
            "average_response_seconds": round(value["response_seconds_sum"] / response_count, 2) if response_count else None,
        })
    return series
