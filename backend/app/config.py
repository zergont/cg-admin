"""Единый конфиг из config.yaml (Pydantic-модели)."""

import os
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, model_validator


# ── Pydantic-модели ──────────────────────────────────────────


class AppSettings(BaseModel):
    name: str = "CG Admin"
    version: str = "0.3.1"
    debug: bool = False


class AuthSettings(BaseModel):
    token: str
    lan_subnets: list[str] = ["192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"]


class DatabaseSettings(BaseModel):
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_dbname: str = "cg_telemetry"
    postgres_user: str = "cg_ui"
    postgres_password: str = ""
    sqlite_path: str = "/opt/cg-admin/data/admin.db"


class ModuleSettings(BaseModel):
    name: str
    repo: str
    repo_path: str
    service: str
    branch: str = "main"
    has_frontend: bool = False
    has_backend: bool = True
    self_: bool = False

    @model_validator(mode="before")
    @classmethod
    def rename_self_key(cls, data: dict) -> dict:
        if isinstance(data, dict) and "self" in data:
            data["self_"] = data.pop("self")
        return data


class MonitoredUnit(BaseModel):
    name: str
    unit: str
    url: str | None = None


class ServicesSettings(BaseModel):
    allowed_units: list[str] = []
    monitored_units: list[MonitoredUnit] = [
        MonitoredUnit(name="UI Dashboard",   unit="cg-dashboard"),
        MonitoredUnit(name="Modbus-декодер", unit="cg-decoder"),
        MonitoredUnit(name="DB-Writer",      unit="cg-db-writer"),
        MonitoredUnit(name="MQTT Server",    unit="cg-mqtt"),
        MonitoredUnit(name="PostgreSQL",     unit="postgresql"),
        MonitoredUnit(name="Wireguard VPN",  unit="wg-quick@wg0"),
        MonitoredUnit(name="WGDashboard",    unit="wg-dashboard"),
        MonitoredUnit(name="Nginx",          unit="nginx"),
        MonitoredUnit(name="Chrony (NTP)",   unit="chrony"),
        MonitoredUnit(name="Admin Panel",    unit="cg-admin"),
    ]


class DiagnosticsSettings(BaseModel):
    db_writer_health_url: str = "http://127.0.0.1:8765/health"
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_smoke_topic: str = "cg/v1/diagnostics/ping"
    mqtt_smoke_timeout_sec: float = 3.0
    latest_state_stale_sec: int = 300
    decoder_health_url: str = "http://127.0.0.1:8080/api/stats"
    dashboard_health_url: str = "http://127.0.0.1:5555/api/health"


class Settings(BaseModel):
    app: AppSettings = AppSettings()
    auth: AuthSettings
    database: DatabaseSettings = DatabaseSettings()
    services: ServicesSettings = ServicesSettings()
    modules: list[ModuleSettings] = []
    diagnostics: DiagnosticsSettings = DiagnosticsSettings()


# ── Загрузка ─────────────────────────────────────────────────


def _resolve_config_path() -> Path:
    """Определяет путь к config.yaml."""
    env = os.environ.get("CG_ADMIN_CONFIG")
    if env:
        return Path(env)
    candidates = [
        Path("/opt/cg-admin/config.yaml"),
        Path(__file__).resolve().parents[2] / "config.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        "config.yaml не найден. Укажите путь через CG_ADMIN_CONFIG."
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Загружает и кеширует настройки из config.yaml."""
    path = _resolve_config_path()
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Settings(**raw)
