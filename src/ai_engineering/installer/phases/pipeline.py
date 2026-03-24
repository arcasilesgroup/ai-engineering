"""Pipeline runner that orchestrates phases in sequence.

The runner iterates over an ordered list of ``PhaseProtocol`` phases,
calling *plan -> execute -> verify* for each one.  If any phase fails
verification the pipeline stops and remaining phases are skipped.

A ``dry_run`` flag collects plans without executing or verifying.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import InstallContext, PhasePlan, PhaseProtocol, PhaseResult, PhaseVerdict


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
            No files are created or modified.

        Returns
        -------
        PipelineSummary
            Collected plans, results, and verdicts for all phases.
        """
        summary = PipelineSummary(dry_run=dry_run)

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
