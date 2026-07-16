"""Lead routing and inquiry management service."""

from datetime import datetime
from sqlalchemy.orm import Session

from backend.app.models import AuditLog, Inquiry, Listing, PhoneRevealEvent


class LeadRoutingService:
    @staticmethod
    def create_inquiry(db: Session, listing: Listing, payload: dict, buyer_id: int | None) -> Inquiry:
        inquiry = Inquiry(
            listing_id=listing.id,
            buyer_id=buyer_id,
            seller_id=listing.seller_id,
            name=payload.get("name"),
            email=payload.get("email"),
            phone=payload.get("phone"),
            message=payload.get("message"),
            status="sent",
        )
        db.add(inquiry)
        db.flush()
        db.add(
            AuditLog(
                actor_user_id=buyer_id,
                event_type="lead.routed",
                details={"listing_id": listing.id, "seller_id": listing.seller_id, "inquiry_id": inquiry.id},
            )
        )
        db.commit()
        db.refresh(inquiry)
        return inquiry

    @staticmethod
    def track_phone_reveal(db: Session, listing_id: int, user_id: int | None):
        db.add(PhoneRevealEvent(listing_id=listing_id, user_id=user_id))
        db.commit()

    @staticmethod
    def get_inbox_for_seller(db: Session, seller_id: int):
        return db.query(Inquiry).filter(Inquiry.seller_id == seller_id).order_by(Inquiry.created_at.desc()).all()

    @staticmethod
    def mark_inquiry_viewed(db: Session, inquiry: Inquiry):
        if inquiry.status == "sent":
            inquiry.status = "viewed"
        if not inquiry.viewed_at:
            inquiry.viewed_at = datetime.utcnow()
        db.commit()
        db.refresh(inquiry)
        return inquiry

    @staticmethod
    def mark_inquiry_replied(db: Session, inquiry: Inquiry, user_id: int):
        now = datetime.utcnow()
        inquiry.status = "replied"
        inquiry.viewed_at = inquiry.viewed_at or now
        inquiry.replied_at = now
        db.add(
            AuditLog(
                actor_user_id=user_id,
                event_type="lead.replied",
                details={"listing_id": inquiry.listing_id, "seller_id": inquiry.seller_id, "inquiry_id": inquiry.id},
            )
        )
        db.commit()
        db.refresh(inquiry)
        return inquiry
