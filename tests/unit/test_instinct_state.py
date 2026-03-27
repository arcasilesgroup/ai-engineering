"""Tests for simplified instinct state artifacts from spec-080."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ai_engineering.state.instincts import (
    append_instinct_observation,
    default_instinct_context,
    ensure_instinct_artifacts,
    extract_instincts,
    instinct_context_path,
    instinct_meta_path,
    instinct_observations_path,
    instincts_path,
    maybe_refresh_instinct_context,
)
from ai_engineering.state.io import append_ndjson, read_ndjson_entries
from ai_engineering.state.models import FrameworkEvent, InstinctMeta, InstinctObservation

pytestmark = pytest.mark.unit


def _seed_manifest(tmp_path: Path) -> None:
    path = tmp_path / ".ai-engineering" / "manifest.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("name: demo-project\n", encoding="utf-8")


class TestInstinctArtifacts:
    def test_ensure_instinct_artifacts_creates_canonical_files(self, tmp_path: Path) -> None:
        _seed_manifest(tmp_path)

        ensure_instinct_artifacts(tmp_path)

        assert instinct_observations_path(tmp_path).is_file()
        assert instincts_path(tmp_path).is_file()
        assert instinct_context_path(tmp_path).is_file()
        assert instinct_meta_path(tmp_path).is_file()
        assert default_instinct_context() in instinct_context_path(tmp_path).read_text(
            encoding="utf-8"
        )

    def test_append_instinct_observation_sanitizes_and_prunes_old_entries(
        self, tmp_path: Path
    ) -> None:
        _seed_manifest(tmp_path)
        ensure_instinct_artifacts(tmp_path)

        old = InstinctObservation(
            engine="claude_code",
            kind="tool_start",
            tool="Read",
            outcome="success",
            timestamp=datetime.now(tz=UTC) - timedelta(days=40),
        )
        append_ndjson(instinct_observations_path(tmp_path), old)

        appended = append_instinct_observation(
            tmp_path,
            engine="claude_code",
            hook_event="PostToolUse",
            session_id="session-1",
            data={
                "tool_name": "Bash",
                "tool_input": {"command": 'echo token="local-test-placeholder"'},
                "result": {"message": 'failed: password="super-secret"'},
            },
        )

        assert appended is not None
        entries = read_ndjson_entries(instinct_observations_path(tmp_path), InstinctObservation)
        assert len(entries) == 1
        assert entries[0].tool == "Bash"
        assert "[REDACTED]" in entries[0].detail["input_summary"]
        assert entries[0].outcome == "failure"

    def test_extract_instincts_updates_canonical_store_and_meta(self, tmp_path: Path) -> None:
        _seed_manifest(tmp_path)

        append_instinct_observation(
            tmp_path,
            engine="claude_code",
            hook_event="PreToolUse",
            session_id="session-2",
            data={"tool_name": "Read", "tool_input": {"file_path": "README.md"}},
        )
        append_instinct_observation(
            tmp_path,
            engine="claude_code",
            hook_event="PostToolUse",
            session_id="session-2",
            data={"tool_name": "Bash", "result": {"message": "failed with error"}},
        )
        append_instinct_observation(
            tmp_path,
            engine="claude_code",
            hook_event="PreToolUse",
            session_id="session-2",
            data={"tool_name": "Grep", "tool_input": {"pattern": "TODO"}},
        )
        append_ndjson(
            tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson",
            FrameworkEvent(
                project="demo-project",
                engine="claude_code",
                kind="skill_invoked",
                outcome="success",
                component="hook.telemetry-skill",
                correlationId="corr-1",
                sessionId="session-2",
                detail={"skill": "ai-dispatch"},
            ),
        )
        append_ndjson(
            tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson",
            FrameworkEvent(
                project="demo-project",
                engine="claude_code",
                kind="agent_dispatched",
                outcome="success",
                component="hook.observe",
                correlationId="corr-2",
                sessionId="session-2",
                detail={"agent": "ai-build"},
            ),
        )

        assert extract_instincts(tmp_path) is True

        instincts = instincts_path(tmp_path).read_text(encoding="utf-8")
        meta = InstinctMeta.model_validate(json.loads(instinct_meta_path(tmp_path).read_text()))
        assert "Read -> Grep" in instincts
        assert "Bash -> Grep" in instincts
        assert "ai-dispatch -> ai-build" in instincts
        assert meta.pending_context_refresh is True
        assert meta.last_extracted_at is not None

    def test_maybe_refresh_instinct_context_writes_bounded_context(self, tmp_path: Path) -> None:
        _seed_manifest(tmp_path)
        ensure_instinct_artifacts(tmp_path)
        instincts_path(tmp_path).write_text(
            """
schemaVersion: "1.0"
toolSequences:
  - key: "Read -> Grep"
    guidance: "Common tool sequence: Read -> Grep."
    evidenceCount: 8
    lastSeenAt: "2026-03-27T12:00:00Z"
  - key: "Read -> Edit"
    guidance: "Common tool sequence: Read -> Edit."
    evidenceCount: 7
    lastSeenAt: "2026-03-27T12:00:00Z"
errorRecoveries:
  - key: "Bash -> Read"
    guidance: "After Bash errors, Read is a common recovery step."
    evidenceCount: 6
    lastSeenAt: "2026-03-27T12:00:00Z"
skillAgentPreferences:
  - key: "ai-dispatch -> ai-build"
    guidance: "Within ai-dispatch, ai-build is the most common dispatched agent."
    evidenceCount: 5
    lastSeenAt: "2026-03-27T12:00:00Z"
  - key: "ai-plan -> ai-guide"
    guidance: "Within ai-plan, ai-guide is the most common dispatched agent."
    evidenceCount: 4
    lastSeenAt: "2026-03-27T12:00:00Z"
  - key: "ai-debug -> ai-build"
    guidance: "Within ai-debug, ai-build is the most common dispatched agent."
    evidenceCount: 3
    lastSeenAt: "2026-03-27T12:00:00Z"
""".strip()
            + "\n",
            encoding="utf-8",
        )
        meta = InstinctMeta(pendingContextRefresh=True)
        instinct_meta_path(tmp_path).write_text(
            meta.model_dump_json(by_alias=True, indent=2) + "\n",
            encoding="utf-8",
        )

        refreshed = maybe_refresh_instinct_context(tmp_path)

        content = instinct_context_path(tmp_path).read_text(encoding="utf-8")
        updated_meta = InstinctMeta.model_validate(
            json.loads(instinct_meta_path(tmp_path).read_text())
        )
        assert refreshed is True
        assert content.count("- ") <= 5
        assert "Read -> Grep" in content
        assert updated_meta.pending_context_refresh is False
        assert updated_meta.last_context_generated_at is not None
