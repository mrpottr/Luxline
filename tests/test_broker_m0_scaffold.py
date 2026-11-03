"""Milestone 0 Scaffold and Seams Verification Tests.

Verifies:
1. Feature flag contract: with BROKER_PANEL_ENABLED=false, endpoints are disabled.
2. Domain roles & permissions: owner, manager, agent, viewer hierarchies.
3. Broker context and permission dependency behavior.
"""

import unittest
from unittest.mock import MagicMock
from fastapi import HTTPException

from backend.app.core.config import settings
from backend.app.broker.domain.roles import (
    BrokerPermission,
    BrokerRole,
    ROLE_PERMISSIONS,
    role_has_permission,
)
from backend.app.broker.api.dependencies import (
    BrokerContext,
    get_broker_context,
    require_broker_permission,
    verify_broker_panel_enabled,
)
from backend.app.broker.api.router import broker_health, get_my_broker_context
from backend.app.models import UserRole


class TestBrokerDomainRoles(unittest.TestCase):
    """Test pure domain roles and permissions."""

    def test_broker_roles_defined(self):
        self.assertEqual(BrokerRole.broker_owner.value, "broker_owner")
        self.assertEqual(BrokerRole.broker_manager.value, "broker_manager")
        self.assertEqual(BrokerRole.broker_agent.value, "broker_agent")
        self.assertEqual(BrokerRole.broker_viewer.value, "broker_viewer")

    def test_owner_has_all_permissions(self):
        for perm in BrokerPermission:
            self.assertTrue(
                role_has_permission(BrokerRole.broker_owner, perm),
                f"Owner should have permission {perm}",
            )

    def test_manager_permissions(self):
        # Manager can manage listings, leads, promotions
        self.assertTrue(role_has_permission(BrokerRole.broker_manager, BrokerPermission.LISTING_PUBLISH))
        self.assertTrue(role_has_permission(BrokerRole.broker_manager, BrokerPermission.LEAD_ASSIGN))
        self.assertTrue(role_has_permission(BrokerRole.broker_manager, BrokerPermission.PROMOTION_MANAGE))
        # Manager cannot manage billing or organization details
        self.assertFalse(role_has_permission(BrokerRole.broker_manager, BrokerPermission.BILLING_MANAGE))
        self.assertFalse(role_has_permission(BrokerRole.broker_manager, BrokerPermission.ORG_EDIT))

    def test_agent_permissions_restricted(self):
        # Agent can only view own listings and assigned leads
        self.assertTrue(role_has_permission(BrokerRole.broker_agent, BrokerPermission.LISTING_VIEW_OWN))
        self.assertTrue(role_has_permission(BrokerRole.broker_agent, BrokerPermission.LEAD_VIEW_OWN))
        self.assertFalse(role_has_permission(BrokerRole.broker_agent, BrokerPermission.LISTING_VIEW_ALL))
        self.assertFalse(role_has_permission(BrokerRole.broker_agent, BrokerPermission.LEAD_VIEW_ALL))
        self.assertFalse(role_has_permission(BrokerRole.broker_agent, BrokerPermission.BILLING_MANAGE))

    def test_viewer_is_read_only(self):
        self.assertTrue(role_has_permission(BrokerRole.broker_viewer, BrokerPermission.ANALYTICS_VIEW))
        self.assertTrue(role_has_permission(BrokerRole.broker_viewer, BrokerPermission.ORG_VIEW))
        self.assertFalse(role_has_permission(BrokerRole.broker_viewer, BrokerPermission.LISTING_CREATE))
        self.assertFalse(role_has_permission(BrokerRole.broker_viewer, BrokerPermission.LEAD_MESSAGE))


class TestBrokerFeatureFlagAndDependencies(unittest.TestCase):
    """Test feature flag enforcement and dependencies."""

    def test_flag_off_raises_404(self):
        # Ensure that when flag is False, verify_broker_panel_enabled raises 404
        original_flag = settings.broker_panel_enabled
        try:
            object.__setattr__(settings, "broker_panel_enabled", False)
            with self.assertRaises(HTTPException) as ctx:
                verify_broker_panel_enabled()
            self.assertEqual(ctx.exception.status_code, 404)
        finally:
            object.__setattr__(settings, "broker_panel_enabled", original_flag)

    def test_flag_on_allows_health(self):
        original_flag = settings.broker_panel_enabled
        try:
            object.__setattr__(settings, "broker_panel_enabled", True)
            verify_broker_panel_enabled()
            health = broker_health()
            self.assertEqual(health["status"], "ok")
            self.assertEqual(health["service"], "broker-panel")
        finally:
            object.__setattr__(settings, "broker_panel_enabled", original_flag)

    def test_standard_user_cannot_access_broker_context(self):
        original_flag = settings.broker_panel_enabled
        try:
            object.__setattr__(settings, "broker_panel_enabled", True)
            mock_user = MagicMock()
            mock_user.role = UserRole.standard_user
            mock_db = MagicMock()

            with self.assertRaises(HTTPException) as ctx:
                get_broker_context(db=mock_db, current_user=mock_user, _flag=None)
            self.assertEqual(ctx.exception.status_code, 403)
        finally:
            object.__setattr__(settings, "broker_panel_enabled", original_flag)

    def test_business_account_gets_broker_context(self):
        original_flag = settings.broker_panel_enabled
        try:
            object.__setattr__(settings, "broker_panel_enabled", True)
            mock_user = MagicMock()
            mock_user.id = 42
            mock_user.email = "broker@example.com"
            mock_user.role = UserRole.business_account
            mock_db = MagicMock()

            ctx = get_broker_context(db=mock_db, current_user=mock_user, _flag=None)
            self.assertEqual(ctx.user.id, 42)
            self.assertEqual(ctx.role, BrokerRole.broker_owner)
            self.assertTrue(ctx.has_permission(BrokerPermission.LISTING_CREATE))

            me_resp = get_my_broker_context(context=ctx)
            self.assertEqual(me_resp["user_id"], 42)
            self.assertEqual(me_resp["role"], "broker_owner")
            self.assertIn("broker:listing:create", me_resp["permissions"])
        finally:
            object.__setattr__(settings, "broker_panel_enabled", original_flag)

    def test_permission_guard_allows_and_rejects(self):
        ctx_owner = BrokerContext(
            user=MagicMock(),
            organization_id=1,
            role=BrokerRole.broker_owner,
            permissions={BrokerPermission.BILLING_MANAGE},
        )
        guard_billing = require_broker_permission(BrokerPermission.BILLING_MANAGE)
        result = guard_billing(context=ctx_owner)
        self.assertEqual(result, ctx_owner)

        ctx_agent = BrokerContext(
            user=MagicMock(),
            organization_id=1,
            role=BrokerRole.broker_agent,
            permissions={BrokerPermission.LISTING_VIEW_OWN},
        )
        with self.assertRaises(HTTPException) as err:
            guard_billing(context=ctx_agent)
        self.assertEqual(err.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()

