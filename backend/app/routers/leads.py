"""Lead-routing and seller-contact endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.dependencies import get_current_user, get_optional_current_user
from backend.app.models import AuditLog, Inquiry, Listing, PhoneRevealEvent, User
from backend.app.schemas import InquiryCreate, InquiryOut


router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("/listings/{listing_id}/inquire", response_model=InquiryOut, status_code=status.HTTP_201_CREATED)
def contact_seller(
    listing_id: int,
    payload: InquiryCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    """Create an inquiry for a listing and record lead-routing audit metadata."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    inquiry = Inquiry(
        listing_id=listing.id,
        buyer_id=current_user.id if current_user else None,
        seller_id=listing.seller_id,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        message=payload.message,
        status="sent",
    )
    db.add(inquiry)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=current_user.id if current_user else None,
            event_type="lead.routed",
            details={"listing_id": listing.id, "seller_id": listing.seller_id, "inquiry_id": inquiry.id},
        )
    )
    db.commit()
    db.refresh(inquiry)
    return inquiry


@router.post("/listings/{listing_id}/reveal-phone")
def reveal_phone_number(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    """Return seller phone details for a listing and track the reveal event."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    db.add(PhoneRevealEvent(listing_id=listing_id, user_id=current_user.id if current_user else None))
    db.commit()
    return {"listing_id": listing_id, "seller_phone": listing.seller.phone, "tracked": True}


@router.get("/me/inbox", response_model=list[InquiryOut])
def my_inbox(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List inbound inquiries received by the authenticated seller."""
    return db.query(Inquiry).filter(Inquiry.seller_id == current_user.id).order_by(Inquiry.created_at.desc()).all()


@router.post("/inquiries/{inquiry_id}/view", response_model=InquiryOut)
def mark_inquiry_viewed(
    inquiry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an inbound inquiry as viewed by the seller."""
    inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    if inquiry.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your inquiry")
    if inquiry.status == "sent":
        inquiry.status = "viewed"
    if not inquiry.viewed_at:
        inquiry.viewed_at = datetime.utcnow()
    db.commit()
    db.refresh(inquiry)
    return inquiry


@router.post("/inquiries/{inquiry_id}/reply", response_model=InquiryOut)
def mark_inquiry_replied(
    inquiry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an inbound inquiry as replied by the seller."""
    inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    if inquiry.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your inquiry")
    now = datetime.utcnow()
    inquiry.status = "replied"
    inquiry.viewed_at = inquiry.viewed_at or now
    inquiry.replied_at = now
    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            event_type="lead.replied",
            details={"listing_id": inquiry.listing_id, "seller_id": inquiry.seller_id, "inquiry_id": inquiry.id},
        )
    )
    db.commit()
    db.refresh(inquiry)
    return inquiry
