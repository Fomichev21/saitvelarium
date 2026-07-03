from __future__ import annotations

import requests

from config import settings

PLATEGO_API_URL = "https://app.platega.io"


def _headers() -> dict:
    return {
        "X-MerchantId": settings.platego_merchant_id,
        "X-Secret": settings.platego_api_key,
        "Content-Type": "application/json",
    }


def create_platego_payment(amount: int, order_id: str, description: str = "VPN подписка") -> dict | None:
    bot_url = f"https://t.me/{settings.bot_username}" if settings.bot_username else "https://t.me/VelariumVPNbot"
    try:
        resp = requests.post(
            f"{PLATEGO_API_URL}/transaction/process",
            headers=_headers(),
            json={
                "paymentMethod": 2,
                "paymentDetails": {
                    "amount": amount,
                    "currency": "RUB",
                },
                "description": description,
                "return": bot_url,
                "failedUrl": bot_url,
                "payload": order_id,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "url": data.get("redirect") or data.get("url") or data.get("payformUrl"),
            "transaction_id": data.get("transactionId") or data.get("id"),
        }
    except Exception as e:
        print(f"Platego create error: {e}")
        return None


def check_platego_payment(transaction_id: str) -> dict | None:
    try:
        resp = requests.get(
            f"{PLATEGO_API_URL}/transaction/{transaction_id}",
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Platego check error: {e}")
        return None
