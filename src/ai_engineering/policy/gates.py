"""Governance gate enforcement for hooks and guarded workflows."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ai_engineering.paths import repo_root, state_dir
from ai_engineering.state.io import append_ndjson


PROTECTED_BRANCHES = {"main", "master"}


def current_branch(root: Path) -> str:
    """Return current git branch name."""
    proc = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return "unknown"
    return proc.stdout.strip()


def _tool_path(root: Path, tool: str) -> str | None:
    """Resolve tool path preferring project-local .venv binaries."""
    venv_tool = root / ".venv" / "bin" / tool
    if venv_tool.exists():
        return str(venv_tool)
    return shutil.which(tool)


def _run_tool(root: Path, tool: str, args: list[str]) -> tuple[bool, str]:
    """Run required tool and return success plus message."""
    executable = _tool_path(root, tool)
    if executable is None:
        return False, f"missing required tool: {tool}"

    proc = subprocess.run(
        [executable, *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return True, "ok"
    output = proc.stdout + proc.stderr
    return False, output.strip() or f"{tool} failed"


def _audit(event: str, details: dict[str, object]) -> None:
    """Append governance event to audit log."""
    try:
        root = repo_root()
        append_ndjson(
            state_dir(root) / "audit-log.ndjson",
            {"event": event, "actor": "gate-engine", "details": details},
        )
    except Exception:
        return


def _block_if_protected(root: Path, stage: str) -> tuple[bool, str]:
    branch = current_branch(root)
    if branch in PROTECTED_BRANCHES:
        msg = f"blocked: direct {stage} is not allowed on protected branch '{branch}'"
        _audit("gate_blocked_protected_branch", {"stage": stage, "branch": branch})
        return False, msg
    return True, "ok"


def run_pre_commit() -> tuple[bool, list[str]]:
    """Run pre-commit mandatory checks."""
    root = repo_root()
    ok, msg = _block_if_protected(root, "commit")
    if not ok:
        return False, [msg]

    checks = [
        ("ruff", ["format", "--check", "src", "tests"]),
        ("ruff", ["check", "src", "tests"]),
        ("gitleaks", ["detect", "--no-banner", "--redact"]),
    ]
    failures: list[str] = []
    for tool, args in checks:
        check_ok, output = _run_tool(root, tool, args)
        if not check_ok:
            failures.append(f"{tool}: {output}")

    if failures:
        _audit("gate_failed", {"stage": "pre-commit", "failures": failures})
        return False, failures
    _audit("gate_passed", {"stage": "pre-commit"})
    return True, ["pre-commit checks passed"]


def run_commit_msg(commit_msg_file: Path) -> tuple[bool, list[str]]:
    """Run commit-msg mandatory checks."""
    root = repo_root()
    ok, msg = _block_if_protected(root, "commit")
    if not ok:
        return False, [msg]

    message = commit_msg_file.read_text(encoding="utf-8").strip()
    if not message:
        failure = "commit message cannot be empty"
        _audit("gate_failed", {"stage": "commit-msg", "failures": [failure]})
        return False, [failure]
    _audit("gate_passed", {"stage": "commit-msg"})
    return True, ["commit-msg checks passed"]


def run_pre_push() -> tuple[bool, list[str]]:
    """Run pre-push mandatory checks."""
    root = repo_root()
    ok, msg = _block_if_protected(root, "push")
    if not ok:
        return False, [msg]

    checks = [
        ("semgrep", ["--config", "auto"]),
        ("pip-audit", []),
        ("pytest", []),
        ("ty", ["check", "src"]),
    ]
    failures: list[str] = []
    for tool, args in checks:
        check_ok, output = _run_tool(root, tool, args)
        if not check_ok:
            failures.append(f"{tool}: {output}")

    if failures:
        _audit("gate_failed", {"stage": "pre-push", "failures": failures})
        return False, failures
    _audit("gate_passed", {"stage": "pre-push"})
    return True, ["pre-push checks passed"]
