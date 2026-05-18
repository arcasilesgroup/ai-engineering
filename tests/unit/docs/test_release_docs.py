"""Drift tests for release authority documentation."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CLI_REFERENCE = PROJECT_ROOT / ".ai-engineering/reference/cli-reference.md"
TEMPLATE_CLI_REFERENCE = (
    PROJECT_ROOT / "src/ai_engineering/templates/.ai-engineering/reference/cli-reference.md"
)


def test_release_cli_reference_documents_current_release_spine() -> None:
    required_phrases = [
        "ai-eng release <VERSION> is the sole authority",
        "tag-triggered Release workflow",
        "TestPyPI before PyPI",
        "Trusted Publishing",
        "provenance packet",
        "protected recovery dispatch",
        "legacy automated release tooling and manual CI commit-back are hard-removed",
    ]

    for path in (CLI_REFERENCE, TEMPLATE_CLI_REFERENCE):
        text = path.read_text(encoding="utf-8")
        for phrase in required_phrases:
            assert phrase in text, f"{path} is missing {phrase!r}"
        assert "semantic-release creates tags" not in text
        assert "manual CI commit-back path" not in text


def test_release_cli_reference_template_matches_source_reference() -> None:
    assert CLI_REFERENCE.read_text(encoding="utf-8") == TEMPLATE_CLI_REFERENCE.read_text(
        encoding="utf-8"
    )
