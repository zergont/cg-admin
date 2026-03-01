"""OS health: CPU, RAM, Disk, Uptime (psutil)."""

import asyncio
import time

import psutil

from app.models import OsHealth


def _collect_os_health() -> OsHealth:
    """Собирает текущие метрики ОС (блокирующий вызов)."""
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    boot = psutil.boot_time()

    return OsHealth(
        cpu_percent=psutil.cpu_percent(interval=0.5),
        ram_percent=vm.percent,
        ram_used_gb=round(vm.used / (1024**3), 1),
        ram_total_gb=round(vm.total / (1024**3), 1),
        disk_percent=disk.percent,
        disk_used_gb=round(disk.used / (1024**3), 1),
        disk_total_gb=round(disk.total / (1024**3), 1),
        uptime_seconds=int(time.time() - boot),
    )


async def get_os_health() -> OsHealth:
    """Собирает метрики ОС без блокировки event loop."""
    return await asyncio.to_thread(_collect_os_health)
