"""Post-pipeline auto-remediation for ``ai-eng install`` (spec-109 D-109-05).

When ``PipelineRunner`` records non-critical failures (today: ``ToolsPhase``
only -- spec-109 D-109-03), this module re-uses the existing doctor fix
paths for tools + hooks to attempt automatic recovery before the install
command exits. The user no longer has to manually run
``ai-eng doctor --fix`` after a partial install failure.

Reuse, never duplicate: every fix routine here delegates to
:mod:`ai_engineering.doctor.phases.tools` and
:mod:`ai_engineering.doctor.phases.hooks`. If a code path works for
``ai-eng doctor --fix``, ``ai-eng install`` automatically benefits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.doctor.phases import hooks as doctor_hooks
from ai_engineering.doctor.phases import tools as doctor_tools
from ai_engineering.installer.phases import PHASE_HOOKS, PHASE_TOOLS

__all__ = (
    "AutoRemediateReport",
    "auto_remediate_after_install",
)


# Mapping from non-critical phase name -> (check_module, fix_module).
# Centralised so adding a new auto-remediable phase is a one-line addition.
_REMEDIATION_TABLE: dict[str, tuple[object, object]] = {
    PHASE_TOOLS: (doctor_tools, doctor_tools),
    PHASE_HOOKS: (doctor_hooks, doctor_hooks),
}


@dataclass
class AutoRemediateReport:
    """Outcome of post-install auto-remediation.

    Fields:
        applied: List of remediation labels that succeeded
            (e.g. ``"tools-required: installed gitleaks"``).
        failed: List of remediation labels that did not produce a FIXED
            status. The user must address these manually.
        errors: Raw exception strings raised by the underlying fix path.
            Always empty in the happy path.
        invoked: True when at least one phase entered the remediation loop.
            False when the pipeline had no non-critical failures.
    """

    applied: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    invoked: bool = False

    @property
    def success(self) -> bool:
        """True only when remediation actually repaired at least one thing.

        spec-113 G-5: success requires ``applied != []`` AND ``failed == []``
        AND ``errors == []``. The pre-spec-113 contract returned True when the
        flow ran with no failures, even if nothing landed in ``applied`` --
        which produced the misleading "all non-critical failures repaired
        automatically" surface even when the framework hadn't fixed anything.
        """
        return self.invoked and bool(self.applied) and not self.failed and not self.errors

    def to_dict(self) -> dict[str, object]:
        """Serialise for the install command's JSON envelope."""
        return {
            "invoked": self.invoked,
            "success": self.success,
            "applied": list(self.applied),
            "failed": list(self.failed),
            "errors": list(self.errors),
        }


def auto_remediate_after_install(
    target: Path,
    non_critical_failures: list[str],
    *,
    install_state=None,
    manifest_config=None,
) -> AutoRemediateReport:
    """Run doctor's fix routines for each non-critical failed phase.

    Args:
        target: Project root.
        non_critical_failures: Phase names recorded as non-critical failures
            by the install pipeline. Order is preserved.
        install_state: Optional :class:`InstallState` to thread into the
            doctor context (avoids a redundant disk read).
        manifest_config: Optional manifest snapshot to thread in.

    Returns:
        :class:`AutoRemediateReport` summarising what was fixed and what
        survived.
    """
    report = AutoRemediateReport()

    if not non_critical_failures:
        return report

    report.invoked = True
    ctx = DoctorContext(
        target=target,
        install_state=install_state,
        manifest_config=manifest_config,
        fix_mode=True,
        dry_run=False,
    )

    for phase_name in non_critical_failures:
        modules = _REMEDIATION_TABLE.get(phase_name)
        if modules is None:
            # Phase has no auto-remediation path declared.
            report.failed.append(f"{phase_name}: no auto-remediation registered")
            continue

        check_mod, fix_mod = modules
        _remediate_phase(ctx, phase_name, check_mod, fix_mod, report)

    return report


def _remediate_phase(
    ctx: DoctorContext,
    phase_name: str,
    check_mod: object,
    fix_mod: object,
    report: AutoRemediateReport,
) -> None:
    """Run check() + fix() for one phase and record the outcome."""
    try:
        results: list[CheckResult] = check_mod.check(ctx)  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - defensive
        report.errors.append(f"{phase_name}.check raised: {exc}")
        report.failed.append(f"{phase_name}: check failed")
        return

    # spec-113: also treat WARN-fixable as eligible for the fix path. The
    # doctor surfaces missing tools as WARN (not FAIL) so a WARN with
    # ``fixable=True`` is the same actionable condition.
    failed_checks = [
        c for c in results if c.status in (CheckStatus.FAIL, CheckStatus.WARN) and c.fixable
    ]
    if not failed_checks:
        # Doctor sees no fixable failure -- maybe the phase failure was
        # transient, the check is non-fixable, OR the install-state
        # record-driven phase failure was reconciled by the doctor's
        # re-evaluation (spec-113 G-12 external recovery). Three cases:
        #
        # 1. Non-fixable FAIL  -> surface to ``failed`` so the user sees it.
        # 2. Non-fixable WARN  -> surface to ``failed`` (same advisory).
        # 3. Everything OK    -> the gap closed itself; surface as
        #    ``applied`` so the honest accounting sees a non-empty result
        #    and the install command exits 0.
        non_fix_failures = [c for c in results if c.status in (CheckStatus.FAIL, CheckStatus.WARN)]
        if non_fix_failures:
            for cr in non_fix_failures:
                report.failed.append(f"{phase_name}.{cr.name}: {cr.message}")
            return
        # All clear -- treat as a self-closing gap.
        report.applied.append(
            f"{phase_name}: phase reconciled on re-evaluation (no remediation needed)"
        )
        return

    try:
        fixed_results: list[CheckResult] = fix_mod.fix(  # type: ignore[attr-defined]
            ctx, failed_checks, dry_run=False
        )
    except Exception as exc:  # pragma: no cover - defensive
        report.errors.append(f"{phase_name}.fix raised: {exc}")
        report.failed.append(f"{phase_name}: fix failed")
        return

    for cr in fixed_results:
        label = f"{phase_name}.{cr.name}: {cr.message}"
        if cr.status == CheckStatus.FIXED:
            report.applied.append(label)
        else:
            report.failed.append(label)
