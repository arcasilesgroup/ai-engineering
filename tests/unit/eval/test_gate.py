"""spec-119 T-4.7 — /ai-eval-gate runtime tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_engineering.eval.gate import (
    filesystem_trial_runner,
    mode_check,
    mode_enforce,
    mode_report,
    run_gate,
    to_json,
)
from ai_engineering.eval.scorecard import Verdict
from ai_engineering.eval.thresholds import ManifestEvaluationConfig

pytestmark = pytest.mark.eval


def _config(
    *,
    threshold: float = 0.8,
    tolerance: float = 0.05,
    enforcement: str = "blocking",
    packs: tuple[str, ...] = (".ai-engineering/evals/baseline.json",),
) -> ManifestEvaluationConfig:
    return ManifestEvaluationConfig(
        pass_at_k_k=3,
        pass_at_k_threshold=threshold,
        hallucination_rate_max=0.1,
        regression_tolerance=tolerance,
        scenario_packs=packs,
        enforcement=enforcement,
    )


def _write_pack(project_root: Path, *, pass_all: bool, with_baseline: bool = True) -> Path:
    evals_dir = project_root / ".ai-engineering" / "evals"
    evals_dir.mkdir(parents=True, exist_ok=True)
    pack = {
        "version": "1",
        **({"baseline": {"pass_at_k": 0.6}} if with_baseline else {}),
        "scenarios": [
            {"id": "scn-1", "k": 3, "metadata": {"size": "S"}},
            {"id": "scn-2", "k": 3, "metadata": {"size": "S"}},
        ],
    }
    path = evals_dir / "baseline.json"
    path.write_text(json.dumps(pack), encoding="utf-8")
    return path


class TestRunGate:
    def test_all_pass_returns_go(self, tmp_path: Path):
        _write_pack(tmp_path, pass_all=True)
        outcome = run_gate(tmp_path, trial_runner=lambda *_: True, config=_config(threshold=0.5))
        assert outcome.verdict == Verdict.GO
        assert outcome.exit_code == 0
        assert len(outcome.scorecards) == 1

    def test_all_fail_returns_no_go_when_baseline_above_threshold(self, tmp_path: Path):
        _write_pack(tmp_path, pass_all=False)
        outcome = run_gate(
            tmp_path,
            trial_runner=lambda *_: False,
            config=_config(threshold=0.8, tolerance=0.05),
        )
        # baseline 0.6, current 0.0, drop = 0.6 > tolerance 0.05 → NO_GO
        assert outcome.verdict == Verdict.NO_GO
        assert outcome.exit_code == 1

    def test_advisory_enforcement_never_exits_nonzero(self, tmp_path: Path):
        _write_pack(tmp_path, pass_all=False)
        outcome = run_gate(
            tmp_path,
            trial_runner=lambda *_: False,
            config=_config(threshold=0.8, tolerance=0.05, enforcement="advisory"),
        )
        assert outcome.verdict == Verdict.NO_GO
        assert outcome.exit_code == 0  # advisory: never blocks

    def test_missing_pack_records_skip_reason(self, tmp_path: Path):
        # No pack written
        outcome = run_gate(
            tmp_path,
            trial_runner=lambda *_: True,
            config=_config(packs=("evals/missing.json",)),
        )
        assert outcome.verdict == Verdict.SKIPPED
        assert any("missing pack" in r for r in outcome.skipped_reasons)


class TestModeWrappers:
    def test_mode_check_returns_dict(self, tmp_path: Path):
        _write_pack(tmp_path, pass_all=True)
        result = mode_check(tmp_path, trial_runner=lambda *_: True, config=_config(threshold=0.5))
        assert "verdict" in result
        assert "scorecards" in result
        assert isinstance(result["scorecards"], list)

    def test_mode_report_returns_markdown(self, tmp_path: Path):
        _write_pack(tmp_path, pass_all=True)
        report = mode_report(tmp_path, trial_runner=lambda *_: True, config=_config(threshold=0.5))
        assert "verdict" in report.lower()
        assert "GO" in report

    def test_mode_enforce_skip_short_circuits(self, tmp_path: Path):
        _write_pack(tmp_path, pass_all=False)
        exit_code, outcome = mode_enforce(
            tmp_path,
            trial_runner=lambda *_: False,
            config=_config(),
            skip=True,
            skip_reason="manual override",
        )
        assert exit_code == 0
        assert outcome.verdict == Verdict.SKIPPED
        assert outcome.skipped_reasons == ("manual override",)


class TestJSONRender:
    def test_to_json_round_trip(self, tmp_path: Path):
        _write_pack(tmp_path, pass_all=True)
        outcome = run_gate(tmp_path, trial_runner=lambda *_: True, config=_config(threshold=0.5))
        text = to_json(outcome)
        parsed = json.loads(text)
        assert parsed["verdict"] == "GO"


class TestFilesystemRunner:
    def test_grades_existing_artifact(self, tmp_path: Path):
        target = tmp_path / "specs" / "spec-x.md"
        target.parent.mkdir(parents=True)
        target.write_text("# spec-x\n\n## acceptance\nyes", encoding="utf-8")
        runner = filesystem_trial_runner(tmp_path)
        scenario = {
            "id": "scn",
            "metadata": {
                "expected_path": "specs/spec-x.md",
                "expected_content_substring": "## acceptance",
            },
        }
        assert runner(scenario, 0) is True

    def test_fails_when_substring_missing(self, tmp_path: Path):
        target = tmp_path / "specs" / "spec-x.md"
        target.parent.mkdir(parents=True)
        target.write_text("# different content", encoding="utf-8")
        runner = filesystem_trial_runner(tmp_path)
        scenario = {
            "id": "scn",
            "metadata": {
                "expected_path": "specs/spec-x.md",
                "expected_content_substring": "## acceptance",
            },
        }
        assert runner(scenario, 0) is False

    def test_forbidden_path_blocks(self, tmp_path: Path):
        forbidden = tmp_path / "secrets.env"
        forbidden.write_text("KEY=val", encoding="utf-8")
        runner = filesystem_trial_runner(tmp_path)
        scenario = {"id": "scn", "metadata": {"forbidden_path": "secrets.env"}}
        assert runner(scenario, 0) is False
