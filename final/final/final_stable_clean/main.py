from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramNetworkError
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiohttp import web

from config import TARIFFS, settings
from database import (
    create_backup_copy,
    get_payment,
    get_stats,
    get_user,
    init_db,
    list_admin_ids,
    mark_payment_paid,
)
from handlers import admin, help, user
from monitor_bot.heartbeat import beat
from monitor_bot.notifier import report_error, report_exception
from payments import deliver_access_message_async, process_expiry_reminders
from remnawave import get_missing_remnawave_settings


def build_bot() -> Bot:
    if settings.telegram_proxy:
        session = AiohttpSession(proxy=settings.telegram_proxy)
        return Bot(token=settings.bot_token, session=session)
    return Bot(token=settings.bot_token)


async def platego_webhook(request: web.Request) -> web.Response:
    try:
        merchant_id = request.headers.get("X-MerchantId", "")
        secret = request.headers.get("X-Secret", "")
        if merchant_id != settings.platego_merchant_id or secret != settings.platego_api_key:
            return web.Response(status=403)

        data = await request.json()
        print(f"Platego webhook: {data}")

        status = data.get("status")
        order_id = data.get("payload") or data.get("orderId") or data.get("id")
        payment = get_payment(order_id) if order_id else None

        status_map = {
            "CONFIRMED": "✅ Оплата подтверждена",
            "CANCELED": "❌ Оплата отменена",
            "PENDING": "⏳ Ожидает оплаты",
            "CHARGEBACKED": "↩️ Возврат средств",
        }
        status_text = status_map.get(status, f"ℹ️ {status}")

        bot = build_bot()
        try:
            admin_ids = list_admin_ids()
            if not admin_ids and settings.owner_id:
                admin_ids = [settings.owner_id]

            if payment:
                tariff_title = TARIFFS.get(payment.get("tariff_code", ""), {}).get("title", "?")
                target_user = get_user(payment["user_id"])
                username = (
                    "@" + target_user["username"]
                    if target_user and target_user.get("username")
                    else str(payment["user_id"])
                )
                remind_markup = None
                if status == "PENDING":
                    remind_markup = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="🔔 Напомнить пользователю",
                                    callback_data=f"remind_payment:{payment['id']}",
                                )
                            ]
                        ]
                    )
                admin_text = (
                    status_text + "\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "👤 " + username + " (" + str(payment["user_id"]) + ")\n"
                    "📦 " + tariff_title + "\n"
                    "💰 " + str(payment["amount"]) + " руб.\n"
                    "🔑 " + (payment.get("invoice_code") or "")
                )
                for admin_id in dict.fromkeys(admin_ids):
                    try:
                        await bot.send_message(admin_id, admin_text, reply_markup=remind_markup)
                    except Exception:
                        pass

            if status == "CANCELED" and payment:
                try:
                    await bot.send_message(
                        payment["user_id"],
                        "❌ Платёж отменён\n\nЕсли хочешь попробовать снова — нажми Купить VPN в главном меню.",
                    )
                except Exception:
                    pass

            if status == "CONFIRMED" and payment and payment.get("status") != "paid":
                result = mark_payment_paid(order_id)
                if result:
                    await deliver_access_message_async(result)
        finally:
            await bot.session.close()

        return web.Response(status=200)
    except Exception as e:
        print(f"Webhook error: {e}")
        report_exception("platego_webhook", e)
        return web.Response(status=200)


async def start_webhook_server() -> None:
    if not (settings.platego_merchant_id and settings.platego_api_key):
        print("Platego is not configured — skipping webhook server startup.")
        return

    app = web.Application()
    app.router.add_post("/payment/webhook", platego_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8181)
    await site.start()
    print("Platego webhook server started on port 8181")


async def main() -> None:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Configure it in environment variables before starting the bot.")

    missing_remnawave = get_missing_remnawave_settings()
    if missing_remnawave:
        raise RuntimeError(
            "Remnawave is not configured. "
            f"Add these variables to .env: {', '.join(missing_remnawave)}"
        )

    init_db()
    await start_webhook_server()

    dispatcher = Dispatcher()
    dispatcher.include_router(admin.router)
    dispatcher.include_router(user.router)
    dispatcher.include_router(help.router)

    while True:
        bot = build_bot()
        reminder_task = asyncio.create_task(reminder_loop(bot))
        backup_task = asyncio.create_task(daily_backup_loop(bot))
        heartbeat_task = asyncio.create_task(heartbeat_loop())
        try:
            try:
                await dispatcher.start_polling(bot)
            except asyncio.CancelledError:
                raise
            except TelegramNetworkError:
                print("Telegram network error. Restarting polling in 10 seconds.")
                await asyncio.sleep(10)
                continue
            except Exception as exc:
                print(f"Polling crashed: {exc!r}. Restarting in 10 seconds.")
                report_exception("bot_polling", exc)
                await asyncio.sleep(10)
                continue
            return
        finally:
            reminder_task.cancel()
            backup_task.cancel()
            heartbeat_task.cancel()
            await asyncio.gather(reminder_task, backup_task, heartbeat_task, return_exceptions=True)
            await bot.session.close()


async def heartbeat_loop() -> None:
    while True:
        beat("main_bot")
        await asyncio.sleep(60)


async def reminder_loop(bot: Bot) -> None:
    while True:
        try:
            await process_expiry_reminders(bot)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            report_exception("reminder_loop", exc)

        await asyncio.sleep(3600)


async def daily_backup_loop(bot: Bot) -> None:
    while True:
        now = datetime.utcnow()
        target_hour = 3
        seconds_until = ((target_hour - now.hour) % 24) * 3600 - now.minute * 60 - now.second
        if seconds_until <= 0:
            seconds_until += 24 * 3600
        await asyncio.sleep(seconds_until)

        try:
            admin_ids = list_admin_ids()
            if not admin_ids and settings.owner_id:
                admin_ids = [settings.owner_id]
            if not admin_ids:
                continue

            stats = get_stats()
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            report = (
                f"📦 Ежедневный бэкап — {date_str}\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👥 Пользователей: {stats['users']}\n"
                f"✅ Активных подписок: {stats['active_subscriptions']}\n"
                f"💳 Оплаченных счетов: {stats['paid_payments']}\n"
                f"💰 Выручка всего: {stats['revenue']}₽\n"
                f"💰 Баланс пользователей: {stats['total_balance']}₽"
            )

            with tempfile.TemporaryDirectory() as tmp_dir:
                backup_path = create_backup_copy(Path(tmp_dir) / f"velarium_backup_{date_str}.sqlite3")
                for admin_id in dict.fromkeys(admin_ids):
                    try:
                        await bot.send_document(admin_id, FSInputFile(backup_path), caption=report)
                    except Exception:
                        pass
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            report_exception("daily_backup_loop", exc)


if __name__ == "__main__":
    asyncio.run(main())
