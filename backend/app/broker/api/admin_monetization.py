"""Platform administrator endpoints for broker plans and entitlements."""

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from backend.app.broker.api.monetization_dependencies import get_broker_plan_admin_use_cases
from backend.app.broker.application.monetization_use_cases import (
    AdminPlanUseCases,
    BrokerPlanAlreadyExists,
    BrokerPlanIdempotencyConflict,
)
from backend.app.broker.schemas import BrokerPlanOut, BrokerPlanUpsert


router = APIRouter(prefix="/admin/plans", tags=["broker-plan-admin"])


def _execute(operation):
    try:
        return operation()
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except BrokerPlanAlreadyExists as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except BrokerPlanIdempotencyConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("", response_model=list[BrokerPlanOut])
def list_all_broker_plans(
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: str = Query(default="code", pattern="^-?code$"),
    cases: AdminPlanUseCases = Depends(get_broker_plan_admin_use_cases),
):
    return _execute(lambda: cases.list_plans(is_active=is_active, limit=limit, offset=offset, sort=sort))


@router.post("", response_model=BrokerPlanOut, status_code=201)
def create_broker_plan(
    payload: BrokerPlanUpsert,
    idempotency_key: str = Header(min_length=8, max_length=128, alias="Idempotency-Key"),
    cases: AdminPlanUseCases = Depends(get_broker_plan_admin_use_cases),
):
    return _execute(lambda: cases.create_plan(payload=payload.model_dump(), idempotency_key=idempotency_key))


@router.put("/{code}", response_model=BrokerPlanOut)
def update_broker_plan(
    code: str,
    payload: BrokerPlanUpsert,
    cases: AdminPlanUseCases = Depends(get_broker_plan_admin_use_cases),
):
    if payload.code != code:
        raise HTTPException(status_code=422, detail="Plan code in path and request must match")
    return _execute(lambda: cases.update_plan(payload=payload.model_dump(), code=code))
