from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from config import settings
from database import add_user, get_role, is_banned
from security import create_jwt
from webapp.schemas import TelegramAuthRequest, TelegramAuthResponse
from webapp.telegram_auth import (
    InitDataError,
    extract_user,
    validate_init_data,
    validate_login_widget,
)

router = APIRouter(tags=["auth"])


def _issue_session(tg_user) -> TelegramAuthResponse:
    add_user(
        tg_user.id,
        tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
    )
    if is_banned(tg_user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is banned")

    role = get_role(tg_user.id)
    token = create_jwt(
        {"uid": tg_user.id, "role": role},
        expires_in=settings.webapp_session_ttl_seconds,
    )
    return TelegramAuthResponse(token=token, expires_in=settings.webapp_session_ttl_seconds, role=role)


@router.post("/auth/telegram", response_model=TelegramAuthResponse)
def telegram_login(payload: TelegramAuthRequest) -> TelegramAuthResponse:
    """Telegram Mini App initData → session (in-Telegram cabinet)."""
    try:
        fields = validate_init_data(payload.init_data)
        tg_user = extract_user(fields)
    except InitDataError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid Telegram init data: {exc}") from exc
    return _issue_session(tg_user)


@router.post("/auth/telegram-login", response_model=TelegramAuthResponse)
def telegram_login_widget(payload: dict) -> TelegramAuthResponse:
    """Website Telegram Login Widget → session (public checkout on the marketing site)."""
    try:
        tg_user = validate_login_widget(payload)
    except InitDataError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid Telegram login: {exc}") from exc
    return _issue_session(tg_user)
