"""Работа с systemd: статус, логи, рестарт."""

import asyncio

from app.config import get_settings
from app.models import ServiceInfo, ServiceDetail


async def _run(cmd: list[str]) -> tuple[str, str, int]:
    """Запускает команду асинхронно и возвращает (stdout, stderr, code)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode(), stderr.decode(), proc.returncode or 0


async def _systemctl_show(unit: str) -> dict[str, str]:
    """systemctl show для одного юнита."""
    stdout, _, _ = await _run([
        "systemctl", "show", f"{unit}.service",
        "--property=ActiveState,SubState,MainPID,NRestarts,"
        "ActiveEnterTimestamp,MemoryCurrent",
    ])
    result: dict[str, str] = {}
    for line in stdout.strip().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            result[k] = v
    return result


def _indicator(active: str) -> str:
    """Определяет индикатор статуса."""
    if active == "active":
        return "ok"
    if active in ("failed", "inactive"):
        return "crit"
    return "warn"


async def get_all_services() -> list[ServiceInfo]:
    """Возвращает краткий статус всех служб (список из config)."""
    settings = get_settings()
    monitored = settings.services.monitored_units

    tasks = [_systemctl_show(m.unit) for m in monitored]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    services: list[ServiceInfo] = []
    for svc, res in zip(monitored, results):
        if isinstance(res, Exception):
            active_state = "unknown"
            sub_state = "error"
        else:
            active_state = res.get("ActiveState", "unknown")
            sub_state = res.get("SubState", "unknown")

        services.append(
            ServiceInfo(
                name=svc.name,
                unit=svc.unit,
                status=active_state,
                sub_state=sub_state,
                version=None,
                url=svc.url,
                indicator=_indicator(active_state),
            )
        )

    return services


async def get_service_detail(unit: str) -> ServiceDetail:
    """Детальная информация о systemd юните."""
    data = await _systemctl_show(unit)

    memory_raw = data.get("MemoryCurrent", "0")
    try:
        memory_bytes = int(memory_raw)
        memory = f"{round(memory_bytes / (1024**2), 1)} MB"
    except ValueError:
        memory = memory_raw

    return ServiceDetail(
        active_state=data.get("ActiveState", "unknown"),
        sub_state=data.get("SubState", "unknown"),
        uptime=data.get("ActiveEnterTimestamp", ""),
        main_pid=int(data.get("MainPID", 0)),
        restart_count=int(data.get("NRestarts", 0)),
        memory=memory,
    )


async def get_journal_logs(
    unit: str,
    lines: int = 100,
    level: str | None = None,
    search: str | None = None,
) -> list[str]:
    """Получает логи из journald."""
    cmd = [
        "sudo", "journalctl",
        "-u", f"{unit}.service",
        "-n", str(lines),
        "--no-pager",
        "-o", "short-iso",
    ]
    if level:
        priority_map = {
            "emerg": "0", "alert": "1", "crit": "2", "error": "3",
            "warning": "4", "notice": "5", "info": "6", "debug": "7",
        }
        p = priority_map.get(level.lower())
        if p:
            cmd.extend(["-p", p])

    if search:
        cmd.extend(["-g", search])

    stdout, _, _ = await _run(cmd)
    return stdout.strip().splitlines()


async def restart_unit(unit: str) -> tuple[bool, str]:
    """Перезапускает systemd юнит через sudo."""
    _, stderr, code = await _run([
        "sudo", "systemctl", "restart", f"{unit}.service",
    ])
    if code == 0:
        return True, f"Service {unit} restarted successfully"
    return False, f"Failed to restart {unit}: {stderr.strip()}"
