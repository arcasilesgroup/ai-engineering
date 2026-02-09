"""Git hook installation and readiness checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any


HOOKS = ("pre-commit", "commit-msg", "pre-push")


def _hook_script(stage: str) -> str:
    """Return hook script content for stage."""
    command = f"gate {stage}"
    if stage == "commit-msg":
        command = 'gate commit-msg "$1"'
    return (
        "#!/bin/sh\n"
        "set -eu\n"
        "# ai-engineering managed hook\n"
        "if [ -x .venv/bin/python ]; then\n"
        "  exec env PYTHONPATH=src .venv/bin/python -m ai_engineering.cli "
        f"{command}\n"
        "elif [ -x .venv/Scripts/python.exe ]; then\n"
        "  exec env PYTHONPATH=src .venv/Scripts/python.exe -m ai_engineering.cli "
        f"{command}\n"
        "elif command -v python3 >/dev/null 2>&1; then\n"
        "  exec env PYTHONPATH=src python3 -m ai_engineering.cli "
        f"{command}\n"
        "elif command -v python >/dev/null 2>&1; then\n"
        "  exec env PYTHONPATH=src python -m ai_engineering.cli "
        f"{command}\n"
        "elif command -v ai >/dev/null 2>&1; then\n"
        f"  exec ai {command}\n"
        "else\n"
        f"  echo 'missing runtime for hook stage: {stage}' >&2\n"
        "  exit 1\n"
        "fi\n"
    )


def hooks_dir(repo_root: Path) -> Path:
    """Return `.git/hooks` directory for repository."""
    return repo_root / ".git" / "hooks"


def install_placeholder_hooks(repo_root: Path) -> None:
    """Install managed hooks for MVP bootstrap."""
    directory = hooks_dir(repo_root)
    directory.mkdir(parents=True, exist_ok=True)
    for hook in HOOKS:
        hook_path = directory / hook
        content = _hook_script(hook)
        hook_path.write_text(content, encoding="utf-8")
        hook_path.chmod(0o755)


def detect_hook_readiness(repo_root: Path) -> dict[str, Any]:
    """Detect if required hooks exist, are executable, and are framework-managed."""
    directory = hooks_dir(repo_root)
    if not directory.exists():
        return {
            "installed": False,
            "integrityVerified": False,
            "managedByFramework": False,
            "conflictDetected": False,
            "details": "missing .git/hooks directory",
        }

    checks: list[bool] = []
    managed_checks: list[bool] = []
    conflict_detected = False
    for hook in HOOKS:
        hook_path = directory / hook
        if not (hook_path.exists() and hook_path.stat().st_mode & 0o111 != 0):
            checks.append(False)
            managed_checks.append(False)
            continue
        content = hook_path.read_text(encoding="utf-8")
        managed = "ai-engineering managed hook" in content
        if not managed and "lefthook" in content:
            conflict_detected = True
        checks.append(True)
        managed_checks.append(managed)

    installed = all(checks)
    managed = all(managed_checks)
    return {
        "installed": installed,
        "integrityVerified": installed and managed,
        "managedByFramework": managed,
        "conflictDetected": conflict_detected,
        "details": "ok" if installed and managed else "run 'ai install' to repair managed hooks",
    }
