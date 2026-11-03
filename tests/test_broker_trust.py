"""M8 review integrity, explainable badges, and audit workflows."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.broker.api.dependencies import verify_broker_panel_enabled
from backend.app.broker.api.trust import admin_router, buyer_router, public_router, router
from backend.app.broker.api.trust_dependencies import (
    get_admin_trust_use_cases,
    get_broker_trust_use_cases,
    get_buyer_review_use_cases,
    get_public_trust_use_cases,
)
from backend.app.broker.application.trust_use_cases import (
    AdminTrustUseCases,
    BrokerTrustUseCases,
    BuyerReviewUseCases,
    PublicTrustUseCases,
)
from backend.app.broker.domain.roles import BrokerPermission, BrokerRole, ROLE_PERMISSIONS
from backend.app.broker.domain.trust import (
    BADGE_RULE_VERSION,
    evaluate_organization_badges,
    evaluate_responsive_agent,
    validate_review,
)
from backend.app.broker.repositories.trust_repository import BrokerTrustRepository


class TestBrokerTrustDomain(unittest.TestCase):
    def test_review_requires_public_consent_and_valid_rating_and_body(self):
        self.assertEqual(validate_review(rating=5, body="  Helpful and professional.  ", public_consent=True)["body"],
                         "Helpful and professional.")
        for values in [
            {"rating": 0, "body": "long enough review", "public_consent": True},
            {"rating": 6, "body": "long enough review", "public_consent": True},
            {"rating": 3, "body": "short", "public_consent": True},
            {"rating": 3, "body": "long enough review", "public_consent": False},
        ]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                validate_review(**values)

    def test_organization_badges_are_deterministic_and_explain_missing_criteria(self):
        evaluations = evaluate_organization_badges(
            broker_approved=True, live_listing_count=4, average_quality=99,
        )
        self.assertEqual([row.code for row in evaluations], ["verified_seller", "quality_lister"])
        self.assertTrue(evaluations[0].awarded)
        self.assertFalse(evaluations[1].awarded)
        self.assertIn("Needs five", evaluations[1].explanation)
        self.assertEqual(BADGE_RULE_VERSION, 1)

    def test_quality_lister_awards_only_at_configured_rule_threshold(self):
        badges = evaluate_organization_badges(broker_approved=False, live_listing_count=5, average_quality=85)
        self.assertTrue(badges[1].awarded)
        self.assertFalse(badges[0].awarded)

    def test_responsive_agent_requires_five_responses_with_one_hour_average(self):
        self.assertFalse(evaluate_responsive_agent(response_count=4, average_response_seconds=30).awarded)
        self.assertTrue(evaluate_responsive_agent(response_count=5, average_response_seconds=3600).awarded)
        slow = evaluate_responsive_agent(response_count=5, average_response_seconds=3601)
        self.assertFalse(slow.awarded)
        self.assertIn("one hour", slow.explanation)


class TestBrokerTrustUseCases(unittest.TestCase):
    def setUp(self):
        self.provider = Mock()
        self.provider.is_approved.return_value = True
        self.owner = BrokerTrustUseCases(
            self.provider, ROLE_PERMISSIONS[BrokerRole.broker_owner], organization_id=12,
            actor_user_id=5, role=BrokerRole.broker_owner, source_ip="127.0.0.1",
        )

    def test_reviews_require_permission_and_approved_profile(self):
        viewer = BrokerTrustUseCases(
            self.provider, ROLE_PERMISSIONS[BrokerRole.broker_viewer], organization_id=12,
            actor_user_id=6, role=BrokerRole.broker_viewer,
        )
        with self.assertRaises(PermissionError):
            viewer.list_reviews(status=None, limit=50, offset=0)
        self.provider.is_approved.return_value = False
        with self.assertRaises(PermissionError):
            self.owner.list_reviews(status=None, limit=50, offset=0)
        self.provider.list_reviews.assert_not_called()

    def test_review_status_and_reply_are_validated_before_provider_call(self):
        with self.assertRaises(ValueError):
            self.owner.list_reviews(status="unknown", limit=10, offset=0)
        with self.assertRaises(ValueError):
            self.owner.reply(review_id=3, body="  ")
        self.provider.reply_to_review.assert_not_called()

    def test_reply_and_appeal_require_repository_eligibility(self):
        self.provider.can_reply_to_review.return_value = False
        self.provider.can_appeal_review.return_value = False
        with self.assertRaises(ValueError):
            self.owner.reply(review_id=7, body="A considered response.")
        with self.assertRaises(ValueError):
            self.owner.appeal(review_id=7, reason="Please review this decision.")
        self.provider.reply_to_review.assert_not_called()
        self.provider.appeal_review.assert_not_called()

    def test_badge_read_requires_analytics_permission(self):
        viewer = BrokerTrustUseCases(
            self.provider, ROLE_PERMISSIONS[BrokerRole.broker_viewer], organization_id=12,
            actor_user_id=6, role=BrokerRole.broker_viewer,
        )
        viewer.list_badges()
        self.provider.save_badge_evaluations.assert_called_once()

    def test_badge_evaluation_saves_explainable_versioned_results(self):
        self.provider.badge_inputs.return_value = {
            "broker_approved": True, "live_listing_count": 5, "average_quality": 90,
            "agents": [{"user_id": 21, "response_count": 5, "average_response_seconds": 120}],
        }
        self.provider.save_badge_evaluations.side_effect = lambda items: items
        values = self.owner.list_badges()
        self.assertEqual(len(values), 3)
        self.assertEqual(values[0]["rule_version"], BADGE_RULE_VERSION)
        self.assertIn("explanation", values[0])
        self.assertTrue(values[-1]["awarded"])

    def test_export_audit_contains_filter_scope_but_not_buyer_data(self):
        self.owner.record_data_export(dimension="listing", date_from="2026-01-01", date_to="2026-01-02")
        self.provider.append_audit.assert_called_once()
        event = self.provider.append_audit.call_args.kwargs
        self.assertEqual(event["action"], "analytics_exported")
        self.assertEqual(event["metadata"]["dimension"], "listing")
        self.assertNotIn("buyer_id", event["metadata"])

    def test_buyer_review_flow_checks_profile_and_validation(self):
        provider = Mock()
        provider.is_approved.return_value = True
        buyer = BuyerReviewUseCases(provider, organization_id=12, buyer_user_id=42)
        buyer.submit(lead_id=7, rating=4, body="Good service overall", public_consent=True, idempotency_key="review-key-1")
        provider.submit_review.assert_called_once_with(
            buyer_id=42, lead_id=7, rating=4, body="Good service overall", public_consent=True,
            idempotency_key="review-key-1",
        )
        with self.assertRaises(ValueError):
            buyer.submit(lead_id=7, rating=4, body="No", public_consent=False, idempotency_key="review-key-2")

    def test_platform_moderation_requires_super_admin(self):
        admin = AdminTrustUseCases(self.provider, actor_user_id=4, actor_role="business_account")
        with self.assertRaises(PermissionError):
            admin.list_cases(status="open", limit=20, offset=0)

    def test_public_reviews_are_empty_for_unapproved_broker(self):
        self.provider.is_approved.return_value = False
        public = PublicTrustUseCases(self.provider)
        self.assertEqual(public.reviews(limit=20, offset=0), [])
        self.provider.public_reviews.assert_not_called()


class TestBrokerTrustRepositoryIsolation(unittest.TestCase):
    def test_review_list_query_is_tenant_scoped_and_paginated(self):
        query = Mock()
        query.order_by.return_value.skip.return_value.limit.return_value = ["review"]
        with patch("backend.app.broker.repositories.trust_repository.BrokerReview.objects", return_value=query) as objects:
            rows = BrokerTrustRepository(88).list_reviews(status="published", limit=9, offset=3)
        self.assertEqual(rows, ["review"])
        objects.assert_called_once_with(organization_id=88, is_deleted=False)
        query.filter.assert_called_once_with(status="published")
        query.order_by.assert_called_once_with("-created_at", "-id")
        query.skip.assert_called_once_with(3)
        query.limit.assert_called_once_with(9)

    def test_tenant_repository_rejects_global_scope_for_broker_data(self):
        with self.assertRaises(ValueError):
            BrokerTrustRepository(None).list_reviews(status=None, limit=10, offset=0)

    def test_platform_moderation_requires_explicit_admin_repository_scope(self):
        with self.assertRaises(PermissionError):
            BrokerTrustRepository(None).list_moderation_cases(status="open", limit=10, offset=0)

    def test_tenant_moderation_case_list_keeps_organization_scope(self):
        query = Mock()
        query.filter.return_value.order_by.return_value.skip.return_value.limit.return_value = []
        with patch("backend.app.broker.repositories.trust_repository.BrokerModerationCase.objects", return_value=query) as objects:
            BrokerTrustRepository(88).list_moderation_cases(status=None, limit=10, offset=0)
        objects.assert_called_once_with(is_deleted=False)
        query.filter.assert_called_once_with(organization_id=88)


class TestBrokerTrustApi(unittest.TestCase):
    def setUp(self):
        self.broker_cases = Mock()
        self.buyer_cases = Mock()
        self.public_cases = Mock()
        self.admin_cases = Mock()
        app = FastAPI()
        app.include_router(router, prefix="/api/broker/v1")
        app.include_router(buyer_router, prefix="/api/broker/v1")
        app.include_router(public_router, prefix="/api/broker/v1")
        app.include_router(admin_router, prefix="/api/broker/v1")
        app.dependency_overrides[verify_broker_panel_enabled] = lambda: None
        app.dependency_overrides[get_broker_trust_use_cases] = lambda: self.broker_cases
        app.dependency_overrides[get_buyer_review_use_cases] = lambda: self.buyer_cases
        app.dependency_overrides[get_public_trust_use_cases] = lambda: self.public_cases
        app.dependency_overrides[get_admin_trust_use_cases] = lambda: self.admin_cases
        self.client = TestClient(app)

    def test_review_list_passes_filters_and_pagination(self):
        self.broker_cases.list_reviews.return_value = []
        response = self.client.get("/api/broker/v1/reviews?status=pending&limit=8&offset=4")
        self.assertEqual(response.status_code, 200)
        self.broker_cases.list_reviews.assert_called_once_with(status="pending", limit=8, offset=4)

    def test_buyer_review_requires_idempotency_and_public_consent(self):
        response = self.client.post("/api/broker/v1/buyer/reviews?organization_id=12", json={
            "lead_id": 4, "rating": 5, "body": "Very helpful and clear service.", "public_consent": True,
        })
        self.assertEqual(response.status_code, 422)
        self.buyer_cases.submit.assert_not_called()

    def test_public_reviews_are_paginated(self):
        self.public_cases.reviews.return_value = []
        response = self.client.get("/api/broker/v1/public/brokers/12/reviews?limit=10&offset=5")
        self.assertEqual(response.status_code, 200)
        self.public_cases.reviews.assert_called_once_with(limit=10, offset=5)

    def test_admin_moderation_cases_are_paginated(self):
        self.admin_cases.list_cases.return_value = []
        response = self.client.get("/api/broker/v1/admin/moderation-cases?status=open&limit=6&offset=2")
        self.assertEqual(response.status_code, 200)
        self.admin_cases.list_cases.assert_called_once_with(status="open", limit=6, offset=2)

    def test_review_integrity_violation_maps_to_conflict(self):
        from backend.app.broker.repositories.trust_repository import BrokerReviewIntegrityViolation
        self.buyer_cases.submit.side_effect = BrokerReviewIntegrityViolation("duplicate")
        response = self.client.post(
            "/api/broker/v1/buyer/reviews?organization_id=12",
            headers={"Idempotency-Key": "review-key-1"},
            json={"lead_id": 4, "rating": 5, "body": "Very helpful and clear service.", "public_consent": True},
        )
        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
