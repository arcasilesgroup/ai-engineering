"""Diagnostic orchestrator for ai-engineering installations (spec-071).

Runs phase checks in ``PHASE_ORDER``, then runtime checks, collecting
results into a :class:`DoctorReport`.  Supports fix mode, dry-run,
and single-phase filtering.
"""

from __future__ import annotations

import importlib
import logging
from datetime import UTC, datetime
from pathlib import Path

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.doctor.models import (
    CheckStatus,
    DoctorContext,
    DoctorReport,
    PhaseReport,
)
from ai_engineering.installer.phases import PHASE_ORDER
from ai_engineering.state.io import append_ndjson
from ai_engineering.state.models import AuditEntry
from ai_engineering.state.service import load_install_state

logger = logging.getLogger(__name__)

_RUNTIME_MODULES: tuple[str, ...] = (
    "vcs_auth",
    "feeds",
    "branch_policy",
    "version",
)

_PRE_INSTALL_RUNTIME: tuple[str, ...] = (
    "branch_policy",
    "version",
)


def diagnose(
    target: Path,
    *,
    fix: bool = False,
    dry_run: bool = False,
    phase_filter: str | None = None,
) -> DoctorReport:
    """Run all diagnostic checks on *target* and return a structured report.

    Parameters
    ----------
    target:
        Root directory of the project to diagnose.
    fix:
        When True, attempt remediation on fixable failures.
    dry_run:
        When True (and *fix* is True), show planned fixes without executing.
    phase_filter:
        If set, only run the named phase (e.g. ``"hooks"``).

    Returns
    -------
    DoctorReport
        Phase-grouped diagnostic report.
    """
    # -- 1. Load state --------------------------------------------------------
    state_dir = target / ".ai-engineering" / "state"
    try:
        install_state = load_install_state(state_dir)
        # A default InstallState with vcs_provider=None means no real install
        state_file = state_dir / "install-state.json"
        if not state_file.exists():
            install_state = None
    except Exception:
        install_state = None

    # -- 2. Load manifest config ----------------------------------------------
    try:
        manifest_config = load_manifest_config(target)
    except Exception:
        manifest_config = None

    # -- 3. Create context ----------------------------------------------------
    ctx = DoctorContext(
        target=target,
        install_state=install_state,
        manifest_config=manifest_config,
        fix_mode=fix,
        dry_run=dry_run,
        phase_filter=phase_filter,
    )

    report = DoctorReport()

    # -- 4. Pre-install mode --------------------------------------------------
    if install_state is None:
        report.installed = False
        _run_phase(ctx, "tools", report, fix=fix, dry_run=dry_run)
        _run_runtime_modules(ctx, _PRE_INSTALL_RUNTIME, report)
        _emit_audit_log(target, report, fix=fix)
        return report

    # -- 5. Run phase checks in PHASE_ORDER -----------------------------------
    for phase_name in PHASE_ORDER:
        if phase_filter is not None and phase_name != phase_filter:
            continue
        _run_phase(ctx, phase_name, report, fix=fix, dry_run=dry_run)

    # -- 6. Run runtime checks ------------------------------------------------
    _run_runtime_modules(ctx, _RUNTIME_MODULES, report)

    # -- 7. Emit audit log ----------------------------------------------------
    _emit_audit_log(target, report, fix=fix)

    return report


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _run_phase(
    ctx: DoctorContext,
    phase_name: str,
    report: DoctorReport,
    *,
    fix: bool,
    dry_run: bool,
) -> None:
    """Import and run a single phase module, appending to *report*."""
    phase_mod = importlib.import_module(f"ai_engineering.doctor.phases.{phase_name}")
    results = phase_mod.check(ctx)

    if fix:
        fixable = [
            r for r in results if r.status in (CheckStatus.FAIL, CheckStatus.WARN) and r.fixable
        ]
        if fixable:
            fixed = phase_mod.fix(ctx, fixable, dry_run=dry_run)
            # Replace matching results with their fixed versions
            fixed_names = {r.name for r in fixed}
            results = [
                next((f for f in fixed if f.name == r.name), r) if r.name in fixed_names else r
                for r in results
            ]

    report.phases.append(PhaseReport(name=phase_name, checks=results))


def _run_runtime_modules(
    ctx: DoctorContext,
    modules: tuple[str, ...],
    report: DoctorReport,
) -> None:
    """Import and run runtime check modules, appending to ``report.runtime``."""
    for mod_name in modules:
        mod = importlib.import_module(f"ai_engineering.doctor.runtime.{mod_name}")
        results = mod.check(ctx)
        report.runtime.extend(results)


def _emit_audit_log(target: Path, report: DoctorReport, *, fix: bool) -> None:
    """Write a single audit log entry for this doctor invocation."""
    audit_path = target / ".ai-engineering" / "state" / "audit-log.ndjson"
    entry = AuditEntry(
        event="doctor",
        actor="ai-engineering-cli",
        timestamp=datetime.now(tz=UTC),
        detail={
            "mode": "fix" if fix else "diagnose",
            "phases_checked": len(report.phases),
            "runtime_checked": len(report.runtime),
            "summary": report.summary,
            "fixes_applied": [
                c.name for p in report.phases for c in p.checks if c.status == CheckStatus.FIXED
            ],
        },
    )
    append_ndjson(audit_path, entry)
