from __future__ import annotations

import re
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from config import settings
from database import (
    delete_email_code,
    get_email_code,
    get_or_create_email_user,
    get_role,
    increment_email_attempts,
    is_banned,
    set_email_code,
)
from security import create_jwt
from webapp import email_auth

router = APIRouter(tags=["checkout"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 45


class EmailStartRequest(BaseModel):
    email: str


class EmailVerifyRequest(BaseModel):
    email: str
    code: str


def _normalize_email(raw: str) -> str:
    email = (raw or "").strip().lower()
    if not EMAIL_RE.match(email) or len(email) > 254:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Некорректный e-mail")
    return email


@router.post("/checkout/email/start")
def email_start(payload: EmailStartRequest) -> dict:
    email = _normalize_email(payload.email)

    # Simple resend cooldown
    existing = get_email_code(email)
    if existing and existing.get("last_sent_at"):
        try:
            last = datetime.fromisoformat(str(existing["last_sent_at"]))
            if (datetime.utcnow() - last).total_seconds() < RESEND_COOLDOWN_SECONDS:
                raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Код уже отправлен, подождите немного")
        except ValueError:
            pass

    code = email_auth.generate_code()
    expires_at = (datetime.utcnow() + timedelta(seconds=settings.email_code_ttl_seconds)).isoformat()
    set_email_code(email, email_auth.hash_code(email, code), expires_at)

    sent = email_auth.send_verification_code(email, code)

    response: dict = {"sent": sent, "cooldown": RESEND_COOLDOWN_SECONDS}
    # Dev fallback: if SMTP is not configured there is no way to receive the code,
    # so echo it back to make the flow usable locally. Never happens in production
    # (production configures SMTP_USER/SMTP_PASSWORD).
    if not email_auth.is_configured():
        response["dev_code"] = code
        response["dev"] = True
    return response


@router.post("/checkout/email/verify")
def email_verify(payload: EmailVerifyRequest) -> dict:
    email = _normalize_email(payload.email)
    code = (payload.code or "").strip()

    record = get_email_code(email)
    if not record:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Код не найден, запросите новый")

    try:
        expires_at = datetime.fromisoformat(str(record["expires_at"]))
    except ValueError:
        expires_at = datetime.utcnow() - timedelta(seconds=1)
    if datetime.utcnow() > expires_at:
        delete_email_code(email)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Код истёк, запросите новый")

    if int(record.get("attempts", 0)) >= MAX_ATTEMPTS:
        delete_email_code(email)
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Слишком много попыток, запросите новый код")

    if not email_auth.verify_code(email, code, str(record["code_hash"])):
        attempts = increment_email_attempts(email)
        remaining = max(0, MAX_ATTEMPTS - attempts)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Неверный код. Осталось попыток: {remaining}")

    # success
    delete_email_code(email)
    user_id = get_or_create_email_user(email)
    if is_banned(user_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Этот аккаунт заблокирован")

    role = get_role(user_id)
    token = create_jwt({"uid": user_id, "role": role}, expires_in=settings.webapp_session_ttl_seconds)
    return {"token": token, "expires_in": settings.webapp_session_ttl_seconds, "role": role, "email": email}
