"""Mongo adapter for broker plan, wallet, and promotion use cases."""

from backend.app.broker.repositories.monetization_repository import BrokerMonetizationRepository


class MongoBrokerMonetizationProvider:
    def __init__(self, organization_id: int):
        self.organization_id = organization_id
        self.repository = BrokerMonetizationRepository(organization_id)

    def is_broker_approved(self) -> bool:
        return self.repository.is_broker_approved()

    def get_active_subscription(self):
        return self.repository.active_subscription()

    def get_active_plans(self, *, limit: int, offset: int, sort: str):
        return self.repository.list_active_plans(limit=limit, offset=offset, sort=sort)

    def get_plan(self, code: str):
        return self.repository.get_plan(code)

    def get_wallet_balance(self) -> int:
        return self.repository.wallet_balance()

    def list_ledger(self, *, limit: int, offset: int):
        return self.repository.list_ledger(limit=limit, offset=offset)

    def list_promotions(self, *, status: str | None, limit: int, offset: int):
        return self.repository.list_promotions(status=status, limit=limit, offset=offset)

    def get_promotion_context(self, *, listing_id: int, actor_user_id: int, restrict_to_assigned_agent: bool):
        return self.repository.promotion_context(
            listing_id=listing_id, actor_user_id=actor_user_id,
            restrict_to_assigned_agent=restrict_to_assigned_agent,
        )

    def create_promotion_transaction(self, **kwargs):
        return self.repository.create_promotion_transaction(**kwargs)

    def purchase_credits_transaction(self, **kwargs):
        return self.repository.purchase_credits_transaction(**kwargs)

    def subscribe_transaction(self, **kwargs):
        return self.repository.subscribe_transaction(**kwargs)
