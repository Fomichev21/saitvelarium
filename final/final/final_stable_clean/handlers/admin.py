from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ROLE_ADMIN, ROLE_OWNER
from database import (
    add_user,
    delete_promo,
    get_payment,
    get_role,
    get_stats,
    get_user,
    list_promo_usages,
    list_promos,
    list_recent_payments,
    list_users,
    mark_payment_failed,
    set_banned,
    set_role,
    update_promo,
    update_balance,
)
from payments import complete_payment, deliver_access_message_async, notify_payment_rejected

router = Router()


class AdminStates(StatesGroup):
    waiting_for_balance_user_id = State()
    waiting_for_balance_amount = State()
    waiting_for_promo_code = State()
    waiting_for_promo_days = State()
    waiting_for_promo_limit = State()
    waiting_for_promo_edit_code = State()
    waiting_for_promo_edit_days = State()
    waiting_for_promo_edit_limit = State()
    waiting_for_promo_delete_code = State()
    waiting_for_broadcast = State()
    waiting_for_ban_user_id = State()
    waiting_for_grant_admin_user_id = State()
    waiting_for_revoke_admin_user_id = State()


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Пользователи", callback_data="adm_users")],
            [InlineKeyboardButton(text="💰 Выдать баланс", callback_data="adm_balance")],
            [InlineKeyboardButton(text="🎁 Промокоды", callback_data="adm_promo")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats")],
            [InlineKeyboardButton(text="💳 Платежи", callback_data="adm_payments")],
            [InlineKeyboardButton(text="🛡 Администраторы", callback_data="adm_roles")],
            [InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast")],
            [InlineKeyboardButton(text="🚫 Бан", callback_data="adm_ban")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")],
        ]
    )


def promo_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Добавить промокод", callback_data="promo_create")],
            [InlineKeyboardButton(text="🛠 Изменить промокод", callback_data="promo_edit")],
            [InlineKeyboardButton(text="🗑 Удалить промокод", callback_data="promo_delete")],
            [InlineKeyboardButton(text="📋 Список и использования", callback_data="promo_list")],
            [InlineKeyboardButton(text="⬅️ Админ-панель", callback_data="open_admin")],
        ]
    )


def roles_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Выдать админку", callback_data="role_grant_admin")],
            [InlineKeyboardButton(text="➖ Снять админку", callback_data="role_revoke_admin")],
            [InlineKeyboardButton(text="⬅️ Админ-панель", callback_data="open_admin")],
        ]
    )


def promo_list_text() -> str:
    rows = list_promos(limit=20)
    if not rows:
        return "🎁 Промокоды\n━━━━━━━━━━━━━━━━━━━━\n\nПромокодов пока нет."

    lines = ["🎁 Промокоды", "━━━━━━━━━━━━━━━━━━━━", ""]
    for row in rows:
        lines.append(
            f"• {row['code']} — {row['value']} дн., использовано {row.get('used_count', 0)}/{row.get('usage_limit', 1)}"
        )
        usages = list_promo_usages(str(row["code"]), limit=5)
        if usages:
            for usage in usages:
                username = f"@{usage['username']}" if usage.get("username") else f"id:{usage['user_id']}"
                lines.append(f"  - {username} / {usage['used_at']}")
        else:
            lines.append("  - использований пока нет")
    return "\n".join(lines)


def _is_admin(user_id: int) -> bool:
    return get_role(user_id) >= ROLE_ADMIN


async def _guard_admin(callback: CallbackQuery | Message) -> bool:
    add_user(callback.from_user.id, callback.from_user.username)
    if not _is_admin(callback.from_user.id):
        if isinstance(callback, CallbackQuery):
            await callback.answer("Недостаточно прав", show_alert=True)
        else:
            await callback.answer("Недостаточно прав")
        return False
    return True


@router.callback_query(F.data == "open_admin")
async def open_admin(callback: CallbackQuery) -> None:
    if not await _guard_admin(callback):
        return
    await callback.answer()
    await callback.message.edit_text("⚙️ Админ-панель", reply_markup=admin_menu())


@router.callback_query(F.data == "adm_stats")
async def stats(callback: CallbackQuery) -> None:
    if not await _guard_admin(callback):
        return

    summary = get_stats()
    await callback.answer()
    await callback.message.edit_text(
        "📊 Статистика\n\n"
        f"Пользователей: {summary['users']}\n"
        f"Активных подписок: {summary['active_subscriptions']}\n"
        f"Оплаченных счетов: {summary['paid_payments']}\n"
        f"Выручка: {summary['revenue']}₽\n"
        f"Баланс пользователей: {summary['total_balance']}₽",
        reply_markup=admin_menu(),
    )


@router.callback_query(F.data == "adm_users")
async def users(callback: CallbackQuery) -> None:
    if not await _guard_admin(callback):
        return

    rows = list_users(limit=10)
    if not rows:
        text = "👥 Пользователей пока нет."
    else:
        text = "👥 Последние пользователи\n\n" + "\n".join(
            f"{row['user_id']} • @{row['username'] or 'unknown'} • роль {row['role']} • баланс {row['balance']}₽"
            for row in rows
        )

    await callback.answer()
    await callback.message.edit_text(text, reply_markup=admin_menu())


@router.callback_query(F.data == "adm_payments")
async def payments(callback: CallbackQuery) -> None:
    if not await _guard_admin(callback):
        return

    rows = list_recent_payments(limit=10)
    if not rows:
        text = "💳 Платежей пока нет."
    else:
        text = "💳 Последние платежи\n\n" + "\n".join(
            f"{row['id'][:8]} • user {row['user_id']} • {row['amount']}₽ • {row['status']}"
            for row in rows
        )

    await callback.answer()
    await callback.message.edit_text(text, reply_markup=admin_menu())


@router.callback_query(F.data == "adm_roles")
async def roles(callback: CallbackQuery) -> None:
    if not await _guard_admin(callback):
        return

    admins = [row for row in list_users(limit=500) if int(row.get("role") or 1) >= ROLE_ADMIN]
    lines = [
        "🛡 Администраторы",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        "Админ может открывать админ-панель и подтверждать/отклонять заказы.",
        "",
        "Текущие администраторы:",
    ]
    if admins:
        lines.extend(f"• {row['user_id']} • @{row['username'] or 'unknown'} • роль {row['role']}" for row in admins[:20])
    else:
        lines.append("Пока нет администраторов.")

    await callback.answer()
    await callback.message.edit_text("\n".join(lines), reply_markup=roles_menu())


@router.callback_query(F.data == "role_grant_admin")
async def grant_admin_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard_admin(callback):
        return
    await callback.answer()
    await state.set_state(AdminStates.waiting_for_grant_admin_user_id)
    await callback.message.edit_text("Введите Telegram ID пользователя, которому нужно выдать админку.")


@router.message(AdminStates.waiting_for_grant_admin_user_id)
async def grant_admin_finish(message: Message, state: FSMContext) -> None:
    if not await _guard_admin(message):
        return
    try:
        target_user_id = int(message.text or "")
    except ValueError:
        await message.answer("Нужен числовой ID пользователя.")
        return
    user = get_user(target_user_id)
    if user["created_at"] is None:
        await message.answer("Такого пользователя нет в базе. Он должен сначала запустить бота.")
        return
    set_role(target_user_id, ROLE_ADMIN)
    await state.clear()
    await message.answer(f"✅ Пользователю {target_user_id} выдана админка.", reply_markup=roles_menu())


@router.callback_query(F.data == "role_revoke_admin")
async def revoke_admin_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard_admin(callback):
        return
    await callback.answer()
    await state.set_state(AdminStates.waiting_for_revoke_admin_user_id)
    await callback.message.edit_text("Введите Telegram ID пользователя, у которого нужно снять админку.")


@router.message(AdminStates.waiting_for_revoke_admin_user_id)
async def revoke_admin_finish(message: Message, state: FSMContext) -> None:
    if not await _guard_admin(message):
        return
    try:
        target_user_id = int(message.text or "")
    except ValueError:
        await message.answer("Нужен числовой ID пользователя.")
        return
    user = get_user(target_user_id)
    if user["created_at"] is None:
        await message.answer("Такого пользователя нет в базе.")
        return
    if int(user.get("role") or 1) >= ROLE_OWNER:
        await message.answer("Нельзя снять роль владельца через админ-панель.")
        return
    set_role(target_user_id, 1)
    await state.clear()
    await message.answer(f"✅ У пользователя {target_user_id} админка снята.", reply_markup=roles_menu())


@router.callback_query(F.data.startswith("adm_payment_accept:"))
async def approve_payment(callback: CallbackQuery) -> None:
    if not await _guard_admin(callback):
        return

    payment_id = callback.data.split(":", maxsplit=1)[1]
    payment = get_payment(payment_id)
    if not payment:
        await callback.answer("Счет не найден", show_alert=True)
        return
    if payment["status"] == "paid":
        await callback.answer("Этот счет уже подтвержден", show_alert=True)
        return
    if payment["status"] == "failed":
        await callback.answer("Этот счет уже отклонен", show_alert=True)
        return

    try:
        result = complete_payment(payment_id, reviewed_by=callback.from_user.id)
        await deliver_access_message_async(result)
    except Exception as exc:
        await callback.answer("Не удалось подтвердить оплату", show_alert=True)
        await callback.message.answer(f"Ошибка при подтверждении счета {payment.get('invoice_code') or payment_id}: {exc}")
        return

    updated = get_payment(payment_id)
    await callback.answer("Оплата подтверждена")
    await callback.message.edit_text(
        "✅ Счет подтвержден.\n\n"
        f"Счет: {updated.get('invoice_code') or payment_id}\n"
        f"Пользователь: {updated['user_id']}\n"
        f"Сумма: {updated['amount']}₽"
    )


@router.callback_query(F.data.startswith("adm_payment_reject:"))
async def reject_payment(callback: CallbackQuery) -> None:
    if not await _guard_admin(callback):
        return

    payment_id = callback.data.split(":", maxsplit=1)[1]
    payment = get_payment(payment_id)
    if not payment:
        await callback.answer("Счет не найден", show_alert=True)
        return
    if payment["status"] == "paid":
        await callback.answer("Этот счет уже подтвержден", show_alert=True)
        return
    if payment["status"] == "failed":
        await callback.answer("Этот счет уже отклонен", show_alert=True)
        return

    updated = mark_payment_failed(payment_id, reviewed_by=callback.from_user.id)
    await notify_payment_rejected(callback.bot, updated)
    await callback.answer("Счет отклонен")
    await callback.message.edit_text(
        "❌ Счет отклонен.\n\n"
        f"Счет: {updated.get('invoice_code') or payment_id}\n"
        f"Пользователь: {updated['user_id']}\n"
        f"Сумма: {updated['amount']}₽"
    )


@router.callback_query(F.data == "adm_balance")
async def balance_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard_admin(callback):
        return

    await callback.answer()
    await state.set_state(AdminStates.waiting_for_balance_user_id)
    await callback.message.edit_text("Введите ID пользователя, которому нужно выдать баланс.")


@router.message(AdminStates.waiting_for_balance_user_id)
async def balance_user_id(message: Message, state: FSMContext) -> None:
    if not await _guard_admin(message):
        return

    try:
        user_id = int(message.text or "")
    except ValueError:
        await message.answer("Нужен числовой ID.")
        return

    await state.update_data(target_user_id=user_id)
    await state.set_state(AdminStates.waiting_for_balance_amount)
    await message.answer("Теперь введите сумму пополнения.")


@router.message(AdminStates.waiting_for_balance_amount)
async def balance_amount(message: Message, state: FSMContext) -> None:
    if not await _guard_admin(message):
        return

    try:
        amount = int(message.text or "")
    except ValueError:
        await message.answer("Сумма должна быть числом.")
        return

    data = await state.get_data()
    target_user_id = int(data["target_user_id"])
    user = get_user(target_user_id)
    if user["created_at"] is None:
        await message.answer("Пользователь еще не запускал бота.")
        return

    update_balance(target_user_id, amount)
    await state.clear()
    await message.answer(
        f"✅ Пользователю {target_user_id} начислено {amount}₽.",
        reply_markup=admin_menu(),
    )


@router.callback_query(F.data == "adm_promo")
async def promo_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard_admin(callback):
        return

    await callback.answer()
    await state.clear()
    await callback.message.edit_text("🎁 Управление промокодами", reply_markup=promo_menu())


@router.callback_query(F.data == "promo_list")
async def promo_list(callback: CallbackQuery) -> None:
    if not await _guard_admin(callback):
        return
    await callback.answer()
    await callback.message.edit_text(promo_list_text(), reply_markup=promo_menu())


@router.callback_query(F.data == "promo_create")
async def promo_create(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard_admin(callback):
        return
    await callback.answer()
    await state.set_state(AdminStates.waiting_for_promo_code)
    await callback.message.edit_text("🎁 Создание промокода\n\nВведите код промокода.")


@router.callback_query(F.data == "promo_edit")
async def promo_edit(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard_admin(callback):
        return
    await callback.answer()
    await state.set_state(AdminStates.waiting_for_promo_edit_code)
    await callback.message.edit_text("🛠 Изменение промокода\n\nВведите код промокода.")


@router.callback_query(F.data == "promo_delete")
async def promo_delete_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard_admin(callback):
        return
    await callback.answer()
    await state.set_state(AdminStates.waiting_for_promo_delete_code)
    await callback.message.edit_text("🗑 Удаление промокода\n\nВведите код промокода.")


@router.message(AdminStates.waiting_for_promo_code)
async def promo_code(message: Message, state: FSMContext) -> None:
    if not await _guard_admin(message):
        return

    code = (message.text or "").strip().upper()
    if not code:
        await message.answer("Промокод не должен быть пустым.")
        return

    await state.update_data(promo_code=code)
    await state.set_state(AdminStates.waiting_for_promo_days)
    await message.answer("Сколько дней подписки даст промокод?")


@router.message(AdminStates.waiting_for_promo_days)
async def promo_days(message: Message, state: FSMContext) -> None:
    if not await _guard_admin(message):
        return

    try:
        days = int(message.text or "")
    except ValueError:
        await message.answer("Количество дней должно быть числом.")
        return
    if days <= 0:
        await message.answer("Количество дней должно быть больше нуля.")
        return

    await state.update_data(promo_days=days)
    await state.set_state(AdminStates.waiting_for_promo_limit)
    await message.answer("Сколько пользователей смогут использовать промокод?")


@router.message(AdminStates.waiting_for_promo_limit)
async def promo_limit(message: Message, state: FSMContext) -> None:
    if not await _guard_admin(message):
        return

    try:
        limit = int(message.text or "")
    except ValueError:
        await message.answer("Лимит должен быть числом.")
        return
    if limit <= 0:
        await message.answer("Лимит должен быть больше нуля.")
        return

    data = await state.get_data()
    update_promo(data["promo_code"], int(data["promo_days"]), limit)
    await state.clear()
    await message.answer(
        f"✅ Промокод {data['promo_code']} сохранен: {data['promo_days']} дн., лимит {limit}.",
        reply_markup=promo_menu(),
    )


@router.message(AdminStates.waiting_for_promo_edit_code)
async def promo_edit_code(message: Message, state: FSMContext) -> None:
    if not await _guard_admin(message):
        return
    code = (message.text or "").strip().upper()
    if not code:
        await message.answer("Промокод не должен быть пустым.")
        return
    await state.update_data(promo_code=code)
    await state.set_state(AdminStates.waiting_for_promo_edit_days)
    await message.answer("Введите новое количество дней.")


@router.message(AdminStates.waiting_for_promo_edit_days)
async def promo_edit_days(message: Message, state: FSMContext) -> None:
    if not await _guard_admin(message):
        return
    try:
        days = int(message.text or "")
    except ValueError:
        await message.answer("Количество дней должно быть числом.")
        return
    await state.update_data(promo_days=days)
    await state.set_state(AdminStates.waiting_for_promo_edit_limit)
    await message.answer("Введите новый лимит использований.")


@router.message(AdminStates.waiting_for_promo_edit_limit)
async def promo_edit_limit(message: Message, state: FSMContext) -> None:
    if not await _guard_admin(message):
        return
    try:
        limit = int(message.text or "")
    except ValueError:
        await message.answer("Лимит должен быть числом.")
        return
    data = await state.get_data()
    update_promo(data["promo_code"], int(data["promo_days"]), limit)
    await state.clear()
    await message.answer(
        f"✅ Промокод {data['promo_code']} обновлен: {data['promo_days']} дн., лимит {limit}.",
        reply_markup=promo_menu(),
    )


@router.message(AdminStates.waiting_for_promo_delete_code)
async def promo_delete_finish(message: Message, state: FSMContext) -> None:
    if not await _guard_admin(message):
        return
    code = (message.text or "").strip().upper()
    delete_promo(code)
    await state.clear()
    await message.answer(f"✅ Промокод {code} удален.", reply_markup=promo_menu())


@router.callback_query(F.data == "adm_broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard_admin(callback):
        return

    await callback.answer()
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.message.edit_text("Введите текст рассылки.")


@router.message(AdminStates.waiting_for_broadcast)
async def broadcast_send(message: Message, state: FSMContext) -> None:
    if not await _guard_admin(message):
        return

    delivered = 0
    for user in list_users(limit=500):
        try:
            await message.bot.send_message(user["user_id"], message.text)
            delivered += 1
        except Exception:
            continue

    await state.clear()
    await message.answer(
        f"✅ Рассылка завершена. Доставлено: {delivered}.",
        reply_markup=admin_menu(),
    )


@router.callback_query(F.data == "adm_ban")
async def ban_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard_admin(callback):
        return

    await callback.answer()
    await state.set_state(AdminStates.waiting_for_ban_user_id)
    await callback.message.edit_text("Введите ID пользователя для переключения бана.")


@router.message(AdminStates.waiting_for_ban_user_id)
async def ban_toggle(message: Message, state: FSMContext) -> None:
    if not await _guard_admin(message):
        return

    try:
        target_user_id = int(message.text or "")
    except ValueError:
        await message.answer("Нужен числовой ID.")
        return

    user = get_user(target_user_id)
    if user["created_at"] is None:
        await message.answer("Такого пользователя нет в базе.")
        return

    new_state = not bool(user["is_banned"])
    set_banned(target_user_id, new_state)
    await state.clear()
    await message.answer(
        f"✅ Пользователь {target_user_id} теперь {'заблокирован' if new_state else 'разблокирован'}.",
        reply_markup=admin_menu(),
    )
