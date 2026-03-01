"""CG Admin Panel — FastAPI backend."""

__version__ = "0.2.0"

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.config import get_settings
from app.database import init_db, close_db
from app.routers import overview, services, updates, audit


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

app.include_router(overview.router)
app.include_router(services.router)
app.include_router(updates.router)
app.include_router(audit.router)
