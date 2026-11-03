"""Broker profile repository."""

from backend.app.broker.models.profile import BrokerProfile, BrokerStatus
from backend.app.broker.repositories.base_repository import BaseTenantRepository


class BrokerProfileRepository(BaseTenantRepository[BrokerProfile]):
    def __init__(self, organization_id: int):
        super().__init__(BrokerProfile, organization_id)

    def get_profile(self) -> BrokerProfile | None:
        """Return the broker profile for this tenant."""
        return self._scoped_query().first()

    def upsert_profile(self, **kwargs) -> BrokerProfile:
        """Create or update profile for this tenant."""
        profile = self.get_profile()
        if not profile:
            return self.create(**kwargs)
        for key, value in kwargs.items():
            if hasattr(profile, key) and key != "organization_id":
                setattr(profile, key, value)
        profile.save()
        return profile

    def submit_for_verification(self) -> BrokerProfile | None:
        """Advance profile state from draft to submitted."""
        profile = self.get_profile()
        if profile and profile.status == BrokerStatus.draft:
            profile.status = BrokerStatus.submitted
            profile.save()
        return profile
