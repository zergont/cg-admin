# Copyright (c) 2026 ООО «НГ-ЭНЕРГОСЕРВИС». Все права защищены.
# Программный комплекс «Честная Генерация»
# Модуль администрирования комплекса
# Автор: Саввиди Александр Анатольевич | ИНН 4725009270
#
# Данное программное обеспечение является конфиденциальным.
# Несанкционированное копирование, распространение или использование
# без письменного разрешения правообладателя запрещено.

"""GET /admin/api/audit — журнал аудита."""

from fastapi import APIRouter, Depends, Query

from app.auth import require_admin
from app.database import get_db
from app.models import AuditEntry

router = APIRouter(prefix="/admin/api", tags=["audit"])


@router.get("/audit", response_model=list[AuditEntry])
async def audit_log(
    action: str | None = Query(None),
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
    limit: int = Query(100, ge=1, le=1000),
    _ip: str = Depends(require_admin),
) -> list[AuditEntry]:
    db = await get_db()

    query = "SELECT * FROM audit_log WHERE 1=1"
    params: list[object] = []

    if action:
        query += " AND action = ?"
        params.append(action)
    if from_date:
        query += " AND timestamp >= ?"
        params.append(from_date)
    if to_date:
        query += " AND timestamp <= ?"
        params.append(to_date + "T23:59:59Z")

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    return [
        AuditEntry(
            id=row["id"],
            timestamp=row["timestamp"],
            who=row["who"],
            action=row["action"],
            target=row["target"],
            details=row["details"],
            ip=row["ip"],
        )
        for row in rows
    ]
