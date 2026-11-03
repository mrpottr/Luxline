"""FastAPI dependencies for Broker authentication, tenant isolation, and permissions."""

from dataclasses import dataclass
from fastapi import Depends, Header, HTTPException, status

from backend.app.core.config import settings
from backend.app.db.session import Session, get_db
from backend.app.dependencies import get_current_user
from backend.app.models import User
from backend.app.broker.application.access_use_cases import ListingAccessUseCases
from backend.app.broker.domain.roles import BrokerPermission, BrokerRole
from backend.app.broker.repositories.organization_access_repository import BrokerOrganizationAccessRepository


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


def get_organization_access_use_cases() -> ListingAccessUseCases:
    return ListingAccessUseCases(BrokerOrganizationAccessRepository())


def get_broker_context(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _flag: None = Depends(verify_broker_panel_enabled),
    requested_organization_id: int | None = Header(default=None, alias="X-Broker-Organization-Id"),
    access: ListingAccessUseCases = Depends(get_organization_access_use_cases),
) -> BrokerContext:
    """Resolve a real organization and the actor's enrolled organization role."""
    user_role = getattr(current_user.role, "value", current_user.role)
    try:
        resolved = access.resolve(
            user_id=current_user.id,
            user_role=user_role,
            requested_organization_id=requested_organization_id,
        )
    except PermissionError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    return BrokerContext(
        user=current_user,
        organization_id=resolved.organization_id,
        role=resolved.role,
        permissions=resolved.permissions,
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
