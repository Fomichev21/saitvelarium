from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import REFERRAL_BONUS_DAYS, TARIFFS, settings
from database import init_db
from monitor_bot.heartbeat import beat
from monitor_bot.notifier import report_exception
from webapp import content
from webapp.bot import close_bot
from webapp.routers import admin, auth, checkout, user

STATIC_DIR = Path(__file__).resolve().parent / "static"


async def _heartbeat_loop() -> None:
    while True:
        beat("webapp")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    heartbeat_task = asyncio.create_task(_heartbeat_loop())
    try:
        yield
    finally:
        heartbeat_task.cancel()
        await asyncio.gather(heartbeat_task, return_exceptions=True)
        await close_bot()


app = FastAPI(title="Velarium VPN Cabinet", lifespan=lifespan)


@app.middleware("http")
async def no_cache_static(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static") or request.url.path in ("/", "/app", "/admin", "/checkout", "/profile"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@app.exception_handler(Exception)
async def report_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    report_exception(f"webapp:{request.url.path}", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(auth.router, prefix="/api")
app.include_router(checkout.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(admin.router, prefix="/api/admin")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _public_config() -> dict:
    """Public marketing config for the landing page (no auth)."""
    bot_username = (settings.bot_username or "VelariumVPNbot").lstrip("@")
    support = settings.support_username.lstrip("@")
    channel = settings.trial_channel_username.lstrip("@")
    return {
        "bot_url": f"https://t.me/{bot_username}",
        "bot_username": bot_username,
        "support_url": f"https://t.me/{support}" if support else f"https://t.me/{bot_username}",
        "channel_url": f"https://t.me/{channel}",
        "terms_url": content.TERMS_URL,
        "privacy_url": content.PRIVACY_URL,
        "referral_bonus_days": REFERRAL_BONUS_DAYS,
        "trial_days": 3,
        "tariffs": TARIFFS,
    }


@app.get("/api/public/config")
def public_config() -> JSONResponse:
    return JSONResponse(_public_config())


@app.api_route("/checkout", methods=["GET", "HEAD"])
def checkout_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "checkout.html")


@app.api_route("/profile", methods=["GET", "HEAD"])
def profile_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "profile.html")


@app.api_route("/", methods=["GET", "HEAD"])
def landing() -> FileResponse:
    return FileResponse(STATIC_DIR / "landing.html")


@app.api_route("/app", methods=["GET", "HEAD"])
def cabinet() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.api_route("/admin", methods=["GET", "HEAD"])
def admin_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "admin.html")
