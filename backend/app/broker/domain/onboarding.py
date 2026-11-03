"""Domain rules and state machine for Broker onboarding and verification."""

from typing import Tuple
from backend.app.broker.models.profile import BrokerProfile, BrokerStatus


class OnboardingRules:
    """Business validation rules for broker application verification."""

    REQUIRED_SUBMISSION_FIELDS = [
        "company_name",
        "legal_name",
        "address",
        "country",
        "city",
        "contact_email",
        "contact_phone",
    ]

    @classmethod
    def validate_for_submission(cls, profile: BrokerProfile) -> Tuple[bool, list[str]]:
        """Verify whether a draft profile has all required fields to submit."""
        missing = []
        for field in cls.REQUIRED_SUBMISSION_FIELDS:
            val = getattr(profile, field, None)
            if not val or not str(val).strip():
                missing.append(field)

        if not profile.licences:
            missing.append("licences")

        return len(missing) == 0, missing

    @staticmethod
    def can_transition(current: BrokerStatus, target: BrokerStatus) -> bool:
        """Validate allowed lifecycle state transitions."""
        valid_transitions = {
            BrokerStatus.draft: {BrokerStatus.submitted},
            BrokerStatus.submitted: {BrokerStatus.approved, BrokerStatus.rejected},
            BrokerStatus.approved: {BrokerStatus.suspended},
            BrokerStatus.rejected: {BrokerStatus.submitted},  # Allowed to fix and resubmit
            BrokerStatus.suspended: {BrokerStatus.approved},
        }
        return target in valid_transitions.get(current, set())

