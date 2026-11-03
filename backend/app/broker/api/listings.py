"""HTTP controllers for broker listing operations."""

from typing import Annotated
from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, status
from fastapi.responses import Response

from backend.app.broker.application.listing_use_cases import ListingUseCases, TooManyBulkRequests
from backend.app.broker.api.listing_dependencies import ListingContext, get_listing_context
from backend.app.broker.config import listing_config
from backend.app.broker.domain.roles import BrokerPermission
from backend.app.broker.schemas import (
    BrokerListingCreate, BrokerListingOut, BrokerListingUpdate, BrokerListingRevisionOut, BulkImportRequest,
)
from backend.app.broker.services.listing_provider import MongoListingProvider
from backend.app.broker.services.bulk_rate_limiter import InMemoryBulkRateLimiter

router = APIRouter(prefix="/listings", tags=["broker-listings"])
bulk_rate_limiter = InMemoryBulkRateLimiter()


def get_listing_use_cases(context: ListingContext = Depends(get_listing_context)) -> ListingUseCases:
    provider = MongoListingProvider(context.organization_id)
    return ListingUseCases(
        provider, context.permissions, listing_config, context.role, context.user.id,
        bulk_rate_limiter, context.organization_id,
    )


def _execute(call):
    try:
        return call()
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except TooManyBulkRequests as error:
        raise HTTPException(status_code=429, detail=str(error)) from error


@router.get("", response_model=list[BrokerListingOut])
def list_broker_listings(
    category: str | None = Query(default=None, max_length=64),
    quality_rating: str | None = Query(default=None, pattern="^(green|orange|red)$"),
    agent_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: str = Query(default="-created_at", max_length=32),
    cases: ListingUseCases = Depends(get_listing_use_cases),
    context: ListingContext = Depends(get_listing_context),
):
    filters = {key: value for key, value in {
        "quality_rating": quality_rating.lower() if quality_rating else None,
        "assigned_agent_id": agent_id if context.role.value != "broker_agent" else context.user.id,
    }.items() if value is not None}
    if category:
        filters["category"] = category.lower()
    return _execute(lambda: cases.list_listings(
        permission=BrokerPermission.LISTING_VIEW_OWN,
        filters=filters,
        limit=limit,
        offset=offset,
        sort=sort,
    ))


@router.get("/categories")
def list_listing_categories(cases: ListingUseCases = Depends(get_listing_use_cases)):
    return _execute(lambda: cases.list_categories(permission=BrokerPermission.LISTING_VIEW_OWN))


@router.get("/export.csv")
def export_broker_listings_csv(
    limit: int = Query(default=500, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    cases: ListingUseCases = Depends(get_listing_use_cases),
):
    content = _execute(lambda: cases.export_listings(
        permission=BrokerPermission.LISTING_VIEW_OWN,
        limit=limit,
        offset=offset,
    ))
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=broker-listings.csv"},
    )


@router.post("", response_model=BrokerListingOut, status_code=status.HTTP_201_CREATED)
def create_broker_listing(
    payload: BrokerListingCreate,
    idempotency_key: str = Header(min_length=8, max_length=128, alias="Idempotency-Key"),
    context: ListingContext = Depends(get_listing_context),
    cases: ListingUseCases = Depends(get_listing_use_cases),
):
    data = payload.model_dump(mode="json", exclude={"photos"})
    data["photos"] = payload.photos
    return _execute(lambda: cases.create_listing(
        permission=BrokerPermission.LISTING_CREATE,
        payload=data,
        user_id=context.user.id,
        idempotency_key=idempotency_key,
    ))


@router.patch("/{listing_id}", response_model=BrokerListingOut)
def update_broker_listing(
    listing_id: Annotated[int, Path(ge=1)],
    payload: BrokerListingUpdate,
    context: ListingContext = Depends(get_listing_context),
    cases: ListingUseCases = Depends(get_listing_use_cases),
):
    result = _execute(lambda: cases.update_listing(
        permission=BrokerPermission.LISTING_EDIT,
        listing_id=listing_id,
        changes=payload.model_dump(exclude_unset=True),
        actor_user_id=context.user.id,
    ))
    if result is None:
        raise HTTPException(status_code=404, detail="Broker listing not found")
    return result


@router.get("/{listing_id}/revisions", response_model=list[BrokerListingRevisionOut])
def list_broker_listing_revisions(
    listing_id: Annotated[int, Path(ge=1)],
    cases: ListingUseCases = Depends(get_listing_use_cases),
):
    result = _execute(lambda: cases.list_revisions(
        permission=BrokerPermission.LISTING_VIEW_OWN,
        listing_id=listing_id,
        limit=50,
    ))
    if result is None:
        raise HTTPException(status_code=404, detail="Broker listing not found")
    return result


@router.post("/{listing_id}/publish", response_model=BrokerListingOut)
def publish_broker_listing(listing_id: Annotated[int, Path(ge=1)], cases: ListingUseCases = Depends(get_listing_use_cases)):
    result = _execute(lambda: cases.set_listing_status(
        permission=BrokerPermission.LISTING_PUBLISH, listing_id=listing_id, target_status="active",
    ))
    if result is None:
        raise HTTPException(status_code=404, detail="Broker listing not found")
    return result


@router.post("/{listing_id}/pause", response_model=BrokerListingOut)
def pause_broker_listing(listing_id: Annotated[int, Path(ge=1)], cases: ListingUseCases = Depends(get_listing_use_cases)):
    result = _execute(lambda: cases.set_listing_status(
        permission=BrokerPermission.LISTING_EDIT, listing_id=listing_id, target_status="draft",
    ))
    if result is None:
        raise HTTPException(status_code=404, detail="Broker listing not found")
    return result


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_broker_listing(listing_id: Annotated[int, Path(ge=1)], cases: ListingUseCases = Depends(get_listing_use_cases)):
    result = _execute(lambda: cases.set_listing_status(
        permission=BrokerPermission.LISTING_DELETE, listing_id=listing_id, target_status="archived",
    ))
    if result is None:
        raise HTTPException(status_code=404, detail="Broker listing not found")


@router.post("/bulk/validate")
def validate_bulk_listings_csv(
    payload: BulkImportRequest,
    context: ListingContext = Depends(get_listing_context),
    cases: ListingUseCases = Depends(get_listing_use_cases),
):
    return _execute(lambda: cases.validate_bulk_import(
        permission=BrokerPermission.LISTING_CREATE,
        csv_content=payload.csv_content,
        user_id=context.user.id,
        idempotency_key="",
        commit=False,
    ))


@router.post("/bulk/import")
def import_validated_listings_csv(
    payload: BulkImportRequest,
    context: ListingContext = Depends(get_listing_context),
    idempotency_key: str = Header(default="", max_length=128, alias="Idempotency-Key"),
    cases: ListingUseCases = Depends(get_listing_use_cases),
):
    return _execute(lambda: cases.validate_bulk_import(
        permission=BrokerPermission.LISTING_CREATE,
        csv_content=payload.csv_content,
        user_id=context.user.id,
        idempotency_key=idempotency_key,
        commit=True,
    ))
