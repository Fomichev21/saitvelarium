from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl

from config import settings


class InitDataError(ValueError):
    pass


@dataclass(frozen=True)
class TelegramUser:
    id: int
    username: str | None
    first_name: str | None
    last_name: str | None


def _secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()


def validate_init_data(init_data: str, *, max_age_seconds: int | None = None) -> dict[str, str]:
    """Validate a Telegram Mini App initData string and return its parsed fields.

    Raises InitDataError if the signature is missing/invalid or the payload is stale.
    See https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    if not init_data:
        raise InitDataError("init_data is empty")
    if not settings.bot_token:
        raise InitDataError("bot token is not configured")

    pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=False)
    fields = dict(pairs)

    provided_hash = fields.pop("hash", None)
    if not provided_hash:
        raise InitDataError("missing hash field")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = _secret_key(settings.bot_token)
    computed_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, provided_hash):
        raise InitDataError("signature mismatch")

    max_age = settings.webapp_init_data_max_age_seconds if max_age_seconds is None else max_age_seconds
    auth_date = fields.get("auth_date")
    if max_age and auth_date:
        try:
            age = time.time() - int(auth_date)
        except ValueError as exc:
            raise InitDataError("invalid auth_date") from exc
        if age > max_age or age < -60:
            raise InitDataError("init_data is stale")

    return fields


def validate_login_widget(data: dict, *, max_age_seconds: int = 86400) -> TelegramUser:
    """Validate a Telegram Login Widget payload (website login) and return the user.

    NOTE: the Login Widget uses a DIFFERENT scheme than Mini App initData —
    secret_key = SHA256(bot_token) (not HMAC("WebAppData", token)).
    See https://core.telegram.org/widgets/login#checking-authorization
    """
    if not settings.bot_token:
        raise InitDataError("bot token is not configured")

    fields = {k: v for k, v in data.items() if v is not None}
    provided_hash = fields.pop("hash", None)
    if not provided_hash:
        raise InitDataError("missing hash field")

    data_check_string = "\n".join(
        f"{key}={fields[key]}" for key in sorted(fields)
    )
    secret_key = hashlib.sha256(settings.bot_token.encode("utf-8")).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, str(provided_hash)):
        raise InitDataError("signature mismatch")

    auth_date = fields.get("auth_date")
    if max_age_seconds and auth_date:
        try:
            age = time.time() - int(auth_date)
        except (ValueError, TypeError) as exc:
            raise InitDataError("invalid auth_date") from exc
        if age > max_age_seconds or age < -60:
            raise InitDataError("login data is stale")

    try:
        user_id = int(fields.get("id"))
    except (ValueError, TypeError) as exc:
        raise InitDataError("invalid user id") from exc

    return TelegramUser(
        id=user_id,
        username=fields.get("username"),
        first_name=fields.get("first_name"),
        last_name=fields.get("last_name"),
    )


def extract_user(fields: dict[str, str]) -> TelegramUser:
    raw_user = fields.get("user")
    if not raw_user:
        raise InitDataError("missing user field")

    try:
        payload = json.loads(raw_user)
    except ValueError as exc:
        raise InitDataError("invalid user field") from exc

    user_id = payload.get("id")
    if not isinstance(user_id, int):
        raise InitDataError("invalid user id")

    return TelegramUser(
        id=user_id,
        username=payload.get("username"),
        first_name=payload.get("first_name"),
        last_name=payload.get("last_name"),
    )
