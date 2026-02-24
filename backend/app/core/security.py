"""Password, token, and one-time-code helpers for authentication flows."""

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Any

import jwt
from passlib.context import CryptContext

from backend.app.core.config import settings


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password using the configured password context."""
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Validate a plain-text password against a stored hash."""
    return password_context.verify(password, password_hash)


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Create a signed JWT access token for a user identifier."""
    claims: dict[str, Any] = {"sub": subject}
    if extra_claims:
        claims.update(extra_claims)
    expires_at = datetime.now(tz=timezone.utc) + timedelta(minutes=settings.jwt_exp_minutes)
    claims["exp"] = expires_at
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT access token."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def generate_otp_code(length: int = 6) -> str:
    """Generate a zero-padded numeric one-time code."""
    max_value = (10**length) - 1
    return str(secrets.randbelow(max_value + 1)).zfill(length)


def hash_otp(code: str) -> str:
    """Derive a deterministic hash for storing OTP codes safely."""
    return hashlib.sha256(f"{code}:{settings.jwt_secret}".encode("utf-8")).hexdigest()


def verify_otp(code: str, code_hash: str) -> bool:
    """Compare a provided OTP code against its stored hash."""
    return hash_otp(code) == code_hash
