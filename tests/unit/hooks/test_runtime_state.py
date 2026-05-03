"""Tests for `.ai-engineering/scripts/hooks/_lib/runtime_state.py`.

Spec-117 ships four runtime hooks (runtime-guard, runtime-stop,
runtime-progressive-disclosure, runtime-compact) plus this shared library.
Earlier versions had no test coverage; the review found four latent contract
bugs that one integration test would have caught. These tests pin the
contract so future edits can't silently regress.

Coverage:
  * Tool-output offload boundary (≤ vs > threshold, exact-byte case)
  * Loop detection: signature repetition AND failure-thrash branches
  * tool-history append + tail read
  * NDJSON tail-byte read (large files)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
RUNTIME_STATE_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "runtime_state.py"


@pytest.fixture
def rs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Load runtime_state.py with offload threshold pinned for boundary tests."""
    monkeypatch.setenv("AIENG_TOOL_OFFLOAD_BYTES", "100")
    monkeypatch.setenv("AIENG_TOOL_OFFLOAD_HEAD", "32")
    monkeypatch.setenv("AIENG_TOOL_OFFLOAD_TAIL", "16")
    monkeypatch.setenv("AIENG_LOOP_REPEAT_THRESHOLD", "3")
    monkeypatch.setenv("AIENG_LOOP_WINDOW", "6")
    monkeypatch.setenv("AIENG_TOOL_HISTORY_MAX", "20")
    # Ensure the module re-evaluates env on each test fixture load.
    sys.modules.pop("aieng_runtime_state", None)
    spec = importlib.util.spec_from_file_location("aieng_runtime_state", RUNTIME_STATE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # @dataclass needs the module registered in sys.modules during exec so
    # __module__ resolves correctly for type-name lookups.
    sys.modules["aieng_runtime_state"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "state" / "runtime").mkdir(parents=True, exist_ok=True)
    return tmp_path


# ---------------------------------------------------------------------------
# Offload boundary
# ---------------------------------------------------------------------------


def test_offload_at_threshold_keeps_payload_in_preview(rs, project: Path) -> None:
    """Exact-threshold payload stays in preview; nothing written."""
    out = rs.offload_large_text(
        project, correlation_id="c1", tool_name="Bash", text="a" * rs.TOOL_OFFLOAD_BYTES
    )
    assert out["offloaded"] is False
    assert out["totalBytes"] == rs.TOOL_OFFLOAD_BYTES
    assert "preview" in out
    out_dir = rs.tool_outputs_dir(project)
    if out_dir.exists():
        assert list(out_dir.iterdir()) == []


def test_offload_just_over_threshold_writes_full_payload(rs, project: Path) -> None:
    """One byte over threshold: file written contains FULL payload, not summary."""
    text = "b" * (rs.TOOL_OFFLOAD_BYTES + 1)
    out = rs.offload_large_text(project, correlation_id="c2", tool_name="Bash", text=text)
    assert out["offloaded"] is True
    assert out["totalBytes"] == len(text)
    on_disk = (project / out["path"]).read_text()
    assert on_disk == text  # full payload, not head+tail


def test_offload_redacts_secrets_before_write(rs, project: Path) -> None:
    """Secret-shaped tokens are redacted on the offload write path."""
    payload = "noise " + ("x" * 200) + " api_key=ABCDEF1234567890 trailer"
    out = rs.offload_large_text(project, correlation_id="c3", tool_name="Bash", text=payload)
    assert out["offloaded"] is True
    on_disk = (project / out["path"]).read_text()
    assert "ABCDEF1234567890" not in on_disk
    assert "[REDACTED]" in on_disk


def test_offload_file_mode_is_user_only(rs, project: Path) -> None:
    """Offloaded files are 0o600 to keep peer users from reading payloads."""
    text = "c" * (rs.TOOL_OFFLOAD_BYTES + 1)
    out = rs.offload_large_text(project, correlation_id="c4", tool_name="Bash", text=text)
    mode = (project / out["path"]).stat().st_mode & 0o777
    assert mode == 0o600


# ---------------------------------------------------------------------------
# Loop detection
# ---------------------------------------------------------------------------


def _entry(rs, **overrides):
    base = dict(
        timestamp="2026-05-04T00:00:00Z",
        session_id="sess",
        tool="Read",
        signature="sig-a",
        outcome="success",
        error_summary=None,
    )
    base.update(overrides)
    return rs.ToolHistoryEntry(**base)


def test_signature_distinguishes_distinct_inputs(rs) -> None:
    sa = rs.tool_signature("Read", {"file_path": "/a"})
    sb = rs.tool_signature("Read", {"file_path": "/b"})
    assert sa != sb


def test_loop_not_detected_below_threshold(rs, project: Path) -> None:
    for _ in range(2):
        rs.append_tool_history(project, _entry(rs))
    history = rs.recent_tool_history(project, session_id="sess", limit=6)
    looped, _ = rs.detect_repetition(history)
    assert looped is False


def test_loop_detected_at_threshold(rs, project: Path) -> None:
    for _ in range(3):
        rs.append_tool_history(project, _entry(rs))
    history = rs.recent_tool_history(project, session_id="sess", limit=6)
    looped, reason = rs.detect_repetition(history)
    assert looped is True
    assert "sig-a" in (reason or "")


def test_loop_detected_on_repeated_failures_with_distinct_signatures(rs, project: Path) -> None:
    for i in range(3):
        rs.append_tool_history(
            project,
            _entry(rs, signature=f"sig-{i}", outcome="failure", error_summary="boom"),
        )
    history = rs.recent_tool_history(project, session_id="sess", limit=6)
    looped, reason = rs.detect_repetition(history)
    assert looped is True
    assert "thrash" in (reason or "").lower() or "failures" in (reason or "").lower()


# ---------------------------------------------------------------------------
# Tool history persistence
# ---------------------------------------------------------------------------


def test_append_tool_history_persists_file_path(rs, project: Path) -> None:
    """ToolHistoryEntry.file_path round-trips through ndjson serialization."""
    rs.append_tool_history(project, _entry(rs, tool="Edit", file_path="/some/path.py"))
    history = rs.recent_tool_history(project, session_id="sess", limit=6)
    assert history
    assert history[-1].get("filePath") == "/some/path.py"


def test_append_tool_history_omits_file_path_when_none(rs, project: Path) -> None:
    """Non-file tools (Bash, Read) don't pollute the record with `filePath: null`."""
    rs.append_tool_history(project, _entry(rs, tool="Bash"))
    history = rs.recent_tool_history(project, session_id="sess", limit=6)
    assert history
    assert "filePath" not in history[-1]
