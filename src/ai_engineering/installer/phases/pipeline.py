"""Pipeline runner that orchestrates phases in sequence.

The runner iterates over an ordered list of ``PhaseProtocol`` phases,
calling *plan -> execute -> verify* for each one.  If any phase fails
verification the pipeline stops and remaining phases are skipped.

A ``dry_run`` flag collects plans without executing or verifying.

Spec-101 T-5.2: before the first phase fires the runner emits a one-shot
BREAKING banner advising users of the new EXIT 80 / EXIT 81 codes, the
``python_env.mode`` default, and 14-stack ``required_tools`` coverage.
The banner is gated by ``InstallState.breaking_banner_seen`` so it only
ever shows up once per project.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.reconciler import (
    ReconcileAction,
    ReconcileApplyResult,
    ReconcileInspection,
    ReconcilePlan,
    ReconcileVerification,
    ResourceReconciler,
)
from ai_engineering.state.models import InstallState
from ai_engineering.state.service import load_install_state, save_install_state

from . import InstallContext, PhasePlan, PhaseProtocol, PhaseResult, PhaseVerdict

# ---------------------------------------------------------------------------
# First-run welcome banner
# ---------------------------------------------------------------------------
# spec-109 follow-up: replaced the spec-101 [BREAKING] banner with friendlier
# copy — same three pieces of information, no spec ID / EXIT-code jargon.

_BREAKING_BANNER = """\
================================================================================
What's new in ai-engineering
================================================================================
Three things to know about this project (this notice appears once):

  1. Missing tools now stop the install
     If a required tool can't be installed, the CLI tells you exactly what's
     missing and how to install it — no more silent partial setups.

  2. Tools install once per machine, not per project
     Python tools (ruff, ty, pip-audit, semgrep) live in
     ~/.local/share/uv/tools/, so creating a new git worktree no longer
     re-installs them. To opt back into the per-project .venv, set
     `python_env.mode: venv` in .ai-engineering/manifest.yml.

  3. Each language stack ships with its own toolchain
     Python, TypeScript, Java, Rust, Go, and 9 more stacks have their tool
     lists declared in your manifest. If you add a stack later, ai-eng will
     prompt you for the missing tools instead of failing silently.

More detail: .ai-engineering/contexts/python-env-modes.md
================================================================================
"""

_AI_ENGINEERING_DIR = ".ai-engineering"
_STATE_DIR_REL = Path(_AI_ENGINEERING_DIR) / "state"


def _state_file_path(target: Path) -> Path:
    return target / _STATE_DIR_REL / "install-state.json"


def _load_or_default_state(target: Path) -> InstallState:
    """Load install-state.json from *target*, falling back to defaults.

    Returns a default ``InstallState`` (with ``breaking_banner_seen=False``)
    when the file is absent -- a fresh install -- so the banner fires.
    """
    state_dir = target / _STATE_DIR_REL
    try:
        return load_install_state(state_dir)
    except (OSError, ValueError):
        # Corrupt or unreadable state file: treat as fresh so the banner
        # still fires once. Safer than silently swallowing the contract.
        return InstallState()


def _maybe_emit_breaking_banner(context: InstallContext) -> None:
    """Emit the spec-101 BREAKING banner once per project.

    Side effects:
      - Writes the banner to ``sys.stderr``.
      - Persists ``InstallState.breaking_banner_seen=True`` to install-state.json
        so subsequent runs stay quiet.

    The function is **fail-open**: any state-load or state-save error degrades
    to "do nothing" rather than blocking install. The contract is "ideally
    once, never twice" -- never an install-blocker.

    JSON mode (``--non-interactive`` / piped output) suppresses the banner
    entirely so machine consumers receive only the structured envelope on
    stdout. The persistence flag is still set so an interactive re-run on the
    same project also stays quiet -- the banner remains a one-shot event.
    """
    emit_breaking_banner_for_target(context.target)


def emit_breaking_banner_for_target(target: Path) -> None:
    """Public wrapper so callers outside the pipeline can fire the banner.

    spec-101 Compat-2 (Wave 27): the banner used to fire from inside the
    pipeline runner, after the prereq gates. A first-upgrade run that
    failed at the uv / SDK prereq gate exited via ``EXIT_PREREQS_MISSING``
    BEFORE the pipeline ran, so the user never saw the banner explaining
    the new contract. Hoisting the emit out of the pipeline lets the CLI
    fire it before any gate, and the existing ``breaking_banner_seen``
    flag still prevents double-emission on subsequent re-runs.
    """
    try:
        state_dir = target / _STATE_DIR_REL
        try:
            state = load_install_state(state_dir)
        except (OSError, ValueError):
            state = InstallState()
    except Exception:  # pragma: no cover - defensive fail-open
        return

    if state.breaking_banner_seen:
        return

    # JSON mode: suppress human-facing banner; CliRunner mixes stderr with
    # stdout when ``mix_stderr`` is the default, which would corrupt the
    # JSON envelope downstream consumers parse.
    from ai_engineering.cli_output import is_json_mode

    if not is_json_mode():
        sys.stderr.write(_BREAKING_BANNER)
        sys.stderr.flush()

    # Persist the flag so the next run stays quiet. We round-trip through
    # the loaded model rather than constructing a fresh default to preserve
    # any existing state already written by an earlier phase or a manual edit.
    try:
        state.breaking_banner_seen = True
        save_install_state(state_dir, state)
    except OSError:  # pragma: no cover - defensive fail-open
        # Filesystem read-only / permission error: banner still showed,
        # but the flag won't persist. Acceptable degradation.
        pass


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

        # spec-101 T-5.2: emit the one-shot BREAKING banner before the first
        # phase, but only on a real (non-dry-run) install. Dry-run is a
        # preview surface -- the banner's persistence side-effect would be
        # surprising there.
        if not dry_run:
            _maybe_emit_breaking_banner(context)

        total = len(self._phases)
        reconciler = ResourceReconciler()
        for index, phase in enumerate(self._phases, start=1):
            self._notify(f"[{index}/{total}] {phase.name}")
            run = reconciler.run(_InstallPhaseAdapter(phase), context, preview=dry_run)
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
