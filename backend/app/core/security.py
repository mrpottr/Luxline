from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Any

import jwt
from passlib.context import CryptContext

from backend.app.core.config import settings


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_context.verify(password, password_hash)


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    claims: dict[str, Any] = {"sub": subject}
    if extra_claims:
        claims.update(extra_claims)
    expires_at = datetime.now(tz=timezone.utc) + timedelta(minutes=settings.jwt_exp_minutes)
    claims["exp"] = expires_at
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def generate_otp_code(length: int = 6) -> str:
    max_value = (10**length) - 1
    return str(secrets.randbelow(max_value + 1)).zfill(length)


def hash_otp(code: str) -> str:
    return hashlib.sha256(f"{code}:{settings.jwt_secret}".encode("utf-8")).hexdigest()


def verify_otp(code: str, code_hash: str) -> bool:
    return hash_otp(code) == code_hash
