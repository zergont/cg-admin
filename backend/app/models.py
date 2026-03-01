"""Pydantic-схемы ответов API."""

from pydantic import BaseModel


# ── OS Health ────────────────────────────────────────────────


class OsHealth(BaseModel):
    cpu_percent: float
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    uptime_seconds: int


# ── Services ─────────────────────────────────────────────────


class ServiceInfo(BaseModel):
    name: str
    unit: str
    status: str
    sub_state: str
    version: str | None = None
    url: str | None = None
    indicator: str  # ok, warn, crit


class ServiceDetail(BaseModel):
    active_state: str
    sub_state: str
    uptime: str
    main_pid: int
    restart_count: int
    memory: str


# ── Overview ─────────────────────────────────────────────────


class OverviewResponse(BaseModel):
    os: OsHealth
    services: list[ServiceInfo]


# ── Logs ─────────────────────────────────────────────────────


class LogsResponse(BaseModel):
    lines: list[str]


# ── Updates ──────────────────────────────────────────────────


class ModuleUpdate(BaseModel):
    module: str
    current_version: str | None = None
    current_commit: str | None = None
    available_commits: int = 0
    up_to_date: bool = True


class UpdateResult(BaseModel):
    ok: bool
    job_id: str | None = None
    message: str = ""


class UpdateStatus(BaseModel):
    state: str  # idle, running, done, error
    progress: str = ""
    log: list[str] = []
    error: str | None = None


# ── Audit ────────────────────────────────────────────────────


class AuditEntry(BaseModel):
    id: int
    timestamp: str
    who: str
    action: str
    target: str
    details: str | None = None
    ip: str | None = None
