"""FastAPI dependencies for Broker authentication, tenant isolation, and permissions."""

from dataclasses import dataclass
from fastapi import Depends, HTTPException, status

from backend.app.core.config import settings
from backend.app.db.session import Session, get_db
from backend.app.dependencies import get_current_user
from backend.app.models import AgencyProfile, User, UserRole
from backend.app.broker.domain.roles import BrokerPermission, BrokerRole, ROLE_PERMISSIONS, role_has_permission


@dataclass(frozen=True)
class BrokerContext:
    """Current authenticated broker user context with active organization scope."""
    user: User
    organization_id: int
    role: BrokerRole
    permissions: set[BrokerPermission]

    def has_permission(self, permission: BrokerPermission) -> bool:
        return permission in self.permissions


def verify_broker_panel_enabled() -> None:
    """Enforce the global feature flag on all broker routes."""
    if not settings.broker_panel_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broker Panel is disabled on this environment",
        )


def get_broker_context(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _flag: None = Depends(verify_broker_panel_enabled),
) -> BrokerContext:
    """Extract and validate the broker context for the current user.

    Super admins and verified business accounts default to broker_owner of their organization.
    """
    if current_user.role not in {UserRole.business_account, UserRole.super_admin}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only approved business accounts and administrators can access the Broker Panel",
        )

    # Resolve or bootstrap organization_id from user.id
    org_id = current_user.id
    try:
        agency = AgencyProfile.objects(owner_id=current_user.id).first()
        if agency:
            org_id = agency.id
    except Exception:
        org_id = current_user.id
    
    role = BrokerRole.broker_owner
    permissions = set(ROLE_PERMISSIONS.get(role, set()))

    return BrokerContext(
        user=current_user,
        organization_id=org_id,
        role=role,
        permissions=permissions,
    )


def require_broker_permission(permission: BrokerPermission):
    """Factory creating a dependency that enforces a specific broker permission."""
    def _dependency(context: BrokerContext = Depends(get_broker_context)) -> BrokerContext:
        if not context.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required broker permission: {permission.value}",
            )
        return context

    return _dependency
