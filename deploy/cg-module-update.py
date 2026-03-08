#!/usr/bin/env python3.12
"""One-shot updater for modules (used by cg-deploy@.service)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import yaml


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print(f"$ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}")


def load_module_by_service(service_name: str) -> dict:
    cfg_path = Path(os.environ.get("CG_ADMIN_CONFIG", "/opt/cg-admin/config.yaml"))
    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    modules = cfg.get("modules", [])
    module = next((m for m in modules if m.get("service") == service_name), None)
    if not module:
        raise RuntimeError(f"Module with service '{service_name}' not found")
    if module.get("self") is True:
        raise RuntimeError("Self update for cg-admin is forbidden")
    return module


def ensure_git_repo(path: Path) -> None:
    if not path.exists() or not (path / ".git").exists():
        raise RuntimeError(f"Repo path is not a git repository: {path}")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: cg-module-update.py <service-name>", file=sys.stderr)
        return 2

    service_name = sys.argv[1]
    module = load_module_by_service(service_name)

    repo_path = Path(module["repo_path"])
    branch = module.get("branch", "main")
    has_backend = bool(module.get("has_backend", True))
    has_frontend = bool(module.get("has_frontend", False))

    ensure_git_repo(repo_path)

    # 1) git update
    run(["git", "fetch", "origin", branch], cwd=repo_path)
    run(["git", "reset", "--hard", f"origin/{branch}"], cwd=repo_path)

    # 2) backend deps
    if has_backend:
        req_backend = repo_path / "backend" / "requirements.txt"
        req_root = repo_path / "requirements.txt"
        req_file = req_backend if req_backend.exists() else req_root

        if req_file.exists():
            # Ищем pip в venv: .venv/ и venv/ (оба варианта), в backend/ и в корне
            pip_candidates = [
                repo_path / "backend" / ".venv" / "bin" / "pip",
                repo_path / "backend" / "venv" / "bin" / "pip",
                repo_path / ".venv" / "bin" / "pip",
                repo_path / "venv" / "bin" / "pip",
            ]
            pip_bin = next((p for p in pip_candidates if p.exists()), None)
            if pip_bin is None:
                raise RuntimeError(
                    f"No venv found for {repo_path}. "
                    f"Checked: {', '.join(str(p.parent.parent) for p in pip_candidates)}"
                )
            run([str(pip_bin), "install", "-r", str(req_file)], cwd=repo_path)

    # 3) frontend build
    if has_frontend:
        frontend_dir = repo_path / "frontend"
        if not frontend_dir.exists():
            frontend_dir = repo_path

        if (frontend_dir / "package.json").exists():
            run(["npm", "install"], cwd=frontend_dir)
            run(["npm", "run", "build"], cwd=frontend_dir)

    # 4) restart target service
    run(["systemctl", "restart", f"{service_name}.service"])

    print("Update complete")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
