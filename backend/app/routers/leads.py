"""Lead-routing and seller-contact endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.dependencies import get_current_user, get_optional_current_user
from backend.app.models import Inquiry, Listing, User
from backend.app.schemas import InquiryCreate, InquiryOut
from backend.app.services.lead_routing.service import LeadRoutingService


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

    buyer_id = current_user.id if current_user else None
    return LeadRoutingService.create_inquiry(db, listing, payload.model_dump(), buyer_id)


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
    
    LeadRoutingService.track_phone_reveal(db, listing_id, current_user.id if current_user else None)
    return {"listing_id": listing_id, "seller_phone": listing.seller.phone, "tracked": True}


@router.get("/me/inbox", response_model=list[InquiryOut])
def my_inbox(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List inbound inquiries received by the authenticated seller."""
    return LeadRoutingService.get_inbox_for_seller(db, current_user.id)


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
    
    return LeadRoutingService.mark_inquiry_viewed(db, inquiry)


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
    
    return LeadRoutingService.mark_inquiry_replied(db, inquiry, current_user.id)
