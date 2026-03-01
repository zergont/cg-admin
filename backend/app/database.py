"""SQLite: audit_log + update_log (aiosqlite)."""

"""SQLite: audit_log + update_log (aiosqlite)."""

from pathlib import Path
from typing import Optional

import aiosqlite

_db: Optional[aiosqlite.Connection] = None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    who         TEXT    NOT NULL DEFAULT 'admin',
    action      TEXT    NOT NULL,
    target      TEXT    NOT NULL,
    details     TEXT,
    ip          TEXT
);

CREATE TABLE IF NOT EXISTS update_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    module          TEXT    NOT NULL,
    version_before  TEXT,
    version_after   TEXT,
    started_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    finished_at     TEXT,
    status          TEXT    NOT NULL DEFAULT 'running',
    log             TEXT,
    source_ip       TEXT
);
"""


async def _ensure_migrations(db: aiosqlite.Connection) -> None:
    """Лёгкие миграции для существующих БД без Alembic."""
    cursor = await db.execute("PRAGMA table_info(update_log)")
    rows = await cursor.fetchall()
    columns = {row[1] for row in rows}

    if "source_ip" not in columns:
        await db.execute("ALTER TABLE update_log ADD COLUMN source_ip TEXT")


async def init_db(sqlite_path: str) -> None:
    """Создаёт БД и таблицы."""
    global _db
    path = Path(sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _db = await aiosqlite.connect(str(path))
    _db.row_factory = aiosqlite.Row
    await _db.executescript(_SCHEMA)
    await _ensure_migrations(_db)
    await _db.commit()


async def get_db() -> aiosqlite.Connection:
    """Возвращает подключение к SQLite."""
    if _db is None:
        raise RuntimeError("Database not initialized")
    return _db


async def close_db() -> None:
    """Закрывает подключение."""
    global _db
    if _db:
        await _db.close()
        _db = None
