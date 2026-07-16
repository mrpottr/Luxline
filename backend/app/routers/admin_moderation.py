"""Administrative endpoints for listing moderation."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.dependencies import require_roles
from backend.app.models import AuditLog, Listing, ModerationStatus, User, UserRole
from backend.app.schemas import ListingOut


router = APIRouter(prefix="/admin/moderation", tags=["admin-moderation"])


@router.get("/queue", response_model=list[ListingOut])
def moderation_queue(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """Return pending listings requiring moderation review."""
    return (
        db.query(Listing)
        .filter(Listing.moderation_status == ModerationStatus.pending)
        .order_by(Listing.created_at.asc())
        .all()
    )


@router.post("/listings/{listing_id}/approve", response_model=ListingOut)
def approve_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """Approve a listing in moderation and record an audit event."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.moderation_status = ModerationStatus.approved
    db.add(AuditLog(actor_user_id=admin.id, event_type="listing.approved", details={"listing_id": listing_id}))
    db.commit()
    db.refresh(listing)
    return listing


@router.post("/listings/{listing_id}/reject", response_model=ListingOut)
def reject_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """Reject a listing in moderation and record an audit event."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.moderation_status = ModerationStatus.rejected
    db.add(AuditLog(actor_user_id=admin.id, event_type="listing.rejected", details={"listing_id": listing_id}))
    db.commit()
    db.refresh(listing)
    return listing
