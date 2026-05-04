"""spec-119 — canonical project smoke for /ai-eval-gate.

Runs the gate engine against the real `.ai-engineering/manifest.yml` and
the real `.ai-engineering/evals/baseline.json` via the filesystem grader.
The seed scenarios in `baseline.json` reference artefacts that exist in
this repo (the spec-119 spec, plan, and the /ai-review skill), so this
test confirms the gate runs end-to-end with no stubbing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.eval import gate as gate_module
from ai_engineering.eval.scorecard import Verdict
from ai_engineering.eval.thresholds import load_evaluation_config

pytestmark = pytest.mark.eval


def test_canonical_gate_smoke(repo_root: Path):
    cfg = load_evaluation_config(repo_root / ".ai-engineering" / "manifest.yml")
    runner = gate_module.filesystem_trial_runner(repo_root)
    outcome = gate_module.run_gate(repo_root, trial_runner=runner, config=cfg)
    # Aggregate verdict cannot be SKIPPED: baseline.json exists with three seed
    # scenarios, all of which must grade pass against repo artefacts.
    assert outcome.verdict in {Verdict.GO, Verdict.CONDITIONAL}
    assert outcome.scorecards, "gate must produce at least one scorecard"
    sc = outcome.scorecards[0]
    assert sc.total_scenarios == 3
    assert sc.total_trials == 15  # 3 scenarios × k=5
    # The seed scenarios target real files; pass@k should be 1.0 against them.
    assert sc.pass_at_k == pytest.approx(1.0)


def test_canonical_gate_emits_dict(repo_root: Path):
    cfg = load_evaluation_config(repo_root / ".ai-engineering" / "manifest.yml")
    runner = gate_module.filesystem_trial_runner(repo_root)
    payload = gate_module.mode_check(repo_root, trial_runner=runner, config=cfg)
    assert "verdict" in payload
    assert "scorecards" in payload
    assert "pack_paths" in payload
