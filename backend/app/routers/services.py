"""Роутер для управления systemd-сервисами."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_admin
from app.config import get_settings
from app.database import get_db
from app.models import ServiceDetail, LogsResponse
from app.services.systemd import get_service_detail, get_journal_logs, restart_unit

router = APIRouter(prefix="/admin/api/services", tags=["services"])


@router.get("/{unit}/status", response_model=ServiceDetail)
async def service_status(
    unit: str,
    _ip: str = Depends(require_admin),
) -> ServiceDetail:
    return await get_service_detail(unit)


@router.get("/{unit}/logs", response_model=LogsResponse)
async def service_logs(
    unit: str,
    lines: int = Query(100, ge=1, le=5000),
    level: str | None = Query(None),
    search: str | None = Query(None),
    _ip: str = Depends(require_admin),
) -> LogsResponse:
    log_lines = await get_journal_logs(unit, lines=lines, level=level, search=search)
    return LogsResponse(lines=log_lines)


@router.post("/{unit}/restart")
async def service_restart(
    unit: str,
    ip: str = Depends(require_admin),
) -> dict[str, object]:
    settings = get_settings()
    if unit not in settings.services.allowed_units:
        raise HTTPException(
            status_code=403,
            detail=f"Unit '{unit}' is not in allowlist",
        )

    ok, message = await restart_unit(unit)

    db = await get_db()
    await db.execute(
        "INSERT INTO audit_log (action, target, details, ip) VALUES (?, ?, ?, ?)",
        ("restart", unit, message, ip),
    )
    await db.commit()

    return {"ok": ok, "message": message}
