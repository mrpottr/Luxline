from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.dependencies import get_current_user, require_roles
from backend.app.models import AlertPreference, Inquiry, SavedListing, SavedSearch, User, UserRole
from backend.app.schemas import (
    AlertPreferenceOut,
    AlertPreferenceUpdate,
    InquiryOut,
    SavedSearchCreate,
    SavedSearchOut,
    UserOut,
    UserPreferencesUpdate,
)


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me/preferences", response_model=UserOut)
def update_preferences(
    payload: UserPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.preferred_currency:
        current_user.preferred_currency = payload.preferred_currency.upper()
    if payload.preferred_language:
        current_user.preferred_language = payload.preferred_language.lower()
    if payload.measurement_system:
        current_user.measurement_system = payload.measurement_system.lower()
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me/saved-listings")
def get_saved_listings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = db.query(SavedListing).filter(SavedListing.user_id == current_user.id).all()
    return {"items": [{"id": row.id, "listing_id": row.listing_id, "saved_at": row.created_at} for row in rows]}


@router.post("/me/saved-searches", response_model=SavedSearchOut, status_code=status.HTTP_201_CREATED)
def create_saved_search(
    payload: SavedSearchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    return db.query(SavedSearch).filter(SavedSearch.user_id == current_user.id).all()


@router.get("/me/alerts", response_model=list[AlertPreferenceOut])
def get_alert_preferences(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(AlertPreference).filter(AlertPreference.user_id == current_user.id).all()


@router.put("/me/alerts", response_model=AlertPreferenceOut)
def set_alert_preference(
    payload: AlertPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    return (
        db.query(Inquiry)
        .filter(or_(Inquiry.buyer_id == current_user.id, Inquiry.seller_id == current_user.id))
        .order_by(Inquiry.created_at.desc())
        .limit(250)
        .all()
    )


@router.get("", response_model=list[UserOut])
def list_users_for_admin(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.super_admin)),
):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.patch("/{user_id}/suspend", response_model=UserOut)
def suspend_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.super_admin)),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user
