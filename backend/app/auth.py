"""Авторизация: Bearer token + LAN auto-admin."""

import ipaddress
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

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


async def require_admin(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Dependency: проверяет доступ администратора.

    Возвращает IP клиента (для audit_log).
    """
    settings = get_settings()
    client_ip = _get_client_ip(request)

    # 1. LAN auto-admin
    if _is_lan(client_ip, settings.auth.lan_subnets):
        return client_ip

    # 2. Bearer token
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if token == settings.auth.token:
            return client_ip

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized",
    )
