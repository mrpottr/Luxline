"""Authenticated request context for broker listing controllers."""

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from backend.app.broker.application.access_use_cases import ListingAccessUseCases
from backend.app.broker.api.dependencies import verify_broker_panel_enabled
from backend.app.broker.domain.roles import BrokerPermission, BrokerRole
from backend.app.broker.repositories.organization_access_repository import BrokerOrganizationAccessRepository
from backend.app.dependencies import get_current_user
from backend.app.models import User


@dataclass(frozen=True)
class ListingContext:
    user: User
    organization_id: int
    role: BrokerRole
    permissions: set[BrokerPermission]


def get_listing_access_use_cases() -> ListingAccessUseCases:
    return ListingAccessUseCases(BrokerOrganizationAccessRepository())


def get_listing_context(
    current_user: User = Depends(get_current_user),
    _flag: None = Depends(verify_broker_panel_enabled),
    requested_organization_id: int | None = Header(default=None, alias="X-Broker-Organization-Id"),
    access: ListingAccessUseCases = Depends(get_listing_access_use_cases),
) -> ListingContext:
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
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Broker membership lookup unavailable") from error

    return ListingContext(
        user=current_user,
        organization_id=resolved.organization_id,
        role=resolved.role,
        permissions=resolved.permissions,
    )
