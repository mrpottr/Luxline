"""Administrative endpoints for moderation and account operations."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.security import hash_password
from backend.app.db.session import get_db
from backend.app.dependencies import require_roles
from backend.app.models import AuditLog, Listing, ModerationStatus, User, UserRole
from backend.app.schemas import AdminResetPasswordRequest, ListingOut, UserOut, UserRoleUpdate


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/moderation-queue", response_model=list[ListingOut])
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


@router.post("/users/{user_id}/verify-business", response_model=UserOut)
def verify_business_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """Mark a user as business-verified and record the admin action."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_verified_business = True
    db.add(AuditLog(actor_user_id=admin.id, event_type="user.business_verified", details={"user_id": user_id}))
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/reset-password", response_model=UserOut)
def admin_reset_password(
    user_id: int,
    payload: AdminResetPasswordRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """Reset a user password as an admin operation and audit the change."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(payload.new_password)
    db.add(AuditLog(actor_user_id=admin.id, event_type="user.password_reset", details={"user_id": user_id}))
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/role", response_model=UserOut)
def admin_update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """Change a user's role (excluding super-admin assignment) and audit it."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.role == UserRole.super_admin:
        raise HTTPException(status_code=400, detail="Cannot assign super admin role from this endpoint")

    user.role = payload.role
    user.is_2fa_enabled = payload.role == UserRole.business_account
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            event_type="user.role_changed",
            details={"user_id": user_id, "new_role": payload.role.value},
        )
    )
    db.commit()
    db.refresh(user)
    return user
