"""Administrative endpoints for moderation and account operations."""

from fastapi import APIRouter, Depends, HTTPException, Query
import requests

from backend.app.core.security import hash_password
from backend.app.core.config import settings
from backend.app.db.session import Session, get_db
from backend.app.dependencies import require_roles
from backend.app.models import AuditLog, Inquiry, Listing, ListingStatus, ModerationStatus, SavedSearch, User, UserRole
from backend.app.schemas import AdminOverviewOut, AdminResetPasswordRequest, AuditLogOut, ListingOut, UserOut, UserRoleUpdate


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def admin_list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """List all platform users for admin management."""
    return list(User.objects.order_by("-created_at"))


@router.get("/overview", response_model=AdminOverviewOut)
def admin_overview(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """Return account-page metrics and recent administrative activity for admins."""
    recent_audit_logs = list(AuditLog.objects.order_by("-created_at").limit(10))
    return {
        "total_users": User.objects.count(),
        "active_users": User.objects(is_active=True).count(),
        "suspended_users": User.objects(is_active=False).count(),
        "total_listings": Listing.objects.count(),
        "active_listings": Listing.objects(status=ListingStatus.active).count(),
        "pending_listings": Listing.objects(moderation_status=ModerationStatus.pending).count(),
        "pending_business_verifications": User.objects(
            role=UserRole.business_account, is_verified_business=False
        ).count(),
        "inquiry_count": Inquiry.objects.count(),
        "saved_search_count": SavedSearch.objects.count(),
        "recent_audit_logs": recent_audit_logs,
    }


@router.get("/audit-logs", response_model=list[AuditLogOut])
def audit_logs(
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """Return recent audit logs for privileged account activity views."""
    return list(AuditLog.objects.order_by("-created_at").limit(limit))



@router.post("/users/{user_id}/verify-business", response_model=UserOut)
def verify_business_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """Mark a user as business-verified and record the admin action."""
    user = User.objects(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_verified_business = True
    db.add(user)
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
    user = User.objects(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(payload.new_password)
    db.add(user)
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
    user = User.objects(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.role == UserRole.super_admin:
        raise HTTPException(status_code=400, detail="Cannot assign super admin role from this endpoint")

    user.role = payload.role
    user.is_2fa_enabled = payload.role in {UserRole.business_account, UserRole.broker_account}
    db.add(user)
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


@router.get("/monitoring/metrics")
def get_monitoring_metrics(
    _admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """Get raw Prometheus metrics for admin dashboard."""
    try:
        response = requests.get(f"{settings.prometheus_internal_url}/api/v1/query", params={"query": "luxline_requests_total"}, timeout=5)
        return {"status": "ok", "data": response.json()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/monitoring/health")
def get_monitoring_health(
    _admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """Get overall system health metrics."""
    try:
        prom_response = requests.get(f"{settings.prometheus_internal_url}/-/healthy", timeout=5)
        grafana_response = requests.get(f"{settings.grafana_internal_url}/api/health", timeout=5)
        
        return {
            "prometheus": "healthy" if prom_response.status_code == 200 else "unhealthy",
            "grafana": "healthy" if grafana_response.status_code == 200 else "unhealthy",
            "grafana_url": "http://localhost:3000",
            "prometheus_url": "http://localhost:9090",
        }
    except Exception as e:
        return {"error": str(e)}
