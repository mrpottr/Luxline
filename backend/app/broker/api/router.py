"""Base API router for `/api/broker/v1`."""

from fastapi import APIRouter, Depends
from backend.app.broker.api.dependencies import BrokerContext, get_broker_context, verify_broker_panel_enabled
from backend.app.broker.api.onboarding import router as onboarding_router

router = APIRouter(dependencies=[Depends(verify_broker_panel_enabled)])
router.include_router(onboarding_router)


@router.get("/health", tags=["broker-health"])
def broker_health():
    """Healthcheck endpoint for the Broker subsystem."""
    return {"status": "ok", "service": "broker-panel", "version": "1.0.0"}


@router.get("/me", tags=["broker-context"])
def get_my_broker_context(context: BrokerContext = Depends(get_broker_context)):
    """Return the current user's active broker identity, role, and organization scope."""
    return {
        "user_id": context.user.id,
        "email": context.user.email,
        "organization_id": context.organization_id,
        "role": context.role.value,
        "permissions": [p.value for p in context.permissions],
    }

