"""spec-119 T-2.6 (foundation tests for the eval module that the agent imports).

Validates:
- ReplayOutcome construction + invariants;
- summarize_replay_outcomes aggregation;
- compute_pass_at_k matches the HumanEval formula on hand-checked numbers;
- Scorecard verdict mapping under representative inputs;
- detect_regression behavior with and without baseline;
- load_evaluation_config parses the manifest section;
- run_scenario_pack runs a packaged scenario through a stub trial runner.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_engineering.eval import (
    ReplayOutcome,
    Scorecard,
    Verdict,
    build_reliability_scorecard,
    build_replay_outcome,
    compute_pass_at_k,
    detect_regression,
    load_evaluation_config,
    regression_delta,
    summarize_replay_outcomes,
)
from ai_engineering.eval.runner import load_baseline, run_scenario_pack

pytestmark = pytest.mark.eval


class TestReplayOutcome:
    def test_pass_rate_simple(self):
        o = build_replay_outcome("s1", [True, False, True, True])
        assert o.trials_total == 4
        assert o.trials_passed == 3
        assert o.pass_rate == pytest.approx(0.75)

    def test_pass_rate_zero_trials(self):
        o = build_replay_outcome("s1", [])
        assert o.pass_rate == 0.0

    def test_rejects_blank_id(self):
        with pytest.raises(ValueError, match="scenario_id"):
            build_replay_outcome("   ", [True])

    def test_rejects_negative_passed(self):
        with pytest.raises(ValueError, match="trials_passed"):
            ReplayOutcome(scenario_id="s1", trials_total=2, trials_passed=-1)


class TestSummarize:
    def test_aggregation(self):
        outcomes = [
            build_replay_outcome("a", [True, True, True]),
            build_replay_outcome("b", [False, False, False]),
            build_replay_outcome("c", [True, False, True]),
        ]
        s = summarize_replay_outcomes(outcomes)
        assert s.total_scenarios == 3
        assert s.total_trials == 9
        assert s.total_passed == 5
        assert s.failed_scenario_ids() == ("b", "c")
        assert s.overall_pass_rate == pytest.approx(5 / 9)


class TestPassAtK:
    def test_k_equals_n_all_pass(self):
        outcomes = [build_replay_outcome("s", [True, True, True])]
        assert compute_pass_at_k(outcomes, 3) == pytest.approx(1.0)

    def test_k_equals_n_no_pass(self):
        outcomes = [build_replay_outcome("s", [False, False, False])]
        assert compute_pass_at_k(outcomes, 3) == pytest.approx(0.0)

    def test_known_humaneval_formula(self):
        # n=5, c=2, k=3:  1 - C(3,3)/C(5,3) = 1 - 1/10 = 0.9
        outcomes = [build_replay_outcome("s", [True, True, False, False, False])]
        assert compute_pass_at_k(outcomes, 3) == pytest.approx(0.9)

    def test_k_greater_than_n_falls_back_to_pass_rate(self):
        outcomes = [build_replay_outcome("s", [True, False, True])]
        # k > n: report c/n = 2/3
        assert compute_pass_at_k(outcomes, 5) == pytest.approx(2 / 3)

    def test_mean_across_problems(self):
        outcomes = [
            build_replay_outcome("a", [True, True, True]),
            build_replay_outcome("b", [False, False, False]),
        ]
        # pass@1 over 1.0 and 0.0 = 0.5
        assert compute_pass_at_k(outcomes, 1) == pytest.approx(0.5)

    def test_rejects_zero_k(self):
        outcomes = [build_replay_outcome("s", [True])]
        with pytest.raises(ValueError, match="positive"):
            compute_pass_at_k(outcomes, 0)


class TestScorecard:
    def _summary(self, outcomes):
        return summarize_replay_outcomes(outcomes)

    def test_verdict_go_when_above_threshold(self):
        outcomes = [build_replay_outcome("s1", [True, True, True, True, True])]
        sc = build_reliability_scorecard(
            self._summary(outcomes),
            5,
            threshold=0.8,
            regression_tolerance=0.05,
            hallucination_rate=0.0,
            hallucination_max=0.1,
            baseline={"pass_at_k": 1.0},
        )
        assert sc.verdict == Verdict.GO
        assert sc.pass_at_k == pytest.approx(1.0)

    def test_verdict_no_go_on_threshold_and_regression(self):
        outcomes = [build_replay_outcome("s1", [False, False, False, False, False])]
        sc = build_reliability_scorecard(
            self._summary(outcomes),
            5,
            threshold=0.8,
            regression_tolerance=0.05,
            hallucination_rate=0.0,
            hallucination_max=0.1,
            baseline={"pass_at_k": 1.0},
        )
        assert sc.verdict == Verdict.NO_GO

    def test_verdict_no_go_on_hallucination(self):
        outcomes = [build_replay_outcome("s1", [True, True, True, True, True])]
        sc = build_reliability_scorecard(
            self._summary(outcomes),
            5,
            threshold=0.8,
            regression_tolerance=0.05,
            hallucination_rate=0.5,
            hallucination_max=0.1,
            baseline={"pass_at_k": 1.0},
        )
        assert sc.verdict == Verdict.NO_GO

    def test_verdict_conditional_on_threshold_alone(self):
        # n=5, c=2, k=2 → 1 - C(3,2)/C(5,2) = 1 - 0.3 = 0.7. With threshold
        # 0.8 the run fails the bar (CONDITIONAL) but the regression delta
        # vs a baseline of 0.7 is exactly 0 — within tolerance.
        outcomes = [build_replay_outcome("s1", [True, True, False, False, False])]
        sc = build_reliability_scorecard(
            self._summary(outcomes),
            2,
            threshold=0.8,
            regression_tolerance=0.5,
            hallucination_rate=0.0,
            hallucination_max=0.1,
            baseline={"pass_at_k": 0.7},
        )
        assert sc.verdict == Verdict.CONDITIONAL
        assert sc.pass_at_k == pytest.approx(0.7)

    def test_no_baseline_zero_regression_delta(self):
        outcomes = [build_replay_outcome("s1", [True, True, True, True, True])]
        sc = build_reliability_scorecard(
            self._summary(outcomes),
            5,
            threshold=0.8,
            regression_tolerance=0.05,
            hallucination_rate=0.0,
            hallucination_max=0.1,
            baseline=None,
        )
        assert sc.regression_delta == 0.0


class TestRegression:
    def test_signed_delta(self):
        assert regression_delta(0.85, 0.9) == pytest.approx(-0.05)
        assert regression_delta(0.95, 0.9) == pytest.approx(0.05)

    def test_detect_regression_within_tolerance(self):
        r = detect_regression(
            current=0.78,
            baseline={"pass_at_k": 0.8},
            threshold=0.8,
            tolerance=0.05,
        )
        assert r.detected is False  # drop is 0.02, within tolerance

    def test_detect_regression_beyond_tolerance(self):
        r = detect_regression(
            current=0.5,
            baseline={"pass_at_k": 0.9},
            threshold=0.8,
            tolerance=0.05,
        )
        assert r.detected is True
        assert r.delta == pytest.approx(-0.4)

    def test_no_baseline(self):
        r = detect_regression(
            current=0.5,
            baseline=None,
            threshold=0.8,
            tolerance=0.05,
        )
        assert r.detected is False
        assert r.delta == 0.0


class TestThresholdLoader:
    def test_loads_canonical_manifest(self, repo_root: Path):
        cfg = load_evaluation_config(repo_root / ".ai-engineering" / "manifest.yml")
        assert cfg.pass_at_k_k >= 1
        assert 0 <= cfg.pass_at_k_threshold <= 1
        assert cfg.is_blocking is True

    def test_rejects_missing_manifest(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_evaluation_config(tmp_path / "no.yml")

    def test_rejects_manifest_without_evaluation(self, tmp_path: Path):
        bad = tmp_path / "manifest.yml"
        bad.write_text("name: x\n", encoding="utf-8")
        with pytest.raises(ValueError, match="evaluation"):
            load_evaluation_config(bad)


class TestRunner:
    def _write_pack(self, tmp_path: Path) -> Path:
        pack = {
            "version": "1",
            "baseline": {"pass_at_k": 0.6},
            "scenarios": [
                {"id": "scn-a", "k": 3, "grader": "stub", "metadata": {"size": "S"}},
                {"id": "scn-b", "k": 3, "grader": "stub", "metadata": {"size": "S"}},
            ],
        }
        path = tmp_path / "pack.json"
        path.write_text(json.dumps(pack), encoding="utf-8")
        return path

    def test_runs_pack_and_builds_scorecard(self, tmp_path: Path, repo_root: Path):
        pack_path = self._write_pack(tmp_path)

        def trial_runner(scenario, trial_id):
            # scn-a always passes; scn-b passes 1/3 trials
            if scenario["id"] == "scn-a":
                return True
            return trial_id == 0

        cfg = load_evaluation_config(repo_root / ".ai-engineering" / "manifest.yml")
        baseline = load_baseline(pack_path)
        result = run_scenario_pack(
            pack_path,
            config=cfg,
            trial_runner=trial_runner,
            baseline=baseline,
            hallucination_rate=0.0,
        )
        assert result.summary.total_scenarios == 2
        assert result.summary.total_trials == 6
        assert result.summary.total_passed == 4
        assert isinstance(result.scorecard, Scorecard)
        assert result.scorecard.k == cfg.pass_at_k_k
        # Failed scenarios surface in the scorecard
        assert "scn-b" in result.scorecard.failed_scenarios
