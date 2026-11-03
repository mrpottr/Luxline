"""Application use cases for broker organization and role resolution."""

from dataclasses import dataclass
from typing import Any

from backend.app.broker.application.ports import ListingAccessProvider
from backend.app.broker.domain.roles import BrokerPermission, BrokerRole, ROLE_PERMISSIONS


@dataclass(frozen=True)
class BrokerAccess:
    organization_id: int
    role: BrokerRole
    permissions: set[BrokerPermission]


class ListingAccessUseCases:
    def __init__(self, provider: ListingAccessProvider):
        self.provider = provider

    def resolve(self, *, user_id: int, user_role: str, requested_organization_id: int | None) -> BrokerAccess:
        if user_role in {"private_seller", "super_admin"}:
            raise PermissionError("Use an eligible business account or an enrolled broker team account")

        owned_organization_id = None
        if user_role == "business_account":
            owned_organization_id = self.provider.find_owned_organization(user_id=user_id)
            if owned_organization_id is None:
                raise PermissionError("An existing organization profile is required")

        if requested_organization_id is not None:
            member_role = self.provider.find_member_role(
                organization_id=requested_organization_id,
                user_id=user_id,
            )
            if member_role is not None:
                organization_id, role = requested_organization_id, member_role
            elif user_role == "business_account" and owned_organization_id == requested_organization_id:
                organization_id, role = requested_organization_id, BrokerRole.broker_owner
            else:
                raise PermissionError("No access to this broker organization")
        elif owned_organization_id is not None:
            member_role = self.provider.find_member_role(
                organization_id=owned_organization_id,
                user_id=user_id,
            )
            organization_id = owned_organization_id
            role = member_role or BrokerRole.broker_owner
        else:
            memberships = self.provider.list_member_roles(user_id=user_id, limit=2)
            if not memberships:
                raise PermissionError("No active broker organization membership")
            if len(memberships) > 1:
                raise ValueError("Select an organization with X-Broker-Organization-Id")
            organization_id, role = memberships[0]

        if not self.provider.organization_exists(organization_id=organization_id):
            raise PermissionError("Broker organization is unavailable")

        return BrokerAccess(
            organization_id=organization_id,
            role=role,
            permissions=set(ROLE_PERMISSIONS.get(role, set())),
        )
