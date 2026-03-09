"""Сервис диагностики pipeline: 6 параллельных проверок."""

import asyncio
import time
from datetime import datetime, timezone

import asyncpg
import aiohttp
import aiomqtt

from app.config import Settings, DiagnosticsSettings
from app.models import DiagnosticsStep, DiagnosticsReport, StepStatus


# ── Шаг 1: MQTT-брокер доступен ──────────────────────────────


async def check_mqtt_broker(cfg: DiagnosticsSettings) -> DiagnosticsStep:
    t0 = time.monotonic()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(cfg.mqtt_host, cfg.mqtt_port),
            timeout=3.0,
        )
        writer.close()
        await writer.wait_closed()
        elapsed = int((time.monotonic() - t0) * 1000)
        return DiagnosticsStep(
            id="mqtt_broker",
            name="MQTT-брокер",
            status=StepStatus.ok,
            message=f"Порт {cfg.mqtt_host}:{cfg.mqtt_port} доступен",
            details=[f"Время ответа: {elapsed} мс"],
            duration_ms=elapsed,
        )
    except Exception as e:
        elapsed = int((time.monotonic() - t0) * 1000)
        return DiagnosticsStep(
            id="mqtt_broker",
            name="MQTT-брокер",
            status=StepStatus.crit,
            message=f"Нет подключения к {cfg.mqtt_host}:{cfg.mqtt_port}",
            details=[str(e)],
            duration_ms=elapsed,
        )


# ── Шаг 2: Данные идут в MQTT ────────────────────────────────


async def check_mqtt_flow(cfg: DiagnosticsSettings) -> DiagnosticsStep:
    t0 = time.monotonic()
    topic = "cg/v1/decoded/SN/+/pcc/+"
    try:
        async with aiomqtt.Client(cfg.mqtt_host, cfg.mqtt_port) as client:
            await client.subscribe(topic)
            try:
                async with asyncio.timeout(cfg.mqtt_smoke_timeout_sec):
                    async for message in client.messages:
                        elapsed = int((time.monotonic() - t0) * 1000)
                        return DiagnosticsStep(
                            id="mqtt_flow",
                            name="Поток MQTT",
                            status=StepStatus.ok,
                            message="Данные получены",
                            details=[
                                f"Топик: {message.topic}",
                                f"Ожидание: {elapsed} мс",
                            ],
                            duration_ms=elapsed,
                        )
            except asyncio.TimeoutError:
                elapsed = int((time.monotonic() - t0) * 1000)
                return DiagnosticsStep(
                    id="mqtt_flow",
                    name="Поток MQTT",
                    status=StepStatus.warn,
                    message=f"Нет данных за {cfg.mqtt_smoke_timeout_sec:.0f} сек",
                    details=[
                        f"Топик подписки: {topic}",
                        f"Ожидание: {elapsed} мс",
                    ],
                    duration_ms=elapsed,
                )
    except Exception as e:
        elapsed = int((time.monotonic() - t0) * 1000)
        return DiagnosticsStep(
            id="mqtt_flow",
            name="Поток MQTT",
            status=StepStatus.crit,
            message="Ошибка подключения к брокеру",
            details=[str(e)],
            duration_ms=elapsed,
        )


# ── Шаг 3: cg-decoder жив ──────────────────────────


async def check_decoder(cfg: DiagnosticsSettings) -> DiagnosticsStep:
    if not cfg.decoder_health_url:
        return DiagnosticsStep(
            id="decoder",
            name="Декодер (cg-decoder)",
            status=StepStatus.skip,
            message="URL не настроен в конфиге",
        )
    t0 = time.monotonic()
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(cfg.decoder_health_url) as resp:
                elapsed = int((time.monotonic() - t0) * 1000)
                if resp.status != 200:
                    return DiagnosticsStep(
                        id="decoder",
                        name="Декодер (cg-decoder)",
                        status=StepStatus.crit,
                        message=f"HTTP {resp.status}",
                        duration_ms=elapsed,
                    )
                data: dict = await resp.json(content_type=None)
                # telemetry2 /api/stats → {"store": {...}, "mqtt": {...}}
                store: dict = data.get("store", {})
                mqtt_info: dict = data.get("mqtt") or {}

                routers = store.get("routers", 0)
                panels  = store.get("panels",  0)
                online  = store.get("online",  0)
                stale   = store.get("stale",   0)
                offline = store.get("offline", 0)

                mqtt_connected = mqtt_info.get("connected", False)
                msgs_received  = mqtt_info.get("messages_received", 0)
                msgs_decoded   = mqtt_info.get("messages_decoded",  0)
                decode_errors  = mqtt_info.get("decode_errors",     0)

                details = [
                    f"Панели: {online} online / {stale} stale / {offline} offline",
                    f"MQTT: {'подключён' if mqtt_connected else 'отключён'}, "
                    f"получено {msgs_received}, декодировано {msgs_decoded}, "
                    f"ошибок {decode_errors}",
                ]

                if routers == 0:
                    return DiagnosticsStep(
                        id="decoder",
                        name="Декодер (cg-decoder)",
                        status=StepStatus.warn,
                        message="Сервис жив, роутеров 0",
                        details=details,
                        duration_ms=elapsed,
                    )
                return DiagnosticsStep(
                    id="decoder",
                    name="Декодер (cg-decoder)",
                    status=StepStatus.ok,
                    message=f"{routers} роутеров, {panels} панелей ({online} online)",
                    details=details,
                    duration_ms=elapsed,
                )
    except aiohttp.ClientConnectionError as e:
        elapsed = int((time.monotonic() - t0) * 1000)
        return DiagnosticsStep(
            id="decoder",
            name="Декодер (cg-decoder)",
            status=StepStatus.crit,
            message="Сервис недоступен (connection refused)",
            details=[str(e)],
            duration_ms=elapsed,
        )
    except Exception as e:
        elapsed = int((time.monotonic() - t0) * 1000)
        return DiagnosticsStep(
            id="decoder",
            name="Декодер (cg-decoder)",
            status=StepStatus.crit,
            message=f"Ошибка: {e}",
            duration_ms=elapsed,
        )


# ── Шаг 4: DB_MQTT (db-writer) жив и пишет ───────────────────


async def check_db_writer(cfg: DiagnosticsSettings) -> DiagnosticsStep:
    t0 = time.monotonic()
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(cfg.db_writer_health_url) as resp:
                elapsed = int((time.monotonic() - t0) * 1000)
                if resp.status != 200:
                    return DiagnosticsStep(
                        id="db_writer",
                        name="DB-Writer",
                        status=StepStatus.crit,
                        message=f"HTTP {resp.status}",
                        duration_ms=elapsed,
                    )
                data: dict = await resp.json(content_type=None)
                status_val = data.get("status", "")
                last_write_ago = float(data.get("last_write_ago_sec", 0))
                queue_size = data.get("queue_decoded_size", 0)
                workers = data.get("workers_alive", 0)

                details = [
                    f"Очередь: {queue_size} сообщений",
                    f"Воркеры: {workers}",
                    f"Последняя запись: {last_write_ago:.1f} сек назад",
                ]

                if status_val == "dead":
                    step_status = StepStatus.crit
                    message = "Сервис сообщает статус: dead"
                elif status_val == "ok" and last_write_ago < 60:
                    step_status = StepStatus.ok
                    message = f"Запись активна, {last_write_ago:.1f} сек назад"
                elif status_val == "ok":
                    step_status = StepStatus.warn
                    message = f"Процесс жив, но данные не пишутся {last_write_ago:.0f} сек"
                else:
                    step_status = StepStatus.crit
                    message = f"Неизвестный статус: {status_val}"

                return DiagnosticsStep(
                    id="db_writer",
                    name="DB-Writer",
                    status=step_status,
                    message=message,
                    details=details,
                    duration_ms=elapsed,
                )
    except aiohttp.ClientConnectionError as e:
        elapsed = int((time.monotonic() - t0) * 1000)
        return DiagnosticsStep(
            id="db_writer",
            name="DB-Writer",
            status=StepStatus.crit,
            message="Процесс упал (connection refused)",
            details=[str(e)],
            duration_ms=elapsed,
        )
    except Exception as e:
        elapsed = int((time.monotonic() - t0) * 1000)
        return DiagnosticsStep(
            id="db_writer",
            name="DB-Writer",
            status=StepStatus.crit,
            message=f"Ошибка: {e}",
            duration_ms=elapsed,
        )


# ── Шаг 5: Данные свежие в PostgreSQL ────────────────────────


async def check_database(cfg: Settings) -> DiagnosticsStep:
    t0 = time.monotonic()
    db = cfg.database
    try:
        conn = await asyncpg.connect(
            host=db.postgres_host,
            port=db.postgres_port,
            database=db.postgres_dbname,
            user=db.postgres_user,
            password=db.postgres_password,
            timeout=5,
        )
        try:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(DISTINCT router_sn)                         AS objects_count,
                    COUNT(DISTINCT (router_sn, panel_id))             AS panels_count,
                    MAX(updated_at)                                   AS last_update,
                    EXTRACT(EPOCH FROM (now() - MAX(updated_at)))     AS stale_sec
                FROM latest_state
                """
            )
            router_rows = await conn.fetch(
                """
                SELECT router_sn, MAX(updated_at) AS last_update
                FROM latest_state
                GROUP BY router_sn
                ORDER BY last_update DESC
                LIMIT 10
                """
            )
        finally:
            await conn.close()

        elapsed = int((time.monotonic() - t0) * 1000)
        objects_count = row["objects_count"] or 0
        panels_count = row["panels_count"] or 0
        stale_sec = float(row["stale_sec"] or 0)
        stale_threshold = cfg.diagnostics.latest_state_stale_sec

        details = [
            f"{r['router_sn']}: {r['last_update']}"
            for r in router_rows
        ]

        if objects_count == 0:
            return DiagnosticsStep(
                id="database",
                name="PostgreSQL",
                status=StepStatus.crit,
                message="Таблица latest_state пустая",
                details=details,
                duration_ms=elapsed,
            )
        if stale_sec >= stale_threshold:
            return DiagnosticsStep(
                id="database",
                name="PostgreSQL",
                status=StepStatus.warn,
                message=(
                    f"{objects_count} объектов, {panels_count} панелей, "
                    f"данные {int(stale_sec)} сек назад"
                ),
                details=details,
                duration_ms=elapsed,
            )
        return DiagnosticsStep(
            id="database",
            name="PostgreSQL",
            status=StepStatus.ok,
            message=(
                f"{objects_count} объектов, {panels_count} панелей, "
                f"обновлено {int(stale_sec)} сек назад"
            ),
            details=details,
            duration_ms=elapsed,
        )
    except Exception as e:
        elapsed = int((time.monotonic() - t0) * 1000)
        return DiagnosticsStep(
            id="database",
            name="PostgreSQL",
            status=StepStatus.crit,
            message=f"Ошибка подключения к БД",
            details=[str(e)],
            duration_ms=elapsed,
        )


# ── Шаг 6: UI Dashboard доступен ─────────────────────────────


async def check_ui_dashboard(cfg: DiagnosticsSettings) -> DiagnosticsStep:
    if not cfg.dashboard_health_url:
        return DiagnosticsStep(
            id="ui_dashboard",
            name="UI Dashboard",
            status=StepStatus.skip,
            message="URL не настроен в конфиге",
        )
    t0 = time.monotonic()
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(cfg.dashboard_health_url) as resp:
                elapsed = int((time.monotonic() - t0) * 1000)
                if resp.status == 200:
                    return DiagnosticsStep(
                        id="ui_dashboard",
                        name="UI Dashboard",
                        status=StepStatus.ok,
                        message="Сервис доступен",
                        duration_ms=elapsed,
                    )
                return DiagnosticsStep(
                    id="ui_dashboard",
                    name="UI Dashboard",
                    status=StepStatus.crit,
                    message=f"HTTP {resp.status}",
                    duration_ms=elapsed,
                )
    except aiohttp.ClientConnectionError as e:
        elapsed = int((time.monotonic() - t0) * 1000)
        return DiagnosticsStep(
            id="ui_dashboard",
            name="UI Dashboard",
            status=StepStatus.crit,
            message="Сервис недоступен (connection refused)",
            details=[str(e)],
            duration_ms=elapsed,
        )
    except Exception as e:
        elapsed = int((time.monotonic() - t0) * 1000)
        return DiagnosticsStep(
            id="ui_dashboard",
            name="UI Dashboard",
            status=StepStatus.crit,
            message=f"Ошибка: {e}",
            duration_ms=elapsed,
        )


# ── Оркестратор ───────────────────────────────────────────────


def _worst_status(steps: list[DiagnosticsStep]) -> StepStatus:
    order = [StepStatus.crit, StepStatus.warn, StepStatus.ok, StepStatus.skip]
    for s in order:
        if any(step.status == s for step in steps):
            return s
    return StepStatus.ok


async def run_diagnostics(cfg: Settings) -> DiagnosticsReport:
    started = datetime.now(timezone.utc)
    t0 = time.monotonic()

    steps = await asyncio.gather(
        check_mqtt_broker(cfg.diagnostics),
        check_mqtt_flow(cfg.diagnostics),
        check_decoder(cfg.diagnostics),
        check_db_writer(cfg.diagnostics),
        check_database(cfg),
        check_ui_dashboard(cfg.diagnostics),
        return_exceptions=False,
    )

    duration_ms = int((time.monotonic() - t0) * 1000)
    steps_list = list(steps)
    overall = _worst_status(steps_list)

    return DiagnosticsReport(
        started_at=started.isoformat(),
        duration_ms=duration_ms,
        overall=overall,
        steps=steps_list,
    )
