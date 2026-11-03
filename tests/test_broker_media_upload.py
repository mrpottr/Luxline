"""Pure use-case tests for broker media upload checks."""

import unittest
import base64
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.broker.application.media_upload_use_cases import MediaUploadUseCases
from backend.app.broker.domain.roles import BrokerPermission
from backend.app.broker.api.listing_dependencies import ListingContext, get_listing_context
from backend.app.broker.api.media import get_media_use_cases, router as media_router
from backend.app.broker.domain.roles import BrokerRole


class FakeStorage:
    def __init__(self):
        self.arguments = None

    def store(self, **kwargs):
        self.arguments = kwargs
        return {
            "asset_id": 321,
            "organization_id": kwargs["organization_id"],
            "url": "https://media.example.test/signed",
            "content_type": kwargs["content_type"],
            "media_type": kwargs["media_type"],
            "alt_text": kwargs["alt_text"],
            "moderation_state": "pending",
            "expires_at": 1_900_000_000,
        }


class FakeScanner:
    def __init__(self, clean=True):
        self.clean = clean

    def scan(self, content):
        return self.clean


class FakeListingProvider:
    def __init__(self, approved=True):
        self.approved = approved

    def is_broker_approved(self):
        return self.approved


class FakeLimiter:
    def consume(self, key, *, maximum, window_seconds):
        return True


class TestBrokerMediaUpload(unittest.TestCase):
    def setUp(self):
        self.storage = FakeStorage()
        self.use_cases = MediaUploadUseCases(
            self.storage,
            FakeScanner(),
            FakeListingProvider(),
            {BrokerPermission.LISTING_CREATE},
            FakeLimiter(),
            20,
            9,
        )

    def test_upload_checks_signature_and_stores_valid_image(self):
        content = b"\x89PNG\r\n\x1a\nvalid image bytes"
        result = self.use_cases.upload(
            organization_id=72,
            content=content,
            content_type="image/png",
            media_type="image",
            alt_text="Front entrance",
        )
        self.assertEqual(result["moderation_state"], "pending")
        self.assertEqual(self.storage.arguments["organization_id"], 72)

    def test_declared_type_must_match_file_signature(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.use_cases.upload(
                organization_id=72,
                content=b"not a png",
                content_type="image/png",
                media_type="image",
                alt_text="Front entrance",
            )

    def test_upload_requires_permission_approval_alt_text_and_clean_scan(self):
        for cases, values in [
            (MediaUploadUseCases(self.storage, FakeScanner(), FakeListingProvider(), set(), FakeLimiter(), 20, 9), {"alt_text": "View"}),
            (MediaUploadUseCases(self.storage, FakeScanner(), FakeListingProvider(False), {BrokerPermission.LISTING_CREATE}, FakeLimiter(), 20, 9), {"alt_text": "View"}),
            (self.use_cases, {"alt_text": ""}),
            (MediaUploadUseCases(self.storage, FakeScanner(False), FakeListingProvider(), {BrokerPermission.LISTING_CREATE}, FakeLimiter(), 20, 9), {"alt_text": "View"}),
        ]:
            with self.subTest(cases=cases):
                with self.assertRaises((PermissionError, ValueError)):
                    cases.upload(
                        organization_id=72,
                        content=b"\x89PNG\r\n\x1a\nvalid",
                        content_type="image/png",
                        media_type="image",
                        **values,
                    )

    def test_upload_endpoint_validates_base64_and_returns_signed_media_result(self):
        app = FastAPI()
        app.include_router(media_router)
        context = ListingContext(
            user=MagicMock(id=9),
            organization_id=72,
            role=BrokerRole.broker_owner,
            permissions={BrokerPermission.LISTING_CREATE},
        )
        app.dependency_overrides[get_listing_context] = lambda: context
        app.dependency_overrides[get_media_use_cases] = lambda: self.use_cases
        client = TestClient(app)
        payload = {
            "content_base64": base64.b64encode(b"\x89PNG\r\n\x1a\nvalid image bytes").decode("ascii"),
            "content_type": "image/png",
            "media_type": "image",
            "alt_text": "Front entrance",
        }

        response = client.post("/media/upload", json=payload)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["url"].startswith("https://media.example.test/"))
        self.assertEqual(response.json()["moderation_state"], "pending")

        payload["content_base64"] = "%%%"
        self.assertEqual(client.post("/media/upload", json=payload).status_code, 422)


if __name__ == "__main__":
    unittest.main()
