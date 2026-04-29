"""Tests for `_lib/hook-common.py` shared lib (spec-112 T-1.7..T-1.9).

Spec-112 G-12: 6 functions x 3 cases each = 18 test cases.

Functions covered:
  1. emit_event             -- writes valid line to NDJSON, rejects invalid
  2. read_stdin_json        -- parses valid JSON, returns {} on malformed
  3. compute_event_hash     -- canonical sorted-keys SHA-256
  4. get_correlation_id     -- UUID4 or env var
  5. get_session_id         -- env var or None
  6. validate_event_schema  -- delegates to event_schema validator
"""

from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from pathlib import Path

import pytest

HOOK_COMMON_PATH = (
    Path(__file__).resolve().parents[3]
    / ".ai-engineering"
    / "scripts"
    / "hooks"
    / "_lib"
    / "hook-common.py"
)


@pytest.fixture
def hc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Load the hook-common module by file path (the file uses a hyphen).

    Importing through the package would require `_lib.hook_common` (underscore);
    we load via spec_from_file_location to honor the spec-mandated filename.
    """
    spec = importlib.util.spec_from_file_location("aieng_hook_common", HOOK_COMMON_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


# ---------------------------------------------------------------------------
# 1. emit_event (3 cases)
# ---------------------------------------------------------------------------


def test_emit_event_writes_valid_line(hc, project_root: Path) -> None:
    event = {
        "kind": "skill_invoked",
        "engine": "claude_code",
        "timestamp": "2026-04-28T00:00:00Z",
        "component": "hook.test",
        "outcome": "success",
        "correlationId": "abc",
        "schemaVersion": "1.0",
        "project": "ai-engineering",
        "detail": {"skill": "ai-test"},
    }
    hc.emit_event(project_root, event)
    ndjson = (project_root / ".ai-engineering" / "state" / "framework-events.ndjson").read_text(
        encoding="utf-8"
    )
    assert ndjson.strip(), "emit_event must write a line"
    written = json.loads(ndjson.strip().splitlines()[-1])
    assert written["kind"] == "skill_invoked"
    assert "prev_event_hash" in written  # spec-110 root chain pointer


def test_emit_event_rejects_invalid_event(hc, project_root: Path) -> None:
    """Invalid events must NOT be written (silent drop is bug)."""
    invalid = {
        "kind": "skill_invoked",
        "engine": "bogus_engine",
    }  # missing required keys + bad engine
    result = hc.emit_event(project_root, invalid)
    ndjson_path = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
    assert result is False, "emit_event must return False on invalid event"
    assert not ndjson_path.exists() or not ndjson_path.read_text(encoding="utf-8").strip()


def test_emit_event_chains_prev_event_hash(hc, project_root: Path) -> None:
    """Successive writes form a hash chain via prev_event_hash at root."""
    base_event = {
        "kind": "skill_invoked",
        "engine": "claude_code",
        "timestamp": "2026-04-28T00:00:00Z",
        "component": "hook.test",
        "outcome": "success",
        "correlationId": "c1",
        "schemaVersion": "1.0",
        "project": "ai-engineering",
        "detail": {"skill": "ai-first"},
    }
    hc.emit_event(project_root, base_event)
    second_event = {**base_event, "correlationId": "c2", "detail": {"skill": "ai-second"}}
    hc.emit_event(project_root, second_event)
    lines = (
        (project_root / ".ai-engineering" / "state" / "framework-events.ndjson")
        .read_text(encoding="utf-8")
        .strip()
        .splitlines()
    )
    assert len(lines) == 2
    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["prev_event_hash"] is None  # chain anchor
    assert isinstance(second["prev_event_hash"], str) and len(second["prev_event_hash"]) == 64


# ---------------------------------------------------------------------------
# 2. read_stdin_json (3 cases)
# ---------------------------------------------------------------------------


def test_read_stdin_json_parses_valid(hc, monkeypatch: pytest.MonkeyPatch) -> None:
    import io

    monkeypatch.setattr(sys, "stdin", io.StringIO('{"foo": 1, "bar": "two"}'))
    result = hc.read_stdin_json()
    assert result == {"foo": 1, "bar": "two"}


def test_read_stdin_json_returns_empty_for_blank(hc, monkeypatch: pytest.MonkeyPatch) -> None:
    import io

    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    result = hc.read_stdin_json()
    assert result == {}


def test_read_stdin_json_returns_empty_on_malformed(hc, monkeypatch: pytest.MonkeyPatch) -> None:
    import io

    monkeypatch.setattr(sys, "stdin", io.StringIO("{not json"))
    result = hc.read_stdin_json()
    assert result == {}


# ---------------------------------------------------------------------------
# 3. compute_event_hash (3 cases)
# ---------------------------------------------------------------------------


def test_compute_event_hash_is_deterministic(hc) -> None:
    event = {"b": 2, "a": 1, "detail": {"y": 4, "x": 3}}
    h1 = hc.compute_event_hash(event)
    h2 = hc.compute_event_hash(event)
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex


def test_compute_event_hash_canonical_sorted_keys(hc) -> None:
    """Key order in input must not change the hash."""
    a = {"a": 1, "b": 2, "detail": {"x": 1, "y": 2}}
    b = {"detail": {"y": 2, "x": 1}, "b": 2, "a": 1}
    assert hc.compute_event_hash(a) == hc.compute_event_hash(b)


def test_compute_event_hash_excludes_prev_event_hash(hc) -> None:
    """The chain pointer field must be excluded so re-hashing is stable."""
    a = {"kind": "x", "prev_event_hash": "deadbeef" * 8}
    b = {"kind": "x", "prev_event_hash": None}
    c = {"kind": "x"}
    h_a = hc.compute_event_hash(a)
    h_b = hc.compute_event_hash(b)
    h_c = hc.compute_event_hash(c)
    assert h_a == h_b == h_c


# ---------------------------------------------------------------------------
# 4. get_correlation_id (3 cases)
# ---------------------------------------------------------------------------


def test_get_correlation_id_returns_uuid4(hc, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_TRACE_ID", raising=False)
    cid = hc.get_correlation_id()
    # uuid4 hex form is 32 hex chars
    assert isinstance(cid, str)
    assert len(cid) == 32
    uuid.UUID(cid)  # raises if invalid


def test_get_correlation_id_uses_env(hc, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_TRACE_ID", "fixed-trace-id")
    cid = hc.get_correlation_id()
    assert cid == "fixed-trace-id"


def test_get_correlation_id_unique(hc, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_TRACE_ID", raising=False)
    a = hc.get_correlation_id()
    b = hc.get_correlation_id()
    assert a != b


# ---------------------------------------------------------------------------
# 5. get_session_id (3 cases)
# ---------------------------------------------------------------------------


def test_get_session_id_from_claude_env(hc, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_SESSION_ID", "sess-claude")
    monkeypatch.delenv("GEMINI_SESSION_ID", raising=False)
    assert hc.get_session_id() == "sess-claude"


def test_get_session_id_from_gemini_env(hc, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.setenv("GEMINI_SESSION_ID", "sess-gemini")
    assert hc.get_session_id() == "sess-gemini"


def test_get_session_id_returns_none_when_unset(hc, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.delenv("GEMINI_SESSION_ID", raising=False)
    assert hc.get_session_id() is None


# ---------------------------------------------------------------------------
# 6. validate_event_schema (3 cases) -- delegates to event_schema.py
# ---------------------------------------------------------------------------


def test_validate_event_schema_valid(hc) -> None:
    event = {
        "kind": "skill_invoked",
        "engine": "claude_code",
        "timestamp": "2026-04-28T00:00:00Z",
        "component": "hook.test",
        "outcome": "success",
        "correlationId": "abc",
        "schemaVersion": "1.0",
        "project": "ai-engineering",
        "detail": {"skill": "ai-test"},
    }
    assert hc.validate_event_schema(event) is True


def test_validate_event_schema_rejects_missing_required(hc) -> None:
    event = {"kind": "skill_invoked"}  # missing required fields
    assert hc.validate_event_schema(event) is False


def test_validate_event_schema_rejects_bad_engine(hc) -> None:
    event = {
        "kind": "skill_invoked",
        "engine": "bogus",
        "timestamp": "2026-04-28T00:00:00Z",
        "component": "hook.test",
        "outcome": "success",
        "correlationId": "abc",
        "schemaVersion": "1.0",
        "project": "ai-engineering",
        "detail": {},
    }
    assert hc.validate_event_schema(event) is False
