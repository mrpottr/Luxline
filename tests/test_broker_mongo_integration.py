"""Opt-in repository integration checks against an isolated MongoDB database.

Set BROKER_TEST_DATABASE_URL to a disposable database named broker_test_*.
The test suite never falls back to the application's DATABASE_URL.
"""

import os
import unittest
from uuid import uuid4

from mongoengine import connect, disconnect
from pymongo import MongoClient
from pymongo.uri_parser import parse_uri

from backend.app.broker.repositories.listing_repository import BrokerListingRepository
from backend.app.broker.services.mongo_bulk_rate_limiter import MongoBulkRateLimiter
from backend.app.broker.services.mongo_media_storage import MongoMockMediaStorage


TEST_DATABASE_URL = os.getenv("BROKER_TEST_DATABASE_URL")


@unittest.skipUnless(TEST_DATABASE_URL, "BROKER_TEST_DATABASE_URL must point to an isolated broker_test_* database")
class TestBrokerMongoTenantIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parsed = parse_uri(TEST_DATABASE_URL)
        cls.database_name = parsed.get("database") or ""
        if not cls.database_name.startswith("broker_test_"):
            raise RuntimeError("Refusing MongoDB integration test outside a broker_test_* database")
        disconnect(alias="default")
        connect(db=cls.database_name, host=TEST_DATABASE_URL, alias="default", uuidRepresentation="standard")

    @classmethod
    def tearDownClass(cls):
        disconnect(alias="default")
        if os.getenv("BROKER_TEST_ALLOW_DB_DROP") == "true":
            client = MongoClient(TEST_DATABASE_URL, serverSelectionTimeoutMS=3000)
            client.drop_database(cls.database_name)
            client.close()

    def test_repositories_never_read_or_write_another_organizations_listing(self):
        organization_a = int(uuid4().int % 2_000_000_000) + 1
        organization_b = int(uuid4().int % 2_000_000_000) + 1
        listing_id = int(uuid4().int % 2_000_000_000) + 1
        payload_hash = "a" * 64
        repository_a = BrokerListingRepository(organization_a)
        repository_b = BrokerListingRepository(organization_b)

        created = repository_a.create(
            listing_id=listing_id,
            idempotency_key=f"integration-{uuid4().hex}",
            idempotency_payload_hash=payload_hash,
        )

        self.assertIsNotNone(repository_a.find_listing(listing_id))
        self.assertIsNone(repository_b.find_listing(listing_id))
        self.assertIsNone(repository_b.find_by_idempotency_key(created.idempotency_key))
        self.assertIsNone(repository_b.update(created.id, quality_score=100))
        self.assertFalse(repository_b.soft_delete(created.id))
        self.assertEqual(repository_a.find_listing(listing_id).quality_score, 0)

    def test_mongo_bulk_rate_limit_is_shared_and_tenant_keyed(self):
        limiter = MongoBulkRateLimiter()
        organization_id = int(uuid4().int % 2_000_000_000) + 1
        user_id = int(uuid4().int % 2_000_000_000) + 1
        self.assertTrue(limiter.consume(f"{organization_id}:{user_id}", maximum=1, window_seconds=60))
        self.assertFalse(limiter.consume(f"{organization_id}:{user_id}", maximum=1, window_seconds=60))
        self.assertTrue(limiter.consume(f"{organization_id + 1}:{user_id}", maximum=1, window_seconds=60))

    def test_signed_media_is_readable_only_for_its_tenant(self):
        storage = MongoMockMediaStorage("https://media.example.test")
        stored = storage.store(
            organization_id=81,
            content=b"\x89PNG\r\n\x1a\ncontent",
            content_type="image/png",
            media_type="image",
            alt_text="Building exterior",
        )
        asset = storage.read_signed(
            asset_id=stored["asset_id"],
            organization_id=81,
            expires=stored["expires_at"],
            token=stored["url"].split("token=")[-1],
        )
        self.assertIsNotNone(asset)
        self.assertEqual(bytes(asset.content), b"\x89PNG\r\n\x1a\ncontent")
        self.assertIsNone(storage.read_signed(
            asset_id=stored["asset_id"],
            organization_id=82,
            expires=stored["expires_at"],
            token=stored["url"].split("token=")[-1],
        ))


if __name__ == "__main__":
    unittest.main()
