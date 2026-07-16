"""Super-admin fraud signal review endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.dependencies import require_roles
from backend.app.models import AuditLog, FraudSignal, User, UserRole
from backend.app.schemas import FraudSignalCreate, FraudSignalOut


router = APIRouter(prefix="/admin/fraud", tags=["admin-fraud"])


@router.get("/signals", response_model=list[FraudSignalOut])
def list_fraud_signals(
    status_filter: str | None = Query(default="open", alias="status"),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """List fraud signals for manual review."""
    query = db.query(FraudSignal).order_by(FraudSignal.created_at.desc())
    if status_filter:
        query = query.filter(FraudSignal.status == status_filter)
    return query.limit(200).all()


@router.post("/signals", response_model=FraudSignalOut, status_code=status.HTTP_201_CREATED)
def create_fraud_signal(
    payload: FraudSignalCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """Create a manual fraud signal for a listing or user."""
    signal = FraudSignal(**payload.model_dump(), status="open")
    db.add(signal)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            event_type="fraud.signal_created",
            details={"signal_id": signal.id, "severity": signal.severity, "signal_type": signal.signal_type},
        )
    )
    db.commit()
    db.refresh(signal)
    return signal


@router.post("/signals/{signal_id}/resolve", response_model=FraudSignalOut)
def resolve_fraud_signal(
    signal_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.super_admin)),
):
    """Resolve a fraud signal after review."""
    signal = db.query(FraudSignal).filter(FraudSignal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Fraud signal not found")
    signal.status = "resolved"
    signal.resolved_at = datetime.utcnow()
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            event_type="fraud.signal_resolved",
            details={"signal_id": signal.id},
        )
    )
    db.commit()
    db.refresh(signal)
    return signal

