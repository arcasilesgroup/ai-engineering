"""Spec-146 caller-inventory artifact contract."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = PROJECT_ROOT / ".ai-engineering" / "specs" / "spec-146-caller-inventory.md"
SCRIPT = PROJECT_ROOT / "tools" / "caller_inventory.py"

REQUIRED_ROWS = (
    "agentsview.py",
    "outbox.py",
    "governance/policy_engine.py",
    "cli_ui_skill_ref.py",
    "trace_context.py",
    "capabilities.py",
    "context_packs.py",
    "relevance.py",
    "StateService",
    "DurableStateRepository",
    "installer/mechanisms/__init__.py",
)


def test_caller_inventory_artifact_exists_and_covers_candidates() -> None:
    assert SCRIPT.is_file()
    assert ARTIFACT.is_file()
    text = ARTIFACT.read_text(encoding="utf-8")

    assert "# Spec 146 Caller Inventory" in text
    assert "rtk .venv/bin/python tools/caller_inventory.py" in text
    for row in REQUIRED_ROWS:
        assert f"`{row}`" in text


def test_caller_inventory_records_delete_preserve_and_split_decisions() -> None:
    text = ARTIFACT.read_text(encoding="utf-8")

    assert "test-only/deleted | Hard-delete" in text
    assert "production/hook-parity | Preserve" in text
    assert "production/validator | Preserve" in text
    assert "production/facade | Partially flatten" in text
    assert "production/registry | Split with thin re-export" in text


def test_caller_inventory_is_timestamp_free() -> None:
    text = ARTIFACT.read_text(encoding="utf-8")

    assert "Generated at" not in text
    assert "Timestamp" not in text
    assert "/Users/" not in text
