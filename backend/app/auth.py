"""Авторизация: Bearer token + LAN auto-admin.

LAN auto-admin разрешает только чтение (GET).
Запись (POST — restart, update) требует Bearer token всегда.
"""

import ipaddress
from typing import Annotated

from fastapi import Header, HTTPException, Request, status

from app.config import get_settings


def _is_lan(ip: str, subnets: list[str]) -> bool:
    """Проверяет, принадлежит ли IP одной из LAN-подсетей."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in ipaddress.ip_network(s, strict=False) for s in subnets)


def _get_client_ip(request: Request) -> str:
    """Извлекает реальный IP клиента (X-Real-IP → fallback)."""
    return (
        request.headers.get("x-real-ip")
        or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "0.0.0.0")
    )


def _check_bearer(authorization: str | None, token: str) -> bool:
    """Проверяет Bearer token."""
    if authorization and authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ").strip() == token
    return False


async def require_admin(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Dependency для GET-эндпоинтов (чтение).

    LAN auto-admin ИЛИ Bearer token.
    Возвращает IP клиента (для audit_log).
    """
    settings = get_settings()
    client_ip = _get_client_ip(request)

    # LAN auto-admin (только чтение)
    if _is_lan(client_ip, settings.auth.lan_subnets):
        return client_ip

    # Bearer token
    if _check_bearer(authorization, settings.auth.token):
        return client_ip

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized",
    )


async def require_admin_write(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Dependency для POST-эндпоинтов (запись: restart, update).

    Только Bearer token — защита от CSRF.
    Клиент всё равно должен быть в LAN/VPN (nginx allowlist).
    """
    settings = get_settings()
    client_ip = _get_client_ip(request)

    if _check_bearer(authorization, settings.auth.token):
        return client_ip

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Bearer token required for write operations",
    )
