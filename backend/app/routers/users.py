"""User profile, preferences, and account-data endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.dependencies import get_current_user, require_roles
from backend.app.models import AlertPreference, Inquiry, Listing, SavedListing, SavedSearch, User, UserRole
from backend.app.schemas import (
    AccountSummaryOut,
    AlertPreferenceOut,
    AlertPreferenceUpdate,
    InquiryOut,
    SavedListingDetailOut,
    SavedSearchCreate,
    SavedSearchOut,
    UserOut,
    UserPreferencesUpdate,
)


router = APIRouter(prefix="/users", tags=["users"])


def _profile_completion(user: User, alert_count: int, saved_search_count: int) -> int:
    checks = [
        bool(user.first_name),
        bool(user.last_name),
        bool(user.email),
        bool(user.phone),
        bool(user.is_email_verified),
        bool(user.preferred_currency),
        bool(user.preferred_language),
        bool(user.measurement_system),
        alert_count > 0,
        saved_search_count > 0,
    ]
    return round((sum(checks) / len(checks)) * 100)


def _saved_listing_details(db: Session, user_id: int) -> list[dict]:
    rows = (
        db.query(SavedListing, Listing)
        .join(Listing, Listing.id == SavedListing.listing_id)
        .filter(SavedListing.user_id == user_id)
        .order_by(SavedListing.created_at.desc())
        .all()
    )
    return [
        {
            "id": saved.id,
            "listing_id": saved.listing_id,
            "saved_at": saved.created_at,
            "listing": listing,
        }
        for saved, listing in rows
    ]


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user


@router.patch("/me/preferences", response_model=UserOut)
def update_preferences(
    payload: UserPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update user-level preference fields such as currency and language."""
    if payload.preferred_currency:
        current_user.preferred_currency = payload.preferred_currency.upper()
    if payload.preferred_language:
        current_user.preferred_language = payload.preferred_language.lower()
    if payload.measurement_system:
        current_user.measurement_system = payload.measurement_system.lower()
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me/saved-listings", response_model=list[SavedListingDetailOut])
def get_saved_listings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Return saved listings with listing details for the account workspace."""
    return _saved_listing_details(db, current_user.id)


@router.post("/me/saved-listings/{listing_id}", response_model=SavedListingDetailOut, status_code=status.HTTP_201_CREATED)
def save_listing_to_account(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save a listing from the account API surface and return the saved item."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    existing = (
        db.query(SavedListing)
        .filter(SavedListing.user_id == current_user.id, SavedListing.listing_id == listing_id)
        .first()
    )
    if existing:
        return {
            "id": existing.id,
            "listing_id": existing.listing_id,
            "saved_at": existing.created_at,
            "listing": listing,
        }

    saved = SavedListing(user_id=current_user.id, listing_id=listing_id)
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return {
        "id": saved.id,
        "listing_id": saved.listing_id,
        "saved_at": saved.created_at,
        "listing": listing,
    }


@router.delete("/me/saved-listings/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_saved_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a listing from the authenticated user's saved-listings collection."""
    saved = (
        db.query(SavedListing)
        .filter(SavedListing.user_id == current_user.id, SavedListing.listing_id == listing_id)
        .first()
    )
    if not saved:
        raise HTTPException(status_code=404, detail="Saved listing not found")
    db.delete(saved)
    db.commit()
    return None


@router.post("/me/saved-searches", response_model=SavedSearchOut, status_code=status.HTTP_201_CREATED)
def create_saved_search(
    payload: SavedSearchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a saved-search definition for the authenticated user."""
    saved = SavedSearch(
        user_id=current_user.id,
        name=payload.name,
        filters=payload.filters,
        alert_enabled=payload.alert_enabled,
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return saved


@router.get("/me/saved-searches", response_model=list[SavedSearchOut])
def list_saved_searches(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List saved-search configurations for the authenticated user."""
    return db.query(SavedSearch).filter(SavedSearch.user_id == current_user.id).all()


@router.get("/me/alerts", response_model=list[AlertPreferenceOut])
def get_alert_preferences(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List notification channel preferences for the authenticated user."""
    return db.query(AlertPreference).filter(AlertPreference.user_id == current_user.id).all()


@router.put("/me/alerts", response_model=AlertPreferenceOut)
def set_alert_preference(
    payload: AlertPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or update a single alert preference channel state."""
    channel = payload.channel.strip().lower()
    if channel not in {"email", "push", "sms"}:
        raise HTTPException(status_code=400, detail="Unsupported alert channel")

    pref = (
        db.query(AlertPreference)
        .filter(AlertPreference.user_id == current_user.id, AlertPreference.channel == channel)
        .first()
    )
    if not pref:
        pref = AlertPreference(user_id=current_user.id, channel=channel, enabled=payload.enabled)
        db.add(pref)
    else:
        pref.enabled = payload.enabled
    db.commit()
    db.refresh(pref)
    return pref


@router.get("/me/messages", response_model=list[InquiryOut])
def get_message_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Return inquiry history where the user is buyer or seller."""
    return (
        db.query(Inquiry)
        .filter(or_(Inquiry.buyer_id == current_user.id, Inquiry.seller_id == current_user.id))
        .order_by(Inquiry.created_at.desc())
        .limit(250)
        .all()
    )


@router.get("/me/account-summary", response_model=AccountSummaryOut)
def get_account_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Return the account workspace data used by the frontend account page."""
    saved_searches = (
        db.query(SavedSearch)
        .filter(SavedSearch.user_id == current_user.id)
        .order_by(SavedSearch.created_at.desc())
        .all()
    )
    inquiries = (
        db.query(Inquiry)
        .filter(or_(Inquiry.buyer_id == current_user.id, Inquiry.seller_id == current_user.id))
        .order_by(Inquiry.created_at.desc())
        .limit(250)
        .all()
    )
    alerts = db.query(AlertPreference).filter(AlertPreference.user_id == current_user.id).all()
    saved_listings = _saved_listing_details(db, current_user.id)
    active_alert_count = len([alert for alert in alerts if alert.enabled])

    return {
        "profile_completion": _profile_completion(current_user, len(alerts), len(saved_searches)),
        "saved_listing_count": len(saved_listings),
        "saved_search_count": len(saved_searches),
        "inquiry_count": len(inquiries),
        "alert_count": len(alerts),
        "active_alert_count": active_alert_count,
        "saved_listings": saved_listings,
        "saved_searches": saved_searches,
        "inquiries": inquiries,
        "alerts": alerts,
    }


@router.get("", response_model=list[UserOut])
def list_users_for_admin(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """List platform users for super-admin management workflows."""
    return db.query(User).order_by(User.created_at.desc()).all()


@router.patch("/{user_id}/suspend", response_model=UserOut)
def suspend_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """Suspend a user account as an administrative action."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user
