"""Ingestion background worker service."""

import uuid

from backend.app.db.session import SessionLocal
from backend.app.models import IngestionJob, IngestionRow, Listing, ListingCategory, ListingStatus, ModerationStatus


class IngestionWorker:
    @staticmethod
    def process_job_background(job_id: int):
        """Process an ingestion job asynchronously in a separate DB session."""
        with SessionLocal() as db:
            job = IngestionJob.objects(id=job_id).first()
            if not job or job.status != "queued":
                return
            
            job.status = "processing"
            db.add(job)
            db.commit()
            
            try:
                rows = list(IngestionRow.objects(job_id=job_id, status="staged"))
                
                success_count = 0
                failed_count = job.failed_rows or 0
                
                for row in rows:
                    try:
                        # In a real app, this would use a complex mapper.
                        # For now, we stub a basic listing creation to satisfy the workflow.
                        payload = row.row_payload or {}
                        
                        listing = Listing(
                            seller_id=job.owner_user_id,
                            category=ListingCategory(payload.get("category", "car").lower()),
                            title=payload.get("title", f"Imported Listing {row.external_id or row.id}"),
                            slug=f"imported-listing-{row.job_id}-{row.id}-{uuid.uuid4().hex[:8]}",
                            status=ListingStatus.draft,
                            moderation_status=ModerationStatus.pending,
                            currency=payload.get("currency", "USD"),
                            price=float(payload.get("price", 0)),
                        )
                        db.add(listing)
                        
                        row.status = "processed"
                        row.listing_id = listing.id
                        db.add(row)
                        success_count += 1
                    except Exception as exc:
                        row.status = "failed"
                        row.error_json = {"error": str(exc)}
                        db.add(row)
                        failed_count += 1
                        
                job.success_rows = success_count
                job.failed_rows = failed_count
                job.status = "completed"
                db.add(job)
                db.commit()
            except Exception as e:
                db.rollback()
                job.status = "failed"
                job.error_json = {"worker_error": str(e)}
                db.add(job)
                db.commit()
