"""Repository adapter for owner and organization-member lookups."""

from backend.app.broker.domain.roles import BrokerRole
from backend.app.broker.models.member import BrokerMember
from backend.app.models import AgencyProfile


class BrokerOrganizationAccessRepository:
    def find_owned_organization(self, *, user_id: int) -> int | None:
        agency = AgencyProfile.objects(owner_id=user_id).first()
        return agency.id if agency else None

    def find_member_role(self, *, organization_id: int, user_id: int) -> BrokerRole | None:
        member = BrokerMember.objects(
            organization_id=organization_id,
            user_id=user_id,
            is_active=True,
            is_deleted=False,
        ).first()
        return member.role if member else None

    def list_member_roles(self, *, user_id: int, limit: int) -> list[tuple[int, BrokerRole]]:
        members = BrokerMember.objects(
            user_id=user_id,
            is_active=True,
            is_deleted=False,
        ).limit(limit)
        return [(member.organization_id, member.role) for member in members]

    def organization_exists(self, *, organization_id: int) -> bool:
        return AgencyProfile.objects(id=organization_id).first() is not None
