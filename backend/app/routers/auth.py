# Copyright (c) 2026 ООО «НГ-ЭНЕРГОСЕРВИС». Все права защищены.
# Программный комплекс «Честная Генерация»
# Модуль администрирования комплекса
# Автор: Саввиди Александр Анатольевич | ИНН 4725009270
#
# Данное программное обеспечение является конфиденциальным.
# Несанкционированное копирование, распространение или использование
# без письменного разрешения правообладателя запрещено.

"""GET /admin/api/auth/token — возвращает Bearer token для LAN auto-admin клиентов."""

from fastapi import APIRouter, Depends

from app.auth import require_admin
from app.config import get_settings

router = APIRouter(prefix="/admin/api", tags=["auth"])


@router.get("/auth/token")
async def get_auth_token(_ip: str = Depends(require_admin)) -> dict[str, str]:
    """Возвращает конфигурационный Bearer token.

    Доступен через LAN auto-admin (без токена) или по Bearer token.
    Позволяет frontend автоматически подтянуть токен для POST-запросов,
    если пользователь находится в доверенной LAN-подсети.
    """
    return {"token": get_settings().auth.token}
