"""Listing management, retrieval, and import endpoints."""

from datetime import datetime
import csv
import io
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.dependencies import get_current_user, get_optional_current_user, require_roles
from backend.app.models import (
    AgencyProfile,
    Listing,
    ListingCategory,
    ListingMedia,
    ListingStatus,
    ModerationStatus,
    OutboxEvent,
    RealEstateListing,
    RentalTerms,
    SavedListing,
    User,
    UserRole,
    VehicleListing,
    VesselAircraftListing,
    WatchJewelryListing,
)
from backend.app.schemas import (
    ListingCreate,
    ListingFeedImportRequest,
    ListingImportRequest,
    ListingOut,
    ListingUpdate,
)
from backend.app.utils import slugify
from backend.app.services.inventory.service import InventoryService


router = APIRouter(prefix="/listings", tags=["listings"])


def ensure_unique_slug(db: Session, base_slug: str) -> str:
    """Generate a unique listing slug by appending an incrementing suffix."""
    slug = base_slug
    counter = 2
    while db.query(Listing).filter(Listing.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def _parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None



@router.post("", response_model=ListingOut, status_code=status.HTTP_201_CREATED)
def create_listing(
    payload: ListingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.private_seller, UserRole.business_account, UserRole.super_admin)
    ),
):
    """Create a new listing for eligible seller roles and attach media items."""
    agency_id = None
    if current_user.role == UserRole.business_account:
        agency = db.query(AgencyProfile).filter(AgencyProfile.owner_id == current_user.id).first()
        agency_id = agency.id if agency else None

    base_slug = slugify(f"{payload.category.value}-{payload.make or ''}-{payload.model or ''}-{payload.title}")
    slug = ensure_unique_slug(db, base_slug or f"listing-{int(datetime.utcnow().timestamp())}")
    listing = Listing(
        seller_id=current_user.id,
        agency_id=agency_id,
        title=payload.title,
        slug=slug,
        description=payload.description,
        category=payload.category,
        status=payload.status,
        moderation_status=ModerationStatus.pending,
        location_country=payload.location_country,
        location_city=payload.location_city,
        location_address=payload.location_address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        currency=payload.currency.upper(),
        price=payload.price,
        year=payload.year,
        make=payload.make,
        model=payload.model,
        condition=payload.condition,
        bedrooms=payload.bedrooms,
        bathrooms=payload.bathrooms,
        square_footage=payload.square_footage,
        mileage=payload.mileage,
        draft_depth=payload.draft_depth,
        beam_width=payload.beam_width,
        attributes=payload.attributes,
    )
    if payload.status == ListingStatus.active:
        listing.published_at = datetime.utcnow()

    db.add(listing)
    db.flush()
    InventoryService.upsert_listing_details(db, listing, payload.details)
    InventoryService.queue_listing_changed(db, listing, "created")

    for media in payload.media_items:
        db.add(
            ListingMedia(
                listing_id=listing.id,
                media_type=media.media_type,
                url=media.url,
                sort_order=media.sort_order,
            )
        )

    db.commit()
    db.refresh(listing)
    return listing


@router.get("", response_model=list[ListingOut])
def list_listings(
    db: Session = Depends(get_db),
    category: str | None = Query(default=None),
    status_filter: ListingStatus | None = Query(default=None, alias="status"),
    city: str | None = Query(default=None),
    min_price: float | None = Query(default=None),
    max_price: float | None = Query(default=None),
):
    """List public approved listings with optional filter parameters."""
    conditions = []
    if category:
        try:
            parsed_category = ListingCategory(category.strip().lower())
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category")
        if parsed_category == ListingCategory.car:
            conditions.append(Listing.category.in_([ListingCategory.car, ListingCategory.hypercar]))
        else:
            conditions.append(Listing.category == parsed_category)
    if status_filter:
        conditions.append(Listing.status == status_filter)
    if city:
        conditions.append(Listing.location_city.ilike(f"%{city}%"))
    if min_price is not None:
        conditions.append(Listing.price >= min_price)
    if max_price is not None:
        conditions.append(Listing.price <= max_price)

    conditions.append(Listing.status == ListingStatus.active)
    conditions.append(Listing.moderation_status == ModerationStatus.approved)

    query = db.query(Listing).order_by(Listing.is_featured.desc(), Listing.created_at.desc())
    if conditions:
        query = query.filter(and_(*conditions))
    return query.limit(100).all()


@router.get("/{listing_id}", response_model=ListingOut)
def get_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    """Return a listing by ID, including owner/admin preview of unpublished listings."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    can_view_unpublished = bool(current_user and (current_user.role == UserRole.super_admin or listing.seller_id == current_user.id))
    if not can_view_unpublished and (
        listing.status != ListingStatus.active or listing.moderation_status != ModerationStatus.approved
    ):
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.patch("/{listing_id}", response_model=ListingOut)
def update_listing(
    listing_id: int,
    payload: ListingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a listing for its owner or an admin user."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if current_user.role != UserRole.super_admin and listing.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your listing")

    for key, value in payload.model_dump(exclude_unset=True).items():
        if key == "details":
            continue
        setattr(listing, key, value)

    if payload.details is not None:
        InventoryService.upsert_listing_details(db, listing, payload.details)

    if listing.status == ListingStatus.active and not listing.published_at:
        listing.published_at = datetime.utcnow()
    InventoryService.queue_listing_changed(db, listing, "updated")
    db.commit()
    db.refresh(listing)
    return listing


@router.post("/{listing_id}/save", status_code=status.HTTP_201_CREATED)
def save_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save a listing to the authenticated user's saved-listings collection."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    existing = (
        db.query(SavedListing)
        .filter(SavedListing.user_id == current_user.id, SavedListing.listing_id == listing_id)
        .first()
    )
    if existing:
        return {"message": "Already saved"}
    row = SavedListing(user_id=current_user.id, listing_id=listing_id)
    db.add(row)
    db.commit()
    return {"message": "Saved"}


@router.post("/import", status_code=status.HTTP_201_CREATED)
def bulk_import_listings(
    payload: ListingImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.business_account, UserRole.super_admin)),
):
    """Bulk-create draft listings from normalized import payload items."""
    created_ids: list[int] = []
    for item in payload.items:
        base_slug = slugify(f"{item.category.value}-{item.make or ''}-{item.model or ''}-{item.title}")
        slug = ensure_unique_slug(db, base_slug or f"imported-{int(datetime.utcnow().timestamp())}")
        listing = Listing(
            seller_id=current_user.id,
            title=item.title,
            slug=slug,
            category=item.category,
            status=ListingStatus.draft,
            moderation_status=ModerationStatus.pending,
            currency=item.currency.upper(),
            price=item.price,
            location_country=item.location_country,
            location_city=item.location_city,
            make=item.make,
            model=item.model,
            attributes=item.attributes,
        )
        db.add(listing)
        db.flush()
        InventoryService.upsert_listing_details(db, listing, item.details)
        InventoryService.queue_listing_changed(db, listing, "imported")
        created_ids.append(listing.id)

    db.commit()
    return {"source": payload.source, "created_count": len(created_ids), "listing_ids": created_ids}


@router.post("/import/feed", status_code=status.HTTP_201_CREATED)
def import_feed(
    payload: ListingFeedImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.business_account, UserRole.super_admin)),
):
    """Parse CSV/XML feed content and import valid rows as draft listings."""
    source = payload.source.strip().lower()
    if source not in {"csv", "xml"}:
        raise HTTPException(status_code=400, detail="Unsupported import source")

    parsed_items: list[dict[str, str]] = []
    if source == "csv":
        reader = csv.DictReader(io.StringIO(payload.content))
        parsed_items = [dict(row) for row in reader]
    else:
        try:
            root = ET.fromstring(payload.content)
        except ET.ParseError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid XML payload: {exc}") from exc
        for row in root.findall(".//listing"):
            parsed_items.append({child.tag: (child.text or "").strip() for child in row})

    created_ids: list[int] = []
    for row in parsed_items:
        title = row.get("title")
        category_raw = row.get("category")
        price_raw = row.get("price")
        if not title or not category_raw or not price_raw:
            continue

        try:
            category = ListingCategory(category_raw.strip().lower())
            price = float(price_raw)
        except (ValueError, TypeError):
            continue

        base_slug = slugify(f"{category.value}-{row.get('make', '')}-{row.get('model', '')}-{title}")
        slug = ensure_unique_slug(db, base_slug or f"feed-{int(datetime.utcnow().timestamp())}")
        listing = Listing(
            seller_id=current_user.id,
            title=title.strip(),
            slug=slug,
            category=category,
            status=ListingStatus.draft,
            moderation_status=ModerationStatus.pending,
            currency=(row.get("currency") or "USD").upper(),
            price=price,
            location_country=row.get("location_country"),
            location_city=row.get("location_city"),
            make=row.get("make"),
            model=row.get("model"),
            attributes={k: v for k, v in row.items() if k not in {"title", "category", "price", "currency"}},
        )
        db.add(listing)
        db.flush()
        InventoryService.upsert_listing_details(db, listing)
        InventoryService.queue_listing_changed(db, listing, "feed_imported")
        created_ids.append(listing.id)

    db.commit()
    return {"source": source, "parsed_count": len(parsed_items), "created_count": len(created_ids), "listing_ids": created_ids}
