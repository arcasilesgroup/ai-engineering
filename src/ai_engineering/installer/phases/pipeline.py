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
from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.state.models import InstallState
from ai_engineering.state.service import load_install_state, save_install_state

from . import InstallContext, PhasePlan, PhaseProtocol, PhaseResult, PhaseVerdict

# ---------------------------------------------------------------------------
# Spec-101 BREAKING banner copy
# ---------------------------------------------------------------------------

_BREAKING_BANNER = """\
================================================================================
[BREAKING] spec-101 -- Stack-Aware User-Scope Tool Bootstrap
================================================================================
This project just received the spec-101 install contract update. Read once;
the banner does not repeat after this run.

  1. Hard-fail on missing tools
     ai-eng install / ai-eng doctor --fix now exit non-zero on a missing
     required tool. EXIT 80 = required tool missing or unverifiable.
     EXIT 81 = SDK / language prerequisite missing (see prereqs.sdk_per_stack).
     The previous "silent pass" behaviour and the `|| true` workaround are
     gone.

  2. python_env.mode defaults to 'uv-tool'
     Python tools install to ~/.local/share/uv/tools/, so worktree creation
     no longer triggers a per-cwd .venv re-install. Opt back into the legacy
     per-cwd .venv with `python_env.mode: venv` in .ai-engineering/manifest.yml.
     `shared-parent` enables a worktree-aware shared .venv at the repo root.

  3. required_tools covers 14 stacks
     baseline + python, typescript, javascript, java, csharp, go, php, rust,
     kotlin, swift, dart, sql, bash, cpp. Adding a stack to manifest without
     declaring its tool block is now impossible by construction.

Details: .ai-engineering/contexts/python-env-modes.md and CHANGELOG.md.
================================================================================
"""


def _state_file_path(target: Path) -> Path:
    return target / ".ai-engineering" / "state" / "install-state.json"


def _load_or_default_state(target: Path) -> InstallState:
    """Load install-state.json from *target*, falling back to defaults.

    Returns a default ``InstallState`` (with ``breaking_banner_seen=False``)
    when the file is absent -- a fresh install -- so the banner fires.
    """
    state_dir = target / ".ai-engineering" / "state"
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
    try:
        state = _load_or_default_state(context.target)
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
        state_dir = context.target / ".ai-engineering" / "state"
        save_install_state(state_dir, state)
    except OSError:  # pragma: no cover - defensive fail-open
        # Filesystem read-only / permission error: banner still showed,
        # but the flag won't persist. Acceptable degradation.
        pass


@dataclass
class PipelineSummary:
    """Aggregated outcome of the full pipeline run."""

    plans: list[PhasePlan] = field(default_factory=list)
    results: list[PhaseResult] = field(default_factory=list)
    verdicts: list[PhaseVerdict] = field(default_factory=list)
    completed_phases: list[str] = field(default_factory=list)
    failed_phase: str | None = None
    dry_run: bool = False


class PipelineRunner:
    """Executes an ordered sequence of install phases."""

    def __init__(self, phases: list[PhaseProtocol]) -> None:
        self._phases = phases

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
        """
        summary = PipelineSummary(dry_run=dry_run)

        # spec-101 T-5.2: emit the one-shot BREAKING banner before the first
        # phase, but only on a real (non-dry-run) install. Dry-run is a
        # preview surface -- the banner's persistence side-effect would be
        # surprising there.
        if not dry_run:
            _maybe_emit_breaking_banner(context)

        for phase in self._phases:
            plan = phase.plan(context)
            summary.plans.append(plan)

            if dry_run:
                summary.completed_phases.append(phase.name)
                continue

            result = phase.execute(plan, context)
            summary.results.append(result)

            verdict = phase.verify(result, context)
            summary.verdicts.append(verdict)

            if not verdict.passed:
                summary.failed_phase = phase.name
                break

            summary.completed_phases.append(phase.name)

        return summary
