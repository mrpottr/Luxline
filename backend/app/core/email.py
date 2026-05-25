"""Email delivery helpers for OTP verification flows."""

from email.message import EmailMessage
import smtplib

from backend.app.core.config import settings


def send_email_otp(to_email: str, code: str) -> bool:
    """Send a verification OTP email. Returns True if delivery was attempted."""
    if not settings.smtp_host or not settings.email_from:
        return False

    from_header = settings.email_from
    if settings.email_from_name:
        from_header = f"{settings.email_from_name} <{settings.email_from}>"

    msg = EmailMessage()
    msg["Subject"] = f"{settings.app_name} verification code"
    msg["From"] = from_header
    msg["To"] = to_email
    msg.set_content(
        "\n".join(
            [
                f"Your {settings.app_name} verification code is {code}.",
                f"It expires in {settings.otp_exp_minutes} minutes.",
                "",
                "If you did not request this, you can ignore this email.",
            ]
        )
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        return True
    except Exception:
        return False
