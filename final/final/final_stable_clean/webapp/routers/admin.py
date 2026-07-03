from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from config import ROLE_OWNER
from database import (
    add_support_message,
    adjust_subscription_days,
    create_backup_copy,
    create_promo_with_limit,
    delete_promo,
    get_referral_stats,
    get_stats,
    get_trial,
    get_user,
    get_vpn_key,
    list_promo_usages,
    list_promos,
    list_recent_payments,
    list_support_messages,
    list_support_threads,
    list_user_payments,
    list_users,
    mark_payment_failed,
    reset_subscription,
    set_banned,
    set_role,
    update_balance,
    update_promo,
)
from payments import (
    complete_payment,
    deliver_access_message_async,
    notify_payment_rejected,
    notify_subscription_reset,
)
from webapp.bot import get_bot
from webapp.deps import CurrentUser, require_admin
from webapp.schemas import (
    BalanceRequest,
    BanRequest,
    BroadcastRequest,
    PromoRequest,
    RoleRequest,
    SubscriptionExtendRequest,
    SupportMessageRequest,
)

router = APIRouter(tags=["admin"])


def _require_known_user(user_id: int) -> dict[str, Any]:
    user = get_user(user_id)
    if user.get("created_at") is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@router.get("/stats")
def stats(_: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    return get_stats()


@router.get("/users")
def users(
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    rows = list_users(limit=500)
    if q:
        needle = q.strip().lower().lstrip("@")
        rows = [
            row
            for row in rows
            if needle in str(row["user_id"])
            or needle in str(row.get("username") or "").lower()
        ]
    return {"total": len(rows), "users": rows[offset : offset + limit]}


@router.get("/users/{user_id}")
def user_detail(user_id: int, _: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    user = _require_known_user(user_id)
    return {
        "user": user,
        "vpn_key": get_vpn_key(user_id),
        "trial": get_trial(user_id),
        "payments": list_user_payments(user_id, limit=10),
        "referral": get_referral_stats(user_id),
    }


@router.post("/users/{user_id}/ban")
def ban_user(user_id: int, payload: BanRequest, _: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    _require_known_user(user_id)
    set_banned(user_id, payload.banned)
    return get_user(user_id)


@router.post("/users/{user_id}/role")
def set_user_role(user_id: int, payload: RoleRequest, _: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    user = _require_known_user(user_id)
    if payload.role >= ROLE_OWNER:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot grant owner role via the web panel")
    if int(user.get("role") or 1) >= ROLE_OWNER:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot change the owner's role")
    set_role(user_id, payload.role)
    return get_user(user_id)


@router.post("/users/{user_id}/balance")
def grant_balance(user_id: int, payload: BalanceRequest, _: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    _require_known_user(user_id)
    update_balance(user_id, payload.amount)
    return get_user(user_id)


@router.post("/users/{user_id}/subscription/reset")
async def reset_user_subscription(user_id: int, _: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    _require_known_user(user_id)
    try:
        result = reset_subscription(user_id)
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Could not revoke VPN access: {exc}") from exc
    try:
        await notify_subscription_reset(get_bot(), user_id)
    except Exception:
        pass
    return result


@router.post("/users/{user_id}/subscription/extend")
async def extend_user_subscription(
    user_id: int, payload: SubscriptionExtendRequest, _: CurrentUser = Depends(require_admin)
) -> dict[str, Any]:
    _require_known_user(user_id)
    try:
        return adjust_subscription_days(user_id, payload.days)
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Could not update subscription: {exc}") from exc


@router.get("/promos")
def promos(_: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    return {"promos": list_promos(limit=100)}


@router.post("/promos")
def upsert_promo(payload: PromoRequest, _: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    create_promo_with_limit(payload.code, payload.days, payload.usage_limit)
    return {"code": payload.code.strip().upper(), "days": payload.days, "usage_limit": payload.usage_limit}


@router.put("/promos/{code}")
def edit_promo(code: str, payload: PromoRequest, _: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    update_promo(code, payload.days, payload.usage_limit)
    return {"code": code.strip().upper(), "days": payload.days, "usage_limit": payload.usage_limit}


@router.delete("/promos/{code}")
def remove_promo(code: str, _: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    delete_promo(code)
    return {"deleted": code.strip().upper()}


@router.get("/promos/{code}/usages")
def promo_usages(code: str, _: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    return {"usages": list_promo_usages(code, limit=100)}


@router.get("/payments")
def payments_list(
    status_filter: str | None = Query(default=None, alias="status"),
    _: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    rows = list_recent_payments(limit=100)
    if status_filter:
        rows = [row for row in rows if row.get("status") == status_filter]
    return {"payments": rows}


@router.post("/payments/{payment_id}/approve")
async def approve_payment(payment_id: str, current_user: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    try:
        result = complete_payment(payment_id, reviewed_by=current_user.user_id)
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Could not activate subscription: {exc}") from exc
    if not result:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")
    try:
        await deliver_access_message_async(result)
    except Exception:
        pass
    return result


@router.post("/payments/{payment_id}/reject")
async def reject_payment(payment_id: str, current_user: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    updated = mark_payment_failed(payment_id, reviewed_by=current_user.user_id)
    if not updated:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")
    try:
        await notify_payment_rejected(get_bot(), updated)
    except Exception:
        pass
    return updated


@router.post("/broadcast")
async def broadcast(payload: BroadcastRequest, _: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    bot = get_bot()
    delivered = 0
    for row in list_users(limit=500):
        try:
            await bot.send_message(row["user_id"], payload.text)
            delivered += 1
        except Exception:
            continue
    return {"delivered": delivered}


@router.get("/support/threads")
def support_threads(_: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    return {"threads": list_support_threads(limit=100)}


@router.get("/support/threads/{user_id}")
def support_thread_messages(user_id: int, _: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    return {"messages": list_support_messages(user_id)}


@router.post("/support/threads/{user_id}/reply")
async def reply_support_thread(
    user_id: int, payload: SupportMessageRequest, current_user: CurrentUser = Depends(require_admin)
) -> dict[str, Any]:
    message = add_support_message(user_id, "admin", payload.text, admin_id=current_user.user_id)
    try:
        await get_bot().send_message(user_id, f"💬 Ответ поддержки:\n\n{payload.text}")
    except Exception:
        pass
    return message


@router.get("/backup")
def download_backup(_: CurrentUser = Depends(require_admin)) -> Response:
    with tempfile.TemporaryDirectory() as tmp_dir:
        backup_path = create_backup_copy(Path(tmp_dir) / "backup.sqlite3")
        data = backup_path.read_bytes()

    filename = f"velarium_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.sqlite3"
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
