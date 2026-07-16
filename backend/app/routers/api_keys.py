"""Broker API key management endpoints."""

from datetime import datetime
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.session import get_db
from backend.app.dependencies import require_roles
from backend.app.models import ApiKey, AuditLog, User, UserRole
from backend.app.schemas import ApiKeyCreate, ApiKeyCreateResponse, ApiKeyOut


router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def _hash_key(secret_key: str) -> str:
    return hashlib.sha256(f"{secret_key}:{settings.jwt_secret}".encode("utf-8")).hexdigest()


@router.get("", response_model=list[ApiKeyOut])
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.business_account, UserRole.super_admin)),
):
    """List API keys owned by the current broker/admin account."""
    query = db.query(ApiKey).order_by(ApiKey.created_at.desc())
    if current_user.role != UserRole.super_admin:
        query = query.filter(ApiKey.owner_user_id == current_user.id)
    return query.limit(100).all()


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: ApiKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.business_account, UserRole.super_admin)),
):
    """Create a broker API key and return the secret once."""
    secret_key = f"lux_live_{secrets.token_urlsafe(32)}"
    api_key = ApiKey(
        owner_user_id=current_user.id,
        name=payload.name,
        key_hash=_hash_key(secret_key),
        scopes=payload.scopes,
    )
    db.add(api_key)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            event_type="api_key.created",
            details={"api_key_id": api_key.id, "name": api_key.name, "scopes": api_key.scopes},
        )
    )
    db.commit()
    db.refresh(api_key)
    return {**ApiKeyOut.model_validate(api_key).model_dump(), "secret_key": secret_key}


@router.delete("/{api_key_id}", response_model=ApiKeyOut)
def revoke_api_key(
    api_key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.business_account, UserRole.super_admin)),
):
    """Revoke an API key without deleting its audit trail."""
    query = db.query(ApiKey).filter(ApiKey.id == api_key_id)
    if current_user.role != UserRole.super_admin:
        query = query.filter(ApiKey.owner_user_id == current_user.id)
    api_key = query.first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.revoked_at = datetime.utcnow()
    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            event_type="api_key.revoked",
            details={"api_key_id": api_key.id},
        )
    )
    db.commit()
    db.refresh(api_key)
    return api_key

