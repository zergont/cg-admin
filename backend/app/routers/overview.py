"""GET /admin/api/overview — OS health + список служб."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_admin
from app.models import OverviewResponse
from app.services.os_health import get_os_health
from app.services.systemd import get_all_services

router = APIRouter(prefix="/admin/api", tags=["overview"])


@router.get("/overview", response_model=OverviewResponse)
async def overview(_ip: str = Depends(require_admin)) -> OverviewResponse:
    os_health = get_os_health()
    services = await get_all_services()
    return OverviewResponse(os=os_health, services=services)
