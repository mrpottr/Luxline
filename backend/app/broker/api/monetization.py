"""Broker subscription, credits wallet, and visibility promotion endpoints."""

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from backend.app.broker.api.dependencies import get_monetization_use_cases
from backend.app.broker.application.monetization_use_cases import MonetizationUseCases
from backend.app.broker.repositories.monetization_repository import (
    InsufficientBrokerCredits,
    MonetizationIdempotencyConflict,
)
from backend.app.broker.schemas import (
    BrokerCreditLedgerOut,
    BrokerCreditWalletOut,
    BrokerPlanOut,
    BrokerPromotionCreate,
    BrokerPromotionOut,
    BrokerSubscriptionOut,
)


router = APIRouter(tags=["broker-monetization"])


def _execute(operation):
    try:
        return operation()
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except (InsufficientBrokerCredits, MonetizationIdempotencyConflict) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/plans", response_model=list[BrokerPlanOut])
def list_broker_plans(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: str = Query(default="code", pattern="^-?code$"),
    cases: MonetizationUseCases = Depends(get_monetization_use_cases),
):
    return _execute(lambda: cases.list_plans(limit=limit, offset=offset, sort=sort))


@router.get("/billing/subscription", response_model=BrokerSubscriptionOut | None)
def get_broker_subscription(cases: MonetizationUseCases = Depends(get_monetization_use_cases)):
    return _execute(cases.current_subscription)


@router.post("/billing/subscribe", response_model=BrokerSubscriptionOut, status_code=201)
def subscribe_to_broker_plan(
    plan_code: str = Query(min_length=1, max_length=50),
    idempotency_key: str = Header(min_length=8, max_length=128, alias="Idempotency-Key"),
    cases: MonetizationUseCases = Depends(get_monetization_use_cases),
):
    return _execute(lambda: cases.subscribe(plan_code=plan_code, idempotency_key=idempotency_key))


@router.get("/credits", response_model=BrokerCreditWalletOut)
def get_credit_wallet(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    cases: MonetizationUseCases = Depends(get_monetization_use_cases),
):
    return _execute(lambda: cases.wallet(limit=limit, offset=offset))


@router.get("/credits/balance")
def get_promotion_credit_balance(cases: MonetizationUseCases = Depends(get_monetization_use_cases)):
    return {"balance": _execute(cases.promotion_balance)}


@router.post("/credits/purchase", response_model=BrokerCreditLedgerOut, status_code=201)
def purchase_credit_pack(
    plan_code: str = Query(min_length=1, max_length=50),
    pack_code: str = Query(min_length=1, max_length=50),
    idempotency_key: str = Header(min_length=8, max_length=128, alias="Idempotency-Key"),
    cases: MonetizationUseCases = Depends(get_monetization_use_cases),
):
    return _execute(lambda: cases.purchase_credit_pack(
        plan_code=plan_code, pack_code=pack_code, idempotency_key=idempotency_key,
    ))


@router.get("/promotions", response_model=list[BrokerPromotionOut])
def list_broker_promotions(
    status: str | None = Query(default=None, max_length=20),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    cases: MonetizationUseCases = Depends(get_monetization_use_cases),
):
    return _execute(lambda: cases.list_promotions(status=status, limit=limit, offset=offset))


@router.post("/promotions/estimate")
def estimate_broker_promotion(
    payload: BrokerPromotionCreate,
    cases: MonetizationUseCases = Depends(get_monetization_use_cases),
):
    return {"credits": _execute(lambda: cases.estimate_promotion(**payload.model_dump()))}


@router.post("/promotions", response_model=BrokerPromotionOut, status_code=201)
def create_broker_promotion(
    payload: BrokerPromotionCreate,
    idempotency_key: str = Header(min_length=8, max_length=128, alias="Idempotency-Key"),
    cases: MonetizationUseCases = Depends(get_monetization_use_cases),
):
    return _execute(lambda: cases.create_promotion(
        payload=payload.model_dump(), idempotency_key=idempotency_key,
    ))
