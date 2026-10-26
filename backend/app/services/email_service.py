"""Transactional email and short-lived email-verification OTP helpers."""

import asyncio
import hashlib
import logging
import secrets
import smtplib
from email.message import EmailMessage
from html import escape

from redis.asyncio import Redis

from app.core.config import settings


logger = logging.getLogger(__name__)
_OTP_PREFIX = "email-verification:"
_PASSWORD_RESET_PREFIX = "password-reset:"


def _otp_hash(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _email_html(*, eyebrow: str, title: str, body: str, code: str | None = None) -> str:
    code_block = "" if code is None else f"""
      <div style="margin:28px 0;background:#f3f1ff;border:1px solid #ddd8f2;border-radius:16px;padding:22px;text-align:center;">
        <p style="margin:0 0 8px;color:#6d7484;font-size:12px;font-weight:700;letter-spacing:1.5px;">YOUR FOUR-DIGIT CODE</p>
        <p style="margin:0;color:#7161d7;font-family:Arial,sans-serif;font-size:34px;font-weight:700;letter-spacing:10px;">{escape(code)}</p>
      </div>"""
    return f"""<!doctype html>
<html><body style="margin:0;background:#fffefa;color:#273045;font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="padding:36px 16px;background:#fffefa;"><tr><td align="center">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border:1px solid #e8e5de;border-radius:24px;overflow:hidden;">
      <tr><td style="padding:28px 32px;background:#ffffff;border-bottom:1px solid #f0eee9;"><span style="font-size:21px;font-weight:700;letter-spacing:-.5px;">klyro<span style="color:#7161d7;">ai</span></span></td></tr>
      <tr><td style="padding:34px 32px 28px;"><p style="margin:0 0 10px;color:#8172d8;font-size:11px;font-weight:700;letter-spacing:1.8px;">{escape(eyebrow)}</p><h1 style="margin:0;color:#273045;font-size:28px;line-height:1.25;font-weight:600;letter-spacing:-.6px;">{escape(title)}</h1><p style="margin:18px 0 0;color:#6d7484;font-size:15px;line-height:1.65;">{escape(body)}</p>{code_block}</td></tr>
      <tr><td style="padding:20px 32px;background:#fcfbf8;border-top:1px solid #f0eee9;"><p style="margin:0;color:#92939e;font-size:12px;line-height:1.5;">Klyro AI &middot; Your knowledge, clearly connected.</p></td></tr>
    </table>
  </td></tr></table>
</body></html>"""


def _send_sync(to_email: str, subject: str, text: str, html: str | None = None) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        logger.warning("SMTP is not configured; email to %s was not sent", to_email)
        return
    message = EmailMessage()
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(text)
    if html:
        message.add_alternative(html, subtype="html")
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as client:
        if settings.SMTP_USE_TLS:
            client.starttls()
        if settings.SMTP_USERNAME:
            client.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        client.send_message(message)


async def send_email(to_email: str, subject: str, text: str, *, eyebrow: str = "KLYRO AI", title: str | None = None) -> None:
    """Email failures should never undo an already-completed user action."""
    try:
        await asyncio.to_thread(_send_sync, to_email, subject, text, _email_html(eyebrow=eyebrow, title=title or subject, body=text))
    except Exception:
        logger.exception("Could not send email to %s", to_email)


async def _send_templated(to_email: str, *, subject: str, eyebrow: str, title: str, body: str) -> None:
    """Send a purpose-specific Klyro email with a plain-text fallback."""
    try:
        await asyncio.to_thread(_send_sync, to_email, subject, body, _email_html(eyebrow=eyebrow, title=title, body=body))
    except Exception:
        logger.exception("Could not send %s email to %s", eyebrow.lower(), to_email)


async def send_email_verified_email(to_email: str) -> None:
    await _send_templated(
        to_email,
        subject="Email verified — Klyro AI",
        eyebrow="EMAIL VERIFIED",
        title="You’re all set!",
        body="Your email address has been verified successfully. You can now securely upload documents and build your knowledge bases.",
    )


async def send_knowledge_base_created_email(to_email: str, name: str) -> None:
    await _send_templated(
        to_email,
        subject="Knowledge base created — Klyro AI",
        eyebrow="KNOWLEDGE BASE CREATED",
        title="Your new space is ready",
        body=f'“{name}” has been created. Add documents whenever you’re ready, and Klyro AI will prepare them for chat.',
    )


async def send_knowledge_base_deleted_email(to_email: str, name: str) -> None:
    await _send_templated(
        to_email,
        subject="Knowledge base deleted — Klyro AI",
        eyebrow="KNOWLEDGE BASE DELETED",
        title="A knowledge base was removed",
        body=f'“{name}” has been deleted from your Klyro AI workspace. This action cannot be undone.',
    )


async def send_all_knowledge_bases_deleted_email(to_email: str) -> None:
    await _send_templated(
        to_email,
        subject="All knowledge bases deleted — Klyro AI",
        eyebrow="WORKSPACE UPDATE",
        title="All knowledge bases were removed",
        body="All knowledge bases in your Klyro AI workspace have been deleted. This action cannot be undone.",
    )


async def send_password_changed_email(to_email: str) -> None:
    await _send_templated(
        to_email,
        subject="Password changed — Klyro AI",
        eyebrow="PASSWORD UPDATED",
        title="Your password was changed",
        body="Your Klyro AI password was changed successfully. If you did not make this change, contact support immediately.",
    )


async def issue_verification_code(redis: Redis, user_id: str, email: str) -> None:
    code = f"{secrets.randbelow(10_000):04d}"
    await redis.setex(f"{_OTP_PREFIX}{user_id}", settings.EMAIL_VERIFICATION_TTL_SECONDS, _otp_hash(code))
    text = f"Your verification code is {code}. It expires in {settings.EMAIL_VERIFICATION_TTL_SECONDS // 60} minutes."
    try:
        await asyncio.to_thread(
            _send_sync, email, "Your Klyro AI verification code", text,
            _email_html(eyebrow="EMAIL VERIFICATION", title="Verify your email", body=f"Use this code to enable secure document uploads. It expires in {settings.EMAIL_VERIFICATION_TTL_SECONDS // 60} minutes.", code=code),
        )
    except Exception:
        logger.exception("Could not send verification email to %s", email)


async def issue_password_reset_code(redis: Redis, user_id: str, email: str) -> None:
    code = f"{secrets.randbelow(10_000):04d}"
    await redis.setex(f"{_PASSWORD_RESET_PREFIX}{user_id}", settings.EMAIL_VERIFICATION_TTL_SECONDS, _otp_hash(code))
    text = f"Your password reset code is {code}. It expires in {settings.EMAIL_VERIFICATION_TTL_SECONDS // 60} minutes."
    try:
        await asyncio.to_thread(
            _send_sync, email, "Reset your Klyro AI password", text,
            _email_html(eyebrow="PASSWORD RESET", title="Reset your password", body=f"Use this code to choose a new password. It expires in {settings.EMAIL_VERIFICATION_TTL_SECONDS // 60} minutes.", code=code),
        )
    except Exception:
        logger.exception("Could not send password reset email to %s", email)


async def verify_code(redis: Redis, user_id: str, code: str) -> bool:
    stored = await redis.get(f"{_OTP_PREFIX}{user_id}")
    if not stored:
        return False
    if not secrets.compare_digest(stored.decode() if isinstance(stored, bytes) else stored, _otp_hash(code)):
        return False
    await redis.delete(f"{_OTP_PREFIX}{user_id}")
    return True


async def verify_password_reset_code(redis: Redis, user_id: str, code: str) -> bool:
    key = f"{_PASSWORD_RESET_PREFIX}{user_id}"
    stored = await redis.get(key)
    if not stored:
        return False
    if not secrets.compare_digest(stored.decode() if isinstance(stored, bytes) else stored, _otp_hash(code)):
        return False
    await redis.delete(key)
    return True
