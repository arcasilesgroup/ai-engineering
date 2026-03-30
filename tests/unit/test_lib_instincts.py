"""Tests for _lib.instincts -- stdlib-only instinct learning module (v2 schema)."""

from __future__ import annotations

import importlib
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

# Insert hooks _lib onto sys.path so we can import without the pip package.
_hooks_dir = str(Path(__file__).parents[2] / ".ai-engineering" / "scripts" / "hooks")
if _hooks_dir not in sys.path:
    sys.path.insert(0, _hooks_dir)
instincts = importlib.import_module("_lib.instincts")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Return a tmp project root with the required directory scaffold."""
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
    (tmp_path / ".ai-engineering" / "instincts").mkdir(parents=True)
    return tmp_path


def _make_obs(
    tool: str = "Read",
    kind: str = "tool_start",
    outcome: str = "success",
    session_id: str = "sess-1",
    ts: datetime | None = None,
    detail: dict | None = None,
) -> dict:
    """Build a minimal observation dict matching the _lib schema."""
    return {
        "schemaVersion": "1.0",
        "timestamp": (ts or datetime.now(tz=UTC)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "engine": "claude_code",
        "kind": kind,
        "tool": tool,
        "outcome": outcome,
        "sessionId": session_id,
        "detail": detail or {},
    }


def _write_obs(project: Path, entries: list[dict]) -> None:
    """Write a list of observation dicts as NDJSON."""
    path = project / instincts.INSTINCT_OBSERVATIONS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(e, default=str) for e in entries]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _write_framework_events(project: Path, events: list[dict]) -> None:
    """Write framework events as NDJSON."""
    path = project / instincts.FRAMEWORK_EVENTS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(e, default=str) for e in events]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. append_instinct_observation with valid data writes NDJSON line
# ---------------------------------------------------------------------------


class TestAppendInstinctObservation:
    def test_valid_data_writes_ndjson_line(self, project: Path) -> None:
        result = instincts.append_instinct_observation(
            project,
            engine="claude_code",
            hook_event="PreToolUse",
            data={"tool_name": "Read", "file_path": "/some/file.py"},
            session_id="sess-42",
        )

        assert result is not None
        assert result["tool"] == "Read"
        assert result["kind"] == "tool_start"
        assert result["engine"] == "claude_code"
        assert result["sessionId"] == "sess-42"

        obs_path = project / instincts.INSTINCT_OBSERVATIONS_REL
        assert obs_path.exists()
        lines = [ln for ln in obs_path.read_text().splitlines() if ln.strip()]
        assert len(lines) >= 1
        parsed = json.loads(lines[-1])
        assert parsed["tool"] == "Read"

    # -------------------------------------------------------------------
    # 2. Empty tool_name returns None
    # -------------------------------------------------------------------

    def test_empty_tool_name_returns_none(self, project: Path) -> None:
        result = instincts.append_instinct_observation(
            project,
            engine="claude_code",
            hook_event="PostToolUse",
            data={"tool_name": "", "result": "ok"},
        )
        assert result is None

    def test_missing_tool_name_returns_none(self, project: Path) -> None:
        result = instincts.append_instinct_observation(
            project,
            engine="claude_code",
            hook_event="PostToolUse",
            data={"result": "ok"},
        )
        assert result is None


# ---------------------------------------------------------------------------
# 3. Observation pruning removes entries older than 30 days
# ---------------------------------------------------------------------------


class TestPruning:
    def test_prune_removes_old_entries(self, project: Path) -> None:
        now = datetime.now(tz=UTC)
        old = now - timedelta(days=31)
        recent = now - timedelta(days=1)

        entries = [
            _make_obs(tool="OldTool", ts=old, session_id="s1"),
            _make_obs(tool="NewTool", ts=recent, session_id="s2"),
        ]
        _write_obs(project, entries)

        kept = instincts.prune_instinct_observations(project, now=now)
        tools = [e["tool"] for e in kept]
        assert "OldTool" not in tools
        assert "NewTool" in tools


# ---------------------------------------------------------------------------
# 4. _derive_outcome detects failure from error keys
# ---------------------------------------------------------------------------


class TestDeriveOutcome:
    def test_error_key_means_failure(self) -> None:
        assert instincts._derive_outcome({"error": "something broke"}) == "failure"

    def test_tool_error_key_means_failure(self) -> None:
        assert instincts._derive_outcome({"tool_error": "denied"}) == "failure"

    def test_exception_key_means_failure(self) -> None:
        assert instincts._derive_outcome({"exception": "traceback"}) == "failure"

    def test_error_hint_in_result_means_failure(self) -> None:
        assert (
            instincts._derive_outcome({"tool_name": "Bash", "result": "Command failed"})
            == "failure"
        )

    def test_success_with_tool_name(self) -> None:
        assert instincts._derive_outcome({"tool_name": "Read"}) == "success"

    def test_unknown_without_tool_name(self) -> None:
        assert instincts._derive_outcome({}) == "unknown"


# ---------------------------------------------------------------------------
# 5. _sanitize_text truncates at 160 chars and redacts secrets
# ---------------------------------------------------------------------------


class TestSanitizeText:
    def test_truncates_long_text(self) -> None:
        long_text = "a" * 200
        result = instincts._sanitize_text(long_text)
        assert result is not None
        assert len(result) == instincts.MAX_SUMMARY_LEN + 3  # +3 for "..."
        assert result.endswith("...")

    def test_redacts_secrets(self) -> None:
        text = 'api_key="sk-very-secret-value-12345"'
        result = instincts._sanitize_text(text)
        assert result is not None
        assert "sk-very-secret-value-12345" not in result
        assert "[REDACTED]" in result

    def test_returns_none_for_empty(self) -> None:
        assert instincts._sanitize_text("") is None
        assert instincts._sanitize_text(None) is None

    def test_collapses_whitespace(self) -> None:
        result = instincts._sanitize_text("hello   \n  world")
        assert result == "hello world"


# ---------------------------------------------------------------------------
# 6. extract_instincts detects error recovery patterns (v2 recoveries)
# ---------------------------------------------------------------------------


class TestExtractInstinctsRecoveries:
    def test_detects_error_recovery_patterns(self, project: Path) -> None:
        now = datetime.now(tz=UTC)
        entries = [
            _make_obs(
                tool="Bash",
                kind="tool_complete",
                outcome="failure",
                ts=now - timedelta(seconds=2),
            ),
            _make_obs(
                tool="Read",
                kind="tool_start",
                outcome="success",
                ts=now - timedelta(seconds=1),
            ),
        ]
        _write_obs(project, entries)

        result = instincts.extract_instincts(project)
        assert result is True

        inst_path = project / instincts.INSTINCTS_REL
        content = inst_path.read_text(encoding="utf-8")
        assert "Bash -> Read" in content
        assert "recovery" in content.lower()


# ---------------------------------------------------------------------------
# 7. extract_instincts returns False when no new observations
# ---------------------------------------------------------------------------


class TestExtractInstinctsNoNew:
    def test_returns_false_when_no_observations(self, project: Path) -> None:
        result = instincts.extract_instincts(project)
        assert result is False

    def test_returns_false_when_already_extracted(self, project: Path) -> None:
        now = datetime.now(tz=UTC)
        entries = [
            _make_obs(tool="Read", kind="tool_start", ts=now - timedelta(seconds=1)),
        ]
        _write_obs(project, entries)

        # First extraction picks up the observations
        assert instincts.extract_instincts(project) is True
        # Second extraction has nothing new
        assert instincts.extract_instincts(project) is False


# ---------------------------------------------------------------------------
# 8. YAML fallback: mock yaml as unavailable, verify JSON write works
# ---------------------------------------------------------------------------


class TestYamlFallback:
    def test_json_fallback_when_yaml_unavailable(self, project: Path) -> None:
        now = datetime.now(tz=UTC)
        entries = [
            _make_obs(
                tool="Bash",
                kind="tool_complete",
                outcome="failure",
                ts=now - timedelta(seconds=2),
            ),
            _make_obs(tool="Read", kind="tool_start", ts=now - timedelta(seconds=1)),
        ]
        _write_obs(project, entries)

        # Temporarily pretend yaml is not available
        original_has_yaml = instincts._HAS_YAML
        try:
            instincts._HAS_YAML = False
            result = instincts.extract_instincts(project)
            assert result is True

            # The instincts file should exist and be valid JSON
            inst_path = project / instincts.INSTINCTS_REL
            content = inst_path.read_text(encoding="utf-8")
            doc = json.loads(content)  # should not raise
            assert "recoveries" in doc
            assert "workflows" in doc
            assert "corrections" in doc
        finally:
            instincts._HAS_YAML = original_has_yaml


# ---------------------------------------------------------------------------
# 9. _detect_skill_agent_preferences does NOT exist
# ---------------------------------------------------------------------------


class TestDroppedFunction:
    def test_skill_agent_preferences_not_present(self) -> None:
        assert not hasattr(instincts, "_detect_skill_agent_preferences")


# ---------------------------------------------------------------------------
# 10. v2 schema version
# ---------------------------------------------------------------------------


class TestV2SchemaVersion:
    def test_schema_version_is_2(self) -> None:
        assert instincts.INSTINCTS_SCHEMA_VERSION == "2.0"

    def test_default_document_has_v2_keys(self) -> None:
        doc = instincts._default_instincts_document()
        assert doc["schemaVersion"] == "2.0"
        assert "corrections" in doc
        assert "recoveries" in doc
        assert "workflows" in doc
        assert "toolSequences" not in doc
        assert "errorRecoveries" not in doc


# ---------------------------------------------------------------------------
# 11. confidence_for_count
# ---------------------------------------------------------------------------


class TestConfidenceForCount:
    def test_low_count_returns_0_3(self) -> None:
        assert instincts.confidence_for_count(0) == 0.3
        assert instincts.confidence_for_count(1) == 0.3
        assert instincts.confidence_for_count(2) == 0.3

    def test_mid_count_returns_0_5(self) -> None:
        assert instincts.confidence_for_count(3) == 0.5
        assert instincts.confidence_for_count(5) == 0.5

    def test_high_count_returns_0_7(self) -> None:
        assert instincts.confidence_for_count(6) == 0.7
        assert instincts.confidence_for_count(9) == 0.7

    def test_very_high_count_returns_0_85(self) -> None:
        assert instincts.confidence_for_count(10) == 0.85
        assert instincts.confidence_for_count(100) == 0.85


# ---------------------------------------------------------------------------
# 12. apply_confidence_decay
# ---------------------------------------------------------------------------


class TestApplyConfidenceDecay:
    def test_no_decay_when_recently_seen(self) -> None:
        now = datetime.now(tz=UTC)
        entries = [
            {
                "key": "A -> B",
                "evidenceCount": 5,
                "confidence": 0.7,
                "lastSeenAt": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        ]
        result = instincts.apply_confidence_decay(entries, [now.strftime("%Y-%m-%dT%H:%M:%SZ")])
        assert result[0]["confidence"] == 0.7

    def test_decay_applied_per_week(self) -> None:
        now = datetime.now(tz=UTC)
        two_weeks_ago = now - timedelta(weeks=2)
        entries = [
            {
                "key": "A -> B",
                "evidenceCount": 10,
                "confidence": 0.85,
                "lastSeenAt": two_weeks_ago.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        ]
        result = instincts.apply_confidence_decay(entries, [now.strftime("%Y-%m-%dT%H:%M:%SZ")])
        # 0.85 - 0.02 * 2 = 0.81
        assert result[0]["confidence"] == 0.81

    def test_empty_entries_returns_empty(self) -> None:
        assert instincts.apply_confidence_decay([], ["2026-01-01T00:00:00Z"]) == []

    def test_empty_dates_returns_unchanged(self) -> None:
        entries = [{"key": "A -> B", "confidence": 0.7}]
        result = instincts.apply_confidence_decay(entries, [])
        assert result[0]["confidence"] == 0.7


# ---------------------------------------------------------------------------
# 13. prune_low_confidence
# ---------------------------------------------------------------------------


class TestPruneLowConfidence:
    def test_removes_entries_below_threshold(self) -> None:
        entries = [
            {"key": "A -> B", "confidence": 0.1},
            {"key": "C -> D", "confidence": 0.5},
            {"key": "E -> F", "confidence": 0.2},
        ]
        result = instincts.prune_low_confidence(entries)
        assert len(result) == 2
        keys = [e["key"] for e in result]
        assert "A -> B" not in keys
        assert "C -> D" in keys
        assert "E -> F" in keys

    def test_custom_threshold(self) -> None:
        entries = [
            {"key": "A -> B", "confidence": 0.4},
            {"key": "C -> D", "confidence": 0.6},
        ]
        result = instincts.prune_low_confidence(entries, threshold=0.5)
        assert len(result) == 1
        assert result[0]["key"] == "C -> D"

    def test_entries_without_confidence_use_default_0_3(self) -> None:
        entries = [{"key": "A -> B"}]
        result = instincts.prune_low_confidence(entries, threshold=0.2)
        assert len(result) == 1  # default 0.3 >= 0.2


# ---------------------------------------------------------------------------
# 14. _detect_skill_workflows
# ---------------------------------------------------------------------------


class TestDetectSkillWorkflows:
    def test_detects_skill_sequences(self, project: Path) -> None:
        now = datetime.now(tz=UTC)
        events = [
            {
                "schemaVersion": "1.0",
                "timestamp": (now - timedelta(seconds=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "project": "test",
                "engine": "claude_code",
                "kind": "skill_invoked",
                "outcome": "success",
                "component": "hook.telemetry",
                "correlationId": "corr-1",
                "sessionId": "sess-1",
                "detail": {"skill": "ai-brainstorm"},
            },
            {
                "schemaVersion": "1.0",
                "timestamp": (now - timedelta(seconds=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "project": "test",
                "engine": "claude_code",
                "kind": "skill_invoked",
                "outcome": "success",
                "component": "hook.telemetry",
                "correlationId": "corr-1",
                "sessionId": "sess-1",
                "detail": {"skill": "ai-plan"},
            },
            {
                "schemaVersion": "1.0",
                "timestamp": (now - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "project": "test",
                "engine": "claude_code",
                "kind": "skill_invoked",
                "outcome": "success",
                "component": "hook.telemetry",
                "correlationId": "corr-1",
                "sessionId": "sess-1",
                "detail": {"skill": "ai-dispatch"},
            },
        ]
        _write_framework_events(project, events)

        result = instincts._detect_skill_workflows(project)
        assert result["ai-brainstorm -> ai-plan"] == 1
        assert result["ai-plan -> ai-dispatch"] == 1

    def test_empty_ndjson_returns_empty_counter(self, project: Path) -> None:
        result = instincts._detect_skill_workflows(project)
        assert len(result) == 0

    def test_ignores_non_skill_events(self, project: Path) -> None:
        now = datetime.now(tz=UTC)
        events = [
            {
                "schemaVersion": "1.0",
                "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "project": "test",
                "engine": "claude_code",
                "kind": "agent_dispatched",
                "outcome": "success",
                "component": "hook.observe",
                "correlationId": "corr-1",
                "detail": {"agent": "ai-build"},
            },
        ]
        _write_framework_events(project, events)

        result = instincts._detect_skill_workflows(project)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# 15. _migrate_v1_to_v2
# ---------------------------------------------------------------------------


class TestMigrateV1ToV2:
    def test_converts_high_evidence_tool_sequences_to_workflows(self) -> None:
        v1_doc = {
            "schemaVersion": "1.0",
            "updatedAt": "2026-03-01T00:00:00Z",
            "toolSequences": [
                {
                    "key": "Read -> Grep",
                    "guidance": "Common tool sequence: Read -> Grep.",
                    "evidenceCount": 8,
                    "lastSeenAt": "2026-03-01T00:00:00Z",
                },
                {
                    "key": "Read -> Edit",
                    "guidance": "Common tool sequence: Read -> Edit.",
                    "evidenceCount": 3,
                    "lastSeenAt": "2026-03-01T00:00:00Z",
                },
            ],
            "errorRecoveries": [
                {
                    "key": "Bash -> Read",
                    "guidance": "After Bash errors, Read is a common recovery step.",
                    "evidenceCount": 4,
                    "lastSeenAt": "2026-03-01T00:00:00Z",
                },
            ],
            "skillAgentPreferences": [
                {
                    "key": "ai-dispatch -> ai-build",
                    "guidance": "...",
                    "evidenceCount": 5,
                    "lastSeenAt": "2026-03-01T00:00:00Z",
                },
            ],
        }

        result = instincts._migrate_v1_to_v2(v1_doc)

        assert result["schemaVersion"] == "2.0"
        assert result["corrections"] == []
        assert result["recoveries"] == []
        assert len(result["workflows"]) == 1
        assert result["workflows"][0]["key"] == "Read -> Grep"
        assert result["workflows"][0]["trigger"] == "Read completed"
        assert result["workflows"][0]["action"] == "Invoke Grep"
        assert result["workflows"][0]["confidence"] == 0.7  # count 8 -> 0.7
        assert "toolSequences" not in result
        assert "errorRecoveries" not in result
        assert "skillAgentPreferences" not in result

    def test_empty_v1_doc_migrates_cleanly(self) -> None:
        v1_doc = {"schemaVersion": "1.0"}
        result = instincts._migrate_v1_to_v2(v1_doc)
        assert result["schemaVersion"] == "2.0"
        assert result["corrections"] == []
        assert result["recoveries"] == []
        assert result["workflows"] == []

    def test_discards_low_evidence_sequences(self) -> None:
        v1_doc = {
            "schemaVersion": "1.0",
            "toolSequences": [
                {"key": "A -> B", "evidenceCount": 4, "lastSeenAt": "2026-01-01T00:00:00Z"},
            ],
        }
        result = instincts._migrate_v1_to_v2(v1_doc)
        assert result["workflows"] == []


# ---------------------------------------------------------------------------
# 16. Context functions are removed
# ---------------------------------------------------------------------------


class TestContextFunctionsRemoved:
    def test_maybe_refresh_not_present(self) -> None:
        assert not hasattr(instincts, "maybe_refresh_instinct_context")

    def test_refresh_not_present(self) -> None:
        assert not hasattr(instincts, "_refresh_instinct_context")

    def test_needs_refresh_not_present(self) -> None:
        assert not hasattr(instincts, "_needs_context_refresh")

    def test_select_context_items_not_present(self) -> None:
        assert not hasattr(instincts, "_select_context_items")

    def test_context_path_not_present(self) -> None:
        assert not hasattr(instincts, "_context_path")

    def test_context_header_not_present(self) -> None:
        assert not hasattr(instincts, "INSTINCT_CONTEXT_HEADER")
