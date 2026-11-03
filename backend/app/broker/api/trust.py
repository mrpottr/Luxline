"""Broker review, badge, moderation, and audit endpoints."""

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from backend.app.broker.api.trust_dependencies import (
    get_admin_trust_use_cases,
    get_broker_trust_use_cases,
    get_buyer_review_use_cases,
    get_public_trust_use_cases,
)
from backend.app.broker.application.trust_use_cases import (
    AdminTrustUseCases,
    BrokerTrustUseCases,
    BuyerReviewUseCases,
    PublicTrustUseCases,
)
from backend.app.broker.repositories.trust_repository import BrokerReviewIntegrityViolation
from backend.app.broker.schemas import (
    BrokerAuditLogOut,
    BrokerBadgeOut,
    BrokerModerationCaseOut,
    BrokerModerationResolve,
    BrokerReviewAppeal,
    BrokerReviewCreate,
    BrokerReviewDecision,
    BrokerReviewOut,
    BrokerReviewReply,
)


router = APIRouter(tags=["broker-trust"])
buyer_router = APIRouter(prefix="/buyer/reviews", tags=["broker-buyer-reviews"])
public_router = APIRouter(prefix="/public/brokers/{organization_id}/reviews", tags=["broker-public-reviews"])
admin_router = APIRouter(prefix="/admin", tags=["broker-trust-admin"])


def _execute(operation):
    try:
        return operation()
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except BrokerReviewIntegrityViolation as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/reviews", response_model=list[BrokerReviewOut])
def list_broker_reviews(
    status: str | None = Query(default=None, max_length=20),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    cases: BrokerTrustUseCases = Depends(get_broker_trust_use_cases),
):
    return _execute(lambda: cases.list_reviews(status=status, limit=limit, offset=offset))


@router.post("/reviews/{review_id}/reply", response_model=BrokerReviewOut)
def reply_to_broker_review(
    review_id: int,
    payload: BrokerReviewReply,
    cases: BrokerTrustUseCases = Depends(get_broker_trust_use_cases),
):
    review = _execute(lambda: cases.reply(review_id=review_id, body=payload.body))
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.post("/reviews/{review_id}/appeal", response_model=BrokerReviewOut)
def appeal_broker_review(
    review_id: int,
    payload: BrokerReviewAppeal,
    cases: BrokerTrustUseCases = Depends(get_broker_trust_use_cases),
):
    review = _execute(lambda: cases.appeal(review_id=review_id, reason=payload.reason))
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.get("/badges", response_model=list[BrokerBadgeOut])
def list_broker_badges(cases: BrokerTrustUseCases = Depends(get_broker_trust_use_cases)):
    return _execute(cases.list_badges)


@router.get("/audit", response_model=list[BrokerAuditLogOut])
def list_broker_audit(
    action: str | None = Query(default=None, max_length=64),
    actor_user_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    cases: BrokerTrustUseCases = Depends(get_broker_trust_use_cases),
):
    return _execute(lambda: cases.audit(action=action, actor_user_id=actor_user_id, limit=limit, offset=offset))


@buyer_router.post("", response_model=BrokerReviewOut, status_code=201)
def submit_broker_review(
    payload: BrokerReviewCreate,
    idempotency_key: str = Header(min_length=8, max_length=128, alias="Idempotency-Key"),
    cases: BuyerReviewUseCases = Depends(get_buyer_review_use_cases),
):
    return _execute(lambda: cases.submit(
        lead_id=payload.lead_id, rating=payload.rating, body=payload.body,
        public_consent=payload.public_consent, idempotency_key=idempotency_key,
    ))


@public_router.get("", response_model=list[BrokerReviewOut])
def list_public_broker_reviews(
    organization_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    cases: PublicTrustUseCases = Depends(get_public_trust_use_cases),
):
    return _execute(lambda: cases.reviews(limit=limit, offset=offset))


@admin_router.get("/moderation-cases", response_model=list[BrokerModerationCaseOut])
def list_broker_moderation_cases(
    status: str | None = Query(default=None, max_length=16),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    cases: AdminTrustUseCases = Depends(get_admin_trust_use_cases),
):
    return _execute(lambda: cases.list_cases(status=status, limit=limit, offset=offset))


@admin_router.post("/moderation-cases/{case_id}/resolve", response_model=BrokerModerationCaseOut)
def resolve_broker_moderation_case(
    case_id: int,
    payload: BrokerModerationResolve,
    cases: AdminTrustUseCases = Depends(get_admin_trust_use_cases),
):
    case = _execute(lambda: cases.resolve_case(case_id=case_id, resolution=payload.resolution))
    if not case:
        raise HTTPException(status_code=404, detail="Moderation case not found")
    return case


@admin_router.post("/reviews/{review_id}/decision", response_model=BrokerReviewOut)
def decide_broker_review(
    review_id: int,
    payload: BrokerReviewDecision,
    cases: AdminTrustUseCases = Depends(get_admin_trust_use_cases),
):
    review = _execute(lambda: cases.decide_review(
        review_id=review_id, decision=payload.decision, notes=payload.notes,
    ))
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review
