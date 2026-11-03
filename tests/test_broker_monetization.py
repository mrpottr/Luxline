"""M7 broker plan, wallet, and promotion rules and API contracts."""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.broker.api.dependencies import verify_broker_panel_enabled
from backend.app.broker.api.monetization import router as monetization_router
from backend.app.broker.api.dependencies import get_monetization_use_cases
from backend.app.broker.api.admin_monetization import router as admin_monetization_router
from backend.app.broker.api.monetization_dependencies import get_broker_plan_admin_use_cases
from backend.app.broker.application.monetization_use_cases import (
    BrokerPlanAlreadyExists,
    BrokerPlanIdempotencyConflict,
    MonetizationUseCases,
)
from backend.app.broker.domain.monetization import (
    calculate_promotion_cost,
    payload_hash,
    validate_plan,
)
from backend.app.broker.domain.roles import BrokerPermission, BrokerRole, ROLE_PERMISSIONS
from backend.app.broker.repositories.monetization_repository import MonetizationIdempotencyConflict
from backend.app.broker.services.payment_provider import MockBrokerPaymentProvider


class TestBrokerMonetizationDomain(unittest.TestCase):
    def test_plan_validation_preserves_configured_amount_and_entitlements(self):
        plan = validate_plan(
            code="growth", name="Growth", description="Configured broker tier", price_amount="125.50", currency="LKR",
            billing_period_days=30, listing_limit=12,
            entitlements={"promotions_enabled": True}, credit_packs=[],
            promotion_prices={"city": {"featured": 3}},
        )
        self.assertEqual(plan["price_amount"], "125.50")
        self.assertEqual(plan["currency"], "LKR")
        self.assertEqual(plan["listing_limit"], 12)
        self.assertEqual(plan["description"], "Configured broker tier")
        self.assertTrue(plan["entitlements"]["promotions_enabled"])

    def test_plan_validation_rejects_invalid_price_pack_and_promotion_configuration(self):
        with self.assertRaises(ValueError):
            validate_plan(code="x", name="X", price_amount="NaN", currency="USD", billing_period_days=30,
                          listing_limit=None, entitlements={}, credit_packs=[], promotion_prices={})
        with self.assertRaises(ValueError):
            validate_plan(code="x", name="X", price_amount="1", currency="US", billing_period_days=30,
                          listing_limit=None, entitlements={}, credit_packs=[], promotion_prices={})
        with self.assertRaises(ValueError):
            validate_plan(code="x", name="X", price_amount="1", currency="USD", billing_period_days=30,
                          listing_limit=None, entitlements={}, credit_packs=[{"code": "bad", "credits": 0,
                          "price_amount": "1", "currency": "USD"}], promotion_prices={})
        with self.assertRaises(ValueError):
            validate_plan(code="x", name="X", price_amount="1", currency="USD", billing_period_days=30,
                          listing_limit=None, entitlements={}, credit_packs=[],
                          promotion_prices={"city": {"unknown": 2}})

    def test_promotion_cost_rounds_partial_days_up_and_reads_only_configured_price(self):
        start = datetime(2030, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(calculate_promotion_cost(
            promotion_prices={"city": {"featured": 4}}, scope="city", placement_type="featured",
            starts_at=start, ends_at=start + timedelta(days=1, seconds=1),
        ), 8)
        with self.assertRaises(ValueError):
            calculate_promotion_cost(promotion_prices={}, scope="city", placement_type="featured",
                                     starts_at=start, ends_at=start + timedelta(days=1))

    def test_payload_hash_is_stable_across_key_order(self):
        self.assertEqual(payload_hash({"a": 1, "b": 2}), payload_hash({"b": 2, "a": 1}))


class TestBrokerMonetizationUseCases(unittest.TestCase):
    def setUp(self):
        self.provider = Mock()
        self.provider.is_broker_approved.return_value = True
        self.payment = Mock()
        self.payment.charge.return_value = "mock_receipt"
        self.owner = MonetizationUseCases(
            self.provider, self.payment, ROLE_PERMISSIONS[BrokerRole.broker_owner],
            organization_id=14, actor_user_id=8, role=BrokerRole.broker_owner,
        )

    def test_owner_subscription_uses_plan_snapshot_and_idempotent_mock_payment(self):
        plan = SimpleNamespace(code="growth", is_active=True, version=3, price_amount="12.50", currency="USD")
        self.provider.get_plan.return_value = plan
        self.owner.subscribe(plan_code="growth", idempotency_key="subscribe-key-1")
        self.payment.charge.assert_called_once_with(
            organization_id=14, amount="12.50", currency="USD", idempotency_key="subscribe-key-1",
        )
        self.provider.subscribe_transaction.assert_called_once()
        self.assertEqual(self.provider.subscribe_transaction.call_args.kwargs["payment_reference"], "mock_receipt")

    def test_agent_cannot_read_billing_or_manage_promotions(self):
        agent = MonetizationUseCases(
            self.provider, self.payment, ROLE_PERMISSIONS[BrokerRole.broker_agent],
            organization_id=14, actor_user_id=9, role=BrokerRole.broker_agent,
        )
        with self.assertRaises(PermissionError):
            agent.current_subscription()
        with self.assertRaises(PermissionError):
            agent.estimate_promotion(
                listing_id=1, scope="city", location_code="city-1", placement_type="featured",
                starts_at=datetime.now(timezone.utc), ends_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
        self.provider.get_promotion_context.assert_not_called()

    def test_unapproved_broker_cannot_perform_billing_even_with_permission(self):
        self.provider.is_broker_approved.return_value = False
        with self.assertRaises(PermissionError):
            self.owner.list_plans(limit=50, offset=0, sort="code")
        self.provider.get_active_plans.assert_not_called()

    def test_promotion_requires_live_approved_listing_consent_and_licence(self):
        self.provider.get_promotion_context.return_value = {
            "is_live": False, "moderation_approved": True, "is_approved_broker": True,
            "has_active_plan": True, "entitlements": {"promotions_enabled": True},
            "promotion_prices": {"city": {"featured": 1}}, "owner_consent": True,
            "valid_region_licence": True,
            "listing_geography": {"city": "Colombo", "country": "Sri Lanka"},
        }
        with self.assertRaisesRegex(ValueError, "Only live"):
            self.owner.estimate_promotion(
                listing_id=2, scope="city", location_code="c1", placement_type="featured",
                starts_at=datetime.now(timezone.utc), ends_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
        context = self.provider.get_promotion_context.return_value
        context["is_live"] = True
        context["owner_consent"] = False
        with self.assertRaisesRegex(ValueError, "Owner consent"):
            self.owner.estimate_promotion(
                listing_id=2, scope="city", location_code="c1", placement_type="featured",
                starts_at=datetime.now(timezone.utc), ends_at=datetime.now(timezone.utc) + timedelta(days=1),
            )

    def test_promotion_geography_must_match_listing_location(self):
        self.provider.get_promotion_context.return_value = {
            "is_live": True, "moderation_approved": True, "is_approved_broker": True,
            "has_active_plan": True, "entitlements": {"promotions_enabled": True},
            "promotion_prices": {"city": {"featured": 2}}, "owner_consent": True,
            "valid_region_licence": True, "listing_geography": {"city": "Colombo"},
        }
        start = datetime.now(timezone.utc)
        with self.assertRaisesRegex(ValueError, "must match"):
            self.owner.estimate_promotion(
                listing_id=2, scope="city", location_code="Kandy", placement_type="featured",
                starts_at=start, ends_at=start + timedelta(days=1),
            )
        self.assertEqual(self.owner.estimate_promotion(
            listing_id=2, scope="city", location_code=" Colombo ", placement_type="featured",
            starts_at=start, ends_at=start + timedelta(days=1),
        ), 2)

    def test_promotion_requires_an_explicit_plan_entitlement(self):
        self.provider.get_promotion_context.return_value = {
            "is_live": True, "moderation_approved": True, "is_approved_broker": True,
            "has_active_plan": True, "entitlements": {}, "promotion_prices": {"city": {"featured": 2}},
            "owner_consent": True, "valid_region_licence": True,
            "listing_geography": {"city": "Colombo"},
        }
        start = datetime.now(timezone.utc)
        with self.assertRaisesRegex(ValueError, "does not include promotions"):
            self.owner.estimate_promotion(
                listing_id=2, scope="city", location_code="Colombo", placement_type="featured",
                starts_at=start, ends_at=start + timedelta(days=1),
            )

    def test_mock_payment_provider_returns_stable_non_secret_receipt(self):
        provider = MockBrokerPaymentProvider()
        first = provider.charge(organization_id=14, amount="12.50", currency="USD", idempotency_key="key-1")
        second = provider.charge(organization_id=14, amount="12.50", currency="USD", idempotency_key="key-1")
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("mock_"))
        self.assertEqual(len(first), 37)


class TestBrokerMonetizationApi(unittest.TestCase):
    def setUp(self):
        self.cases = Mock()
        self.admin_cases = Mock()
        app = FastAPI()
        app.include_router(monetization_router, prefix="/api/broker/v1")
        app.include_router(admin_monetization_router, prefix="/api/broker/v1")
        app.dependency_overrides[verify_broker_panel_enabled] = lambda: None
        app.dependency_overrides[get_monetization_use_cases] = lambda: self.cases
        app.dependency_overrides[get_broker_plan_admin_use_cases] = lambda: self.admin_cases
        self.client = TestClient(app)

    def test_promotion_create_requires_idempotency_key(self):
        response = self.client.post("/api/broker/v1/promotions", json={
            "listing_id": 4, "scope": "city", "location_code": "city-1", "placement_type": "featured",
            "starts_at": "2026-01-01T00:00:00Z", "ends_at": "2026-01-02T00:00:00Z",
        })
        self.assertEqual(response.status_code, 422)
        self.cases.create_promotion.assert_not_called()

    def test_credit_pack_purchase_requires_idempotency_key(self):
        response = self.client.post("/api/broker/v1/credits/purchase?plan_code=basic&pack_code=small")
        self.assertEqual(response.status_code, 422)
        self.cases.purchase_credit_pack.assert_not_called()

    def test_purchase_surfaces_idempotency_conflict_as_conflict(self):
        self.cases.purchase_credit_pack.side_effect = MonetizationIdempotencyConflict("key reused")
        response = self.client.post(
            "/api/broker/v1/credits/purchase?plan_code=basic&pack_code=small",
            headers={"Idempotency-Key": "credit-pack-1"},
        )
        self.assertEqual(response.status_code, 409)

    def test_public_plan_list_is_paginated_and_sorted(self):
        self.cases.list_plans.return_value = []
        response = self.client.get("/api/broker/v1/plans?limit=7&offset=2&sort=-code")
        self.assertEqual(response.status_code, 200)
        self.cases.list_plans.assert_called_once_with(limit=7, offset=2, sort="-code")

    def test_admin_plan_list_is_filtered_paginated_and_sorted(self):
        self.admin_cases.list_plans.return_value = []
        response = self.client.get("/api/broker/v1/admin/plans?is_active=false&limit=9&offset=3&sort=code")
        self.assertEqual(response.status_code, 200)
        self.admin_cases.list_plans.assert_called_once_with(is_active=False, limit=9, offset=3, sort="code")

    def test_plan_list_rejects_unbounded_pagination(self):
        response = self.client.get("/api/broker/v1/plans?limit=101")
        self.assertEqual(response.status_code, 422)

    def test_admin_duplicate_plan_code_returns_conflict(self):
        self.admin_cases.create_plan.side_effect = BrokerPlanAlreadyExists("duplicate code")
        response = self.client.post("/api/broker/v1/admin/plans", json={
            "code": "starter", "name": "Starter", "description": "", "price_amount": "10.00",
            "currency": "USD", "billing_period_days": 30, "listing_limit": None,
            "entitlements": {}, "credit_packs": [], "promotion_prices": {}, "is_active": True,
        }, headers={"Idempotency-Key": "plan-create-1"})
        self.assertEqual(response.status_code, 409)

    def test_admin_plan_create_requires_idempotency_key(self):
        response = self.client.post("/api/broker/v1/admin/plans", json={
            "code": "starter", "name": "Starter", "description": "", "price_amount": "10.00",
            "currency": "USD", "billing_period_days": 30, "listing_limit": None,
            "entitlements": {}, "credit_packs": [], "promotion_prices": {}, "is_active": True,
        })
        self.assertEqual(response.status_code, 422)
        self.admin_cases.create_plan.assert_not_called()

    def test_admin_idempotency_payload_conflict_returns_conflict(self):
        self.admin_cases.create_plan.side_effect = BrokerPlanIdempotencyConflict("key reused")
        response = self.client.post("/api/broker/v1/admin/plans", json={
            "code": "starter", "name": "Starter", "description": "", "price_amount": "10.00",
            "currency": "USD", "billing_period_days": 30, "listing_limit": None,
            "entitlements": {}, "credit_packs": [], "promotion_prices": {}, "is_active": True,
        }, headers={"Idempotency-Key": "plan-create-1"})
        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
