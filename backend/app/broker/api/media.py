"""Broker media upload and signed-read endpoints."""

import base64
import binascii
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response

from backend.app.broker.api.listing_dependencies import ListingContext, get_listing_context
from backend.app.broker.application.media_upload_use_cases import MediaUploadUseCases, MockVirusScanner, TooManyMediaUploads
from backend.app.broker.config import listing_config
from backend.app.broker.schemas import BrokerMediaUploadOut, BrokerMediaUploadRequest
from backend.app.broker.services.listing_provider import MongoListingProvider
from backend.app.broker.services.mongo_media_storage import MongoMockMediaStorage
from backend.app.broker.services.mongo_bulk_rate_limiter import broker_rate_limiter

router = APIRouter(prefix="/media", tags=["broker-media"])


def get_media_use_cases(
    request: Request,
    context: ListingContext = Depends(get_listing_context),
) -> MediaUploadUseCases:
    if os.getenv("BROKER_MEDIA_STORAGE", "mock_mongo") != "mock_mongo":
        raise HTTPException(status_code=503, detail="Configured broker media storage provider is unavailable")
    if os.getenv("BROKER_VIRUS_SCANNER", "mock") != "mock":
        raise HTTPException(status_code=503, detail="Configured broker virus scanner is unavailable")
    storage = MongoMockMediaStorage(str(request.base_url))
    provider = MongoListingProvider(context.organization_id)
    return MediaUploadUseCases(
        storage,
        MockVirusScanner(),
        provider,
        context.permissions,
        broker_rate_limiter,
        listing_config.media_uploads_per_minute,
        context.user.id,
    )


@router.post("/upload", response_model=BrokerMediaUploadOut, status_code=status.HTTP_201_CREATED)
def upload_broker_media(
    payload: BrokerMediaUploadRequest,
    context: ListingContext = Depends(get_listing_context),
    use_cases: MediaUploadUseCases = Depends(get_media_use_cases),
):
    try:
        content = base64.b64decode(payload.content_base64, validate=True)
    except (binascii.Error, ValueError) as error:
        raise HTTPException(status_code=422, detail="content_base64 must contain valid base64 data") from error
    try:
        return use_cases.upload(
            organization_id=context.organization_id,
            content=content,
            content_type=payload.content_type,
            media_type=payload.media_type,
            alt_text=payload.alt_text,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except TooManyMediaUploads as error:
        raise HTTPException(status_code=429, detail=str(error)) from error


@router.get("/{asset_id}", name="read_broker_media")
def read_broker_media(
    asset_id: int,
    organization_id: int = Query(ge=1),
    expires: int = Query(ge=1),
    token: str = Query(min_length=64, max_length=64),
):
    asset = MongoMockMediaStorage("").read_signed(
        asset_id=asset_id,
        organization_id=organization_id,
        expires=expires,
        token=token,
    )
    if asset is None:
        raise HTTPException(status_code=404, detail="Signed media URL is invalid or expired")
    return Response(
        content=bytes(asset.content),
        media_type=asset.content_type,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=300",
            "Content-Disposition": "attachment" if asset.content_type == "application/pdf" else "inline",
        },
    )
