"""Broker lead pipeline endpoints."""

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from backend.app.broker.api.lead_dependencies import get_lead_use_cases
from backend.app.broker.application.lead_use_cases import LeadUseCases
from backend.app.broker.schemas import (
    BrokerLeadActivityCreate, BrokerLeadActivityOut, BrokerLeadAssign,
    BrokerLeadOut, BrokerLeadSpamUpdate, BrokerLeadStageUpdate,
)

router = APIRouter(prefix="/leads", tags=["broker-leads"])


def _execute(operation):
    try:
        return operation()
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("", response_model=list[BrokerLeadOut])
def list_broker_leads(
    stage: str | None = Query(default=None, max_length=24),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: str = Query(default="-created_at", max_length=24),
    cases: LeadUseCases = Depends(get_lead_use_cases),
):
    return _execute(lambda: cases.list_leads(stage=stage, limit=limit, offset=offset, sort=sort))


@router.patch("/{lead_id}/stage", response_model=BrokerLeadOut)
def update_broker_lead_stage(
    lead_id: int,
    payload: BrokerLeadStageUpdate,
    cases: LeadUseCases = Depends(get_lead_use_cases),
):
    lead = _execute(lambda: cases.set_stage(lead_id, payload.stage))
    if not lead:
        raise HTTPException(status_code=404, detail="Broker lead not found")
    return lead


@router.post("/{lead_id}/assign", response_model=BrokerLeadOut)
def assign_broker_lead(
    lead_id: int,
    payload: BrokerLeadAssign,
    cases: LeadUseCases = Depends(get_lead_use_cases),
):
    lead = _execute(lambda: cases.assign(lead_id, payload.member_user_id))
    if not lead:
        raise HTTPException(status_code=404, detail="Broker lead or member not found")
    return lead


@router.patch("/{lead_id}/spam", response_model=BrokerLeadOut)
def set_broker_lead_spam(
    lead_id: int,
    payload: BrokerLeadSpamUpdate,
    cases: LeadUseCases = Depends(get_lead_use_cases),
):
    lead = _execute(lambda: cases.set_spam_flag(lead_id, payload.spam_flag))
    if not lead:
        raise HTTPException(status_code=404, detail="Broker lead not found")
    return lead


@router.get("/{lead_id}/activities", response_model=list[BrokerLeadActivityOut])
def list_broker_lead_activities(
    lead_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    cases: LeadUseCases = Depends(get_lead_use_cases),
):
    activities = _execute(lambda: cases.list_activities(lead_id, limit=limit, offset=offset))
    if activities is None:
        raise HTTPException(status_code=404, detail="Broker lead not found")
    return activities


@router.post("/{lead_id}/activities", response_model=BrokerLeadActivityOut, status_code=201)
def create_broker_lead_activity(
    lead_id: int,
    payload: BrokerLeadActivityCreate,
    idempotency_key: str = Header(min_length=8, max_length=128, alias="Idempotency-Key"),
    cases: LeadUseCases = Depends(get_lead_use_cases),
):
    activity = _execute(lambda: cases.add_activity(
        lead_id, activity_type=payload.activity_type, body=payload.body,
        due_at=payload.due_at, idempotency_key=idempotency_key,
    ))
    if not activity:
        raise HTTPException(status_code=404, detail="Broker lead not found")
    return activity
