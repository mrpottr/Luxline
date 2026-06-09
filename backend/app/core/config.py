"""Environment-backed application settings."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)


@dataclass(frozen=True)
class Settings:
    """Runtime configuration loaded from `.env` with safe defaults."""
    app_name: str = os.getenv("APP_NAME", "Luxline API")
    app_env: str = os.getenv("APP_ENV", "development")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./luxline.db")
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me-in-production")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_exp_minutes: int = int(os.getenv("JWT_EXP_MINUTES", "120"))
    otp_exp_minutes: int = int(os.getenv("OTP_EXP_MINUTES", "10"))
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")
    default_currency: str = os.getenv("DEFAULT_CURRENCY", "USD")
    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes", "on"}
    email_from: str = os.getenv("EMAIL_FROM", "")
    email_from_name: str = os.getenv("EMAIL_FROM_NAME", "")
    admin_bootstrap_enabled: bool = os.getenv("ADMIN_BOOTSTRAP_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    admin_email: str = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "admin123")


settings = Settings()
