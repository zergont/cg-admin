"""Роутер обновлений модулей."""

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_admin, require_admin_write
from app.config import get_settings
from app.database import get_db
from app.models import ModuleUpdate, UpdateResult, UpdateStatus
from app.services.updater import (
    check_updates,
    run_update,
    get_update_status,
)

router = APIRouter(prefix="/admin/api/updates", tags=["updates"])


@router.get("", response_model=list[ModuleUpdate])
async def list_updates(
    _ip: str = Depends(require_admin),
) -> list[ModuleUpdate]:
    settings = get_settings()
    modules = [m for m in settings.modules if not m.self_]
    return await check_updates(modules)


@router.post("/{module_name}", response_model=UpdateResult)
async def start_update(
    module_name: str,
    ip: str = Depends(require_admin_write),
) -> UpdateResult:
    settings = get_settings()
    module = next((m for m in settings.modules if m.name == module_name), None)
    if not module:
        raise HTTPException(
            status_code=404,
            detail=f"Module '{module_name}' not found",
        )
    if module.self_:
        raise HTTPException(
            status_code=400,
            detail="Admin Panel обновляется через UI-telemetry",
        )

    result = await run_update(module, ip)

    db = await get_db()
    if result.ok:
        await db.execute(
            "INSERT INTO audit_log (action, target, details, ip) VALUES (?, ?, ?, ?)",
            ("update_start", module_name, result.job_id, ip),
        )
    else:
        await db.execute(
            "INSERT INTO audit_log (action, target, details, ip) VALUES (?, ?, ?, ?)",
            ("update_start_fail", module_name, result.message, ip),
        )
    await db.commit()

    return result


@router.get("/{module_name}/status", response_model=UpdateStatus)
async def update_status(
    module_name: str,
    _ip: str = Depends(require_admin),
) -> UpdateStatus:
    return await get_update_status(module_name)
