"""Broker member repository."""

from backend.app.broker.domain.roles import BrokerRole
from backend.app.broker.models.member import BrokerMember
from backend.app.broker.repositories.base_repository import BaseTenantRepository


class BrokerMemberRepository(BaseTenantRepository[BrokerMember]):
    def __init__(self, organization_id: int):
        super().__init__(BrokerMember, organization_id)

    def find_by_user_id(self, user_id: int) -> BrokerMember | None:
        """Find member record for a given user within this organization."""
        return self._scoped_query(user_id=user_id).first()

    def list_active_members(self) -> list[BrokerMember]:
        """List all active members for this organization."""
        return list(self._scoped_query(is_active=True).order_by("role", "display_name"))

    def add_or_update_member(self, user_id: int, role: BrokerRole, **details) -> BrokerMember:
        """Upsert a team member inside this organization."""
        member = self.find_by_user_id(user_id)
        if not member:
            return self.create(user_id=user_id, role=role, **details)
        member.role = role
        for key, value in details.items():
            if hasattr(member, key) and key not in {"id", "organization_id", "user_id"}:
                setattr(member, key, value)
        member.save()
        return member
