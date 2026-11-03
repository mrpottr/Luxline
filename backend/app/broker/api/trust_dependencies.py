"""Dependency wiring for organization, buyer, public, and admin trust use cases."""

from fastapi import Depends, HTTPException, Query, Request, status

from backend.app.broker.api.dependencies import BrokerContext, get_broker_context
from backend.app.broker.application.trust_use_cases import (
    AdminTrustUseCases,
    BrokerTrustUseCases,
    BuyerReviewUseCases,
    PublicTrustUseCases,
)
from backend.app.broker.repositories.trust_repository import BrokerTrustRepository
from backend.app.dependencies import get_current_user
from backend.app.models import User, UserRole


def get_broker_trust_use_cases(
    request: Request,
    context: BrokerContext = Depends(get_broker_context),
) -> BrokerTrustUseCases:
    return BrokerTrustUseCases(
        BrokerTrustRepository(context.organization_id), context.permissions,
        organization_id=context.organization_id, actor_user_id=context.user.id,
        role=context.role, source_ip=request.client.host if request.client else None,
    )


def get_buyer_review_use_cases(
    organization_id: int = Query(ge=1),
    buyer: User = Depends(get_current_user),
) -> BuyerReviewUseCases:
    return BuyerReviewUseCases(
        BrokerTrustRepository(organization_id), organization_id=organization_id,
        buyer_user_id=buyer.id,
    )


def get_public_trust_use_cases(organization_id: int) -> PublicTrustUseCases:
    return PublicTrustUseCases(BrokerTrustRepository(organization_id))


def get_admin_trust_use_cases(
    request: Request,
    admin: User = Depends(get_current_user),
) -> AdminTrustUseCases:
    if admin.role != UserRole.super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform administrator access is required")
    return AdminTrustUseCases(
        BrokerTrustRepository(0), actor_user_id=admin.id, actor_role=admin.role,
        source_ip=request.client.host if request.client else None,
    )
