from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from config import settings
from database import (
    delete_email_code,
    get_email_code,
    increment_email_attempts,
    set_email_code,
)
from webapp import email_auth

MAX_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 45


def request_code(email: str) -> dict[str, Any]:
    """Generate + send (or dev-echo) a verification code for `email`.

    Shared between the web checkout and the bot's "link e-mail" flow so both
    surfaces use identical rate-limiting and delivery behavior.
    """
    email = email.strip().lower()

    existing = get_email_code(email)
    if existing and existing.get("last_sent_at"):
        try:
            last = datetime.fromisoformat(str(existing["last_sent_at"]))
            if (datetime.utcnow() - last).total_seconds() < RESEND_COOLDOWN_SECONDS:
                return {"ok": False, "reason": "cooldown", "cooldown": RESEND_COOLDOWN_SECONDS}
        except ValueError:
            pass

    code = email_auth.generate_code()
    expires_at = (datetime.utcnow() + timedelta(seconds=settings.email_code_ttl_seconds)).isoformat()
    set_email_code(email, email_auth.hash_code(email, code), expires_at)
    sent = email_auth.send_verification_code(email, code)

    result: dict[str, Any] = {"ok": True, "sent": sent, "cooldown": RESEND_COOLDOWN_SECONDS}
    if not email_auth.is_configured():
        result["dev_code"] = code
    return result


def verify_code(email: str, code: str) -> tuple[bool, str]:
    """Check a submitted code. Returns (success, error_message_if_any)."""
    email = email.strip().lower()
    code = (code or "").strip()

    record = get_email_code(email)
    if not record:
        return False, "Код не найден, запросите новый"

    try:
        expires_at = datetime.fromisoformat(str(record["expires_at"]))
    except ValueError:
        expires_at = datetime.utcnow() - timedelta(seconds=1)
    if datetime.utcnow() > expires_at:
        delete_email_code(email)
        return False, "Код истёк, запросите новый"

    if int(record.get("attempts", 0)) >= MAX_ATTEMPTS:
        delete_email_code(email)
        return False, "Слишком много попыток, запросите новый код"

    if not email_auth.verify_code(email, code, str(record["code_hash"])):
        attempts = increment_email_attempts(email)
        remaining = max(0, MAX_ATTEMPTS - attempts)
        return False, f"Неверный код. Осталось попыток: {remaining}"

    delete_email_code(email)
    return True, ""
