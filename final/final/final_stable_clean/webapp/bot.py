from __future__ import annotations

from aiogram import Bot

from config import settings

_bot: Bot | None = None
_bot_username: str | None = None


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(token=settings.bot_token)
    return _bot


async def get_bot_username() -> str:
    """Resolve the bot's @username, preferring config and caching the getMe() lookup."""
    global _bot_username

    if settings.bot_username:
        return settings.bot_username
    if _bot_username is not None:
        return _bot_username

    try:
        me = await get_bot().get_me()
        _bot_username = me.username or ""
    except Exception:
        _bot_username = ""
    return _bot_username


async def close_bot() -> None:
    global _bot, _bot_username
    if _bot is not None:
        await _bot.session.close()
        _bot = None
    _bot_username = None
