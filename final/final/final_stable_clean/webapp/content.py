from __future__ import annotations

# Placeholder copy for v1 — replace with real FAQ/knowledge-base text and links
# once available. No FAQ table exists in database.py, so this is served as-is.

FAQ_ITEMS: list[dict[str, str]] = [
    {
        "question": "Как подключиться?",
        "answer": (
            "Скопируй ссылку на подписку из раздела «Главная» и добавь её в "
            "приложении, которое поддерживает подписки по URL (Happ, V2RayNG, Hiddify)."
        ),
    },
    {
        "question": "На каких устройствах работает?",
        "answer": "iOS, Android, Windows и macOS — через одно из поддерживаемых приложений.",
    },
    {
        "question": "Как продлить подписку?",
        "answer": "На главной странице нажми «Продлить» и выбери тариф.",
    },
    {
        "question": "Соединение не работает — что делать?",
        "answer": "Попробуй переподключиться или обновить конфигурацию в приложении. Если не помогло — напиши в поддержку.",
    },
    {
        "question": "Как работает реферальная программа?",
        "answer": "Поделись своей ссылкой — когда друг оплатит первую подписку, тебе начислятся бонусные дни.",
    },
]

KNOWLEDGE_BASE_URL: str | None = None

SUPPORT_AUTO_REPLY = (
    "Здравствуйте! Ваше обращение принято, поддержка рассмотрит его в ближайшее время — пожалуйста, подождите ответа здесь."
)

INFO_DESCRIPTION = (
    "Мы обеспечиваем быстрый и стабильный доступ к интернету без ограничений и слежки."
)
INFO_TAGLINE = "Присоединяйся — твоя свобода в сети начинается здесь."
TERMS_URL = "https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19"
PRIVACY_URL = "https://telegra.ph/Politika-konfidencialnosti-06-21-31"

CONNECT_APPS: list[dict[str, str]] = [
    {
        "name": "Happ",
        "platform": "iOS / Android / Windows",
        "url": "https://happ.su/",
        "icon": "/static/assets/app-happ.png",
    },
    {
        "name": "V2RayNG",
        "platform": "Android",
        "url": "https://play.google.com/store/apps/details?id=com.v2ray.ang",
        "icon": "/static/assets/app-v2rayng.jpg",
    },
    {
        "name": "Hiddify",
        "platform": "iOS / Android / Windows / macOS",
        "url": "https://hiddify.com/",
        "icon": "/static/assets/app-hiddify.png",
    },
]

HIGHLIGHTS: list[dict[str, str]] = [
    {"icon": "bolt", "text": "Высокая скорость без просадок"},
    {"icon": "globe", "text": "Сервера в нескольких странах"},
    {"icon": "lock", "text": "Без логов и слежки"},
    {"icon": "devices", "text": "До нескольких устройств на одной подписке"},
]
