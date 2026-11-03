"""M6 analytics domain, use-case, and API tests."""

import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.broker.api.analytics import router as analytics_router, view_router
from backend.app.broker.api.analytics_dependencies import get_analytics_use_cases
from backend.app.broker.application.public_view_use_case import ListingViewRateLimitExceeded
from backend.app.broker.application.public_view_use_case import RecordPublicListingView
from backend.app.broker.application.analytics_use_cases import AnalyticsUseCases
from backend.app.broker.domain.analytics import aggregate_events, validate_date_range
from backend.app.broker.domain.roles import BrokerPermission, BrokerRole


def event(kind, day, *, listing=1, agent=8, response=None, stage="new"):
    return SimpleNamespace(
        event_type=kind, occurred_at=datetime.combine(day, datetime.min.time()),
        listing_id=listing, agent_user_id=agent, response_seconds=response, lead_stage=stage,
    )


class TestAnalyticsDomain(unittest.TestCase):
    def test_date_range_must_be_ordered_and_bounded(self):
        with self.assertRaises(ValueError):
            validate_date_range(date(2025, 2, 2), date(2025, 2, 1))
        with self.assertRaises(ValueError):
            validate_date_range(date(2024, 1, 1), date(2025, 1, 2))

    def test_aggregate_calculates_daily_listing_agent_and_response_metrics(self):
        start = date(2025, 2, 1)
        end = date(2025, 2, 3)
        report = aggregate_events([
            event("lead_created", start, listing=11, agent=7, response=600, stage="qualified"),
            event("broker_reply", start, listing=11, agent=7),
            event("phone_reveal", end, listing=12, agent=None),
            event("lead_created", date(2025, 1, 31), listing=11, agent=7),
        ], start=start, end=end)
        self.assertEqual(report["totals"]["leads"], 1)
        self.assertEqual(report["totals"]["replies"], 1)
        self.assertEqual(report["totals"]["phone_reveals"], 1)
        self.assertEqual(report["totals"]["average_response_seconds"], 600)
        self.assertEqual(report["totals"]["conversion_rate"], 1)
        self.assertEqual(len(report["daily"]), 3)
        self.assertEqual(report["daily"][1]["leads"], 0)
        self.assertEqual(report["totals"]["views"], 0)
        self.assertIsNone(report["totals"]["click_through_rate"])
        self.assertEqual(report["by_listing"][0]["listing_id"], 11)
        self.assertEqual(report["by_agent"][0]["agent_id"], 7)

    def test_views_are_counted_per_listing_but_ctr_stays_unavailable_without_impressions(self):
        day = date(2025, 2, 1)
        report = aggregate_events([
            event("listing_view", day, listing=11, agent=7),
            event("listing_view", day, listing=11, agent=7),
            event("lead_created", day, listing=11, agent=7),
        ], start=day, end=day)
        self.assertEqual(report["totals"]["views"], 2)
        self.assertIsNone(report["totals"]["click_through_rate"])
        self.assertEqual(report["by_listing"][0]["views"], 2)

    def test_click_through_rate_uses_detail_views_over_visible_impressions(self):
        day = date(2025, 2, 1)
        report = aggregate_events([
            event("listing_impression", day, listing=11, agent=7),
            event("listing_impression", day, listing=11, agent=7),
            event("listing_view", day, listing=11, agent=7),
        ], start=day, end=day)
        self.assertEqual(report["totals"]["click_through_rate"], 0.5)
        self.assertEqual(report["by_listing"][0]["impressions"], 2)


class TestAnalyticsUseCases(unittest.TestCase):
    def setUp(self):
        self.provider = Mock()
        self.provider.is_broker_approved.return_value = True
        self.provider.list_events.return_value = [event("lead_created", date(2025, 3, 1), response=300)]
        self.provider.list_daily_rollups.return_value = []
        self.owner = AnalyticsUseCases(
            self.provider, {BrokerPermission.ANALYTICS_VIEW}, role=BrokerRole.broker_owner, actor_user_id=3,
        )

    def test_report_captures_events_and_refreshes_daily_rollups(self):
        report = self.owner.report(start=date(2025, 3, 1), end=date(2025, 3, 2))
        self.provider.capture_source_events.assert_called_once_with(start=date(2025, 3, 1), end=date(2025, 3, 2))
        self.provider.save_daily_rollups.assert_called_once()
        self.assertEqual(report["totals"]["leads"], 1)

    def test_agent_cannot_request_another_agents_metrics(self):
        agent = AnalyticsUseCases(
            self.provider, {BrokerPermission.ANALYTICS_VIEW}, role=BrokerRole.broker_agent, actor_user_id=7,
        )
        with self.assertRaises(PermissionError):
            agent.report(start=date(2025, 3, 1), end=date(2025, 3, 1), agent_id=99)
        agent.report(start=date(2025, 3, 1), end=date(2025, 3, 1))
        self.provider.list_events.assert_called_with(
            start=date(2025, 3, 1), end=date(2025, 3, 1), listing_id=None, agent_id=7,
        )

    def test_permission_and_approval_are_checked_before_data_access(self):
        forbidden = AnalyticsUseCases(self.provider, set(), role=BrokerRole.broker_viewer)
        with self.assertRaises(PermissionError):
            forbidden.report(start=date(2025, 3, 1), end=date(2025, 3, 1))
        self.provider.is_broker_approved.return_value = False
        with self.assertRaises(PermissionError):
            self.owner.report(start=date(2025, 3, 1), end=date(2025, 3, 1))
        self.provider.capture_source_events.assert_not_called()

    def test_csv_export_has_stable_columns(self):
        content = self.owner.export_csv(
            start=date(2025, 3, 1), end=date(2025, 3, 1), dimension="listing", limit=10, offset=0,
        )
        self.assertIn("listing_id,impressions,views,click_through_rate,leads,replies,phone_reveals,average_response_seconds,conversion_rate", content)

    def test_public_capture_checks_eligibility_before_consuming_rate_limit(self):
        provider = Mock()
        limiter = Mock()
        cases = RecordPublicListingView(provider, limiter)
        provider.is_public_listing_eligible.return_value = False
        self.assertFalse(cases.execute(listing_id=7, visitor_key=99, event_type="listing_view"))
        limiter.consume.assert_not_called()
        provider.is_public_listing_eligible.return_value = True
        provider.record_public_listing_event.return_value = True
        limiter.consume.return_value = True
        self.assertTrue(cases.execute(listing_id=7, visitor_key=99, event_type="listing_impression"))
        limiter.consume.assert_called_once_with("7:99", maximum=30, window_seconds=60)


class TestAnalyticsApi(unittest.TestCase):
    def setUp(self):
        provider = Mock()
        provider.is_broker_approved.return_value = True
        provider.list_events.return_value = [event("lead_created", date(2025, 4, 1))]
        provider.list_daily_rollups.return_value = []
        self.cases = AnalyticsUseCases(provider, {BrokerPermission.ANALYTICS_VIEW}, role=BrokerRole.broker_manager)
        app = FastAPI()
        app.include_router(analytics_router)
        app.include_router(view_router)
        app.dependency_overrides[get_analytics_use_cases] = lambda: self.cases
        self.client = TestClient(app)

    def test_summary_and_csv_endpoints(self):
        response = self.client.get("/analytics?date_from=2025-04-01&date_to=2025-04-02")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["totals"]["leads"], 1)
        exported = self.client.get("/analytics/export.csv?date_from=2025-04-01&date_to=2025-04-02")
        self.assertEqual(exported.status_code, 200)
        self.assertTrue(exported.text.startswith("listing_id,"))

    def test_invalid_date_range_returns_validation_error(self):
        response = self.client.get("/analytics?date_from=2025-04-03&date_to=2025-04-01")
        self.assertEqual(response.status_code, 422)

    def test_public_view_capture_is_flag_guarded_and_uses_injected_use_case(self):
        from backend.app.broker.api.analytics_dependencies import get_public_view_use_case
        from backend.app.core.config import settings

        capture = Mock()
        capture.execute.return_value = True
        self.client.app.dependency_overrides[get_public_view_use_case] = lambda: capture
        previous = settings.broker_panel_enabled
        try:
            object.__setattr__(settings, "broker_panel_enabled", False)
            disabled = self.client.post("/analytics/views", json={"listing_id": 7})
            self.assertEqual(disabled.status_code, 404)
            object.__setattr__(settings, "broker_panel_enabled", True)
            enabled = self.client.post("/analytics/views", json={"listing_id": 7})
            self.assertEqual(enabled.status_code, 204)
            capture.execute.assert_called_once()
            self.assertEqual(capture.execute.call_args.kwargs["event_type"], "listing_view")
            impression = self.client.post("/analytics/impressions", json={"listing_id": 7})
            self.assertEqual(impression.status_code, 204)
            self.assertEqual(capture.execute.call_args.kwargs["event_type"], "listing_impression")
        finally:
            object.__setattr__(settings, "broker_panel_enabled", previous)

    def test_public_view_rate_limit_maps_to_429(self):
        from backend.app.broker.api.analytics_dependencies import get_public_view_use_case
        from backend.app.core.config import settings

        capture = Mock()
        capture.execute.side_effect = ListingViewRateLimitExceeded("too many")
        self.client.app.dependency_overrides[get_public_view_use_case] = lambda: capture
        previous = settings.broker_panel_enabled
        try:
            object.__setattr__(settings, "broker_panel_enabled", True)
            response = self.client.post("/analytics/views", json={"listing_id": 7})
            self.assertEqual(response.status_code, 429)
        finally:
            object.__setattr__(settings, "broker_panel_enabled", previous)


if __name__ == "__main__":
    unittest.main()
