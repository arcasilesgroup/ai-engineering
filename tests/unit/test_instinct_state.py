"""Tests for simplified instinct state artifacts (v2 schema, spec-090)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ai_engineering.state.instincts import (
    append_instinct_observation,
    ensure_instinct_artifacts,
    extract_instincts,
    instinct_meta_path,
    instinct_observations_path,
    instincts_path,
)
from ai_engineering.state.io import append_ndjson, read_ndjson_entries
from ai_engineering.state.models import FrameworkEvent, InstinctMeta, InstinctObservation


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
        assert instinct_meta_path(tmp_path).is_file()

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
                kind="skill_invoked",
                outcome="success",
                component="hook.telemetry-skill",
                correlationId="corr-1",
                sessionId="session-2",
                detail={"skill": "ai-code"},
            ),
        )

        assert extract_instincts(tmp_path) is True

        instincts_content = instincts_path(tmp_path).read_text(encoding="utf-8")
        meta = InstinctMeta.model_validate(json.loads(instinct_meta_path(tmp_path).read_text()))
        # v2: recoveries contain error recovery patterns
        assert "Bash -> Grep" in instincts_content
        # v2: workflows contain skill sequence patterns
        assert "ai-dispatch -> ai-code" in instincts_content
        assert meta.last_extracted_at is not None
        # v2: no skillAgentPreferences in output
        assert "skillAgentPreferences" not in instincts_content

    def test_v2_schema_in_default_document(self, tmp_path: Path) -> None:
        _seed_manifest(tmp_path)
        ensure_instinct_artifacts(tmp_path)

        import yaml

        doc = yaml.safe_load(instincts_path(tmp_path).read_text(encoding="utf-8"))
        assert doc["schemaVersion"] == "2.0"
        assert "corrections" in doc
        assert "recoveries" in doc
        assert "workflows" in doc
        assert "toolSequences" not in doc
        assert "errorRecoveries" not in doc

    def test_v1_migration_on_load(self, tmp_path: Path) -> None:
        _seed_manifest(tmp_path)
        ensure_instinct_artifacts(tmp_path)
        # Write a v1-style document
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
    evidenceCount: 3
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
""".strip()
            + "\n",
            encoding="utf-8",
        )

        from ai_engineering.state.instincts import load_instincts_document

        doc = load_instincts_document(tmp_path)
        assert doc["schemaVersion"] == "2.0"
        assert "corrections" in doc
        assert "recoveries" in doc
        assert "workflows" in doc
        # Only Read -> Grep had evidenceCount >= 5, so only it migrates
        assert len(doc["workflows"]) == 1
        assert doc["workflows"][0]["key"] == "Read -> Grep"
        assert "toolSequences" not in doc
        assert "errorRecoveries" not in doc
        assert "skillAgentPreferences" not in doc

    def test_append_returns_none_when_tool_name_empty(self, tmp_path: Path) -> None:
        _seed_manifest(tmp_path)
        result = append_instinct_observation(
            tmp_path,
            engine="claude_code",
            hook_event="PostToolUse",
            session_id="session-x",
            data={"tool_name": "", "result": {"message": "ok"}},
        )
        assert result is None

    def test_append_returns_none_when_tool_name_missing(self, tmp_path: Path) -> None:
        _seed_manifest(tmp_path)
        result = append_instinct_observation(
            tmp_path,
            engine="claude_code",
            hook_event="PostToolUse",
            session_id="session-x",
            data={"result": {"message": "ok"}},
        )
        assert result is None

    def test_derive_outcome_failure_from_error_key(self, tmp_path: Path) -> None:
        _seed_manifest(tmp_path)
        obs = append_instinct_observation(
            tmp_path,
            engine="claude_code",
            hook_event="PostToolUse",
            session_id="session-err",
            data={"tool_name": "Bash", "error": "command failed"},
        )
        assert obs is not None
        assert obs.outcome == "failure"

    def test_coerce_text_with_list_and_dict_without_output_keys(self, tmp_path: Path) -> None:
        from ai_engineering.state.instincts import _coerce_text

        assert "item1" in _coerce_text(["item1", "item2"])
        result = _coerce_text({"custom_key": "value"})
        assert "fields=" in result

    def test_summarize_mapping_fallback_to_fields(self, tmp_path: Path) -> None:
        from ai_engineering.state.instincts import _summarize_mapping

        result = _summarize_mapping({"alpha": None, "beta": None}, keys=("alpha", "beta"))
        assert result is not None
        assert "fields=" in result

    def test_extract_session_id_from_alternate_key(self) -> None:
        from ai_engineering.state.instincts import _extract_session_id

        assert _extract_session_id({"sessionId": "abc"}) == "abc"
        assert _extract_session_id({"session_id": "def"}) == "def"
        assert _extract_session_id({}) is None

    def test_coerce_mapping_with_json_string(self) -> None:
        from ai_engineering.state.instincts import _coerce_mapping

        assert _coerce_mapping('{"key": "val"}') == {"key": "val"}
        assert _coerce_mapping("not json") == {}
        assert _coerce_mapping('"just a string"') == {}
        assert _coerce_mapping(42) == {}

    def test_json_serializer_raises_for_unknown_types(self) -> None:
        import pytest

        from ai_engineering.state.instincts import _json_serializer

        _json_serializer(datetime.now(tz=UTC))  # should not raise
        with pytest.raises(TypeError, match="not JSON serializable"):
            _json_serializer(set())

    def test_detect_skill_workflows_no_events_file(self, tmp_path: Path) -> None:
        from ai_engineering.state.instincts import _detect_skill_workflows

        _seed_manifest(tmp_path)
        result = _detect_skill_workflows(tmp_path)
        assert len(result) == 0

    def test_detect_skill_workflows_no_skill_events(self, tmp_path: Path) -> None:
        from ai_engineering.state.instincts import _detect_skill_workflows

        _seed_manifest(tmp_path)
        events_path = tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson"
        events_path.parent.mkdir(parents=True, exist_ok=True)
        append_ndjson(
            events_path,
            FrameworkEvent(
                project="demo",
                engine="claude_code",
                kind="agent_dispatched",
                outcome="success",
                component="agent.build",
                correlationId="corr-no-skill",
                sessionId="session-no-skill",
            ),
        )
        result = _detect_skill_workflows(tmp_path)
        assert len(result) == 0

    def test_merge_counter_updates_existing_entries(self, tmp_path: Path) -> None:
        from collections import Counter

        from ai_engineering.state.instincts import _merge_counter

        target: list[dict[str, Any]] = [
            {"key": "Read -> Edit", "evidenceCount": 3, "lastSeenAt": "2026-01-01T00:00:00Z"},
        ]
        counts: Counter[str] = Counter({"Read -> Edit": 2, "Bash -> Read": 1})
        _merge_counter(
            target,
            counts,
            builder=lambda k, c, t: {"key": k, "evidenceCount": c, "lastSeenAt": t},
        )
        assert len(target) == 2
        existing = next(e for e in target if e["key"] == "Read -> Edit")
        assert existing["evidenceCount"] == 5

    def test_merge_counter_skips_zero_counts(self) -> None:
        from collections import Counter

        from ai_engineering.state.instincts import _merge_counter

        target: list[dict[str, Any]] = []
        counts: Counter[str] = Counter({"a": 0})
        _merge_counter(
            target,
            counts,
            builder=lambda k, c, t: {"key": k, "evidenceCount": c, "lastSeenAt": t},
        )
        assert len(target) == 0
