"""Tests for the ai-eng eval CLI surface (P2.1 / 2026-05-04 gap closure).

The eval module already had a runtime; the harness audit flagged the missing
Typer wiring as the prerequisite for the new CI workflow.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app
from ai_engineering.eval.gate import GateOutcome
from ai_engineering.eval.scorecard import Verdict


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def app():
    return create_app()


def _make_outcome(verdict: Verdict, *, enforcement: str = "blocking") -> GateOutcome:
    return GateOutcome(
        verdict=verdict,
        scorecards=(),
        pack_results=(),
        skipped_reasons=(),
        enforcement=enforcement,
    )


def test_eval_check_emits_json(runner: CliRunner, app, tmp_path: Path) -> None:
    """check --json emits the dict and exits 0 even on NO_GO."""
    (tmp_path / ".ai-engineering").mkdir()
    fake = {
        "verdict": "NO_GO",
        "exit_code": 1,
        "enforcement": "blocking",
        "skipped_reasons": [],
        "scorecards": [],
        "pack_paths": [],
    }
    with patch("ai_engineering.cli_commands.eval_cmd.mode_check", return_value=fake) as mock_check:
        result = runner.invoke(
            app,
            ["eval", "check", "--target", str(tmp_path), "--json"],
        )
    assert result.exit_code == 0, result.output
    assert mock_check.called
    payload = json.loads(result.output)
    assert payload["verdict"] == "NO_GO"


def test_eval_check_human_text(runner: CliRunner, app, tmp_path: Path) -> None:
    """Default no-json renders human-readable verdict text."""
    (tmp_path / ".ai-engineering").mkdir()
    fake = {
        "verdict": "GO",
        "exit_code": 0,
        "enforcement": "blocking",
        "skipped_reasons": [],
        "scorecards": [],
        "pack_paths": [],
    }
    with patch("ai_engineering.cli_commands.eval_cmd.mode_check", return_value=fake):
        result = runner.invoke(app, ["eval", "check", "--target", str(tmp_path)])
    assert result.exit_code == 0
    assert "verdict: GO" in result.output


def test_eval_report_emits_markdown(runner: CliRunner, app, tmp_path: Path) -> None:
    (tmp_path / ".ai-engineering").mkdir()
    with patch(
        "ai_engineering.cli_commands.eval_cmd.mode_report",
        return_value="# Eval Gate verdict: GO\n",
    ):
        result = runner.invoke(app, ["eval", "report", "--target", str(tmp_path)])
    assert result.exit_code == 0
    assert "Eval Gate" in result.output


def test_eval_enforce_returns_zero_on_go(runner: CliRunner, app, tmp_path: Path) -> None:
    (tmp_path / ".ai-engineering").mkdir()
    outcome = _make_outcome(Verdict.GO)
    with patch("ai_engineering.cli_commands.eval_cmd.mode_enforce", return_value=(0, outcome)):
        result = runner.invoke(app, ["eval", "enforce", "--target", str(tmp_path)])
    assert result.exit_code == 0
    assert "verdict: GO" in result.output


def test_eval_enforce_returns_one_on_nogo(runner: CliRunner, app, tmp_path: Path) -> None:
    """Blocking enforcement + NO_GO verdict yields process exit 1."""
    (tmp_path / ".ai-engineering").mkdir()
    outcome = _make_outcome(Verdict.NO_GO)
    with patch("ai_engineering.cli_commands.eval_cmd.mode_enforce", return_value=(1, outcome)):
        result = runner.invoke(app, ["eval", "enforce", "--target", str(tmp_path)])
    assert result.exit_code == 1


def test_eval_enforce_skip_requires_reason(runner: CliRunner, app, tmp_path: Path) -> None:
    """skip without skip-reason must fail fast for audit traceability."""
    (tmp_path / ".ai-engineering").mkdir()
    result = runner.invoke(app, ["eval", "enforce", "--target", str(tmp_path), "--skip"])
    assert result.exit_code == 2
    assert "skip-reason" in result.output


def test_eval_enforce_skip_with_reason(runner: CliRunner, app, tmp_path: Path) -> None:
    """skip with reason short-circuits with SKIPPED verdict, exit 0."""
    (tmp_path / ".ai-engineering").mkdir()
    skipped_outcome = _make_outcome(Verdict.SKIPPED)
    with patch(
        "ai_engineering.cli_commands.eval_cmd.mode_enforce",
        return_value=(0, skipped_outcome),
    ):
        result = runner.invoke(
            app,
            [
                "eval",
                "enforce",
                "--target",
                str(tmp_path),
                "--skip",
                "--skip-reason",
                "manual override for hot-fix branch",
            ],
        )
    assert result.exit_code == 0
    assert "verdict: SKIPPED" in result.output


def test_eval_workflow_yaml_lints() -> None:
    """The new GitHub Actions workflow must parse as YAML and have one job."""
    import yaml

    repo = Path(__file__).resolve().parents[3]
    path = repo / ".github" / "workflows" / "eval-gate.yml"
    assert path.is_file(), f"missing workflow file: {path}"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    on_block = data.get("on") or data.get(True)
    assert on_block is not None, "missing on trigger block"
    assert "pull_request" in on_block
    assert "push" in on_block
    assert list(data["jobs"]) == ["eval-gate"], "expected exactly one job"
    steps = data["jobs"]["eval-gate"]["steps"]
    cmds = [s.get("run", "") for s in steps]
    joined = "\n".join(cmds)
    assert "ai-eng eval check" in joined
    assert "ai-eng eval enforce" in joined
