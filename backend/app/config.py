"""Единый конфиг из config.yaml (Pydantic-модели)."""

import os
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel


# ── Pydantic-модели ──────────────────────────────────────────


class AppSettings(BaseModel):
    name: str = "CG Admin"
    version: str = "0.1.0"
    debug: bool = False


class AuthSettings(BaseModel):
    token: str
    lan_subnets: list[str] = ["192.168.0.0/16", "10.0.0.0/8"]


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
    has_frontend: bool = False
    has_backend: bool = True
    self_: bool = False

    model_config = {"populate_by_name": True}

    def __init__(self, **data: object) -> None:
        if "self" in data:
            data["self_"] = data.pop("self")  # type: ignore[arg-type]
        super().__init__(**data)


class ServicesSettings(BaseModel):
    allowed_units: list[str] = []


class ExternalLinks(BaseModel):
    wgdashboard: str = ""
    decoder_ui: str = ""
    ui_dashboard: str = ""


class Settings(BaseModel):
    app: AppSettings = AppSettings()
    auth: AuthSettings
    database: DatabaseSettings = DatabaseSettings()
    services: ServicesSettings = ServicesSettings()
    modules: list[ModuleSettings] = []
    external_links: ExternalLinks = ExternalLinks()


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
