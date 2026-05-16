"""Pipeline runner that orchestrates phases in sequence.

The runner iterates over an ordered list of ``PhaseProtocol`` phases,
calling *plan -> execute -> verify* for each one.  If any phase fails
verification the pipeline stops and remaining phases are skipped.

A ``dry_run`` flag collects plans without executing or verifying.

spec-124 D-124-02: removed first-run BREAKING banner. Install pipeline
emits phase output directly without preamble notice.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field

from ai_engineering.reconciler import (
    ReconcileAction,
    ReconcileApplyResult,
    ReconcileInspection,
    ReconcilePlan,
    ReconcileVerification,
    ResourceReconciler,
)

from . import InstallContext, PhasePlan, PhaseProtocol, PhaseResult, PhaseVerdict

# spec-124 D-124-02: removed first-run welcome banner. The "What's new"
# notice was noise without ongoing value; install pipeline now starts
# directly with the phase output.

# spec-124 D-124-02: banner code removed; CLI starts with phase output directly.


@dataclass
class PipelineSummary:
    """Aggregated outcome of the full pipeline run.

    spec-109 D-109-02: ``non_critical_failures`` records phases that returned
    ``verdict.passed == False`` but were marked ``critical=False`` so the
    runner kept going. ``failed_phase`` still names the *critical* phase that
    broke the pipeline (or None when the pipeline ran end-to-end).
    """

    plans: list[PhasePlan] = field(default_factory=list)
    results: list[PhaseResult] = field(default_factory=list)
    verdicts: list[PhaseVerdict] = field(default_factory=list)
    completed_phases: list[str] = field(default_factory=list)
    failed_phase: str | None = None
    non_critical_failures: list[str] = field(default_factory=list)
    dry_run: bool = False


class _InstallPhaseAdapter:
    """Adapt legacy install phases to the shared reconciler contract."""

    def __init__(self, phase: PhaseProtocol) -> None:
        self._phase = phase

    @property
    def name(self) -> str:
        return self._phase.name

    def inspect(self, context: object) -> ReconcileInspection:
        return ReconcileInspection(resource_name=self.name, payload=context)

    def plan(self, _inspection: ReconcileInspection, context: object) -> ReconcilePlan:
        install_context = self._coerce_context(context)
        phase_plan = self._phase.plan(install_context)
        actions = [
            ReconcileAction(
                action_id=f"{phase_plan.phase_name}:{index}",
                action_type=action.action_type,
                resource=action.destination or phase_plan.phase_name,
                reason=action.rationale,
                metadata={"source": action.source},
            )
            for index, action in enumerate(phase_plan.actions, start=1)
        ]
        return ReconcilePlan(resource_name=self.name, actions=actions, payload=phase_plan)

    def apply(self, plan: ReconcilePlan, context: object) -> ReconcileApplyResult:
        install_context = self._coerce_context(context)
        phase_plan = self._coerce_plan(plan.payload)
        result = self._phase.execute(phase_plan, install_context)
        return ReconcileApplyResult(
            resource_name=self.name,
            applied_actions=list(result.created) + list(result.deleted),
            skipped_actions=list(result.skipped),
            failed_actions=list(result.failed),
            payload=result,
        )

    def verify(
        self,
        apply_result: ReconcileApplyResult,
        context: object,
    ) -> ReconcileVerification:
        install_context = self._coerce_context(context)
        phase_result = self._coerce_result(apply_result.payload)
        verdict = self._phase.verify(phase_result, install_context)
        return ReconcileVerification(
            resource_name=self.name,
            passed=verdict.passed,
            warnings=list(verdict.warnings),
            errors=list(verdict.errors),
            payload=verdict,
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
    def _coerce_context(context: object) -> InstallContext:
        if not isinstance(context, InstallContext):
            msg = "install reconciler context must be InstallContext"
            raise TypeError(msg)
        return context

    @staticmethod
    def _coerce_plan(payload: object | None) -> PhasePlan:
        if not isinstance(payload, PhasePlan):
            msg = "install reconciler plan payload must be PhasePlan"
            raise TypeError(msg)
        return payload

    @staticmethod
    def _coerce_result(payload: object | None) -> PhaseResult:
        if not isinstance(payload, PhaseResult):
            msg = "install reconciler result payload must be PhaseResult"
            raise TypeError(msg)
        return payload


class PipelineRunner:
    """Executes an ordered sequence of install phases."""

    def __init__(
        self,
        phases: list[PhaseProtocol],
        *,
        progress_callback: Callable[[str], None] | None = None,
    ) -> None:
        self._phases = phases
        self._progress_callback = progress_callback

    def run(self, context: InstallContext, *, dry_run: bool = False) -> PipelineSummary:
        """Run the pipeline.

        Parameters
        ----------
        context:
            Shared install context available to every phase.
        dry_run:
            When *True*, only ``plan()`` is called on each phase.
            No files are created or modified, and the BREAKING banner is
            suppressed because dry-run is a preview, not an install event.

        Returns
        -------
        PipelineSummary
            Collected plans, results, and verdicts for all phases.

        Notes
        -----
        spec-109 D-109-02: a phase whose verdict fails AND whose ``critical``
        flag is False is logged in ``summary.non_critical_failures`` but does
        not break the loop -- subsequent phases still run. A phase missing the
        ``critical`` attribute defaults to True (legacy behaviour).
        """
        summary = PipelineSummary(dry_run=dry_run)

        # spec-124 D-124-02: removed BREAKING banner emission point.

        total = len(self._phases)
        reconciler = ResourceReconciler()
        for index, phase in enumerate(self._phases, start=1):
            self._notify(f"[{index}/{total}] {phase.name}")
            run = reconciler.run(_InstallPhaseAdapter(phase), context, preview=dry_run)  # ty:ignore[invalid-argument-type]
            plan = _InstallPhaseAdapter._coerce_plan(run.plan.payload)
            summary.plans.append(plan)

            if dry_run:
                summary.completed_phases.append(phase.name)
                continue

            if run.apply_result is None or run.verification is None:
                msg = f"reconciler did not apply install phase {phase.name!r}"
                raise RuntimeError(msg)
            result = _InstallPhaseAdapter._coerce_result(run.apply_result.payload)
            summary.results.append(result)

            verdict_payload = run.verification.payload
            if not isinstance(verdict_payload, PhaseVerdict):
                msg = f"reconciler did not verify install phase {phase.name!r}"
                raise RuntimeError(msg)
            verdict = verdict_payload
            summary.verdicts.append(verdict)

            if not verdict.passed:
                if getattr(phase, "critical", True):
                    summary.failed_phase = phase.name
                    break
                summary.non_critical_failures.append(phase.name)
                # Non-critical phase still completed its attempt; keep going.
                summary.completed_phases.append(phase.name)
                continue

            summary.completed_phases.append(phase.name)

        return summary

    def _notify(self, message: str) -> None:
        """Forward a phase-progress message to the optional callback.

        Progress UI must never break the pipeline; any callback exception is
        suppressed (fail-open).
        """
        if self._progress_callback is None:
            return
        with suppress(Exception):
            self._progress_callback(message)
