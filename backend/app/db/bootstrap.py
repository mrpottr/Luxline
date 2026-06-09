"""Database bootstrap helpers for local development."""

from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.security import hash_password
from backend.app.models import User, UserRole


def ensure_default_admin(db: Session) -> None:
    """Create an initial admin account for non-production environments."""
    if settings.app_env == "production" or not settings.admin_bootstrap_enabled:
        return

    existing_admin = db.query(User.id).filter(User.role == UserRole.super_admin).first()
    if existing_admin:
        return

    admin = db.query(User).filter(User.email == settings.admin_email).first()
    if admin:
        admin.role = UserRole.super_admin
        admin.is_active = True
        admin.is_email_verified = True
        admin.is_2fa_enabled = False
    else:
        admin = User(
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            first_name="System",
            last_name="Admin",
            role=UserRole.super_admin,
            is_active=True,
            is_email_verified=True,
            is_verified_business=False,
            is_2fa_enabled=False,
        )
        db.add(admin)

    db.commit()
