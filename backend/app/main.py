# Copyright (c) 2026 ООО «НГ-ЭНЕРГОСЕРВИС». Все права защищены.
# Программный комплекс «Честная Генерация»
# Модуль администрирования комплекса
# Автор: Саввиди Александр Анатольевич | ИНН 4725009270
#
# Данное программное обеспечение является конфиденциальным.
# Несанкционированное копирование, распространение или использование
# без письменного разрешения правообладателя запрещено.

"""CG Admin Panel — FastAPI backend."""

from pathlib import Path

# Единый источник версии для backend, frontend и деплоя — файл VERSION в корне
# репозитория. Должно быть определено до импорта app.routers: system.py делает
# `from app.main import __version__`, а это циклический импорт обратно в этот
# модуль — если __version__ ещё не присвоен на тот момент, будет ImportError.
__version__ = (Path(__file__).resolve().parents[2] / "VERSION").read_text(encoding="utf-8").strip()

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.config import get_settings
from app.database import init_db, close_db
from app.routers import overview, services, updates, audit, diagnostics, auth, system


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown."""
    settings = get_settings()
    await init_db(settings.database.sqlite_path)
    yield
    await close_db()


app = FastAPI(
    title="CG Admin",
    version=__version__,
    docs_url="/admin/api/docs",
    openapi_url="/admin/api/openapi.json",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(overview.router)
app.include_router(services.router)
app.include_router(updates.router)
app.include_router(audit.router)
app.include_router(diagnostics.router)
app.include_router(system.router)
