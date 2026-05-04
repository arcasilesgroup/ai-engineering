"""spec-119 /ai-eval-gate runtime (Phase 4 functional engine).

Provides the `enforce`, `check`, and `report` modes that the SKILL.md
will dispatch, packaged as Python functions so a) the gate is testable
without spinning up a Claude Code agent, b) `/ai-pr` and
`/ai-release-gate` consume the same engine, and c) CI can call it
directly through the `ai-eng eval-gate` CLI subcommand (registered in
`src/ai_engineering/cli_factory.py` once that wiring is approved).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.eval.runner import (
    ScenarioRunResult,
    TrialRunner,
    load_baseline,
    run_scenario_pack,
)
from ai_engineering.eval.scorecard import Scorecard, Verdict
from ai_engineering.eval.thresholds import (
    ManifestEvaluationConfig,
    load_evaluation_config,
)


@dataclass(frozen=True)
class GateOutcome:
    """Aggregated outcome across all scenario packs declared in the manifest."""

    verdict: Verdict
    scorecards: tuple[Scorecard, ...]
    pack_results: tuple[ScenarioRunResult, ...]
    skipped_reasons: tuple[str, ...] = field(default_factory=tuple)
    enforcement: str = "blocking"

    @property
    def exit_code(self) -> int:
        """Process exit-code mapping. blocking + NO_GO → 1, else 0."""
        if self.enforcement == "advisory":
            return 0
        if self.verdict == Verdict.NO_GO:
            return 1
        return 0


def _aggregate(verdicts: list[Verdict]) -> Verdict:
    if not verdicts:
        return Verdict.SKIPPED
    if Verdict.NO_GO in verdicts:
        return Verdict.NO_GO
    if Verdict.CONDITIONAL in verdicts:
        return Verdict.CONDITIONAL
    if all(v == Verdict.GO for v in verdicts):
        return Verdict.GO
    return Verdict.CONDITIONAL


def run_gate(
    project_root: Path,
    *,
    trial_runner: TrialRunner,
    config: ManifestEvaluationConfig | None = None,
) -> GateOutcome:
    """Run every scenario pack declared in the manifest and aggregate."""
    if config is None:
        config = load_evaluation_config(project_root / ".ai-engineering" / "manifest.yml")
    pack_results: list[ScenarioRunResult] = []
    scorecards: list[Scorecard] = []
    skipped_reasons: list[str] = []
    for relative in config.scenario_packs:
        pack_path = project_root / relative
        if not pack_path.exists():
            skipped_reasons.append(f"missing pack: {relative}")
            continue
        baseline = load_baseline(pack_path)
        result = run_scenario_pack(
            pack_path,
            config=config,
            trial_runner=trial_runner,
            baseline=baseline,
        )
        pack_results.append(result)
        scorecards.append(result.scorecard)
    if not scorecards:
        return GateOutcome(
            verdict=Verdict.SKIPPED,
            scorecards=tuple(scorecards),
            pack_results=tuple(pack_results),
            skipped_reasons=tuple(skipped_reasons),
            enforcement=config.enforcement,
        )
    aggregate = _aggregate([sc.verdict for sc in scorecards])
    return GateOutcome(
        verdict=aggregate,
        scorecards=tuple(scorecards),
        pack_results=tuple(pack_results),
        skipped_reasons=tuple(skipped_reasons),
        enforcement=config.enforcement,
    )


# ---------------------------------------------------------------------------
# Mode handlers — `check`, `report`, `enforce`
# ---------------------------------------------------------------------------


def mode_check(
    project_root: Path,
    *,
    trial_runner: TrialRunner,
    config: ManifestEvaluationConfig | None = None,
) -> Mapping[str, object]:
    """Return a JSON-serialisable dict describing the run."""
    outcome = run_gate(project_root, trial_runner=trial_runner, config=config)
    return _to_dict(outcome)


def mode_report(
    project_root: Path,
    *,
    trial_runner: TrialRunner,
    config: ManifestEvaluationConfig | None = None,
) -> str:
    """Return a markdown report intended for human review."""
    outcome = run_gate(project_root, trial_runner=trial_runner, config=config)
    return _render_markdown(outcome)


def mode_enforce(
    project_root: Path,
    *,
    trial_runner: TrialRunner,
    config: ManifestEvaluationConfig | None = None,
    skip: bool = False,
    skip_reason: str | None = None,
) -> tuple[int, GateOutcome]:
    """Run the gate and return (exit_code, outcome).

    `skip=True` short-circuits with a SKIPPED verdict — it is the call site
    used by `/ai-pr --skip-eval-gate` so the bypass is auditable. The
    caller is responsible for emitting the audit event with the reason.
    """
    if skip:
        outcome = GateOutcome(
            verdict=Verdict.SKIPPED,
            scorecards=(),
            pack_results=(),
            skipped_reasons=(skip_reason or "manual skip",),
            enforcement=(config.enforcement if config else "blocking"),
        )
        return 0, outcome
    outcome = run_gate(project_root, trial_runner=trial_runner, config=config)
    return outcome.exit_code, outcome


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def _to_dict(outcome: GateOutcome) -> Mapping[str, object]:
    return {
        "verdict": outcome.verdict.value,
        "exit_code": outcome.exit_code,
        "enforcement": outcome.enforcement,
        "skipped_reasons": list(outcome.skipped_reasons),
        "scorecards": [
            {
                "verdict": sc.verdict.value,
                "k": sc.k,
                "pass_at_k": sc.pass_at_k,
                "regression_delta": sc.regression_delta,
                "hallucination_rate": sc.hallucination_rate,
                "failed_scenarios": list(sc.failed_scenarios),
                "total_scenarios": sc.total_scenarios,
                "total_trials": sc.total_trials,
            }
            for sc in outcome.scorecards
        ],
        "pack_paths": [r.pack_path for r in outcome.pack_results],
    }


def _render_markdown(outcome: GateOutcome) -> str:
    lines = [
        f"# Eval Gate — verdict: **{outcome.verdict.value}**",
        "",
        f"Enforcement: `{outcome.enforcement}`",
        f"Exit code: `{outcome.exit_code}`",
        "",
    ]
    if outcome.skipped_reasons:
        lines.append("## Skipped")
        for reason in outcome.skipped_reasons:
            lines.append(f"- {reason}")
        lines.append("")
    if outcome.scorecards:
        lines.append("## Scorecards")
        lines.append("")
        lines.append("| Verdict | k | pass@k | Δ vs baseline | Hallucination | Failed scenarios |")
        lines.append("|---|---|---|---|---|---|")
        for sc in outcome.scorecards:
            failed = ", ".join(sc.failed_scenarios) if sc.failed_scenarios else "—"
            lines.append(
                f"| {sc.verdict.value} | {sc.k} | {sc.pass_at_k:.3f} "
                f"| {sc.regression_delta:+.3f} | {sc.hallucination_rate:.3f} | {failed} |"
            )
    return "\n".join(lines)


def to_json(outcome: GateOutcome, *, indent: int | None = 2) -> str:
    return json.dumps(_to_dict(outcome), indent=indent, sort_keys=True)


__all__ = [
    "GateOutcome",
    "mode_check",
    "mode_enforce",
    "mode_report",
    "run_gate",
    "to_json",
]


# ---------------------------------------------------------------------------
# Convenience trial runner: filesystem-graded scenarios
# ---------------------------------------------------------------------------


def filesystem_trial_runner(project_root: Path) -> TrialRunner:
    """Trial runner that grades by file existence + content match.

    Scenario metadata may declare:
      `expected_path`: relative path that must exist
      `expected_content_substring`: substring that must appear in the file
      `forbidden_path`: relative path that must NOT exist

    Each declared rule must hold for the trial to count as a pass. Useful
    for the seed scenarios shipped under `.ai-engineering/evals/scenarios/`
    that grade artefact presence (specs, plans, tests).
    """

    def runner(scenario: Mapping[str, object], _trial_id: int) -> bool:
        meta = scenario.get("metadata", {}) or {}
        if not isinstance(meta, Mapping):
            return False
        expected_path = meta.get("expected_path")
        if isinstance(expected_path, str):
            target = project_root / expected_path
            if not target.exists():
                return False
            substr = meta.get("expected_content_substring")
            if isinstance(substr, str) and substr:
                try:
                    if substr not in target.read_text(encoding="utf-8"):
                        return False
                except OSError:
                    return False
        forbidden = meta.get("forbidden_path")
        if isinstance(forbidden, str) and (project_root / forbidden).exists():
            return False
        return True

    return runner
