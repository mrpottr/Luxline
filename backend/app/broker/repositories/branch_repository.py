"""Broker branch repository."""

from backend.app.broker.models.branch import BrokerBranch
from backend.app.broker.repositories.base_repository import BaseTenantRepository


class BrokerBranchRepository(BaseTenantRepository[BrokerBranch]):
    def __init__(self, organization_id: int):
        super().__init__(BrokerBranch, organization_id)

    def find_by_code(self, code: str) -> BrokerBranch | None:
        return self._scoped_query(code=code.upper()).first()
