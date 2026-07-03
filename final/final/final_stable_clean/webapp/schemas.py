from __future__ import annotations

from pydantic import BaseModel, Field


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(min_length=1)


class TelegramAuthResponse(BaseModel):
    token: str
    expires_in: int
    role: int


class CheckoutRequest(BaseModel):
    tariff_code: str


class BanRequest(BaseModel):
    banned: bool


class RoleRequest(BaseModel):
    role: int = Field(ge=1, le=3)


class BalanceRequest(BaseModel):
    amount: int


class SubscriptionExtendRequest(BaseModel):
    days: int = Field(ne=0)


class PromoRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    days: int = Field(gt=0)
    usage_limit: int = Field(gt=0)


class BroadcastRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class SupportMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
