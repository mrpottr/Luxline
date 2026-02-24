"""Reusable FastAPI dependency providers for auth and authorization."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from backend.app.core.security import decode_access_token
from backend.app.db.session import get_db
from backend.app.models import User, UserRole


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    """Return the authenticated active user or raise a 401 error."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
    except (InvalidTokenError, ValueError, TypeError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise credentials_exception
    return user


def get_optional_current_user(db: Session = Depends(get_db), token: str | None = Depends(optional_oauth2_scheme)) -> User | None:
    """Return the authenticated user if possible; otherwise return `None`."""
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
    except (InvalidTokenError, ValueError, TypeError):
        return None

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    return user


def require_roles(*roles: UserRole):
    """Build a dependency that allows only users with one of the provided roles."""
    def _role_dependency(current_user: User = Depends(get_current_user)) -> User:
        """Validate that the current user matches the accepted role set."""
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return _role_dependency
