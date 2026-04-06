"""Minimal runtime preflight for the ai-engineering CLI."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from ai_engineering.doctor.dependency_closure import validate_framework_dependency_closure
from ai_engineering.doctor.environment import classify_failure
from ai_engineering.doctor.remediation import RemediationEngine, RemediationStatus

_MINIMUM_PYTHON = (3, 11)


def preflight_check() -> None:
    """Validate the framework runtime before importing the full CLI surface."""
    try:
        _validate_python_version()
        _validate_interpreter()
        _validate_dependency_closure()
    except Exception as exc:
        category = _classify_failure(exc, context={"argv": tuple(sys.argv)})
        if category == "packaging" and _attempt_packaging_repair(exc):
            return
        _emit_fatal(_render_fatal_message(exc, category))
        raise SystemExit(1) from exc


def _validate_python_version() -> None:
    version = sys.version_info
    if tuple(version[:2]) < _MINIMUM_PYTHON:
        minimum = f"{_MINIMUM_PYTHON[0]}.{_MINIMUM_PYTHON[1]}"
        current = ".".join(str(part) for part in version[:3])
        raise RuntimeError(
            f"ai-engineering requires Python {minimum}+; current interpreter is {current}."
        )


def _validate_interpreter() -> None:
    if not sys.executable:
        raise RuntimeError("ai-engineering could not determine the active Python interpreter.")


def _validate_dependency_closure() -> None:
    violations = validate_framework_dependency_closure()
    if not violations:
        return

    details = ", ".join(
        f"{violation.package} requires {violation.dependency}{violation.required_specifier} "
        f"but found {violation.actual_version}"
        for violation in violations
    )
    raise ImportError(details)


def _classify_failure(exc: Exception, context: dict[str, Any] | None = None) -> str:
    return classify_failure(exc, context=context).value


def _attempt_packaging_repair(exc: Exception) -> bool:
    engine = RemediationEngine(packaging_repair=_repair_framework_dependency_closure)
    remediation = engine.remediate_packaging_drift(str(exc), source="cli-preflight")
    if remediation.status != RemediationStatus.REPAIRED:
        return False
    return not validate_framework_dependency_closure()


def _repair_framework_dependency_closure(detail: str, *, source: str) -> bool:
    del detail, source
    violations = validate_framework_dependency_closure()
    if not violations:
        return False

    project_root = _find_repo_root(Path.cwd())
    if project_root is None or shutil.which("uv") is None:
        return False

    try:
        subprocess.run(
            ["uv", "sync", "--dev"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False

    return True


def _render_fatal_message(exc: Exception, category: str) -> str:
    if category == "runtime":
        return str(exc)
    if category == "packaging":
        return f"ai-engineering preflight failed: {exc}. {_packaging_repair_guidance()}"
    return f"ai-engineering preflight failed: {exc}"


def _packaging_repair_guidance() -> str:
    project_root = _find_repo_root(Path.cwd())
    if project_root is not None:
        return (
            "Automatic repair is only supported from a repo-managed uv environment. "
            "Run `uv sync --dev` from the repository root, then retry."
        )
    return (
        "Automatic repair is not supported in this environment. "
        "Recreate or reinstall the ai-engineering runtime, then retry."
    )


def _find_repo_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "uv.lock").is_file():
            return candidate
    return None


def _emit_fatal(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
