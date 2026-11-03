"""Broker inbox and consent-scoped buyer conversation endpoints."""

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from backend.app.broker.api.lead_dependencies import get_buyer_lead_use_cases, get_lead_use_cases
from backend.app.broker.application.lead_use_cases import LeadUseCases, TooManyLeadMessages
from backend.app.broker.domain.roles import BrokerPermission
from backend.app.broker.schemas import (
    BrokerLeadBuyerOut, BrokerMessageCreate, BrokerMessageOut, BrokerReplyTemplateCreate, BrokerReplyTemplateOut,
)

router = APIRouter(prefix="/inbox", tags=["broker-inbox"])
buyer_router = APIRouter(prefix="/buyer/inbox", tags=["broker-buyer-inbox"])


def _execute(operation):
    try:
        return operation()
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except TooManyLeadMessages as error:
        raise HTTPException(status_code=429, detail=str(error)) from error


@router.get("/templates", response_model=list[BrokerReplyTemplateOut])
def list_reply_templates(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    cases: LeadUseCases = Depends(get_lead_use_cases),
):
    return _execute(lambda: cases.list_templates(limit=limit, offset=offset))


@router.post("/templates", response_model=BrokerReplyTemplateOut, status_code=201)
def create_reply_template(
    payload: BrokerReplyTemplateCreate,
    idempotency_key: str = Header(min_length=8, max_length=128, alias="Idempotency-Key"),
    cases: LeadUseCases = Depends(get_lead_use_cases),
):
    return _execute(lambda: cases.create_template(title=payload.title, body=payload.body, idempotency_key=idempotency_key))


@router.get("/{lead_id}/messages", response_model=list[BrokerMessageOut])
def list_lead_messages(
    lead_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    cases: LeadUseCases = Depends(get_lead_use_cases),
):
    messages = _execute(lambda: cases.list_messages(lead_id, limit=limit, offset=offset))
    if messages is None:
        raise HTTPException(status_code=404, detail="Broker lead not found")
    return messages


@router.post("/{lead_id}/messages", response_model=BrokerMessageOut, status_code=201)
def send_lead_message(
    lead_id: int,
    payload: BrokerMessageCreate,
    idempotency_key: str = Header(min_length=8, max_length=128, alias="Idempotency-Key"),
    cases: LeadUseCases = Depends(get_lead_use_cases),
):
    message = _execute(lambda: cases.send_agent_message(lead_id, payload.body, idempotency_key))
    if message is None:
        raise HTTPException(status_code=404, detail="A consented account lead is required to message this buyer")
    return message


@buyer_router.get("", response_model=list[BrokerLeadBuyerOut])
def list_buyer_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    cases: LeadUseCases = Depends(get_buyer_lead_use_cases),
):
    return _execute(lambda: cases.list_buyer_leads(cases.actor_user_id, limit=limit, offset=offset))


@buyer_router.get("/{lead_id}/messages", response_model=list[BrokerMessageOut])
def list_buyer_messages(
    lead_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    cases: LeadUseCases = Depends(get_buyer_lead_use_cases),
):
    messages = _execute(lambda: cases.list_buyer_messages(
        lead_id, cases.actor_user_id, limit=limit, offset=offset,
    ))
    if messages is None:
        raise HTTPException(status_code=404, detail="Buyer conversation not found")
    return messages


@buyer_router.post("/{lead_id}/messages", response_model=BrokerMessageOut, status_code=201)
def send_buyer_message(
    lead_id: int,
    payload: BrokerMessageCreate,
    idempotency_key: str = Header(min_length=8, max_length=128, alias="Idempotency-Key"),
    cases: LeadUseCases = Depends(get_buyer_lead_use_cases),
):
    message = _execute(lambda: cases.send_buyer_message(
        lead_id, cases.actor_user_id, payload.body, idempotency_key,
    ))
    if message is None:
        raise HTTPException(status_code=404, detail="Buyer conversation not found")
    return message
