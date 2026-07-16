"""Authentication and account-access endpoints."""

from datetime import datetime, timedelta
import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.email import send_email_otp
from backend.app.core.security import (
    create_access_token,
    generate_otp_code,
    hash_otp,
    hash_password,
    verify_otp,
    verify_password,
)
from backend.app.db.session import get_db
from backend.app.dependencies import get_current_user as get_current_user_dep
from backend.app.models import EmailVerificationChallenge, SocialAccount, TwoFactorChallenge, User, UserRole
from backend.app.schemas import (
    EmailVerificationRequest,
    EmailVerificationResendRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    SocialLoginRequest,
    TokenResponse,
    TwoFactorVerifyRequest,
    UserOut,
)


router = APIRouter(prefix="/auth", tags=["auth"])


def _create_email_verification(db: Session, user: User) -> tuple[EmailVerificationChallenge, str | None, bool]:
    code = generate_otp_code()
    challenge = EmailVerificationChallenge(
        user_id=user.id,
        code_hash=hash_otp(code),
        expires_at=datetime.utcnow() + timedelta(minutes=settings.otp_exp_minutes),
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    email_sent = send_email_otp(user.email, code)
    dev_code = code if settings.app_env != "production" else None
    if not email_sent and settings.app_env != "production":
        dev_code = code
    return challenge, dev_code, email_sent


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account with role-based defaults."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    if payload.role == UserRole.super_admin:
        raise HTTPException(status_code=400, detail="Cannot self-register as super admin")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        role=payload.role,
        is_2fa_enabled=payload.role == UserRole.business_account,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    challenge, dev_code, email_sent = _create_email_verification(db, user)
    return RegisterResponse(
        user=user,
        verification_required=True,
        email_verification_id=challenge.id,
        email_otp_expires_in_seconds=settings.otp_exp_minutes * 60,
        email_otp_code_dev_only=dev_code,
        email_sent=email_sent,
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate a user and return either a token or a 2FA challenge."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is suspended")
    if not user.is_email_verified:
        challenge, dev_code, email_sent = _create_email_verification(db, user)
        return LoginResponse(
            requires_email_verification=True,
            email_verification_id=challenge.id,
            email_otp_expires_in_seconds=settings.otp_exp_minutes * 60,
            email_otp_code_dev_only=dev_code,
            email_sent=email_sent,
        )

    two_factor_required = bool(user.role == UserRole.business_account and user.is_2fa_enabled)
    if two_factor_required:
        code = generate_otp_code()
        challenge = TwoFactorChallenge(
            user_id=user.id,
            code_hash=hash_otp(code),
            expires_at=datetime.utcnow() + timedelta(minutes=settings.otp_exp_minutes),
        )
        db.add(challenge)
        db.commit()
        db.refresh(challenge)
        return LoginResponse(
            requires_2fa=True,
            challenge_id=challenge.id,
            otp_expires_in_seconds=settings.otp_exp_minutes * 60,
            otp_code_dev_only=code if settings.app_env != "production" else None,
        )

    token = create_access_token(str(user.id), extra_claims={"role": user.role.value})
    return LoginResponse(access_token=token, requires_2fa=False)


@router.post("/email/verify", response_model=TokenResponse)
def verify_email(payload: EmailVerificationRequest, db: Session = Depends(get_db)):
    """Verify a user's email address using a one-time code."""
    challenge = (
        db.query(EmailVerificationChallenge)
        .filter(EmailVerificationChallenge.id == payload.verification_id)
        .first()
    )
    if not challenge:
        raise HTTPException(status_code=404, detail="Verification request not found")
    if challenge.consumed_at:
        raise HTTPException(status_code=400, detail="Verification code already used")
    if challenge.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification code expired")
    if not verify_otp(payload.code, challenge.code_hash):
        raise HTTPException(status_code=401, detail="Invalid verification code")

    user = db.query(User).filter(User.id == challenge.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User is not active")

    user.is_email_verified = True
    challenge.consumed_at = datetime.utcnow()
    db.commit()

    token = create_access_token(str(user.id), extra_claims={"role": user.role.value})
    return TokenResponse(access_token=token)


@router.post("/email/resend", response_model=RegisterResponse)
def resend_email_verification(payload: EmailVerificationResendRequest, db: Session = Depends(get_db)):
    """Resend a verification code to an unverified user email."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    challenge, dev_code, email_sent = _create_email_verification(db, user)
    return RegisterResponse(
        user=user,
        verification_required=True,
        email_verification_id=challenge.id,
        email_otp_expires_in_seconds=settings.otp_exp_minutes * 60,
        email_otp_code_dev_only=dev_code,
        email_sent=email_sent,
    )


@router.post("/2fa/verify", response_model=TokenResponse)
def verify_two_factor(payload: TwoFactorVerifyRequest, db: Session = Depends(get_db)):
    """Validate a 2FA challenge code and issue an access token."""
    challenge = db.query(TwoFactorChallenge).filter(TwoFactorChallenge.id == payload.challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="2FA challenge not found")
    if challenge.consumed_at:
        raise HTTPException(status_code=400, detail="2FA challenge already used")
    if challenge.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="2FA challenge expired")
    if not verify_otp(payload.code, challenge.code_hash):
        raise HTTPException(status_code=401, detail="Invalid verification code")

    user = db.query(User).filter(User.id == challenge.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User is not active")

    challenge.consumed_at = datetime.utcnow()
    db.commit()

    token = create_access_token(str(user.id), extra_claims={"role": user.role.value})
    return TokenResponse(access_token=token)


@router.post("/social/login", response_model=TokenResponse)
def social_login(payload: SocialLoginRequest, db: Session = Depends(get_db)):
    """Log in or provision a user from a supported social identity provider."""
    provider = payload.provider.lower().strip()
    if provider not in {"google", "apple"}:
        raise HTTPException(status_code=400, detail="Unsupported social provider")

    # Placeholder identity extraction; replace with provider token verification in production.
    provider_user_id = hashlib.sha256(payload.id_token.encode("utf-8")).hexdigest()

    social = (
        db.query(SocialAccount)
        .filter(SocialAccount.provider == provider, SocialAccount.provider_user_id == provider_user_id)
        .first()
    )
    if social:
        user = db.query(User).filter(User.id == social.user_id, User.is_active.is_(True)).first()
        if not user:
            raise HTTPException(status_code=401, detail="Linked user unavailable")
        if not user.is_email_verified:
            user.is_email_verified = True
            db.commit()
        token = create_access_token(str(user.id), extra_claims={"role": user.role.value})
        return TokenResponse(access_token=token)

    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        user = User(
            email=payload.email,
            password_hash=hash_password(payload.id_token),
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone=payload.phone,
            role=UserRole.standard_user,
            is_email_verified=True,
        )
        db.add(user)
        db.flush()

    db.add(
        SocialAccount(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            email=payload.email,
        )
    )
    db.commit()
    db.refresh(user)
    token = create_access_token(str(user.id), extra_claims={"role": user.role.value})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def get_authenticated_user(current_user: User = Depends(get_current_user_dep)):
    """Return the authenticated user's own profile – convenience alias for /users/me."""
    return current_user


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(current_user: User = Depends(get_current_user_dep)):
    """Issue a fresh JWT for an already-authenticated user (slide the expiry window)."""
    token = create_access_token(str(current_user.id), extra_claims={"role": current_user.role.value})
    return TokenResponse(access_token=token)


@router.post("/logout")
def logout(_current_user: User = Depends(get_current_user_dep)):
    """Invalidate the current session. JWTs are stateless; clients must discard the token."""
    return {"message": "Logged out successfully"}
