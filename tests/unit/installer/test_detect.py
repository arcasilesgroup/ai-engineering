"""Unit tests for DetectPhase."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.installer.phases import InstallContext, InstallMode
from ai_engineering.installer.phases.detect import DetectPhase

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _ctx(tmp_path: Path, mode: InstallMode = InstallMode.INSTALL) -> InstallContext:
    return InstallContext(
        target=tmp_path,
        mode=mode,
        providers=["claude_code"],
        vcs_provider="github",
        stacks=["python"],
        ides=["terminal"],
    )


# ---------------------------------------------------------------------------
# DetectPhase
# ---------------------------------------------------------------------------


class TestDetectPhase:
    def test_detects_missing_tools(self, tmp_path: Path) -> None:
        """Missing tools appear as informational skip actions."""
        phase = DetectPhase()
        with patch("shutil.which", return_value=None):
            plan = phase.plan(_ctx(tmp_path))
        tool_actions = [
            a
            for a in plan.actions
            if "tool check" in a.rationale.lower() or "not found" in a.rationale.lower()
        ]
        assert len(tool_actions) >= 4  # One per tool in _CHECKED_TOOLS
        rationales = " ".join(a.rationale for a in tool_actions)
        assert "gitleaks" in rationales
        assert "ruff" in rationales

    def test_detects_legacy_path(self, tmp_path: Path) -> None:
        """Legacy context/ path detected and migration planned."""
        phase = DetectPhase()
        legacy = tmp_path / ".ai-engineering" / "context" / "product"
        legacy.mkdir(parents=True)
        (legacy / "test.md").write_text("test")

        plan = phase.plan(_ctx(tmp_path))
        migration_actions = [
            a
            for a in plan.actions
            if a.action_type == "delete"
            or "migration" in a.rationale.lower()
            or "legacy" in a.rationale.lower()
        ]
        assert len(migration_actions) > 0

    def test_verify_always_passes(self, tmp_path: Path) -> None:
        """Detect phase verify always passes."""
        phase = DetectPhase()
        plan = phase.plan(_ctx(tmp_path))
        result = phase.execute(plan, _ctx(tmp_path))
        verdict = phase.verify(result, _ctx(tmp_path))
        assert verdict.passed
