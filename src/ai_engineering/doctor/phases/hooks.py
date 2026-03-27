"""Doctor phase: git hook integrity validation.

Checks:
- hooks-integrity: All required hooks pass verify_hooks().
- hooks-scripts: scripts/hooks/ directory exists under .ai-engineering/.
- hooks-executable: All hook scripts have executable permission.
- hooks-lib-complete: Required library files exist in _lib/.
- hooks-registered: All scripts referenced in settings.json exist on disk.
- hooks-python: python3 is available on PATH.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from pathlib import Path

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.hooks.manager import install_hooks, verify_hooks

_REQUIRED_LIB_FILES = frozenset(
    {
        "audit.py",
        "observability.py",
        "instincts.py",
        "injection_patterns.py",
    }
)

_HOOK_PATH_RE = re.compile(r"\.ai-engineering/scripts/hooks/([\w./-]+)")
_HOOK_EXTENSIONS = frozenset({".sh", ".py"})


def _check_hooks_integrity(ctx: DoctorContext) -> CheckResult:
    """Verify that all required hooks are installed and have valid hashes."""
    try:
        status = verify_hooks(ctx.target)
    except FileNotFoundError:
        return CheckResult(
            name="hooks-integrity",
            status=CheckStatus.FAIL,
            message="git hooks directory not found; is this a git repository?",
            fixable=True,
        )

    failed_hooks = [name for name, ok in status.items() if not ok]

    if failed_hooks:
        return CheckResult(
            name="hooks-integrity",
            status=CheckStatus.FAIL,
            message=f"hook verification failed: {', '.join(sorted(failed_hooks))}",
            fixable=True,
        )

    return CheckResult(
        name="hooks-integrity",
        status=CheckStatus.OK,
        message="all hooks verified",
    )


def _check_hooks_scripts(ctx: DoctorContext) -> CheckResult:
    """Check that scripts/hooks/ directory exists under .ai-engineering/."""
    scripts_dir = ctx.target / ".ai-engineering" / "scripts" / "hooks"
    if not scripts_dir.is_dir():
        return CheckResult(
            name="hooks-scripts",
            status=CheckStatus.WARN,
            message="scripts/hooks/ directory missing under .ai-engineering/",
        )

    return CheckResult(
        name="hooks-scripts",
        status=CheckStatus.OK,
        message="scripts/hooks/ directory present",
    )


def _check_hooks_executable(ctx: DoctorContext) -> CheckResult:
    """Verify all hook scripts have executable permission."""
    hooks_dir = ctx.target / ".ai-engineering" / "scripts" / "hooks"
    if not hooks_dir.is_dir():
        return CheckResult(
            name="hooks-executable",
            status=CheckStatus.OK,
            message="scripts/hooks/ directory not present; skipped",
        )

    non_exec: list[str] = []
    for path in sorted(hooks_dir.iterdir()):
        if path.is_dir():
            continue
        if path.suffix not in _HOOK_EXTENSIONS:
            continue
        if not os.access(path, os.X_OK):
            non_exec.append(path.name)

    if non_exec:
        return CheckResult(
            name="hooks-executable",
            status=CheckStatus.FAIL,
            message=f"non-executable hook scripts: {', '.join(non_exec)}",
            fixable=True,
        )

    return CheckResult(
        name="hooks-executable",
        status=CheckStatus.OK,
        message="all hook scripts are executable",
    )


def _check_hooks_lib_complete(ctx: DoctorContext) -> CheckResult:
    """Verify the _lib/ directory contains all required library files."""
    lib_dir = ctx.target / ".ai-engineering" / "scripts" / "hooks" / "_lib"
    if not lib_dir.is_dir():
        return CheckResult(
            name="hooks-lib-complete",
            status=CheckStatus.FAIL,
            message="hooks/_lib/ directory missing; run ai-eng install",
        )

    existing = {f.name for f in lib_dir.iterdir() if f.is_file()}
    missing = sorted(_REQUIRED_LIB_FILES - existing)

    if missing:
        return CheckResult(
            name="hooks-lib-complete",
            status=CheckStatus.FAIL,
            message=f"missing _lib/ files: {', '.join(missing)}",
        )

    return CheckResult(
        name="hooks-lib-complete",
        status=CheckStatus.OK,
        message="all required _lib/ files present",
    )


def _check_hooks_registered(ctx: DoctorContext) -> CheckResult:
    """Verify all hook scripts referenced in settings.json exist on disk."""
    settings_path = ctx.target / ".claude" / "settings.json"
    if not settings_path.is_file():
        return CheckResult(
            name="hooks-registered",
            status=CheckStatus.WARN,
            message="settings.json not found; skipped (non-Claude-Code IDE?)",
        )

    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return CheckResult(
            name="hooks-registered",
            status=CheckStatus.WARN,
            message="settings.json could not be parsed; skipped",
        )

    referenced: set[str] = set()
    hooks_cfg = settings.get("hooks", {})
    for _event, entries in hooks_cfg.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            cmd = entry.get("command", "") if isinstance(entry, dict) else ""
            for match in _HOOK_PATH_RE.finditer(cmd):
                referenced.add(match.group(1))

    missing: list[str] = []
    hooks_dir = ctx.target / ".ai-engineering" / "scripts" / "hooks"
    for script_name in sorted(referenced):
        if not (hooks_dir / script_name).is_file():
            missing.append(script_name)

    if missing:
        return CheckResult(
            name="hooks-registered",
            status=CheckStatus.FAIL,
            message=f"registered scripts missing on disk: {', '.join(missing)}",
        )

    return CheckResult(
        name="hooks-registered",
        status=CheckStatus.OK,
        message=f"all {len(referenced)} registered hook scripts exist",
    )


def _check_hooks_python(ctx: DoctorContext) -> CheckResult:
    """Verify python3 is available on PATH."""
    try:
        result = subprocess.run(
            ["python3", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return CheckResult(
                name="hooks-python",
                status=CheckStatus.OK,
                message=f"python3 available: {version}",
            )
        return CheckResult(
            name="hooks-python",
            status=CheckStatus.WARN,
            message="python3 returned non-zero exit code",
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return CheckResult(
            name="hooks-python",
            status=CheckStatus.WARN,
            message="python3 not found on PATH; hooks require python3",
        )


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Run all hooks phase checks."""
    return [
        _check_hooks_integrity(ctx),
        _check_hooks_scripts(ctx),
        _check_hooks_executable(ctx),
        _check_hooks_lib_complete(ctx),
        _check_hooks_registered(ctx),
        _check_hooks_python(ctx),
    ]


def _fix_hooks_executable(
    ctx: DoctorContext,
    cr: CheckResult,
    *,
    dry_run: bool = False,
) -> CheckResult:
    """Apply chmod u+x,g+x to non-executable hook scripts."""
    hooks_dir = ctx.target / ".ai-engineering" / "scripts" / "hooks"
    targets: list[Path] = []
    for path in sorted(hooks_dir.iterdir()):
        if path.is_dir() or path.suffix not in _HOOK_EXTENSIONS:
            continue
        if not os.access(path, os.X_OK):
            targets.append(path)

    if not targets:
        return CheckResult(
            name=cr.name,
            status=CheckStatus.OK,
            message="all hook scripts already executable",
        )

    if dry_run:
        names = ", ".join(p.name for p in targets)
        return CheckResult(
            name=cr.name,
            status=CheckStatus.FIXED,
            message=f"would chmod +x: {names}",
        )

    for path in targets:
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)

    names = ", ".join(p.name for p in targets)
    return CheckResult(
        name=cr.name,
        status=CheckStatus.FIXED,
        message=f"applied chmod +x: {names}",
    )


def fix(
    ctx: DoctorContext,
    failed: list[CheckResult],
    *,
    dry_run: bool = False,
) -> list[CheckResult]:
    """Attempt to fix failed hooks checks.

    Fixable checks:
    - ``hooks-integrity``: reinstall via ``install_hooks(force=True)``
    - ``hooks-executable``: apply ``chmod u+x,g+x`` to non-executable scripts
    """
    results: list[CheckResult] = []

    for cr in failed:
        if cr.name == "hooks-executable":
            results.append(_fix_hooks_executable(ctx, cr, dry_run=dry_run))
            continue

        if cr.name != "hooks-integrity":
            results.append(cr)
            continue

        if dry_run:
            results.append(
                CheckResult(
                    name=cr.name,
                    status=CheckStatus.FIXED,
                    message="would reinstall hooks with force=True",
                )
            )
            continue

        try:
            result = install_hooks(ctx.target, force=True)
            if result.installed:
                results.append(
                    CheckResult(
                        name=cr.name,
                        status=CheckStatus.FIXED,
                        message=f"reinstalled hooks: {', '.join(result.installed)}",
                    )
                )
            else:
                results.append(cr)
        except FileNotFoundError:
            results.append(cr)

    return results
