"""Listing rule and use-case tests for milestone M4."""

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.broker.application.listing_use_cases import ListingUseCases
from backend.app.broker.domain.listing_rules import ListingRules
from backend.app.broker.domain.quality_score import QualityScoreCalculator
from backend.app.broker.domain.roles import BrokerPermission
from backend.app.broker.services.bulk_import import BulkImportService
from backend.app.broker.models.listing_extension import BrokerListing
from backend.app.broker.repositories.listing_repository import BrokerListingRepository
from backend.app.broker.api.listing_dependencies import ListingContext, get_listing_context
from backend.app.broker.api.listings import get_listing_use_cases, router as listing_router
from backend.app.broker.application.access_use_cases import ListingAccessUseCases
from backend.app.broker.schemas import BrokerListingCreate
from backend.app.broker.schemas import BrokerListingMediaInput
from backend.app.broker.services.bulk_rate_limiter import InMemoryBulkRateLimiter


class TestListingRules(unittest.TestCase):
    def test_price_floor_is_configured_and_missing_floor_is_not_invented(self):
        self.assertIsNone(ListingRules.get_price_floor("real_estate", "USD", {}))
        self.assertEqual(ListingRules.get_price_floor("real_estate", "USD", {"real_estate": {"USD": 123.0}}), 123.0)

    def test_publish_requires_approval_plan_licence_consent_quality_and_media(self):
        allowed, reasons = ListingRules.validate_publish_eligibility(
            is_approved_broker=True,
            has_active_plan=True,
            valid_region_licence=True,
            owner_consent=True,
            category="real_estate",
            currency="USD",
            price=200,
            quality_score=80,
            media_count=5,
            minimum_media_count=5,
            price_floors={"real_estate": {"USD": 100}},
        )
        self.assertTrue(allowed)
        self.assertEqual(reasons, [])
        allowed, reasons = ListingRules.validate_publish_eligibility(
            is_approved_broker=False,
            has_active_plan=False,
            valid_region_licence=False,
            owner_consent=False,
            category="real_estate",
            currency="USD",
            price=50,
            quality_score=20,
            media_count=0,
            minimum_media_count=5,
            price_floors={"real_estate": {"USD": 100}},
        )
        self.assertFalse(allowed)
        self.assertGreaterEqual(len(reasons), 7)

    def test_property_broker_must_record_commission_terms_before_publishing(self):
        eligibility = dict(
            is_approved_broker=True,
            has_active_plan=True,
            valid_region_licence=True,
            owner_consent=True,
            category="real_estate",
            currency="LKR",
            price=100,
            quality_score=80,
            media_count=5,
            minimum_media_count=5,
            price_floors={},
            require_commission_terms=True,
            require_owner_mandate=True,
        )
        allowed, reasons = ListingRules.validate_publish_eligibility(**eligibility)
        self.assertFalse(allowed)
        self.assertIn("The agreed commission terms must be recorded before publishing.", reasons)

        allowed, reasons = ListingRules.validate_publish_eligibility(
            **eligibility,
            owner_name="Property Owner",
            owner_mandate_reference="MANDATE-2026-001",
            commission_terms="5% of the completed sale price, payable by the seller.",
        )
        self.assertTrue(allowed)
        self.assertEqual(reasons, [])

    def test_quality_score_returns_actionable_suggestions(self):
        score, rating, suggestions = QualityScoreCalculator.calculate(
            title="x", description="short", price=0, photo_count=0,
            has_location=False, has_specs=False, owner_consent=False,
        )
        self.assertEqual(score, 0)
        self.assertEqual(rating, "red")
        self.assertTrue(suggestions)

    def test_listing_input_requires_https_media_and_three_letter_currency(self):
        payload = BrokerListingCreate(
            title="Coastal Residence",
            category="real_estate",
            price=100000,
            currency="LKR",
            location_country="Sri Lanka",
            location_city="Galle",
            photos=["https://cdn.example.test/residence.jpg"],
        )
        self.assertEqual(payload.currency, "LKR")
        with self.assertRaises(ValueError):
            BrokerListingCreate(
                title="Coastal Residence",
                category="real_estate",
                price=100000,
                currency="US",
                location_country="Sri Lanka",
                location_city="Galle",
                photos=["http://cdn.example.test/residence.jpg"],
            )


class TestListingMediaAndRateLimits(unittest.TestCase):
    def test_media_requires_https_and_descriptive_alt_text_for_visual_media(self):
        with self.assertRaises(ValueError):
            BrokerListingMediaInput(url="http://example.com/image.jpg", media_type="image", sort_order=0, alt_text="Villa")
        with self.assertRaises(ValueError):
            BrokerListingMediaInput(url="https://example.com/image.jpg", media_type="image", sort_order=0)
        image = BrokerListingMediaInput(
            url="https://example.com/image.jpg", media_type="image", sort_order=0, alt_text="Villa exterior"
        )
        video = BrokerListingMediaInput(url="https://example.com/tour", media_type="video", sort_order=1)
        self.assertEqual(image.alt_text, "Villa exterior")
        self.assertEqual(video.media_type, "video")

    def test_bulk_limiter_blocks_after_configured_window_capacity(self):
        limiter = InMemoryBulkRateLimiter()
        self.assertTrue(limiter.consume("101:7", maximum=1, window_seconds=60))
        self.assertFalse(limiter.consume("101:7", maximum=1, window_seconds=60))
        self.assertTrue(limiter.consume("102:7", maximum=1, window_seconds=60))


class TestListingUseCases(unittest.TestCase):
    def setUp(self):
        self.provider = Mock()
        self.provider.is_broker_approved.return_value = True
        self.config = SimpleNamespace(price_floors={}, minimum_media_count=0)

    def test_every_use_case_checks_permission(self):
        from backend.app.broker.domain.roles import BrokerRole
        cases = ListingUseCases(self.provider, set(), self.config, BrokerRole.broker_owner, actor_user_id=10)
        with self.assertRaises(PermissionError):
            cases.list_listings(
                permission=BrokerPermission.LISTING_VIEW_OWN,
                filters={}, limit=50, offset=0, sort="-created_at",
            )
        self.provider.list_listings.assert_not_called()

    def test_publish_checks_tenant_provider_eligibility_context(self):
        permissions = {BrokerPermission.LISTING_PUBLISH}
        from backend.app.broker.domain.roles import BrokerRole
        cases = ListingUseCases(self.provider, permissions, self.config, BrokerRole.broker_owner, actor_user_id=10)
        self.provider.get_publish_context.return_value = {
            "is_approved_broker": False,
            "has_active_plan": False,
            "valid_region_licence": False,
            "owner_consent": False,
            "category": "real_estate",
            "currency": "USD",
            "price": 10,
            "quality_score": 0,
            "media_count": 0,
        }
        with self.assertRaisesRegex(ValueError, "Cannot publish listing"):
            cases.set_listing_status(
                permission=BrokerPermission.LISTING_PUBLISH,
                listing_id=12,
                target_status="active",
            )
        self.provider.set_listing_status.assert_not_called()

    def test_agent_scope_is_applied_by_use_case(self):
        from backend.app.broker.domain.roles import BrokerRole
        cases = ListingUseCases(
            self.provider,
            {BrokerPermission.LISTING_VIEW_OWN},
            self.config,
            BrokerRole.broker_agent,
            actor_user_id=77,
        )
        cases.list_listings(
            permission=BrokerPermission.LISTING_VIEW_OWN,
            filters={"assigned_agent_id": 12},
            limit=20,
            offset=0,
            sort="-created_at",
        )
        self.provider.list_listings.assert_called_once_with(
            filters={"assigned_agent_id": 77}, limit=20, offset=0, sort="-created_at",
        )

    def test_agent_cannot_reassign_an_owned_listing(self):
        from backend.app.broker.domain.roles import BrokerRole
        cases = ListingUseCases(
            self.provider,
            {BrokerPermission.LISTING_EDIT},
            self.config,
            BrokerRole.broker_agent,
            actor_user_id=77,
        )
        with self.assertRaises(PermissionError):
            cases.update_listing(
                permission=BrokerPermission.LISTING_EDIT,
                listing_id=12,
                changes={"assigned_agent_id": 88},
                actor_user_id=77,
            )
        self.provider.update_listing.assert_not_called()

    def test_export_uses_provider_scope_and_csv_columns(self):
        from backend.app.broker.domain.roles import BrokerRole
        cases = ListingUseCases(
            self.provider,
            {BrokerPermission.LISTING_VIEW_OWN},
            self.config,
            BrokerRole.broker_owner,
            actor_user_id=10,
        )
        self.provider.list_listings.return_value = [{
            "title": "Villa", "category": "real_estate", "price": 100,
            "currency": "LKR", "location_country": "Sri Lanka", "location_city": "Galle",
        }]
        result = cases.export_listings(permission=BrokerPermission.LISTING_VIEW_OWN, limit=10, offset=0)
        self.assertIn("title,category,price,currency,location_country,location_city", result)
        self.assertIn("Villa,real_estate,100,LKR,Sri Lanka,Galle", result)


class TestBulkImportValidation(unittest.TestCase):
    def test_csv_without_data_rows_is_invalid(self):
        result = BulkImportService.validate_csv(
            "title,category,price,currency,location_country,location_city",
            price_floors={},
        )
        self.assertFalse(result["is_valid"])

    def test_csv_validation_reports_bad_rows_without_committing(self):
        result = BulkImportService.validate_csv(
            "title,category,price,currency,location_country,location_city\nBad,unknown,abc,USD,LK,Colombo",
            price_floors={},
        )
        self.assertFalse(result["is_valid"])
        self.assertEqual(result["invalid_rows"], 1)
        self.assertTrue(result["row_reports"][0]["errors"])


class TestBrokerListingRepositoryIsolation(unittest.TestCase):
    @patch.object(BrokerListing, "objects")
    def test_find_listing_is_scoped_to_organization_and_agent(self, objects):
        query = MagicMock()
        objects.return_value = query
        query.filter.return_value = query
        query.first.return_value = None
        repository = BrokerListingRepository(organization_id=100)
        self.assertIsNone(repository.find_listing(listing_id=50, assigned_agent_id=9))
        objects.assert_called_once_with(organization_id=100, listing_id=50, assigned_agent_id=9)
        query.filter.assert_called_once_with(is_deleted=False)


class TestListingContextIsolation(unittest.TestCase):
    def setUp(self):
        self.provider = Mock()
        self.access = ListingAccessUseCases(self.provider)
        self.provider.organization_exists.return_value = True

    def test_business_owner_role_comes_from_membership_when_present(self):
        from backend.app.broker.domain.roles import BrokerRole
        self.provider.find_owned_organization.return_value = 101
        self.provider.find_member_role.return_value = BrokerRole.broker_manager
        context = self.access.resolve(user_id=7, user_role="business_account", requested_organization_id=None)

        self.assertEqual(context.organization_id, 101)
        self.assertEqual(context.role, BrokerRole.broker_manager)

    def test_property_broker_owner_resolves_through_its_brokerage_profile(self):
        from backend.app.broker.domain.roles import BrokerRole
        self.provider.find_owned_organization.return_value = 303
        self.provider.find_member_role.return_value = None
        context = self.access.resolve(user_id=8, user_role="broker_account", requested_organization_id=None)

        self.assertEqual(context.organization_id, 303)
        self.assertEqual(context.role, BrokerRole.broker_owner)

    def test_standard_user_requires_an_active_membership(self):
        from backend.app.broker.domain.roles import BrokerRole
        self.provider.list_member_roles.return_value = [(202, BrokerRole.broker_agent)]
        context = self.access.resolve(user_id=9, user_role="standard_user", requested_organization_id=None)

        self.assertEqual(context.organization_id, 202)
        self.assertEqual(context.role, BrokerRole.broker_agent)

    def test_private_seller_and_platform_admin_are_denied(self):
        for role in ("private_seller", "super_admin"):
            with self.subTest(role=role):
                with self.assertRaises(PermissionError):
                    self.access.resolve(user_id=9, user_role=role, requested_organization_id=None)


class TestListingApi(unittest.TestCase):
    def setUp(self):
        from backend.app.broker.domain.roles import BrokerRole
        self.provider = Mock()
        self.provider.is_broker_approved.return_value = True
        self.provider.list_categories.return_value = ["real_estate"]
        self.provider.list_listings.return_value = []
        self.provider.get_publish_context.return_value = {
            "is_approved_broker": True,
            "has_active_plan": True,
            "valid_region_licence": True,
            "owner_consent": True,
            "category": "real_estate",
            "currency": "USD",
            "price": 100,
            "quality_score": 80,
            "media_count": 5,
        }
        self.item = {
            "id": 1,
            "organization_id": 101,
            "listing_id": 501,
            "title": "Coastal Residence",
            "description": "",
            "category": "real_estate",
            "price": 100,
            "currency": "USD",
            "location_country": "Sri Lanka",
            "location_city": "Galle",
            "status": "draft",
            "moderation_status": "pending",
            "owner_consent": True,
            "quality_score": 80,
            "quality_rating": "green",
            "quality_suggestions": [],
            "urgent_flag": False,
            "photos": [],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        self.provider.create_listing.return_value = self.item
        self.provider.set_listing_status.return_value = self.item
        self.provider.update_listing.return_value = None
        self.provider.list_revisions.return_value = []
        self.cases = ListingUseCases(
            self.provider,
            set(BrokerPermission),
            SimpleNamespace(price_floors={}, minimum_media_count=0, maximum_bulk_rows=500, categories=("real_estate",)),
            BrokerRole.broker_owner,
            actor_user_id=7,
        )
        app = FastAPI()
        app.include_router(listing_router)
        app.dependency_overrides[get_listing_context] = lambda: ListingContext(
            user=MagicMock(id=7), organization_id=101, role=BrokerRole.broker_owner,
            permissions=set(BrokerPermission),
        )
        app.dependency_overrides[get_listing_use_cases] = lambda: self.cases
        self.client = TestClient(app)

    def test_listing_endpoints_cover_create_read_edit_publish_archive_import_export_and_forbidden(self):
        created = self.client.post(
            "/listings",
            headers={"Idempotency-Key": "create-key-123"},
            json={
                "title": "Coastal Residence",
                "category": "real_estate",
                "price": 100,
                "currency": "USD",
                "location_country": "Sri Lanka",
                "location_city": "Galle",
                "owner_consent": True,
            },
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(self.client.get("/listings").status_code, 200)
        self.assertEqual(self.client.get("/listings/categories").json(), ["real_estate"])
        self.assertEqual(self.client.get("/listings/501/revisions").status_code, 200)

        # A listing absent from the organization-scoped provider is not writable.
        self.assertEqual(self.client.patch("/listings/501", json={"title": "Revised Residence"}).status_code, 404)
        self.assertEqual(self.client.post("/listings/501/publish").status_code, 200)
        self.assertEqual(self.client.post("/listings/501/pause").status_code, 200)
        self.assertEqual(self.client.delete("/listings/501").status_code, 204)

        csv_body = "title,category,price,currency,location_country,location_city\nVilla,real_estate,100,USD,LK,Galle"
        self.assertTrue(self.client.post("/listings/bulk/validate", json={"csv_content": csv_body}).json()["is_valid"])
        imported = self.client.post(
            "/listings/bulk/import",
            headers={"Idempotency-Key": "bulk-key-123"},
            json={"csv_content": csv_body},
        )
        self.assertEqual(imported.status_code, 200)
        self.assertIn("title,category,price,currency", self.client.get("/listings/export.csv").text)

        self.cases.permissions = set()
        self.assertEqual(self.client.get("/listings").status_code, 403)


if __name__ == "__main__":
    unittest.main()
