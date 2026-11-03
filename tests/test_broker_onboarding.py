"""Milestone 2 Onboarding & Public Profile Verification Tests."""

import unittest
from unittest.mock import MagicMock, patch

from backend.app.broker.domain.onboarding import OnboardingRules
from backend.app.broker.models.profile import BrokerProfile, BrokerStatus
from backend.app.broker.schemas import BrokerVerificationDecision
from backend.app.broker.api.onboarding import admin_review_broker


class TestBrokerOnboardingDomain(unittest.TestCase):
    """Test onboarding domain validation and lifecycle state machine."""

    def test_incomplete_profile_validation_fails(self):
        profile = BrokerProfile(
            organization_id=10,
            company_name="Incomplete Estates",
            status=BrokerStatus.draft,
        )
        is_valid, missing = OnboardingRules.validate_for_submission(profile)
        self.assertFalse(is_valid)
        self.assertIn("address", missing)
        self.assertIn("country", missing)
        self.assertIn("licences", missing)

    def test_complete_profile_validation_passes(self):
        profile = BrokerProfile(
            organization_id=10,
            company_name="Apex Estates",
            legal_name="Apex Holdings PLC",
            address="100 Ocean Drive",
            country="Sri Lanka",
            city="Colombo",
            contact_email="concierge@apex.com",
            contact_phone="+94 11 234 5678",
            licences={"LK": "REA-2026-001"},
            status=BrokerStatus.draft,
        )
        is_valid, missing = OnboardingRules.validate_for_submission(profile)
        self.assertTrue(is_valid)
        self.assertEqual(len(missing), 0)

    def test_valid_state_transitions(self):
        self.assertTrue(OnboardingRules.can_transition(BrokerStatus.draft, BrokerStatus.submitted))
        self.assertTrue(OnboardingRules.can_transition(BrokerStatus.submitted, BrokerStatus.approved))
        self.assertTrue(OnboardingRules.can_transition(BrokerStatus.submitted, BrokerStatus.rejected))
        self.assertTrue(OnboardingRules.can_transition(BrokerStatus.rejected, BrokerStatus.submitted))
        self.assertTrue(OnboardingRules.can_transition(BrokerStatus.approved, BrokerStatus.suspended))

    def test_invalid_state_transitions(self):
        self.assertFalse(OnboardingRules.can_transition(BrokerStatus.draft, BrokerStatus.approved))
        self.assertFalse(OnboardingRules.can_transition(BrokerStatus.draft, BrokerStatus.suspended))
        self.assertFalse(OnboardingRules.can_transition(BrokerStatus.rejected, BrokerStatus.approved))


class TestBrokerAdminReview(unittest.TestCase):
    """Test admin review workflow."""

    @patch.object(BrokerProfile, "objects")
    def test_admin_approve_broker(self, mock_objects):
        mock_profile = MagicMock()
        mock_profile.organization_id = 555
        mock_profile.status = BrokerStatus.submitted
        mock_objects.return_value.first.return_value = mock_profile

        admin_user = MagicMock()
        admin_user.id = 1

        decision = BrokerVerificationDecision(decision="approve", notes="Credentials verified with regulator")
        updated = admin_review_broker(organization_id=555, decision_payload=decision, admin=admin_user)

        self.assertEqual(mock_profile.status, BrokerStatus.approved)
        self.assertIn("verified with regulator", mock_profile.decision_notes)
        mock_profile.save.assert_called_once()


if __name__ == "__main__":
    unittest.main()
