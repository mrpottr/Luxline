"""Dependency wiring for analytics use cases."""

from fastapi import Depends

from backend.app.broker.api.dependencies import BrokerContext, get_broker_context
from backend.app.broker.application.analytics_use_cases import AnalyticsUseCases
from backend.app.broker.application.public_view_use_case import RecordPublicListingView
from backend.app.broker.services.analytics_provider import MongoAnalyticsProvider
from backend.app.broker.services.mongo_bulk_rate_limiter import broker_rate_limiter


def get_analytics_use_cases(context: BrokerContext = Depends(get_broker_context)) -> AnalyticsUseCases:
    return AnalyticsUseCases(
        MongoAnalyticsProvider(context.organization_id),
        context.permissions,
        role=context.role,
        actor_user_id=context.user.id,
    )


def get_public_view_use_case() -> RecordPublicListingView:
    return RecordPublicListingView(
        MongoAnalyticsProvider(organization_id=0),
        broker_rate_limiter,
    )
