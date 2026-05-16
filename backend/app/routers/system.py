"""Версия и самообновление cg-admin."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import require_admin, require_admin_write
from app.config import get_settings
from app.main import __version__
from app.services.updater import _git_current_commit, _git_current_version, _run

router = APIRouter(prefix="/admin/api/system", tags=["system"])


class VersionResponse(BaseModel):
    version: str
    git_tag: str | None = None
    commit: str | None = None


class UpdateSelfResult(BaseModel):
    ok: bool
    message: str


@router.get("/version", response_model=VersionResponse)
async def get_version(_ip: str = Depends(require_admin)) -> VersionResponse:
    settings = get_settings()
    self_module = next((m for m in settings.modules if m.self_), None)
    repo_path = self_module.repo_path if self_module else None

    return VersionResponse(
        version=__version__,
        git_tag=await _git_current_version(repo_path) if repo_path else None,
        commit=await _git_current_commit(repo_path) if repo_path else None,
    )


@router.post("/update", status_code=202, response_model=UpdateSelfResult)
async def update_self(ip: str = Depends(require_admin_write)) -> UpdateSelfResult:
    settings = get_settings()
    self_module = next((m for m in settings.modules if m.self_), None)
    if not self_module:
        raise HTTPException(
            status_code=404,
            detail="Self module not configured (add 'self: true' to the cg-admin entry in config.yaml)",
        )

    unit = f"cg-deploy@{self_module.service}.service"
    _, _, active_code = await _run(["systemctl", "is-active", "--quiet", unit])
    if active_code == 0:
        return UpdateSelfResult(ok=False, message="Update already running")

    # Fire-and-forget: возвращаем 202 до того, как юнит перезапустит cg-admin
    await asyncio.create_subprocess_exec("sudo", "systemctl", "start", unit)
    return UpdateSelfResult(ok=True, message=f"Update started via {unit}")
