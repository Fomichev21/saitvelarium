from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from config import PAYMENT_STATUSES, REFERRAL_BONUS_DAYS, ROLE_ADMIN, TARIFFS, settings
from database import (
    add_user,
    activate_trial_days,
    get_balance,
    get_payment,
    get_referral_stats,
    get_role,
    get_trial,
    get_user,
    get_vpn_key,
    is_banned,
    use_promo,
)
from payments import check_payment, create_payment_for_tariff
from vpn import build_download_name

router = Router()
TRIAL_CHANNEL_URL = "https://t.me/VelariumVPNchannel"


class UserStates(StatesGroup):
    waiting_for_promo = State()


def support_url() -> str:
    return f"https://t.me/{settings.support_username.lstrip('@')}"


def site_url() -> str:
    return settings.public_base_url or support_url()


def ref_link(user_id: int) -> str:
    bot_username = settings.public_base_url  # fallback
    return f"https://t.me/{settings.support_username.lstrip('@')}?start=ref_{user_id}"


def main_menu(user_id: int) -> InlineKeyboardMarkup:
    role = get_role(user_id)
    rows = [
        [InlineKeyboardButton(text="💎 Купить VPN", callback_data="buy_menu")],
        [
            InlineKeyboardButton(text="🔑 Моя подписка", callback_data="profile"),
            InlineKeyboardButton(text="🎁 Промокод", callback_data="promo"),
        ],
        [InlineKeyboardButton(text="🆓 Пробное использование", callback_data="trial")],
        [InlineKeyboardButton(text="👥 Пригласить друзей", callback_data="referral")],
        [InlineKeyboardButton(text="🆘 Поддержка", url=support_url())],
    ]
    if role >= ROLE_ADMIN:
        rows.insert(3, [InlineKeyboardButton(text="⚙️ Админка", callback_data="open_admin")])
    if settings.webapp_public_url:
        rows.insert(
            0,
            [InlineKeyboardButton(text="🌐 Личный кабинет", web_app=WebAppInfo(url=settings.webapp_public_url))],
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_main_markup(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")],
            [InlineKeyboardButton(text="📞 Поддержка", url=support_url())],
        ]
    )


def tariff_menu() -> InlineKeyboardMarkup:
    rows = []
    for code, tariff in TARIFFS.items():
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{tariff['title']} • {tariff['price']}₽",
                    callback_data=f"buy:{code}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_actions(payment_id: str) -> InlineKeyboardMarkup:
    payment = get_payment(payment_id)
    rows = [
        [InlineKeyboardButton(text="💸 Открыть оплату", url=payment["payment_url"])],
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"payment:{payment_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _guard_user(message_or_callback: Message | CallbackQuery, referred_by: int | None = None) -> bool:
    user = message_or_callback.from_user
    add_user(user.id, user.username, referred_by=referred_by)
    if is_banned(user.id):
        text = "Ваш аккаунт заблокирован. Напишите в поддержку, если это ошибка."
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.answer(text, show_alert=True)
        else:
            await message_or_callback.answer(text)
        return False
    return True


def profile_text(user_id: int) -> str:
    user = get_user(user_id)
    vpn_key = get_vpn_key(user_id)
    subscription = user["subscription_until"] or "не активна"
    key_value = vpn_key["vpn_key"] if vpn_key else "еще не выдан"
    balance = get_balance(user_id)
    trial = get_trial(user_id)
    trial_status = "не активен"
    if trial and trial.get("expire_at") and not trial.get("revoked_at"):
        trial_status = f"активен до {trial['expire_at']}"
    return (
        "🔑 Velarium VPN — личный кабинет\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"ID: {user['user_id']}\n"
        f"Username: @{user['username'] or 'unknown'}\n"
        f"Баланс: {balance}₽\n"
        f"Подписка до: {subscription}\n"
        f"Пробный период: {trial_status}\n"
        f"VPN ключ: {key_value}"
    )


def main_menu_text() -> str:
    return (
        "🛡 Velarium VPN — главное меню\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚡ Быстрый и стабильный VPN для телефона, ПК и Telegram.\n"
        "🌍 Доступ к любимым сервисам без лишних настроек.\n"
        "🎁 Промокоды, бонусы, пробный доступ и реферальные дни внутри бота.\n\n"
        "👇 Выбери нужный раздел:"
    )


@router.message(CommandStart())
async def start(message: Message) -> None:
    # Обработка реферальной ссылки: /start ref_12345
    referred_by: int | None = None
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referred_by = int(args[1][4:])
            if referred_by == message.from_user.id:
                referred_by = None
        except ValueError:
            referred_by = None

    if not await _guard_user(message, referred_by=referred_by):
        return

    await message.answer(main_menu_text(), reply_markup=main_menu(message.from_user.id))


@router.message(Command("pay"))
async def pay_cmd(message: Message) -> None:
    if not await _guard_user(message):
        return
    await message.answer(
        "💳 Выберите тариф.\n\nПосле оплаты бот активирует подписку и подготовит VPN конфиг.",
        reply_markup=tariff_menu(),
    )


@router.message(Command("gift"))
async def gift_cmd(message: Message, state: FSMContext) -> None:
    if not await _guard_user(message):
        return
    await state.set_state(UserStates.waiting_for_promo)
    await message.answer(
        "🎁 Отправьте промокод одним сообщением.",
        reply_markup=back_to_main_markup(message.from_user.id),
    )


@router.message(Command("ref"))
async def ref_cmd(message: Message) -> None:
    if not await _guard_user(message):
        return

    user_id = message.from_user.id
    bot_info = await message.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    stats = get_referral_stats(user_id)

    await message.answer(
        "👥 Реферальная программа\n\n"
        f"Приглашай друзей — за каждого, кто сделает первую оплату, ты получишь +{REFERRAL_BONUS_DAYS} дня к подписке.\n\n"
        f"Твоя ссылка:\n{link}\n\n"
        f"Приглашено: {stats['total']}\n"
        f"Оплатили (бонус получен): {stats['rewarded']}",
        reply_markup=back_to_main_markup(user_id),
    )


@router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard_user(callback):
        return
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        main_menu_text(),
        reply_markup=main_menu(callback.from_user.id),
    )


@router.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery) -> None:
    if not await _guard_user(callback):
        return
    await callback.answer()
    await callback.message.edit_text(
        profile_text(callback.from_user.id),
        reply_markup=back_to_main_markup(callback.from_user.id),
    )


@router.callback_query(F.data == "buy_menu")
async def buy_menu(callback: CallbackQuery) -> None:
    if not await _guard_user(callback):
        return
    await callback.answer()
    await callback.message.edit_text(
        "💎 Выбор тарифа\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "После оплаты администратор подтвердит перевод, а бот автоматически создаст доступ и пришлет ссылку на подписку.\n\n"
        "👇 Выбери подходящий срок:",
        reply_markup=tariff_menu(),
    )


@router.callback_query(F.data == "referral")
async def referral(callback: CallbackQuery) -> None:
    if not await _guard_user(callback):
        return

    await callback.answer()
    user_id = callback.from_user.id
    bot_info = await callback.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    stats = get_referral_stats(user_id)
    await callback.message.edit_text(
        "👥 Пригласи друзей\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "За каждого друга, который оплатит первую подписку, ты получишь бонусные дни VPN.\n\n"
        f"Твоя ссылка:\n{link}\n\n"
        f"Приглашено: {stats['total']}\n"
        f"С бонусом: {stats['rewarded']}",
        reply_markup=back_to_main_markup(user_id),
    )


async def is_trial_channel_member(callback: CallbackQuery) -> bool:
    try:
        member = await callback.bot.get_chat_member(
            chat_id=f"@{settings.trial_channel_username}",
            user_id=callback.from_user.id,
        )
    except Exception:
        return False
    return member.status in {"member", "administrator", "creator"}


def trial_join_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться на канал", url=TRIAL_CHANNEL_URL)],
            [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="trial")],
            [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_main")],
        ]
    )


@router.callback_query(F.data == "trial")
async def trial(callback: CallbackQuery) -> None:
    if not await _guard_user(callback):
        return

    if not await is_trial_channel_member(callback):
        await callback.answer("Сначала подпишись на канал", show_alert=True)
        await callback.message.edit_text(
            "🆓 Пробное использование\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Чтобы получить 3 дня пробного доступа, подпишись на наш Telegram-канал и нажми «Проверить подписку».\n\n"
            f"Канал: {TRIAL_CHANNEL_URL}",
            reply_markup=trial_join_markup(),
        )
        return

    existing = get_trial(callback.from_user.id)
    if existing:
        await callback.answer("Пробный доступ уже был использован", show_alert=True)
        await callback.message.edit_text(
            "🆓 Пробное использование\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Статус: уже использован\n"
            f"Доступ был выдан до: {existing.get('expire_at') or 'не указано'}",
            reply_markup=back_to_main_markup(callback.from_user.id),
        )
        return

    try:
        result = activate_trial_days(callback.from_user.id, 3)
    except Exception as exc:
        await callback.answer("Не удалось выдать пробный доступ", show_alert=True)
        await callback.message.edit_text(
            f"❌ Не удалось активировать пробный период: {exc}",
            reply_markup=back_to_main_markup(callback.from_user.id),
        )
        return

    await callback.answer("Пробный доступ активирован")
    await callback.message.edit_text(
        "✅ Пробный доступ активирован\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Действует до: {result['trial_until']}\n"
        "Через 3 дня доступ будет автоматически завершен.",
        reply_markup=back_to_main_markup(callback.from_user.id),
    )


@router.callback_query(F.data.startswith("buy:"))
async def buy(callback: CallbackQuery) -> None:
    if not await _guard_user(callback):
        return

    tariff_code = callback.data.split(":", maxsplit=1)[1]
    if tariff_code not in TARIFFS:
        await callback.answer("Неизвестный тариф", show_alert=True)
        return

    payment = create_payment_for_tariff(callback.from_user.id, tariff_code)
    await callback.answer()
    await callback.message.edit_text(
        "💳 Счет создан.\n\n"
        f"Тариф: {payment['title']}\n"
        f"Сумма: {payment['amount']}₽\n"
        f"Статус: {PAYMENT_STATUSES['pending']}\n\n"
        "Открой страницу оплаты, затем нажми «Проверить оплату».",
        reply_markup=payment_actions(payment["id"]),
    )


@router.callback_query(F.data.startswith("payment:"))
async def payment_status(callback: CallbackQuery) -> None:
    if not await _guard_user(callback):
        return

    payment_id = callback.data.split(":", maxsplit=1)[1]
    payment = check_payment(payment_id)
    if not payment:
        await callback.answer("Платеж не найден", show_alert=True)
        return

    if payment["status"] != "paid":
        await callback.answer("Оплата еще не подтверждена", show_alert=True)
        await callback.message.edit_text(
            "💳 Платеж еще ожидает оплату.\n\n"
            "Если ты уже завершил оплату на странице, попробуй проверить статус еще раз.",
            reply_markup=payment_actions(payment_id),
        )
        return

    vpn_key = get_vpn_key(callback.from_user.id)
    await callback.answer("Оплата подтверждена")
    await callback.message.edit_text(
        "✅ Оплата подтверждена.\n\n"
        f"Подписка активна до: {get_user(callback.from_user.id)['subscription_until']}\n"
        f"VPN ключ: {vpn_key['vpn_key'] if vpn_key else 'создается'}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📥 Скачать конфиг", callback_data="download_config")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")],
            ]
        ),
    )


@router.callback_query(F.data == "download_config")
async def download_config(callback: CallbackQuery) -> None:
    if not await _guard_user(callback):
        return

    vpn_key = get_vpn_key(callback.from_user.id)
    if not vpn_key:
        await callback.answer("Конфиг еще не подготовлен", show_alert=True)
        return

    await callback.answer()
    config_bytes = vpn_key["config_text"].encode("utf-8")
    file = BufferedInputFile(config_bytes, filename=build_download_name(callback.from_user.id))
    await callback.message.answer_document(
        file,
        caption="🔐 Вот твой VPN конфиг.",
    )


@router.callback_query(F.data == "promo")
async def promo(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard_user(callback):
        return

    await callback.answer()
    await state.set_state(UserStates.waiting_for_promo)
    await callback.message.edit_text(
        "🎁 Отправьте промокод одним сообщением.",
        reply_markup=back_to_main_markup(callback.from_user.id),
    )


@router.message(UserStates.waiting_for_promo)
async def promo_handler(message: Message, state: FSMContext) -> None:
    if not await _guard_user(message):
        return

    result = use_promo(message.from_user.id, message.text or "")
    await state.clear()
    if result is None:
        await message.answer(
            "❌ Такой промокод не найден или уже использован.",
            reply_markup=main_menu(message.from_user.id),
        )
        return

    await message.answer(
        "✅ Промокод активирован\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Добавлено дней: {result['days']}\n"
        f"Подписка активна до: {result['subscription_until']}",
        reply_markup=main_menu(message.from_user.id),
    )
