from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import ROLE_ADMIN, is_admin
from security import decode_jwt

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    user_id: int
    role: int


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    payload = decode_jwt(credentials.credentials)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")

    uid = payload.get("uid")
    role = payload.get("role")
    if not isinstance(uid, int) or not isinstance(role, int):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed session token")

    return CurrentUser(user_id=uid, role=role)


def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not is_admin(current_user.role):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return current_user


__all__ = ["CurrentUser", "get_current_user", "require_admin", "ROLE_ADMIN"]
