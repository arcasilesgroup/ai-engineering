"""Tests for _lib.instincts -- stdlib-only instinct learning module."""

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
# 6. extract_instincts detects tool sequence pairs
# ---------------------------------------------------------------------------


class TestExtractInstinctsToolSequences:
    def test_detects_tool_sequence_pairs(self, project: Path) -> None:
        now = datetime.now(tz=UTC)
        entries = [
            _make_obs(tool="Read", kind="tool_start", ts=now - timedelta(seconds=3)),
            _make_obs(tool="Grep", kind="tool_start", ts=now - timedelta(seconds=2)),
            _make_obs(tool="Edit", kind="tool_start", ts=now - timedelta(seconds=1)),
        ]
        _write_obs(project, entries)

        result = instincts.extract_instincts(project)
        assert result is True

        inst_path = project / instincts.INSTINCTS_REL
        assert inst_path.exists()

        # Read back the instincts document
        content = inst_path.read_text(encoding="utf-8")
        # Regardless of YAML/JSON format, the sequences should be present
        assert "Read -> Grep" in content
        assert "Grep -> Edit" in content


# ---------------------------------------------------------------------------
# 7. extract_instincts detects error recovery patterns
# ---------------------------------------------------------------------------


class TestExtractInstinctsErrorRecoveries:
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
# 8. extract_instincts returns False when no new observations
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
# 9. maybe_refresh_instinct_context generates markdown with top items
# ---------------------------------------------------------------------------


class TestMaybeRefreshInstinctContext:
    def test_generates_context_markdown(self, project: Path) -> None:
        now = datetime.now(tz=UTC)
        # Build observations with repeated sequences so we get instinct entries
        entries = []
        for i in range(5):
            entries.append(
                _make_obs(
                    tool="Read",
                    kind="tool_start",
                    ts=now - timedelta(seconds=20 - i * 2),
                    session_id=f"sess-{i}",
                )
            )
            entries.append(
                _make_obs(
                    tool="Grep",
                    kind="tool_start",
                    ts=now - timedelta(seconds=19 - i * 2),
                    session_id=f"sess-{i}",
                )
            )
        _write_obs(project, entries)

        # Extract first to populate instincts.yml
        instincts.extract_instincts(project)

        # Now refresh context
        result = instincts.maybe_refresh_instinct_context(project)
        assert result is True

        ctx_path = project / instincts.INSTINCT_CONTEXT_REL
        assert ctx_path.exists()
        content = ctx_path.read_text(encoding="utf-8")
        assert content.startswith("# Instinct Context")
        assert "Read -> Grep" in content
        assert "Evidence:" in content


# ---------------------------------------------------------------------------
# 10. YAML fallback: mock yaml as unavailable, verify JSON write works
# ---------------------------------------------------------------------------


class TestYamlFallback:
    def test_json_fallback_when_yaml_unavailable(self, project: Path) -> None:
        now = datetime.now(tz=UTC)
        entries = [
            _make_obs(tool="Read", kind="tool_start", ts=now - timedelta(seconds=2)),
            _make_obs(tool="Grep", kind="tool_start", ts=now - timedelta(seconds=1)),
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
            assert "toolSequences" in doc
        finally:
            instincts._HAS_YAML = original_has_yaml


# ---------------------------------------------------------------------------
# 11. _detect_skill_agent_preferences does NOT exist
# ---------------------------------------------------------------------------


class TestDroppedFunction:
    def test_skill_agent_preferences_not_present(self) -> None:
        assert not hasattr(instincts, "_detect_skill_agent_preferences")
