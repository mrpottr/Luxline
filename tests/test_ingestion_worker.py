"""Ingestion worker persistence ordering tests."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.app.services.ingestion.service import IngestionWorker


class TestIngestionWorker(unittest.TestCase):
    @patch("backend.app.services.ingestion.service.Listing")
    @patch("backend.app.services.ingestion.service.IngestionRow")
    @patch("backend.app.services.ingestion.service.IngestionJob")
    @patch("backend.app.services.ingestion.service.SessionLocal")
    def test_flushes_listing_before_assigning_generated_id(self, session_factory, jobs, rows, listings):
        session = MagicMock()
        session_factory.return_value.__enter__.return_value = session
        job = SimpleNamespace(status="queued", failed_rows=0, owner_user_id=7, success_rows=0)
        row = SimpleNamespace(id=15, job_id=31, row_payload={"title": "Residence", "category": "real_estate"}, external_id="ext-1", status="staged")
        listing = SimpleNamespace(id=None)
        jobs.objects.return_value.first.return_value = job
        rows.objects.return_value = [row]
        listings.return_value = listing

        def flush(document):
            if document is listing:
                document.id = 9301

        session.flush.side_effect = flush
        IngestionWorker.process_job_background(31)

        self.assertEqual(row.status, "processed", getattr(row, "error_json", None))
        self.assertEqual(row.listing_id, 9301)
        session.flush.assert_called_once_with(listing)


if __name__ == "__main__":
    unittest.main()
