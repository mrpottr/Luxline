"""Dependency wiring for lead use cases."""

from fastapi import Depends, Query

from backend.app.broker.api.dependencies import BrokerContext, get_broker_context
from backend.app.broker.application.lead_use_cases import LeadUseCases
from backend.app.broker.config import listing_config
from backend.app.broker.services.mongo_bulk_rate_limiter import broker_rate_limiter
from backend.app.dependencies import get_current_user
from backend.app.models import User
from backend.app.broker.services.lead_provider import MongoLeadProvider


def get_lead_use_cases(context: BrokerContext = Depends(get_broker_context)) -> LeadUseCases:
    return LeadUseCases(
        MongoLeadProvider(context.organization_id),
        context.permissions,
        role=context.role,
        actor_user_id=context.user.id,
        organization_id=context.organization_id,
        rate_limiter=broker_rate_limiter,
        message_limit=listing_config.messages_per_minute,
    )


def get_buyer_lead_use_cases(
    organization_id: int = Query(ge=1),
    buyer: User = Depends(get_current_user),
) -> LeadUseCases:
    """Resolve the buyer's conversation service within the explicitly selected tenant."""
    return LeadUseCases(
        MongoLeadProvider(organization_id),
        set(),
        role="buyer",
        actor_user_id=buyer.id,
        organization_id=organization_id,
        rate_limiter=broker_rate_limiter,
        message_limit=listing_config.messages_per_minute,
    )
