from __future__ import annotations

import hashlib
import hmac
import secrets

import requests

from config import settings

RESEND_API_URL = "https://api.resend.com/emails"


def is_configured() -> bool:
    # Resend's SMTP password IS the API key, so the same value already
    # stored as SMTP_PASSWORD works as the Bearer token here — no .env
    # change needed when switching transport.
    return bool(settings.smtp_password)


def generate_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def hash_code(email: str, code: str) -> str:
    key = settings.app_secret_key.encode("utf-8")
    msg = f"{email.strip().lower()}:{code}".encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def verify_code(email: str, code: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_code(email, code), code_hash)


def _sender() -> str:
    addr = settings.smtp_from or settings.smtp_user
    name = settings.smtp_from_name or "Velarium VPN"
    return f"{name} <{addr}>"


def _send(to: str, subject: str, text: str, html: str | None = None) -> bool:
    if not is_configured():
        return False

    payload: dict = {"from": _sender(), "to": [to], "subject": subject, "text": text}
    if html:
        payload["html"] = html

    try:
        response = requests.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {settings.smtp_password}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
        if response.status_code >= 400:
            print(f"[email] send failed to {to}: {response.status_code} {response.text}")
            return False
        return True
    except Exception as exc:  # noqa: BLE001 — never leak API errors to the client
        print(f"[email] send failed to {to}: {exc}")
        return False


def send_verification_code(email: str, code: str) -> bool:
    subject = f"Код подтверждения Velarium VPN: {code}"
    text = (
        f"Ваш код подтверждения: {code}\n\n"
        "Введите его на странице оформления, чтобы завершить покупку.\n"
        "Код действует несколько минут. Если вы не запрашивали его — просто игнорируйте это письмо."
    )
    html = f"""
    <div style="font-family:Arial,sans-serif;background:#0b0304;color:#f7efef;padding:32px;border-radius:16px;max-width:440px;margin:auto">
      <h2 style="margin:0 0 8px;color:#ff5b5b">Velarium VPN</h2>
      <p style="color:#c4a6a8;margin:0 0 20px">Код подтверждения для оформления заказа:</p>
      <div style="font-size:34px;font-weight:700;letter-spacing:8px;color:#fff;background:#1c090b;border:1px solid #3d151a;border-radius:12px;padding:16px;text-align:center">{code}</div>
      <p style="color:#8b6a6c;font-size:13px;margin:18px 0 0">Код действует несколько минут. Если вы не запрашивали его, проигнорируйте письмо.</p>
    </div>
    """
    return _send(email, subject, text, html)


def send_access_email(email: str, subscription_url: str, subscription_until: str | None = None) -> bool:
    until = f"\nПодписка активна до: {subscription_until}\n" if subscription_until else "\n"
    subject = "Доступ к Velarium VPN активирован"
    text = (
        "Оплата подтверждена, доступ активирован.\n"
        f"{until}\n"
        "Ссылка на подписку:\n"
        f"{subscription_url}\n\n"
        "Как подключиться:\n"
        "1. Скопируйте ссылку на подписку.\n"
        "2. Откройте приложение с поддержкой подписок по URL (Happ, V2RayNG, Hiddify).\n"
        "3. Добавьте подписку через URL и обновите конфигурацию.\n\n"
        "Если что-то не работает — ответьте на это письмо или напишите в поддержку."
    )
    html = f"""
    <div style="font-family:Arial,sans-serif;background:#0b0304;color:#f7efef;padding:32px;border-radius:16px;max-width:480px;margin:auto">
      <h2 style="margin:0 0 8px;color:#ff5b5b">Velarium VPN — доступ активирован</h2>
      <p style="color:#c4a6a8;margin:0 0 16px">Оплата подтверждена. {('Подписка активна до <b style=\"color:#fff\">' + subscription_until + '</b>.') if subscription_until else ''}</p>
      <p style="color:#c4a6a8;margin:0 0 8px">Ссылка на подписку:</p>
      <div style="font-family:monospace;font-size:13px;color:#fff;background:#1c090b;border:1px solid #3d151a;border-radius:12px;padding:14px;word-break:break-all">{subscription_url}</div>
      <p style="color:#8b6a6c;font-size:13px;margin:18px 0 0">Добавьте ссылку в приложение Happ, V2RayNG или Hiddify через «добавить подписку по URL».</p>
    </div>
    """
    return _send(email, subject, text, html)
