"""spec-119 T-1.8 -- emit_eval_* helpers round-trip through the audit chain.

Validates:
- each helper writes exactly one valid eval_run event;
- the canonical sub-operations land in detail.operation;
- numeric required fields appear with their expected types and bounds;
- verdict-aware emit_eval_gated maps verdict -> outcome correctly;
- rejects unknown operations and unknown verdicts (fail-closed).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.eval


def _read_events(ndjson: Path) -> list[dict]:
    if not ndjson.exists():
        return []
    out: list[dict] = []
    for line in ndjson.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


class TestEmitEvalStarted:
    def test_writes_single_eval_run_event(self, lib_obs, project_root: Path, ndjson_path: Path):
        lib_obs.emit_eval_started(
            project_root,
            component="ai-evaluator",
            scenario_pack="baseline.json",
            correlation_id="corr-1",
        )
        events = _read_events(ndjson_path)
        assert len(events) == 1
        e = events[0]
        assert e["kind"] == "eval_run"
        assert e["component"] == "ai-evaluator"
        assert e["correlationId"] == "corr-1"
        assert e["detail"]["operation"] == "eval_started"
        assert e["detail"]["scenario_pack"] == "baseline.json"


class TestEmitScenarioExecuted:
    def test_passes_through_pass_and_trial_id(self, lib_obs, project_root: Path, ndjson_path: Path):
        lib_obs.emit_scenario_executed(
            project_root,
            component="ai-evaluator",
            scenario_id="scn-1",
            trial_id=3,
            pass_=True,
            duration_ms=12.5,
        )
        e = _read_events(ndjson_path)[-1]
        assert e["detail"]["operation"] == "scenario_executed"
        assert e["detail"]["scenario_id"] == "scn-1"
        assert e["detail"]["trial_id"] == 3
        assert e["detail"]["pass"] is True
        assert e["detail"]["duration_ms"] == 12.5

    def test_omits_duration_when_not_provided(self, lib_obs, project_root: Path, ndjson_path: Path):
        lib_obs.emit_scenario_executed(
            project_root,
            component="ai-evaluator",
            scenario_id="scn-2",
            trial_id=0,
            pass_=False,
        )
        e = _read_events(ndjson_path)[-1]
        assert "duration_ms" not in e["detail"]


class TestEmitPassAtKComputed:
    def test_records_score_and_counts(self, lib_obs, project_root: Path, ndjson_path: Path):
        lib_obs.emit_pass_at_k_computed(
            project_root,
            component="ai-evaluator",
            k=5,
            pass_count=4,
            total=5,
            score=0.8,
        )
        e = _read_events(ndjson_path)[-1]
        assert e["detail"]["operation"] == "pass_at_k_computed"
        assert e["detail"]["k"] == 5
        assert e["detail"]["pass_count"] == 4
        assert e["detail"]["total"] == 5
        assert e["detail"]["score"] == pytest.approx(0.8)


class TestEmitHallucinationRateComputed:
    def test_records_rate(self, lib_obs, project_root: Path, ndjson_path: Path):
        lib_obs.emit_hallucination_rate_computed(
            project_root,
            component="ai-evaluator",
            rate=0.05,
            total_assertions=20,
            failed_assertions=1,
        )
        e = _read_events(ndjson_path)[-1]
        assert e["detail"]["operation"] == "hallucination_rate_computed"
        assert e["detail"]["rate"] == pytest.approx(0.05)
        assert e["detail"]["total_assertions"] == 20
        assert e["detail"]["failed_assertions"] == 1


class TestEmitRegressionDetected:
    def test_force_outcome_failure(self, lib_obs, project_root: Path, ndjson_path: Path):
        lib_obs.emit_regression_detected(
            project_root,
            component="ai-eval-gate",
            delta=-0.1,
            threshold=0.8,
            tolerance=0.05,
        )
        e = _read_events(ndjson_path)[-1]
        assert e["detail"]["operation"] == "regression_detected"
        assert e["outcome"] == "failure"
        assert e["detail"]["delta"] == pytest.approx(-0.1)


class TestEmitRegressionCleared:
    def test_records_delta(self, lib_obs, project_root: Path, ndjson_path: Path):
        lib_obs.emit_regression_cleared(
            project_root,
            component="ai-eval-gate",
            delta=0.02,
        )
        e = _read_events(ndjson_path)[-1]
        assert e["detail"]["operation"] == "regression_cleared"
        assert e["detail"]["delta"] == pytest.approx(0.02)


class TestEmitEvalGated:
    @pytest.mark.parametrize(
        ("verdict", "expected_outcome"),
        [
            ("GO", "success"),
            ("CONDITIONAL", "success"),
            ("NO_GO", "failure"),
            ("SKIPPED", "degraded"),
        ],
    )
    def test_verdict_outcome_mapping(
        self,
        lib_obs,
        project_root: Path,
        ndjson_path: Path,
        verdict: str,
        expected_outcome: str,
    ):
        lib_obs.emit_eval_gated(
            project_root,
            component="ai-eval-gate",
            verdict=verdict,
            regression_delta_vs_baseline=0.0,
            failed_scenarios=["scn-x"] if verdict == "NO_GO" else [],
            reason="manual skip" if verdict == "SKIPPED" else None,
        )
        e = _read_events(ndjson_path)[-1]
        assert e["detail"]["operation"] == "eval_gated"
        assert e["detail"]["verdict"] == verdict
        assert e["outcome"] == expected_outcome

    def test_rejects_unknown_verdict(self, lib_obs, project_root: Path):
        with pytest.raises(ValueError, match="eval_gated verdict"):
            lib_obs.emit_eval_gated(
                project_root,
                component="ai-eval-gate",
                verdict="MAYBE",
            )


class TestEmitBaselineUpdated:
    def test_records_prev_and_new(self, lib_obs, project_root: Path, ndjson_path: Path):
        lib_obs.emit_baseline_updated(
            project_root,
            component="ai-eval-gate",
            prev_pass_at_k=0.6,
            new_pass_at_k=0.85,
        )
        e = _read_events(ndjson_path)[-1]
        assert e["detail"]["operation"] == "baseline_updated"
        assert e["detail"]["prev_pass_at_k"] == pytest.approx(0.6)
        assert e["detail"]["new_pass_at_k"] == pytest.approx(0.85)


class TestUnknownOperationRejection:
    def test_internal_helper_rejects_bogus_operation(self, lib_obs, project_root: Path):
        with pytest.raises(ValueError, match="eval_run operation"):
            lib_obs._emit_eval_run(
                project_root,
                operation="not_a_real_op",
                component="ai-evaluator",
            )


class TestHashChainIntact:
    def test_chain_links_subsequent_events(self, lib_obs, project_root: Path, ndjson_path: Path):
        lib_obs.emit_eval_started(
            project_root,
            component="ai-evaluator",
            scenario_pack="baseline.json",
        )
        lib_obs.emit_pass_at_k_computed(
            project_root,
            component="ai-evaluator",
            k=5,
            pass_count=5,
            total=5,
            score=1.0,
        )
        events = _read_events(ndjson_path)
        assert len(events) == 2
        assert "prev_event_hash" in events[1]
        # Anchor record may be empty/None; second event must reference previous.
        assert events[1]["prev_event_hash"]
