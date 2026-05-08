"""Eval runner — thin orchestrator over the four sub-007 ports.

Sub-007 M6 application layer, pilot scope. The runner coordinates:

1. ``OptimizerPort`` — runs an :class:`EvalCorpus` and returns pass@1.
2. ``LLMPort`` + ``GitLogPort`` — delegated to a future
   ``corpus generator`` use case (not in pilot scope; see
   ``sub-007/plan.md`` Self-Report).
3. ``LessonsPort`` — read by ``/ai-skill-tune`` integration; not by
   the regression gate itself.

The runner is intentionally thin: heavy lifting (LLM-driven case
generation, manual operator review, multi-wave corpus scale-out) is
deferred per the wave-time scope guardrail. What ships in pilot is
the *path*: load baseline → run optimizer → call regression gate →
emit JSON report. Wiring the path now means the full corpus rollout
is a data delivery, not a code delivery.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path

from skill_app.eval_regression_gate import compute_regression_report
from skill_app.ports.optimizer import OptimizerPort
from skill_domain.eval_types import (
    BaselineEntry,
    EvalCorpus,
    RegressionReport,
)


def load_baseline(baseline_path: Path) -> tuple[BaselineEntry, ...]:
    """Read ``evals/baseline.json`` and return the entries.

    The file format is ``{"entries": [...]}`` with one
    :class:`BaselineEntry` ``to_dict`` payload per row. This wrapper
    object (instead of a top-level list) leaves room for future
    metadata (capture timestamp, optimizer SHA, framework version)
    without breaking the wire format.
    """
    if not baseline_path.exists():
        return ()
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    rows = payload.get("entries", [])
    return tuple(BaselineEntry.from_dict(row) for row in rows)


def load_corpora(corpus_root: Path) -> dict[str, EvalCorpus]:
    """Read every ``<skill>.jsonl`` under ``corpus_root`` into corpora.

    JSONL format: one :class:`EvalCase` ``to_dict`` payload per line.
    The skill name is the file stem. Corpora that fail to parse are
    skipped with a sentinel empty corpus so the runner can still
    emit a regression report — the alternative (raise) would mask
    legitimate regressions on neighbour skills.
    """
    corpora: dict[str, EvalCorpus] = {}
    if not corpus_root.is_dir():
        return corpora
    for jsonl_path in sorted(corpus_root.glob("*.jsonl")):
        skill = jsonl_path.stem
        cases = []
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                cases.append(json.loads(stripped))
            except json.JSONDecodeError:
                # Malformed line → skip. The corpus shape test (T-4.7)
                # is the canonical place to fail on malformed lines.
                continue
        corpora[skill] = EvalCorpus.from_dict({"skill": skill, "cases": cases})
    return corpora


def run_skill_set_regression(
    *,
    optimizer: OptimizerPort,
    baseline: Iterable[BaselineEntry],
    corpora: Mapping[str, EvalCorpus],
) -> RegressionReport:
    """Run the optimizer over each skill's corpus and gate vs baseline.

    The function is pure given a deterministic optimizer adapter; it
    is the canonical end-to-end entry point for the regression gate.
    """
    baseline_tuple = tuple(baseline)
    current: dict[str, float] = {}
    for entry in baseline_tuple:
        corpus = corpora.get(entry.skill)
        if corpus is None:
            # Missing corpus ⇒ leave skill out of ``current`` so the
            # gate scores it as 0.0 and surfaces dropped coverage.
            continue
        current[entry.skill] = float(optimizer.run(entry.skill, corpus))
    return compute_regression_report(baseline=baseline_tuple, current=current)


__all__ = [
    "load_baseline",
    "load_corpora",
    "run_skill_set_regression",
]
