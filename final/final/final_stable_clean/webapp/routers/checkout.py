from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from config import settings
from database import get_or_create_email_user, get_role, get_user_by_email, is_banned
from email_otp import request_code, verify_code
from security import create_jwt

router = APIRouter(tags=["checkout"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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
    result = request_code(email)
    if not result["ok"]:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Код уже отправлен, подождите немного")
    response = {"sent": result["sent"], "cooldown": result["cooldown"]}
    if "dev_code" in result:
        response["dev_code"] = result["dev_code"]
        response["dev"] = True
    return response


@router.post("/checkout/email/verify")
def email_verify(payload: EmailVerifyRequest) -> dict:
    email = _normalize_email(payload.email)
    ok, error = verify_code(email, payload.code)
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, error)

    # If this e-mail is already linked to an account (real Telegram account
    # via bot profile, or a returning web-only buyer), log into THAT account
    # instead of minting a new one — keeps subscription/history in one place.
    existing_user = get_user_by_email(email)
    user_id = int(existing_user["user_id"]) if existing_user else get_or_create_email_user(email)

    if is_banned(user_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Этот аккаунт заблокирован")

    role = get_role(user_id)
    token = create_jwt({"uid": user_id, "role": role}, expires_in=settings.webapp_session_ttl_seconds)
    return {"token": token, "expires_in": settings.webapp_session_ttl_seconds, "role": role, "email": email}
