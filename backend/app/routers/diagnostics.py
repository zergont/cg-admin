"""GET /admin/api/diagnostics/run — запуск диагностики pipeline."""

from fastapi import APIRouter, Depends

from app.auth import require_admin
from app.config import get_settings
from app.models import DiagnosticsReport
from app.services.diagnostics import run_diagnostics

router = APIRouter(prefix="/admin/api", tags=["diagnostics"])


@router.get("/diagnostics/run", response_model=DiagnosticsReport)
async def run_diagnostics_endpoint(
    _ip: str = Depends(require_admin),
) -> DiagnosticsReport:
    cfg = get_settings()
    return await run_diagnostics(cfg)
