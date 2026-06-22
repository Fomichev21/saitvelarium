from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import TARIFFS, settings
from database import (
    create_payment,
    get_payment,
    list_admin_ids,
    list_trials_expiring_soon,
    list_trials_to_revoke,
    list_users_expiring_soon,
    mark_expiry_notice_sent,
    mark_payment_access_sent,
    mark_payment_paid,
    mark_trial_notice_sent,
    revoke_trial,
)


def create_payment_for_tariff(user_id: int, tariff_code: str) -> dict[str, str | int]:
    tariff = TARIFFS[tariff_code]
    payment_id = str(uuid.uuid4())
    pay_url = settings.manual_payment_url

    invoice_seq = create_payment(
        payment_id=payment_id,
        user_id=user_id,
        amount=tariff["price"],
        tariff_code=tariff_code,
        provider=settings.payment_provider,
        payment_url=pay_url,
    )

    payment = get_payment(payment_id)
    return {
        "id": payment_id,
        "url": pay_url,
        "amount": tariff["price"],
        "title": tariff["title"],
        "invoice_code": payment["invoice_code"],
        "invoice_seq": invoice_seq,
    }


def check_payment(payment_id: str) -> dict | None:
    return get_payment(payment_id)


def complete_payment(payment_id: str, reviewed_by: int | None = None) -> dict | None:
    return mark_payment_paid(payment_id, reviewed_by=reviewed_by)


def build_access_instructions_text(payment_result: dict | None) -> str | None:
    if not payment_result:
        return None

    payment = payment_result.get("payment") or {}
    user = payment_result.get("user") or {}
    vpn_key = payment_result.get("vpn_key") or {}
    activation = payment_result.get("activation") or {}

    access_url = str(vpn_key.get("config_text") or activation.get("config_text") or "").strip()
    if not access_url:
        return None

    username = str(user.get("username") or "").strip()
    display_name = f"@{username}" if username else f"id:{payment.get('user_id')}"
    subscription_until = user.get("subscription_until") or activation.get("subscription_until") or "не задано"

    return (
        "Оплата подтверждена.\n\n"
        f"Пользователь: {display_name}\n"
        f"Подписка активна до: {subscription_until}\n\n"
        "Ссылка на подписку:\n"
        f"{access_url}\n\n"
        "Инструкция по подключению:\n"
        "1. Скопируй ссылку на подписку.\n"
        "2. Открой приложение для VPN, которое поддерживает подписки по ссылке.\n"
        "3. Добавь подписку через URL.\n"
        "4. После импорта обнови конфигурацию, если приложение попросит.\n\n"
        "Если подключение не получилось, напиши в поддержку и приложи этот текст."
    )


def build_access_button_markup(payment_result: dict | None) -> InlineKeyboardMarkup | None:
    if not payment_result:
        return None

    vpn_key = payment_result.get("vpn_key") or {}
    activation = payment_result.get("activation") or {}
    access_url = str(vpn_key.get("config_text") or activation.get("config_text") or "").strip()
    if not access_url.startswith(("http://", "https://")):
        return None

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть подписку", url=access_url)]
        ]
    )


async def deliver_access_message_async(payment_result: dict | None) -> bool:
    if not payment_result or not settings.bot_token:
        return False

    payment = payment_result.get("payment") or {}
    payment_id = payment.get("id")
    if not payment_id or payment.get("access_sent_at"):
        return False

    text = build_access_instructions_text(payment_result)
    if not text:
        return False
    markup = build_access_button_markup(payment_result)

    try:
        bot = Bot(token=settings.bot_token)
        try:
            await bot.send_message(payment["user_id"], text, reply_markup=markup)
        finally:
            await bot.session.close()
    except Exception:
        return False

    mark_payment_access_sent(payment_id)
    return True


def deliver_access_message(payment_result: dict | None) -> bool:
    return asyncio.run(deliver_access_message_async(payment_result))


def build_admin_payment_markup(payment_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Принять", callback_data=f"adm_payment_accept:{payment_id}"),
                InlineKeyboardButton(text="Отклонить", callback_data=f"adm_payment_reject:{payment_id}"),
            ]
        ]
    )


async def notify_admins_about_payment(bot: Bot, payment_id: str) -> int:
    payment = get_payment(payment_id)
    if not payment:
        return 0

    admin_ids = list_admin_ids()
    if not admin_ids and settings.owner_id:
        admin_ids = [settings.owner_id]

    if not admin_ids:
        return 0

    text = (
        "Новый счёт ожидает проверки.\n\n"
        f"Счёт: {payment['invoice_code'] or payment['id']}\n"
        f"ID платежа: {payment['id']}\n"
        f"Пользователь: {payment['user_id']}\n"
        f"Тариф: {TARIFFS[payment['tariff_code']]['title']}\n"
        f"Сумма: {payment['amount']} ₽\n"
        f"Ссылка на оплату:\n{payment['payment_url']}"
    )

    delivered = 0
    markup = build_admin_payment_markup(payment_id)
    for admin_id in dict.fromkeys(admin_ids):
        try:
            await bot.send_message(admin_id, text, reply_markup=markup)
            delivered += 1
        except Exception:
            continue

    return delivered


async def notify_payment_rejected(bot: Bot, payment: dict | None) -> bool:
    if not payment:
        return False

    try:
        await bot.send_message(
            payment["user_id"],
            (
                "Оплата не подтверждена администратором.\n\n"
                f"Счёт: {payment.get('invoice_code') or payment['id']}\n"
                "Если ты уже оплатил, свяжись с поддержкой и приложи чек."
            ),
        )
    except Exception:
        return False

    return True


async def notify_subscription_reset(bot: Bot, user_id: int) -> bool:
    try:
        await bot.send_message(
            user_id,
            (
                "Доступ к VPN и подписка были сброшены администратором.\n\n"
                "Если это ошибка, напиши в поддержку."
            ),
        )
    except Exception:
        return False

    return True


async def process_expiry_reminders(bot: Bot) -> int:
    reminded = 0
    for user in list_users_expiring_soon(within_hours=24):
        subscription_until = str(user.get("subscription_until") or "").strip()
        if not subscription_until:
            continue

        try:
            await bot.send_message(
                int(user["user_id"]),
                (
                    "Подписка заканчивается меньше чем через 24 часа.\n\n"
                    f"Дата окончания: {subscription_until}\n"
                    "Продли подписку заранее, чтобы не потерять доступ."
                ),
            )
        except Exception:
            continue

        mark_expiry_notice_sent(int(user["user_id"]), subscription_until)
        reminded += 1

    for user in list_trials_expiring_soon(within_hours=24):
        trial_until = str(user.get("trial_until") or "").strip()
        if not trial_until:
            continue

        try:
            await bot.send_message(
                int(user["user_id"]),
                (
                    "Пробный доступ заканчивается меньше чем через 24 часа.\n\n"
                    f"Дата окончания: {trial_until}\n"
                    "Если хочешь сохранить доступ, оформи обычную подписку заранее."
                ),
            )
        except Exception:
            continue

        mark_trial_notice_sent(int(user["user_id"]), trial_until)
        reminded += 1

    now = datetime.utcnow().replace(microsecond=0)
    for user in list_trials_to_revoke():
        trial_until = str(user.get("trial_until") or "").strip()
        if not trial_until:
            continue
        try:
            if datetime.fromisoformat(trial_until) <= now:
                revoke_trial(int(user["user_id"]))
                await bot.send_message(
                    int(user["user_id"]),
                    "Пробный доступ завершён, доступ удалён.",
                )
        except Exception:
            continue

    return reminded
