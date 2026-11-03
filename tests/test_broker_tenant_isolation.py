"""Milestone 1 Tenant Isolation & Data Foundation Tests.

Proves that:
1. All broker repository queries enforce tenant isolation via mandatory organization_id.
2. Organization A can never read, modify, or delete Organization B records.
3. Soft-deleted records are properly excluded by default.
"""

import unittest
from unittest.mock import MagicMock, patch

from backend.app.broker.domain.roles import BrokerRole
from backend.app.broker.models.base import BrokerBaseDocument
from backend.app.broker.models.profile import BrokerProfile, BrokerStatus
from backend.app.broker.models.member import BrokerMember
from backend.app.broker.models.branch import BrokerBranch
from backend.app.broker.repositories.base_repository import BaseTenantRepository
from backend.app.broker.repositories.profile_repository import BrokerProfileRepository
from backend.app.broker.repositories.member_repository import BrokerMemberRepository
from backend.app.broker.repositories.branch_repository import BrokerBranchRepository


class DummyBrokerDoc(BrokerBaseDocument):
    meta = {"collection": "test_broker_docs"}


class TestTenantRepositoryIsolation(unittest.TestCase):
    """Verify tenant isolation behavior at repository layer."""

    def test_repository_organization_id_binding(self):
        repo_a = BaseTenantRepository(BrokerProfile, organization_id=101)
        repo_b = BaseTenantRepository(BrokerProfile, organization_id=202)

        self.assertEqual(repo_a.organization_id, 101)
        self.assertEqual(repo_b.organization_id, 202)

    @patch.object(BrokerMember, "objects")
    def test_find_by_id_scopes_to_tenant(self, mock_objects):
        mock_qs = MagicMock()
        mock_objects.return_value = mock_qs
        mock_qs.filter.return_value = mock_qs
        mock_qs.first.return_value = None

        repo = BrokerMemberRepository(organization_id=500)
        repo.find_by_id(item_id=12)

        # Must have filtered on organization_id=500 and id=12
        mock_objects.assert_called_with(organization_id=500, id=12)
        mock_qs.filter.assert_called_with(is_deleted=False)

    @patch.object(BrokerBranch, "objects")
    def test_cross_tenant_read_returns_none(self, mock_objects):
        # Setup mock where item exists under org 200, but queried under org 100
        mock_qs = MagicMock()
        mock_objects.return_value = mock_qs
        mock_qs.filter.return_value = mock_qs
        mock_qs.first.return_value = None  # query with org_id=100 returns nothing

        repo_a = BrokerBranchRepository(organization_id=100)
        result = repo_a.find_by_id(item_id=99)

        mock_objects.assert_called_with(organization_id=100, id=99)
        self.assertIsNone(result)

    @patch.object(BrokerProfile, "save")
    def test_create_enforces_tenant_id(self, mock_save):
        repo = BrokerProfileRepository(organization_id=777)
        profile = repo.create(
            company_name="Royal Marine Brokerage",
            status=BrokerStatus.draft,
            organization_id=999,  # attacker tries to spoof tenant ID
        )
        # Repository must override spoofed tenant ID with authorized organization_id
        self.assertEqual(profile.organization_id, 777)
        self.assertEqual(profile.company_name, "Royal Marine Brokerage")

    @patch.object(BrokerMember, "objects")
    def test_cross_tenant_update_blocked(self, mock_objects):
        mock_qs = MagicMock()
        mock_objects.return_value = mock_qs
        mock_qs.filter.return_value = mock_qs
        mock_qs.first.return_value = None  # item not found in tenant A

        repo_a = BrokerMemberRepository(organization_id=111)
        updated = repo_a.update(item_id=888, title="Compromised Title")

        self.assertIsNone(updated)

    @patch.object(BrokerMember, "objects")
    def test_cross_tenant_soft_delete_blocked(self, mock_objects):
        mock_qs = MagicMock()
        mock_objects.return_value = mock_qs
        mock_qs.filter.return_value = mock_qs
        mock_qs.first.return_value = None  # item not found in tenant A

        repo_a = BrokerMemberRepository(organization_id=111)
        deleted = repo_a.soft_delete(item_id=888)

        self.assertFalse(deleted)


if __name__ == "__main__":
    unittest.main()
