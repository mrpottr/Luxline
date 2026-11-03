"""Milestone 3 Team & Branches Tests."""

import unittest
from unittest.mock import MagicMock, patch

from backend.app.broker.domain.roles import BrokerRole
from backend.app.broker.domain.team_rules import TeamRules
from backend.app.broker.models.branch import BrokerBranch
from backend.app.broker.models.member import BrokerMember
from backend.app.broker.repositories.branch_repository import BrokerBranchRepository
from backend.app.broker.repositories.member_repository import BrokerMemberRepository


class TestTeamRules(unittest.TestCase):
    """Test team role hierarchy validation."""

    def test_owner_permissions_over_roles(self):
        self.assertTrue(TeamRules.can_manage_member(BrokerRole.broker_owner, BrokerRole.broker_owner))
        self.assertTrue(TeamRules.can_manage_member(BrokerRole.broker_owner, BrokerRole.broker_manager))
        self.assertTrue(TeamRules.can_manage_member(BrokerRole.broker_owner, BrokerRole.broker_agent))

    def test_manager_cannot_manage_owners(self):
        self.assertFalse(TeamRules.can_manage_member(BrokerRole.broker_manager, BrokerRole.broker_owner))
        self.assertFalse(TeamRules.can_manage_member(BrokerRole.broker_manager, BrokerRole.broker_manager))
        self.assertTrue(TeamRules.can_manage_member(BrokerRole.broker_manager, BrokerRole.broker_agent))
        self.assertTrue(TeamRules.can_manage_member(BrokerRole.broker_manager, BrokerRole.broker_viewer))

    def test_last_owner_demotion_prevention(self):
        # When only 1 owner exists, removal must be rejected
        self.assertFalse(TeamRules.validate_owner_removal(total_owners_count=1))
        # When 2+ owners exist, removal is permitted
        self.assertTrue(TeamRules.validate_owner_removal(total_owners_count=2))


class TestTeamBranchRepositories(unittest.TestCase):
    """Test team and branch repositories."""

    @patch.object(BrokerMember, "save")
    def test_member_creation(self, mock_save):
        repo = BrokerMemberRepository(organization_id=300)
        member = repo.create(
            user_id=102,
            role=BrokerRole.broker_agent,
            display_name="Kavinda Perera",
            title="Luxury Advisor",
        )
        self.assertEqual(member.organization_id, 300)
        self.assertEqual(member.role, BrokerRole.broker_agent)
        self.assertEqual(member.display_name, "Kavinda Perera")

    @patch.object(BrokerBranch, "save")
    def test_branch_creation(self, mock_save):
        repo = BrokerBranchRepository(organization_id=300)
        branch = repo.create(
            name="Colombo Flagship",
            code="HQ-CMB",
            city="Colombo",
            country="Sri Lanka",
        )
        self.assertEqual(branch.organization_id, 300)
        self.assertEqual(branch.code, "HQ-CMB")


if __name__ == "__main__":
    unittest.main()
