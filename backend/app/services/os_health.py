"""OS health: CPU, RAM, Disk, Uptime (psutil)."""

from __future__ import annotations

import time

import psutil

from app.models import OsHealth


def get_os_health() -> OsHealth:
    """Собирает текущие метрики ОС."""
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
