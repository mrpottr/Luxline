"""Broker organization analytics and CSV export endpoints."""

from datetime import date, timedelta
from hashlib import blake2s

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from backend.app.broker.api.analytics_dependencies import get_analytics_use_cases
from backend.app.broker.api.analytics_dependencies import get_public_view_use_case
from backend.app.broker.application.analytics_use_cases import AnalyticsUseCases
from backend.app.broker.application.public_view_use_case import (
    ListingViewRateLimitExceeded,
    RecordPublicListingView,
)
from backend.app.broker.api.trust_dependencies import get_broker_trust_use_cases
from backend.app.broker.application.trust_use_cases import BrokerTrustUseCases
from backend.app.core.config import settings
from backend.app.broker.schemas import BrokerAnalyticsOut
from pydantic import BaseModel, Field

router = APIRouter(prefix="/analytics", tags=["broker-analytics"])
view_router = APIRouter(prefix="/analytics", tags=["broker-analytics"])


class ListingViewIn(BaseModel):
    listing_id: int = Field(ge=1)


def _execute(operation):
    try:
        return operation()
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def _default_start() -> date:
    return date.today() - timedelta(days=29)


@view_router.post("/views", status_code=204)
def record_listing_view(
    payload: ListingViewIn,
    request: Request,
    cases: RecordPublicListingView = Depends(get_public_view_use_case),
):
    return _record_public_listing_event(payload, request, cases, "listing_view")


@view_router.post("/impressions", status_code=204)
def record_listing_impression(
    payload: ListingViewIn,
    request: Request,
    cases: RecordPublicListingView = Depends(get_public_view_use_case),
):
    return _record_public_listing_event(payload, request, cases, "listing_impression")


def _record_public_listing_event(payload, request, cases, event_type: str):
    if not settings.broker_panel_enabled:
        raise HTTPException(status_code=404, detail="Broker Panel is disabled on this environment")
    client_host = request.client.host if request.client else "unknown"
    client_key = int.from_bytes(blake2s(f"{payload.listing_id}:{client_host}".encode(), digest_size=4).digest(), "big") + 1
    try:
        recorded = cases.execute(listing_id=payload.listing_id, visitor_key=client_key, event_type=event_type)
    except ListingViewRateLimitExceeded as error:
        raise HTTPException(status_code=429, detail=str(error)) from error
    if not recorded:
        raise HTTPException(status_code=404, detail="Listing not found")
    return None


@router.get("", response_model=BrokerAnalyticsOut)
def get_broker_analytics(
    date_from: date = Query(default_factory=_default_start),
    date_to: date = Query(default_factory=date.today),
    listing_id: int | None = Query(default=None, ge=1),
    agent_id: int | None = Query(default=None, ge=1),
    cases: AnalyticsUseCases = Depends(get_analytics_use_cases),
):
    return _execute(lambda: cases.report(
        start=date_from, end=date_to, listing_id=listing_id, agent_id=agent_id,
    ))


@router.get("/export.csv")
def export_broker_analytics(
    date_from: date = Query(default_factory=_default_start),
    date_to: date = Query(default_factory=date.today),
    dimension: str = Query(default="listing", pattern="^(listing|agent)$"),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    cases: AnalyticsUseCases = Depends(get_analytics_use_cases),
    audit: BrokerTrustUseCases = Depends(get_broker_trust_use_cases),
):
    content = _execute(lambda: cases.export_csv(
        start=date_from, end=date_to, dimension=dimension, limit=limit, offset=offset,
    ))
    _execute(lambda: audit.record_data_export(
        dimension=dimension, date_from=date_from.isoformat(), date_to=date_to.isoformat(),
    ))
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=broker-analytics.csv"},
    )
