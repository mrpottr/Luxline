"""Threaded messaging between buyers and sellers."""

from fastapi import APIRouter, Depends, HTTPException, status
from mongoengine import Q

from backend.app.db.session import Session, get_db
from backend.app.dependencies import get_current_user
from backend.app.models import Inquiry, Listing, User
from backend.app.schemas import InquiryCreate, InquiryOut


router = APIRouter(prefix="/messages", tags=["messaging"])


@router.get("", response_model=list[InquiryOut])
def get_my_messages(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all messages/inquiries where the user is either buyer or seller."""
    return list(
        Inquiry.objects(Q(buyer_id=current_user.id) | Q(seller_id=current_user.id))
        .order_by("-created_at")
    )


@router.get("/threads")
def get_message_threads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return grouped message threads by listing, with most recent message per listing."""
    inquiries = list(
        Inquiry.objects(Q(buyer_id=current_user.id) | Q(seller_id=current_user.id))
        .order_by("listing_id", "-created_at")
    )
    # Group by listing_id (acts as thread key)
    threads: dict[int, dict] = {}
    for inq in inquiries:
        lid = inq.listing_id
        if lid not in threads:
            threads[lid] = {
                "listing_id": lid,
                "latest_message": {
                    "id": inq.id,
                    "message": inq.message,
                    "created_at": inq.created_at,
                    "status": inq.status.value if hasattr(inq.status, "value") else inq.status,
                },
                "message_count": 1,
                "other_party_id": inq.seller_id if inq.buyer_id == current_user.id else inq.buyer_id,
            }
        else:
            threads[lid]["message_count"] += 1
    return list(threads.values())


@router.post("/listings/{listing_id}", response_model=InquiryOut, status_code=status.HTTP_201_CREATED)
def send_message_to_seller(
    listing_id: int,
    payload: InquiryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send an inquiry/message to a listing seller."""
    listing = Listing.objects(id=listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot message yourself")

    inq = Inquiry(
        listing_id=listing_id,
        buyer_id=current_user.id,
        seller_id=listing.seller_id,
        **payload.model_dump(),
    )
    db.add(inq)
    db.commit()
    db.refresh(inq)
    return inq
