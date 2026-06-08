# Copyright (c) 2026 ООО «НГ-ЭНЕРГОСЕРВИС». Все права защищены.
# Программный комплекс «Честная Генерация»
# Модуль администрирования комплекса
# Автор: Саввиди Александр Анатольевич | ИНН 4725009270
#
# Данное программное обеспечение является конфиденциальным.
# Несанкционированное копирование, распространение или использование
# без письменного разрешения правообладателя запрещено.

"""GET /admin/api/overview — OS health + список служб."""

from fastapi import APIRouter, Depends

from app.auth import require_admin
from app.models import OverviewResponse
from app.services.os_health import get_os_health
from app.services.systemd import get_all_services

router = APIRouter(prefix="/admin/api", tags=["overview"])


@router.get("/overview", response_model=OverviewResponse)
async def overview(_ip: str = Depends(require_admin)) -> OverviewResponse:
    os_health = await get_os_health()
    services = await get_all_services()
    return OverviewResponse(os=os_health, services=services)
