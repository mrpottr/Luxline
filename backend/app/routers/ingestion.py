"""Asynchronous-style broker feed ingestion staging endpoints."""

import csv
import io
import json
import xml.etree.ElementTree as ET

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.dependencies import require_roles
from backend.app.models import BrokerFeed, IngestionJob, IngestionRow, OutboxEvent, User, UserRole
from backend.app.schemas import BrokerFeedCreate, BrokerFeedOut, IngestionJobCreate, IngestionJobOut, IngestionRowOut
from backend.app.services.ingestion.service import IngestionWorker


router = APIRouter(prefix="/ingestion", tags=["ingestion"])


def _parse_rows(source_type: str, content: str | None) -> list[dict]:
    if not content:
        return []

    if source_type == "json":
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            parsed = parsed.get("listings", [])
        if not isinstance(parsed, list):
            raise ValueError("JSON content must be a list or an object with a listings array")
        return [row for row in parsed if isinstance(row, dict)]

    if source_type == "csv":
        return [dict(row) for row in csv.DictReader(io.StringIO(content))]

    if source_type == "xml":
        root = ET.fromstring(content)
        return [{child.tag: (child.text or "").strip() for child in node} for node in root.findall(".//listing")]

    return []


@router.post("/feeds", response_model=BrokerFeedOut, status_code=status.HTTP_201_CREATED)
def create_feed(
    payload: BrokerFeedCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.business_account, UserRole.super_admin)),
):
    """Register a broker feed definition for scheduled or manual ingestion."""
    source_type = payload.source_type.strip().lower()
    if source_type not in {"json", "xml", "csv", "url"}:
        raise HTTPException(status_code=400, detail="Unsupported feed source type")

    feed = BrokerFeed(
        owner_user_id=current_user.id,
        name=payload.name,
        source_type=source_type,
        pull_url=payload.pull_url,
        mapping_json=payload.mapping_json,
        schedule_cron=payload.schedule_cron,
    )
    db.add(feed)
    db.commit()
    db.refresh(feed)
    return feed


@router.get("/feeds", response_model=list[BrokerFeedOut])
def list_feeds(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.business_account, UserRole.super_admin)),
):
    """List feed definitions visible to the current broker/admin."""
    query = db.query(BrokerFeed).order_by(BrokerFeed.created_at.desc())
    if current_user.role != UserRole.super_admin:
        query = query.filter(BrokerFeed.owner_user_id == current_user.id)
    return query.limit(100).all()


@router.post("/jobs", response_model=IngestionJobOut, status_code=status.HTTP_201_CREATED)
def create_ingestion_job(
    payload: IngestionJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.business_account, UserRole.super_admin)),
):
    """Stage a bulk ingestion job and trigger background processing."""
    source_type = payload.source_type.strip().lower()
    if source_type not in {"json", "xml", "csv", "url"}:
        raise HTTPException(status_code=400, detail="Unsupported ingestion source type")

    rows: list[dict] = []
    error_json: dict = {}
    if payload.content:
        try:
            rows = _parse_rows(source_type, payload.content)
        except (ValueError, json.JSONDecodeError, ET.ParseError) as exc:
            error_json = {"parse_error": str(exc)}

    job = IngestionJob(
        owner_user_id=current_user.id,
        feed_id=payload.feed_id,
        source_type=source_type,
        status="queued" if not error_json else "failed",
        total_rows=len(rows),
        failed_rows=1 if error_json else 0,
        error_json=error_json,
    )
    db.add(job)
    db.flush()

    for index, row in enumerate(rows):
        external_id = row.get("external_id") or row.get("id") or row.get("reference")
        db.add(
            IngestionRow(
                job_id=job.id,
                external_id=str(external_id) if external_id else None,
                row_payload=row,
                status="staged",
            )
        )

    db.add(
        OutboxEvent(
            aggregate_type="ingestion_job",
            aggregate_id=str(job.id),
            event_type="ingestion.job.created",
            payload={"job_id": job.id, "source_type": source_type, "row_count": len(rows)},
        )
    )
    db.commit()
    db.refresh(job)
    
    if job.status == "queued":
        background_tasks.add_task(IngestionWorker.process_job_background, job.id)
        
    return job


@router.get("/jobs", response_model=list[IngestionJobOut])
def list_ingestion_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.business_account, UserRole.super_admin)),
):
    """List recent ingestion jobs."""
    query = db.query(IngestionJob).order_by(IngestionJob.created_at.desc())
    if current_user.role != UserRole.super_admin:
        query = query.filter(IngestionJob.owner_user_id == current_user.id)
    return query.limit(100).all()


@router.get("/jobs/{job_id}/rows", response_model=list[IngestionRowOut])
def list_ingestion_rows(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.business_account, UserRole.super_admin)),
):
    """Return staged row details and validation errors for a job."""
    job_query = db.query(IngestionJob).filter(IngestionJob.id == job_id)
    if current_user.role != UserRole.super_admin:
        job_query = job_query.filter(IngestionJob.owner_user_id == current_user.id)
    if not job_query.first():
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    return db.query(IngestionRow).filter(IngestionRow.job_id == job_id).order_by(IngestionRow.id.asc()).limit(500).all()

