"""SQLite: audit_log + update_log (aiosqlite)."""

from __future__ import annotations

from pathlib import Path

import aiosqlite

_db: aiosqlite.Connection | None = None

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
    log             TEXT
);
"""


async def init_db(sqlite_path: str) -> None:
    """Создаёт БД и таблицы."""
    global _db
    path = Path(sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _db = await aiosqlite.connect(str(path))
    _db.row_factory = aiosqlite.Row
    await _db.executescript(_SCHEMA)
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
