"""Tests for canonical skill and agent event emitters."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.state.io import read_ndjson_entries
from ai_engineering.state.models import FrameworkEvent
from ai_engineering.state.observability import (
    emit_agent_dispatched,
    emit_skill_invoked,
    framework_events_path,
)

pytestmark = pytest.mark.unit


def _write_manifest(tmp_path: Path) -> None:
    manifest_path = tmp_path / ".ai-engineering" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("name: demo-project\n", encoding="utf-8")


class TestCanonicalEmitters:
    def test_claude_code_skill_invoked_emits_success(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path)

        entry = emit_skill_invoked(
            tmp_path,
            engine="claude_code",
            skill_name="brainstorm",
            component="hook.telemetry-skill",
            source="hook",
            session_id="session-1",
            trace_id="trace-1",
        )

        assert entry.outcome == "success"
        assert entry.detail["skill"] == "ai-brainstorm"
        stored = read_ndjson_entries(framework_events_path(tmp_path), FrameworkEvent)
        assert stored[0].engine == "claude_code"
        assert stored[0].kind == "skill_invoked"

    def test_github_copilot_agent_dispatch_emits_success(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path)

        entry = emit_agent_dispatched(
            tmp_path,
            engine="github_copilot",
            agent_name="Build",
            component="hook.copilot-agent",
            source="hook",
            session_id="session-2",
            trace_id="trace-2",
        )

        assert entry.outcome == "success"
        assert entry.detail["agent"] == "ai-build"
        stored = read_ndjson_entries(framework_events_path(tmp_path), FrameworkEvent)
        assert stored[0].engine == "github_copilot"
        assert stored[0].kind == "agent_dispatched"

    def test_codex_skill_invoked_degrades_when_host_metadata_is_missing(
        self, tmp_path: Path
    ) -> None:
        _write_manifest(tmp_path)

        entry = emit_skill_invoked(
            tmp_path,
            engine="codex",
            skill_name="dispatch",
            component="bridge.codex",
            source="compat",
        )

        assert entry.outcome == "degraded"
        assert entry.detail["degraded_reason"] == "missing-host-metadata"
        assert entry.detail["missing_fields"] == ["sessionId", "traceId"]

    def test_gemini_agent_dispatch_succeeds_with_native_hooks(self, tmp_path: Path) -> None:
        """Gemini has native hooks (spec-087) so missing host metadata no longer degrades."""
        _write_manifest(tmp_path)

        entry = emit_agent_dispatched(
            tmp_path,
            engine="gemini",
            agent_name="plan",
            component="bridge.gemini",
            source="compat",
        )

        assert entry.outcome == "success"
        assert entry.detail["agent"] == "ai-plan"
        assert "missing_fields" not in entry.detail
