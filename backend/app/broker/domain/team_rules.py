"""Business rules for broker team allocation, role hierarchies, and safety checks."""

from backend.app.broker.domain.roles import BrokerRole


class TeamRules:
    """Team management validation rules."""

    @staticmethod
    def can_manage_member(actor_role: BrokerRole, target_role: BrokerRole) -> bool:
        """Only owners can manage owners and managers; managers can only manage agents/viewers."""
        if actor_role == BrokerRole.broker_owner:
            return True
        if actor_role == BrokerRole.broker_manager:
            return target_role in {BrokerRole.broker_agent, BrokerRole.broker_viewer}
        return False

    @staticmethod
    def validate_owner_removal(total_owners_count: int) -> bool:
        """Prevent deleting or demoting the last remaining broker owner in an organization."""
        return total_owners_count > 1
