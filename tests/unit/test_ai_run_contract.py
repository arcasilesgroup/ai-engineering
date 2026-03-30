"""Contract checks for the canonical ai-run skill and orchestrator surfaces."""

from __future__ import annotations

from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[2]
_AI_RUN_DIR = _ROOT / ".claude" / "skills" / "ai-run"
_AI_RUN_AGENT = _ROOT / ".claude" / "agents" / "ai-run-orchestrator.md"
_MANIFEST = _ROOT / ".ai-engineering" / "manifest.yml"


def test_ai_run_skill_exists() -> None:
    assert (_AI_RUN_DIR / "SKILL.md").is_file()


def test_ai_run_reference_set_exists() -> None:
    expected = {
        "architecture.md",
        "phases.md",
        "provider-matrix.md",
        "run-manifest.md",
    }
    actual = {path.name for path in (_AI_RUN_DIR / "references").iterdir() if path.is_file()}
    assert actual >= expected


def test_ai_run_handler_set_exists() -> None:
    expected = {
        "phase-deliver.md",
        "phase-execute.md",
        "phase-intake.md",
        "phase-item-plan.md",
        "phase-orchestrate.md",
    }
    actual = {path.name for path in (_AI_RUN_DIR / "handlers").iterdir() if path.is_file()}
    assert actual == expected


def test_ai_run_orchestrator_exists() -> None:
    assert _AI_RUN_AGENT.is_file()


def test_manifest_registers_ai_run_and_agent() -> None:
    data = yaml.safe_load(_MANIFEST.read_text(encoding="utf-8"))
    assert "ai-run" in data["skills"]["registry"]
    assert "run-orchestrator" in data["agents"]["names"]
