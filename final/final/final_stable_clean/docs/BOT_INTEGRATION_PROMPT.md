# Промпт: доработать Telegram-бота Velarium под веб-чекаут с автовыдачей

> Скопируй весь текст ниже и отдай ИИ-агенту (Claude Code / другому), который работает с кодом бота.
> Он самодостаточный: описывает контекст, что уже сделано на сайте, и что нужно доделать в боте.

---

## Контекст

Проект — Telegram VPN-сервис Velarium. Репозиторий: `final/final/final_stable_clean`.
- Бот: `main.py` (aiogram polling) + `handlers/` (user/admin/help).
- Веб-приложение: `webapp/` (FastAPI) — лендинг `/`, кабинет `/app`, админ `/admin`, **новый чекаут `/checkout`**.
- Платежи: `payments.py` + `platego.py`. Автоподтверждение — Platego-вебхук в `main.py::platego_webhook` (порт 8181): на `CONFIRMED` вызывает `database.mark_payment_paid()` (провижинит VPN через `remnawave`) и `payments.deliver_access_message_async()` (шлёт ключ пользователю в Telegram-личку).
- Провижининг и всё в БД завязаны на целочисленный `user_id`.

## Что уже сделано на сайте (НЕ трогать, только учитывать)

Добавлен публичный веб-чекаут `/checkout` с **двумя способами входа**:
1. **Telegram** — Login Widget на сайте (прод) или fallback deep-link в бота `?start=buy_<plan>`.
2. **E-mail** — пользователь вводит e-mail → на почту приходит код (SMTP) → вводит код → создаётся **синтетический аккаунт** с **отрицательным** `user_id` (`database.email_to_user_id()` / `get_or_create_email_user()`, колонка `users.email`). Дальше — тот же `create_payment_for_tariff()` и тот же Platego-вебхук.
   - Для e-mail-аккаунтов ключ доставляется **письмом** из веб-процесса (`webapp/routers/user.py::checkout_status` → `webapp/email_auth.send_access_email`), а НЕ в Telegram.

Новые эндпоинты (уже готовы): `POST /api/checkout/email/start`, `POST /api/checkout/email/verify`, `POST /api/auth/telegram-login`.
Пробный период — **3 дня** (`database.activate_trial_days(..., 3)`).

## Что нужно доделать В БОТЕ

### 1. Deep-link роутинг в `/start` (главное)
Сейчас `handlers/user.py::start` (около строки 157) парсит только `ref_<id>`. Добавь обработку payload'ов, которыми сайт передаёт заказ в бота:
- `/start buy_<plan>` где `<plan>` ∈ `month | quarter | year` — сразу инициировать покупку этого тарифа: то же, что делает callback `buy:` (см. `handlers/user.py`, около строки 343) — вызвать `payments.create_payment_for_tariff(user_id, plan)`, показать ссылку/кнопку на оплату Platego и уведомить админов (`notify_admins_about_payment`). Не открывать общее меню, а сразу вести к оплате выбранного тарифа.
- `/start trial` — сразу вести в флоу пробного периода (проверка подписки на канал + `activate_trial_days(user_id, 3)`), как кнопка «Пробный доступ».
- Неизвестный payload или без payload — как сейчас (меню). `ref_` не ломать.

Провалидируй `<plan>` по ключам `config.TARIFFS`; при неверном — просто открой меню.

### 2. Не пытаться слать DM e-mail-аккаунтам (чистота логов)
В `payments.deliver_access_message_async()` (и/или в `main.py::platego_webhook`) перед отправкой ключа в Telegram проверь: если `payment["user_id"] < 0` — это e-mail-аккаунт, DM невозможен. Тогда **пропусти** отправку в Telegram (ключ уже уходит письмом из веб-части) и не помечай `access_sent_at` telegram-доставкой. Опционально: уведомить админов, что оплатил e-mail-покупатель `users.email`.

### 3. Проверки
- `mark_payment_paid()` корректно провижинит и для отрицательных `user_id` (ничего Telegram-специфичного там быть не должно) — убедись.
- Реферальные бонусы и уведомления об истечении не должны падать на отрицательных id (там нет Telegram-чата) — оберни отправку в try/except, если ещё не обёрнуто.

## Критерии готовности
- `t.me/<bot>?start=buy_quarter` → бот сразу предлагает оплату тарифа «3 месяца».
- `t.me/<bot>?start=trial` → бот сразу ведёт в пробный период (3 дня).
- Оплата e-mail-покупателя проходит вебхук без ошибок в логах, Telegram-DM ему не шлётся, VPN провижинится, ключ уходит письмом (веб-часть).
- Существующее поведение бота (меню, `ref_`, обычные покупки) не сломано.

## Тестирование
- Deep-link: отправь боту `/start buy_year` и `/start trial` вручную.
- E-mail-вебхук: синтетический POST на `platego_webhook` с `status=CONFIRMED` и `payload=<payment_id e-mail-заказа>` — проверь, что нет падений и нет попытки DM (в песочнице без Remnawave провижининг остановится на API-вызове — это ок).
