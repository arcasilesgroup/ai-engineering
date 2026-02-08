"""Governance gate enforcement for hooks and guarded workflows."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import NamedTuple

from ai_engineering.paths import repo_root, state_dir
from ai_engineering.state.io import append_ndjson


PROTECTED_BRANCHES = {"main", "master"}


class GateCheck(NamedTuple):
    """Single mandatory check definition."""

    tool: str
    args: list[str]
    remediation: str


PRE_COMMIT_CHECKS = [
    GateCheck(
        "ruff", ["format", "--check", "src", "tests"], "run '.venv/bin/ruff format src tests'"
    ),
    GateCheck("ruff", ["check", "src", "tests"], "run '.venv/bin/ruff check src tests'"),
    GateCheck(
        "gitleaks",
        ["detect", "--no-banner", "--redact"],
        "review staged content and remove secrets before retrying",
    ),
]


PRE_PUSH_CHECKS = [
    GateCheck("semgrep", ["--config", "auto"], "address findings or tune local code before push"),
    GateCheck("pip-audit", [], "upgrade vulnerable dependencies and regenerate lockfiles"),
    GateCheck("pytest", [], "fix failing tests and rerun '.venv/bin/python -m pytest'"),
    GateCheck("ty", ["check", "src"], "fix type diagnostics and rerun '.venv/bin/ty check src'"),
]


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


def _github_repo_slug_from_origin(root: Path) -> tuple[str, str] | None:
    """Parse owner/repo from origin URL if it is a GitHub remote."""
    proc = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    url = proc.stdout.strip()
    if "github.com" not in url:
        return None

    normalized = url
    if normalized.startswith("git@github.com:"):
        normalized = normalized.replace("git@github.com:", "")
    elif normalized.startswith("https://github.com/"):
        normalized = normalized.replace("https://github.com/", "")
    else:
        return None

    normalized = normalized.removesuffix(".git")
    parts = normalized.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return None
    return parts[0], parts[1]


def discover_protected_branches(root: Path) -> set[str]:
    """Discover protected branches from GitHub, with safe fallback."""
    branches = set(PROTECTED_BRANCHES)
    slug = _github_repo_slug_from_origin(root)
    if slug is None:
        return branches

    owner, repo = slug
    proc = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{owner}/{repo}/branches?protected=true",
            "--jq",
            ".[].name",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return branches
    discovered = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if discovered:
        branches.update(discovered)
    return branches


def gate_requirements(root: Path) -> dict[str, object]:
    """Return machine-readable gate requirements for current repository."""
    return {
        "protectedBranches": sorted(discover_protected_branches(root)),
        "stages": {
            "pre-commit": [
                {"tool": check.tool, "args": check.args, "remediation": check.remediation}
                for check in PRE_COMMIT_CHECKS
            ],
            "pre-push": [
                {"tool": check.tool, "args": check.args, "remediation": check.remediation}
                for check in PRE_PUSH_CHECKS
            ],
            "commit-msg": [
                {
                    "tool": "commit-message",
                    "args": [],
                    "remediation": "provide a non-empty commit message",
                }
            ],
        },
    }


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
    protected_branches = discover_protected_branches(root)
    branch = current_branch(root)
    if branch in protected_branches:
        msg = f"blocked: direct {stage} is not allowed on protected branch '{branch}'"
        _audit(
            "gate_blocked_protected_branch",
            {"stage": stage, "branch": branch, "protectedBranches": sorted(protected_branches)},
        )
        return False, msg
    return True, "ok"


def _run_gate_checks(root: Path, stage: str, checks: list[GateCheck]) -> tuple[bool, list[str]]:
    """Run mandatory gate checks and include remediation in failures."""
    failures: list[str] = []
    for check in checks:
        check_ok, output = _run_tool(root, check.tool, check.args)
        if check_ok:
            continue
        failures.append(f"{check.tool}: {output}\nremediation: {check.remediation}")

    if failures:
        _audit("gate_failed", {"stage": stage, "failures": failures})
        return False, failures
    _audit("gate_passed", {"stage": stage})
    return True, [f"{stage} checks passed"]


def run_pre_commit() -> tuple[bool, list[str]]:
    """Run pre-commit mandatory checks."""
    root = repo_root()
    ok, msg = _block_if_protected(root, "commit")
    if not ok:
        return False, [msg]

    return _run_gate_checks(root, "pre-commit", PRE_COMMIT_CHECKS)


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

    return _run_gate_checks(root, "pre-push", PRE_PUSH_CHECKS)
