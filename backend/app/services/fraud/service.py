"""Rule-based fraud detection service."""

from sqlalchemy.orm import Session
from backend.app.models import FraudSignal, Listing


class FraudService:
    @staticmethod
    def analyze_listing(db: Session, listing: Listing) -> list[FraudSignal]:
        signals = []
        
        # Rule 1: Suspiciously low price for luxury items
        if listing.price and listing.price < 1000 and listing.category.value in ["car", "hypercar", "yacht", "jet"]:
            signals.append(FraudSignal(
                listing_id=listing.id,
                user_id=listing.seller_id,
                signal_type="suspiciously_low_price",
                severity="high",
                details={"price": float(listing.price), "category": listing.category.value}
            ))

        # Rule 2: Unverified user posting high-value asset
        if not listing.seller.is_verified_business and listing.price > 1000000:
            signals.append(FraudSignal(
                listing_id=listing.id,
                user_id=listing.seller_id,
                signal_type="high_value_unverified_seller",
                severity="medium",
                details={"price": float(listing.price)}
            ))

        for signal in signals:
            db.add(signal)
            
        if signals:
            db.commit()
            
        return signals
