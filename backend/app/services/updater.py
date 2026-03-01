"""Обновление модулей через systemd oneshot unit `cg-deploy@`."""

import asyncio
from pathlib import Path

from app.config import ModuleSettings, get_settings
from app.database import get_db
from app.models import ModuleUpdate, UpdateResult, UpdateStatus


async def _run(cmd: list[str], cwd: str | None = None) -> tuple[str, str, int]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode(), stderr.decode(), proc.returncode or 0


async def _git_current_commit(repo_path: str) -> str | None:
    stdout, _, code = await _run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=repo_path,
    )
    return stdout.strip() if code == 0 else None


async def _git_current_version(repo_path: str) -> str | None:
    stdout, _, code = await _run(
        ["git", "describe", "--tags", "--abbrev=0"], cwd=repo_path,
    )
    return stdout.strip() if code == 0 else None


async def _ensure_safe_directory(repo_path: str) -> None:
    """Mark repo as safe so git doesn't reject it due to ownership mismatch."""
    await _run(["git", "config", "--global", "--add", "safe.directory", repo_path])


async def _git_fetch(repo_path: str) -> None:
    _, stderr, code = await _run(["git", "fetch", "--all"], cwd=repo_path)
    if code != 0:
        raise RuntimeError(f"git fetch failed in {repo_path}: {stderr.strip()}")


async def _git_available_commits(repo_path: str, branch: str = "main") -> int:
    stdout, _, _ = await _run(
        ["git", "rev-list", "--count", f"HEAD..origin/{branch}"],
        cwd=repo_path,
    )
    try:
        return int(stdout.strip())
    except ValueError:
        return 0


def _deploy_unit(module: ModuleSettings) -> str:
    return f"cg-deploy@{module.service}.service"


async def check_updates(modules: list[ModuleSettings]) -> list[ModuleUpdate]:
    """Проверяет наличие обновлений для всех модулей."""
    results: list[ModuleUpdate] = []

    for m in modules:
        if not Path(m.repo_path).exists():
            results.append(ModuleUpdate(module=m.name))
            continue

        await _ensure_safe_directory(m.repo_path)

        try:
            await _git_fetch(m.repo_path)
        except RuntimeError:
            pass  # fetch failed — compare with whatever origin info we have

        commit = await _git_current_commit(m.repo_path)
        version = await _git_current_version(m.repo_path)
        available = await _git_available_commits(m.repo_path, m.branch)

        results.append(
            ModuleUpdate(
                module=m.name,
                current_version=version,
                current_commit=commit,
                available_commits=available,
                up_to_date=available == 0,
            )
        )

    return results


async def run_update(module: ModuleSettings, ip: str) -> UpdateResult:
    """Запускает обновление через systemd oneshot unit."""
    unit = _deploy_unit(module)

    _, _, is_active_code = await _run(["systemctl", "is-active", "--quiet", unit])
    if is_active_code == 0:
        return UpdateResult(ok=False, message="Update already running")

    await _ensure_safe_directory(module.repo_path)
    version_before = await _git_current_version(module.repo_path)
    db = await get_db()
    cursor = await db.execute(
        "INSERT INTO update_log (module, version_before, status, source_ip) VALUES (?, ?, 'running', ?)",
        (module.name, version_before, ip),
    )
    await db.commit()
    update_row_id = cursor.lastrowid

    _, stderr, code = await _run(["sudo", "systemctl", "start", unit])
    if code != 0:
        await db.execute(
            "UPDATE update_log "
            "SET finished_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), status = 'error', log = ? "
            "WHERE id = ?",
            (stderr.strip(), update_row_id),
        )
        await db.commit()
        return UpdateResult(ok=False, message=f"Failed to start update unit: {stderr.strip()}")

    return UpdateResult(ok=True, job_id=module.service, message=f"Update started via {unit}")


async def _finalize_update_if_needed(module: ModuleSettings, state: str, logs: list[str], error: str | None) -> None:
    if state not in {"done", "error"}:
        return

    db = await get_db()
    cursor = await db.execute(
        "SELECT id, version_before, source_ip "
        "FROM update_log "
        "WHERE module = ? AND status = 'running' "
        "ORDER BY id DESC LIMIT 1",
        (module.name,),
    )
    row = await cursor.fetchone()
    if not row:
        return

    await _ensure_safe_directory(module.repo_path)
    version_after = await _git_current_version(module.repo_path) if state == "done" else None
    log_text = "\n".join(logs)

    update_cursor = await db.execute(
        "UPDATE update_log "
        "SET finished_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), "
        "    version_after = ?, status = ?, log = ? "
        "WHERE id = ?",
        (version_after, state, log_text, row["id"]),
    )
    await db.commit()

    if update_cursor.rowcount <= 0:
        return

    ip = row["source_ip"]
    if state == "done":
        version_before = row["version_before"] or "unknown"
        details = f"{version_before} → {version_after or 'unknown'}"
        action = "update_done"
    else:
        details = error or "update failed"
        action = "update_fail"

    await db.execute(
        "INSERT INTO audit_log (action, target, details, ip) VALUES (?, ?, ?, ?)",
        (action, module.name, details, ip),
    )
    await db.commit()


async def get_update_status(module_name: str) -> UpdateStatus:
    """Возвращает статус обновления по systemd unit и journald."""
    settings = get_settings()
    module = next((m for m in settings.modules if m.name == module_name), None)
    if not module:
        return UpdateStatus(state="idle", error="Module not found")

    unit = _deploy_unit(module)
    stdout, stderr, code = await _run(
        [
            "systemctl",
            "show",
            unit,
            "--property=ActiveState,SubState,Result,ExecMainStatus",
        ]
    )
    if code != 0:
        return UpdateStatus(state="idle", error=stderr.strip() or "Unit not found")

    props: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            props[k] = v

    active = props.get("ActiveState", "unknown")
    sub = props.get("SubState", "")
    result = props.get("Result", "")
    exit_status = props.get("ExecMainStatus", "")

    if active == "active":
        state = "running"
    elif result == "success":
        state = "done"
    elif result in {"failed", "exit-code", "signal", "timeout"}:
        state = "error"
    else:
        state = "idle"

    logs_out, _, _ = await _run(
        [
            "journalctl",
            "-u",
            unit,
            "-n",
            "100",
            "--no-pager",
            "-o",
            "short-iso",
        ]
    )
    logs = [line for line in logs_out.strip().splitlines() if line.strip()]

    error = None
    if state == "error":
        error = f"result={result}, exit_code={exit_status}"

    await _finalize_update_if_needed(module, state, logs, error)

    return UpdateStatus(
        state=state,
        progress=f"{active}/{sub}" if sub else active,
        log=logs,
        error=error,
    )
