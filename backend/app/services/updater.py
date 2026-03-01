"""Обновление модулей: git pull + build + restart."""

import asyncio
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app.config import ModuleSettings
from app.database import get_db
from app.models import ModuleUpdate, UpdateResult, UpdateStatus
from app.services.systemd import restart_unit


# ── Состояние обновлений (in-memory) ────────────────────────


@dataclass
class _UpdateJob:
    job_id: str
    module: str
    state: str = "running"  # running, done, error
    progress: str = ""
    log: list[str] = field(default_factory=list)
    error: str | None = None


_jobs: dict[str, _UpdateJob] = {}  # module_name → job


# ── Helpers ──────────────────────────────────────────────────


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
    """Пытается получить версию из git describe."""
    stdout, _, code = await _run(
        ["git", "describe", "--tags", "--abbrev=0"], cwd=repo_path,
    )
    return stdout.strip() if code == 0 else None


async def _git_fetch(repo_path: str) -> None:
    await _run(["git", "fetch", "--all"], cwd=repo_path)


async def _git_available_commits(repo_path: str, branch: str = "main") -> int:
    """Количество коммитов, доступных для pull."""
    stdout, _, code = await _run(
        ["git", "rev-list", "--count", f"HEAD..origin/{branch}"],
        cwd=repo_path,
    )
    try:
        return int(stdout.strip())
    except ValueError:
        return 0


# ── Публичный API ────────────────────────────────────────────


async def check_updates(modules: list[ModuleSettings]) -> list[ModuleUpdate]:
    """Проверяет наличие обновлений для всех модулей."""
    results: list[ModuleUpdate] = []

    for m in modules:
        if not Path(m.repo_path).exists():
            results.append(ModuleUpdate(module=m.name))
            continue

        await _git_fetch(m.repo_path)
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
    """Запускает обновление модуля (async background task)."""
    if module.name in _jobs and _jobs[module.name].state == "running":
        return UpdateResult(ok=False, message="Update already running")

    job_id = str(uuid.uuid4())[:8]
    job = _UpdateJob(job_id=job_id, module=module.name)
    _jobs[module.name] = job

    asyncio.create_task(_do_update(module, job, ip))

    return UpdateResult(ok=True, job_id=job_id, message="Update started")


async def _do_update(
    module: ModuleSettings,
    job: _UpdateJob,
    ip: str,
) -> None:
    """Процесс обновления в фоне."""
    db = await get_db()
    version_before = await _git_current_version(module.repo_path)

    await db.execute(
        "INSERT INTO update_log (module, version_before, status) "
        "VALUES (?, ?, 'running')",
        (module.name, version_before),
    )
    await db.commit()

    try:
        # 1. git pull
        branch = module.branch
        job.progress = "git pull"
        job.log.append(f"$ git pull origin {branch}")
        stdout, stderr, code = await _run(
            ["git", "pull", "origin", branch], cwd=module.repo_path,
        )
        job.log.append(stdout.strip())
        if code != 0:
            raise RuntimeError(f"git pull failed: {stderr.strip()}")

        # 2. pip install (если backend)
        if module.has_backend:
            req_path = Path(module.repo_path) / "backend" / "requirements.txt"
            if not req_path.exists():
                req_path = Path(module.repo_path) / "requirements.txt"
            if req_path.exists():
                job.progress = "pip install"
                job.log.append(f"$ pip install -r {req_path}")
                venv_pip = Path(module.repo_path) / "backend" / ".venv" / "bin" / "pip"
                if not venv_pip.exists():
                    venv_pip = Path(module.repo_path) / ".venv" / "bin" / "pip"
                pip_cmd = str(venv_pip) if venv_pip.exists() else "pip"
                stdout, stderr, code = await _run(
                    [pip_cmd, "install", "-r", str(req_path)],
                    cwd=module.repo_path,
                )
                job.log.append(stdout.strip()[-500:] if stdout else "")
                if code != 0:
                    raise RuntimeError(f"pip install failed: {stderr.strip()}")

        # 3. npm build (если frontend)
        if module.has_frontend:
            frontend_dir = Path(module.repo_path) / "frontend"
            if not frontend_dir.exists():
                frontend_dir = Path(module.repo_path)
            pkg = frontend_dir / "package.json"
            if pkg.exists():
                job.progress = "npm install"
                job.log.append("$ npm install")
                stdout, stderr, code = await _run(
                    ["npm", "install"], cwd=str(frontend_dir),
                )
                job.log.append(stdout.strip()[-300:] if stdout else "")

                job.progress = "npm run build"
                job.log.append("$ npm run build")
                stdout, stderr, code = await _run(
                    ["npm", "run", "build"], cwd=str(frontend_dir),
                )
                job.log.append(stdout.strip()[-500:] if stdout else "")
                if code != 0:
                    raise RuntimeError(
                        f"npm run build failed: {stderr.strip()}"
                    )

        # 4. restart service
        job.progress = "restart"
        job.log.append(f"$ systemctl restart {module.service}")
        ok, msg = await restart_unit(module.service)
        job.log.append(msg)
        if not ok:
            raise RuntimeError(msg)

        # Done
        version_after = await _git_current_version(module.repo_path)
        job.state = "done"
        job.progress = "complete"
        job.log.append("✅ Update complete")

        await db.execute(
            "UPDATE update_log "
            "SET finished_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), "
            "    version_after = ?, status = 'done', log = ? "
            "WHERE module = ? AND status = 'running'",
            (version_after, "\n".join(job.log), module.name),
        )
        await db.commit()

        await db.execute(
            "INSERT INTO audit_log (action, target, details, ip) "
            "VALUES (?, ?, ?, ?)",
            (
                "update_done",
                module.name,
                f"{version_before} → {version_after}",
                ip,
            ),
        )
        await db.commit()

    except Exception as e:
        job.state = "error"
        job.error = str(e)
        job.log.append(f"❌ Error: {e}")

        await db.execute(
            "UPDATE update_log "
            "SET finished_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), "
            "    status = 'error', log = ? "
            "WHERE module = ? AND status = 'running'",
            ("\n".join(job.log), module.name),
        )
        await db.commit()

        await db.execute(
            "INSERT INTO audit_log (action, target, details, ip) "
            "VALUES (?, ?, ?, ?)",
            ("update_fail", module.name, str(e), ip),
        )
        await db.commit()


def get_update_status(module_name: str) -> UpdateStatus:
    """Возвращает текущий статус обновления."""
    job = _jobs.get(module_name)
    if not job:
        return UpdateStatus(state="idle")
    return UpdateStatus(
        state=job.state,
        progress=job.progress,
        log=job.log,
        error=job.error,
    )
