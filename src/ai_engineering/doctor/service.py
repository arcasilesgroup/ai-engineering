"""Diagnostic orchestrator for ai-engineering installations (spec-071).

Runs phase checks in ``PHASE_ORDER``, then runtime checks, collecting
results into a :class:`DoctorReport`.  Supports fix mode, dry-run,
and single-phase filtering.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.doctor.models import (
    CheckResult,
    CheckStatus,
    DoctorContext,
    DoctorReport,
    PhaseReport,
)
from ai_engineering.doctor.phases import detect, governance, hooks, ide_config, state, tools
from ai_engineering.doctor.runtime import (
    branch_policy,
    feeds,
    opa_health,
    secrets_gate,
    vcs_auth,
    version,
)
from ai_engineering.doctor.runtime.feeds import validate_feeds_for_install
from ai_engineering.installer.phases import (
    PHASE_DETECT,
    PHASE_GOVERNANCE,
    PHASE_HOOKS,
    PHASE_IDE_CONFIG,
    PHASE_ORDER,
    PHASE_STATE,
    PHASE_TOOLS,
)
from ai_engineering.reconciler import (
    ReconcileAction,
    ReconcileApplyResult,
    ReconcileInspection,
    ReconcilePlan,
    ReconcileVerification,
    ResourceReconciler,
)
from ai_engineering.state.observability import emit_framework_operation
from ai_engineering.state.service import load_install_state

logger = logging.getLogger(__name__)

_PHASE_MODULES = {
    PHASE_DETECT: detect,
    PHASE_GOVERNANCE: governance,
    PHASE_IDE_CONFIG: ide_config,
    PHASE_STATE: state,
    PHASE_TOOLS: tools,
    PHASE_HOOKS: hooks,
}

_RUNTIME_CHECK_MODULES = {
    "vcs_auth": vcs_auth,
    "feeds": feeds,
    "branch_policy": branch_policy,
    "version": version,
    "opa_health": opa_health,
    "secrets_gate": secrets_gate,
}

_RUNTIME_MODULES: tuple[str, ...] = (
    "vcs_auth",
    "feeds",
    "branch_policy",
    "version",
    "opa_health",
    "secrets_gate",
)


@dataclass(frozen=True)
class _DoctorPlanPayload:
    initial_results: list[CheckResult]
    fixable: list[CheckResult]


class _DoctorPhaseAdapter:
    """Adapt doctor phase modules to the shared reconciler contract."""

    def __init__(self, phase_name: str, phase_mod: ModuleType, *, fix: bool, dry_run: bool) -> None:
        self._phase_name = phase_name
        self._phase_mod = phase_mod
        self._fix = fix
        self._dry_run = dry_run

    @property
    def name(self) -> str:
        return self._phase_name

    def inspect(self, context: object) -> ReconcileInspection:
        doctor_context = self._coerce_context(context)
        check_fn = self._phase_mod.check
        results = list(check_fn(doctor_context))
        return ReconcileInspection(resource_name=self.name, payload=results)

    def plan(self, inspection: ReconcileInspection, _context: object) -> ReconcilePlan:
        initial_results = self._coerce_results(inspection.payload)
        fixable = [
            result
            for result in initial_results
            if result.status in (CheckStatus.FAIL, CheckStatus.WARN) and result.fixable
        ]
        actions = [
            ReconcileAction(
                action_id=f"{self.name}:{result.name}",
                action_type="fix",
                resource=result.name,
                reason=result.message,
            )
            for result in fixable
        ]
        return ReconcilePlan(
            resource_name=self.name,
            actions=actions,
            payload=_DoctorPlanPayload(initial_results=initial_results, fixable=fixable),
        )

    def apply(self, plan: ReconcilePlan, context: object) -> ReconcileApplyResult:
        doctor_context = self._coerce_context(context)
        payload = self._coerce_plan_payload(plan.payload)
        results = list(payload.initial_results)

        if self._fix and payload.fixable:
            fix_fn = self._phase_mod.fix
            fixed = list(fix_fn(doctor_context, payload.fixable, dry_run=self._dry_run))
            fixed_names = {result.name for result in fixed}
            results = [
                next(
                    (fixed_result for fixed_result in fixed if fixed_result.name == result.name),
                    result,
                )
                if result.name in fixed_names
                else result
                for result in payload.initial_results
            ]

        return ReconcileApplyResult(
            resource_name=self.name,
            applied_actions=[action.action_id for action in plan.actions],
            payload=results,
        )

    def verify(
        self,
        apply_result: ReconcileApplyResult,
        _context: object,
    ) -> ReconcileVerification:
        return ReconcileVerification(
            resource_name=self.name, passed=True, payload=apply_result.payload
        )

    def rollback(
        self,
        _plan: ReconcilePlan,
        _context: object,
        _reason: BaseException | ReconcileVerification,
    ) -> None:
        return None

    def finalize(
        self,
        _plan: ReconcilePlan,
        _apply_result: ReconcileApplyResult,
        _verification: ReconcileVerification,
        _context: object,
    ) -> None:
        return None

    @staticmethod
    def _coerce_context(context: object) -> DoctorContext:
        if not isinstance(context, DoctorContext):
            msg = "doctor reconciler context must be DoctorContext"
            raise TypeError(msg)
        return context

    @staticmethod
    def _coerce_results(payload: object | None) -> list[CheckResult]:
        if not isinstance(payload, list):
            msg = "doctor reconciler inspection payload must be a list"
            raise TypeError(msg)
        return payload

    @staticmethod
    def _coerce_plan_payload(payload: object | None) -> _DoctorPlanPayload:
        if not isinstance(payload, _DoctorPlanPayload):
            msg = "doctor reconciler plan payload must be _DoctorPlanPayload"
            raise TypeError(msg)
        return payload


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
    # Spec-125: install_state moved from JSON file to state.db's
    # install_state singleton row. Treat the absence of state.db OR the
    # absence of the singleton row at id=1 as "not installed yet" so
    # diagnose() falls into pre-install mode (matching pre-spec-125
    # semantics where the missing JSON file did the same). The probe
    # MUST NOT lazy-bootstrap state.db: doctor on a tmp_path with no
    # ``.ai-engineering`` directory must observe a missing DB and report
    # ``installed=False`` (test_fails_on_missing_ai_engineering_dir).
    state_dir = target / ".ai-engineering" / "state"
    db_path = state_dir / "state.db"
    install_state = None
    if db_path.is_file():
        import sqlite3 as _sqlite3

        try:
            _conn = _sqlite3.connect(db_path, timeout=2)
            try:
                _tbl = _conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='install_state'"
                ).fetchone()
                if _tbl is not None:
                    _row = _conn.execute("SELECT 1 FROM install_state WHERE id = 1").fetchone()
                    if _row is not None:
                        try:
                            install_state = load_install_state(state_dir)
                        except Exception:
                            install_state = None
            finally:
                _conn.close()
        except _sqlite3.Error:
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

    if fix:
        feed_preflight = validate_feeds_for_install(ctx, mode="repair")
        if feed_preflight.status == "blocked":
            report.runtime.append(
                CheckResult(
                    name="feed-preflight",
                    status=CheckStatus.FAIL,
                    message=feed_preflight.message,
                )
            )
            _emit_audit_log(target, report, fix=fix)
            return report

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
    phase_mod = _PHASE_MODULES.get(phase_name)
    if phase_mod is None:
        msg = f"Unknown phase: {phase_name}"
        raise ValueError(msg)
    run = ResourceReconciler().run(
        _DoctorPhaseAdapter(phase_name, phase_mod, fix=fix, dry_run=dry_run),
        ctx,
    )
    if run.apply_result is None:
        msg = f"doctor reconciler did not apply phase {phase_name!r}"
        raise RuntimeError(msg)
    results = _DoctorPhaseAdapter._coerce_results(run.apply_result.payload)
    report.phases.append(PhaseReport(name=phase_name, checks=results))


def _run_runtime_modules(
    ctx: DoctorContext,
    modules: tuple[str, ...],
    report: DoctorReport,
) -> None:
    """Import and run runtime check modules, appending to ``report.runtime``."""
    for mod_name in modules:
        mod = _RUNTIME_CHECK_MODULES.get(mod_name)
        if mod is None:
            msg = f"Unknown runtime module: {mod_name}"
            raise ValueError(msg)
        results = mod.check(ctx)
        report.runtime.extend(results)


def _emit_audit_log(target: Path, report: DoctorReport, *, fix: bool) -> None:
    """Emit a single framework operation event for this doctor invocation."""
    emit_framework_operation(
        target,
        operation="doctor",
        component="doctor",
        source="cli",
        metadata={
            "mode": "fix" if fix else "diagnose",
            "phases_checked": len(report.phases),
            "runtime_checked": len(report.runtime),
            "summary": report.summary,
            "fixes_applied": [
                c.name for p in report.phases for c in p.checks if c.status == CheckStatus.FIXED
            ],
        },
    )
