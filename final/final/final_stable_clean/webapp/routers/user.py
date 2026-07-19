from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from config import REFERRAL_BONUS_DAYS, TARIFFS, settings
from database import (
    activate_trial_days,
    add_support_message,
    count_unread_support_for_user,
    get_balance,
    get_referral_stats,
    get_trial,
    get_user,
    get_user_email,
    get_vpn_key,
    list_admin_ids,
    list_support_messages,
    list_user_payments,
    mark_payment_access_sent,
    mark_support_messages_read,
    use_promo,
)
from payments import check_payment, create_payment_for_tariff, notify_admins_about_payment
from webapp.email_auth import send_access_email
from remnawave import check_nodes_status, get_user_traffic
from webapp.bot import get_bot, get_bot_username
from webapp.content import (
    CONNECT_APPS,
    FAQ_ITEMS,
    HIGHLIGHTS,
    INFO_DESCRIPTION,
    INFO_TAGLINE,
    KNOWLEDGE_BASE_URL,
    PRIVACY_URL,
    SUPPORT_AUTO_REPLY,
    TERMS_URL,
)
from webapp.deps import CurrentUser, get_current_user
from webapp.qr import qrcode_png_response
from webapp.schemas import CheckoutRequest, PromoRedeemRequest, SupportMessageRequest

router = APIRouter(tags=["user"])


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _subscription_status(user: dict[str, Any], trial: dict[str, Any] | None) -> dict[str, Any]:
    now = datetime.utcnow()

    sub_until = _parse_dt(user.get("subscription_until"))
    if sub_until and sub_until > now:
        return _build_status("active", sub_until, now, user_id=int(user["user_id"]))

    trial_until = _parse_dt(user.get("trial_until"))
    if trial_until and trial_until > now and trial and not trial.get("revoked_at"):
        return _build_status("trial", trial_until, now, user_id=None)

    return {"status": "none", "expires_at": None, "days_remaining": 0, "total_days": None}


def _build_status(kind: str, expires_at: datetime, now: datetime, *, user_id: int | None) -> dict[str, Any]:
    days_remaining = max(0, (expires_at.date() - now.date()).days)
    total_days = None

    if kind == "active" and user_id is not None:
        for payment in list_user_payments(user_id, limit=10):
            if payment.get("status") == "paid" and payment.get("tariff_code") in TARIFFS:
                total_days = TARIFFS[payment["tariff_code"]]["duration_days"]
                break
    if total_days is None:
        total_days = days_remaining or 1

    return {
        "status": kind,
        "expires_at": expires_at.isoformat(sep=" "),
        "days_remaining": days_remaining,
        "total_days": total_days,
    }


@router.get("/me")
def me(current_user: CurrentUser = Depends(get_current_user)) -> dict[str, Any]:
    user = get_user(current_user.user_id)
    return {
        "user_id": user["user_id"],
        "username": user.get("username"),
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "email": get_user_email(current_user.user_id),
        "balance": get_balance(current_user.user_id),
        "role": current_user.role,
        "created_at": user.get("created_at"),
        "is_web_only": current_user.user_id < 0,
    }


@router.get("/subscription")
def subscription(current_user: CurrentUser = Depends(get_current_user)) -> dict[str, Any]:
    user = get_user(current_user.user_id)
    trial = get_trial(current_user.user_id)
    vpn_key = get_vpn_key(current_user.user_id)

    traffic = None
    if vpn_key and vpn_key.get("vpn_key"):
        try:
            traffic = get_user_traffic(str(vpn_key["vpn_key"]))
        except Exception:
            traffic = None

    return {
        **_subscription_status(user, trial),
        "subscription_url": (vpn_key or {}).get("config_text"),
        "traffic": traffic,
    }


@router.get("/status")
def server_status() -> dict[str, Any]:
    status_summary = check_nodes_status()
    if status_summary is None:
        return {"available": False}
    return {"available": True, **status_summary}


@router.get("/info")
def info() -> dict[str, Any]:
    return {
        "description": INFO_DESCRIPTION,
        "tagline": INFO_TAGLINE,
        "support_username": settings.support_username,
        "terms_url": TERMS_URL,
        "privacy_url": PRIVACY_URL,
        "connect_apps": CONNECT_APPS,
        "highlights": HIGHLIGHTS,
    }


@router.get("/subscription/key")
def subscription_key(current_user: CurrentUser = Depends(get_current_user)) -> dict[str, Any]:
    vpn_key = get_vpn_key(current_user.user_id)
    if not vpn_key:
        return {"subscription_url": None, "expire_at": None}
    return {"subscription_url": vpn_key.get("config_text"), "expire_at": vpn_key.get("expire_at")}


@router.get("/subscription/key/qrcode")
def subscription_key_qrcode(current_user: CurrentUser = Depends(get_current_user)):
    vpn_key = get_vpn_key(current_user.user_id)
    data = (vpn_key or {}).get("config_text")
    if not data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No subscription key yet")
    return qrcode_png_response(data)


@router.get("/tariffs")
def tariffs() -> dict[str, Any]:
    return {"tariffs": [{"code": code, **tariff} for code, tariff in TARIFFS.items() if not tariff.get("traffic_reset")]}


@router.post("/subscription/checkout")
async def checkout(
    payload: CheckoutRequest, current_user: CurrentUser = Depends(get_current_user)
) -> dict[str, Any]:
    if payload.tariff_code not in TARIFFS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown tariff")

    payment = create_payment_for_tariff(current_user.user_id, payload.tariff_code)
    # Fire admin notification in the background — never block the buyer's response
    # on Telegram (and on this dev machine a proxy-less Bot() can hang).
    asyncio.create_task(_notify_admins_bg(str(payment["id"])))
    return payment


async def _notify_admins_bg(payment_id: str) -> None:
    try:
        await asyncio.wait_for(notify_admins_about_payment(get_bot(), payment_id), timeout=8)
    except Exception:
        pass


@router.get("/subscription/checkout/{payment_id}/status")
def checkout_status(payment_id: str, current_user: CurrentUser = Depends(get_current_user)) -> dict[str, Any]:
    payment = check_payment(payment_id)
    if not payment or int(payment["user_id"]) != current_user.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")

    # E-mail buyers are not reachable via a Telegram DM, so deliver the key by e-mail
    # once the payment is confirmed (idempotent via access_sent_at).
    if payment.get("status") == "paid" and not payment.get("access_sent_at"):
        email = get_user_email(current_user.user_id)
        if email:
            vpn_key = get_vpn_key(current_user.user_id)
            sub_url = (vpn_key or {}).get("config_text")
            if sub_url:
                user = get_user(current_user.user_id)
                if send_access_email(email, sub_url, user.get("subscription_until")):
                    mark_payment_access_sent(payment_id)

    return payment


@router.post("/promo/redeem")
def redeem_promo(
    payload: PromoRedeemRequest, current_user: CurrentUser = Depends(get_current_user)
) -> dict[str, Any]:
    try:
        result = use_promo(current_user.user_id, payload.code)
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Не удалось активировать подписку: {exc}") from exc
    if result is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Промокод не найден или уже использован")
    return result


@router.post("/trial/activate")
async def activate_trial(current_user: CurrentUser = Depends(get_current_user)) -> dict[str, Any]:
    existing = get_trial(current_user.user_id)
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Trial already used")

    bot = get_bot()
    try:
        member = await bot.get_chat_member(
            chat_id=f"@{settings.trial_channel_username}",
            user_id=current_user.user_id,
        )
        is_member = member.status in {"member", "administrator", "creator"}
    except Exception:
        is_member = False

    if not is_member:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Subscribe to @{settings.trial_channel_username} first",
        )

    try:
        result = activate_trial_days(current_user.user_id, 3)
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    return result


@router.get("/referral")
async def referral(current_user: CurrentUser = Depends(get_current_user)) -> dict[str, Any]:
    bot_username = await get_bot_username()
    stats = get_referral_stats(current_user.user_id)
    return {
        "link": f"https://t.me/{bot_username}?start=ref_{current_user.user_id}",
        "bonus_days": REFERRAL_BONUS_DAYS,
        **stats,
    }


@router.get("/referral/qrcode")
async def referral_qrcode(current_user: CurrentUser = Depends(get_current_user)):
    bot_username = await get_bot_username()
    link = f"https://t.me/{bot_username}?start=ref_{current_user.user_id}"
    return qrcode_png_response(link)


@router.get("/payments/history")
def payments_history(current_user: CurrentUser = Depends(get_current_user)) -> dict[str, Any]:
    return {"payments": list_user_payments(current_user.user_id, limit=20)}


@router.get("/support/faq")
def support_faq() -> dict[str, Any]:
    return {
        "support_username": settings.support_username,
        "faq": FAQ_ITEMS,
        "knowledge_base_url": KNOWLEDGE_BASE_URL,
    }


@router.get("/support/unread")
def support_unread(current_user: CurrentUser = Depends(get_current_user)) -> dict[str, Any]:
    return {"unread": count_unread_support_for_user(current_user.user_id)}


@router.get("/support/chat")
def support_chat(current_user: CurrentUser = Depends(get_current_user)) -> dict[str, Any]:
    messages = list_support_messages(current_user.user_id)
    mark_support_messages_read(current_user.user_id, viewer="user")
    return {"messages": messages}


@router.post("/support/chat")
async def send_support_message(
    payload: SupportMessageRequest, current_user: CurrentUser = Depends(get_current_user)
) -> dict[str, Any]:
    is_first_message = not list_support_messages(current_user.user_id, limit=1)
    message = add_support_message(current_user.user_id, "user", payload.text)

    if is_first_message:
        add_support_message(current_user.user_id, "admin", SUPPORT_AUTO_REPLY)

    bot = get_bot()
    user = get_user(current_user.user_id)
    display = f"@{user['username']}" if user.get("username") else f"id:{current_user.user_id}"
    admin_ids = list_admin_ids() or ([settings.owner_id] if settings.owner_id else [])
    for admin_id in dict.fromkeys(admin_ids):
        try:
            await bot.send_message(
                admin_id,
                f"💬 Новое сообщение в поддержку от {display}:\n\n{payload.text}",
            )
        except Exception:
            continue

    return message
