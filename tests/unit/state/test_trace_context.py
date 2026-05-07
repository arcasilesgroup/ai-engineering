"""Tests for `src/ai_engineering/state/trace_context.py` (spec-120 §4.1, T-A3).

Coverage:
  * ID generation surface (32-hex / 16-hex)
  * read/write round-trip + atomic publish (no `.tmp` leftover)
  * push/pop span stack semantics (including stack-underflow)
  * current_trace_context fresh-fallback when file missing
  * corruption recovery -> framework_error event + fresh trace
  * clear_trace_context removes the file (idempotent)

Backed by the spec-120 plan §A3 acceptance criteria. Each test is hermetic
(uses `tmp_path` as project_root) so the suite is parallel-safe under
pytest-xdist.
"""

from __future__ import annotations

import json
from pathlib import Path

from ai_engineering.state import trace_context as tc

# ---------------------------------------------------------------------------
# ID-generation surface
# ---------------------------------------------------------------------------


def test_new_trace_id_is_32_hex() -> None:
    """`new_trace_id` returns a 32-char lowercase hex string."""
    trace_id = tc.new_trace_id()
    assert isinstance(trace_id, str)
    assert len(trace_id) == 32
    assert all(c in "0123456789abcdef" for c in trace_id)


def test_new_span_id_is_16_hex() -> None:
    """`new_span_id` returns a 16-char lowercase hex string."""
    span_id = tc.new_span_id()
    assert isinstance(span_id, str)
    assert len(span_id) == 16
    assert all(c in "0123456789abcdef" for c in span_id)


def test_new_trace_ids_are_unique_in_practice() -> None:
    """Sanity: 200 successive calls produce no collisions."""
    seen = {tc.new_trace_id() for _ in range(200)}
    assert len(seen) == 200


# ---------------------------------------------------------------------------
# Read/write round-trip
# ---------------------------------------------------------------------------


def test_read_returns_none_when_missing(tmp_path: Path) -> None:
    """No state file => read returns None."""
    assert tc.read_trace_context(tmp_path) is None


def test_write_then_read_round_trip(tmp_path: Path) -> None:
    """Write a payload, read it back; values survive."""
    payload = {
        "traceId": "0123456789abcdef0123456789abcdef",
        "span_stack": ["aaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbb"],
    }
    tc.write_trace_context(tmp_path, payload)
    out = tc.read_trace_context(tmp_path)
    assert out is not None
    assert out["traceId"] == payload["traceId"]
    assert out["span_stack"] == payload["span_stack"]
    # write_trace_context stamps schemaVersion + updatedAt as metadata.
    assert out["schemaVersion"] == tc.SCHEMA_VERSION
    assert "updatedAt" in out


def test_atomic_write_via_tmp_no_leftover(tmp_path: Path) -> None:
    """After a successful write, no `.tmp` siblings remain in the runtime dir."""
    tc.write_trace_context(tmp_path, {"traceId": tc.new_trace_id(), "span_stack": []})
    runtime_dir = tmp_path / ".ai-engineering" / "runtime"
    leftovers = [p for p in runtime_dir.iterdir() if p.suffix == ".tmp" or ".tmp" in p.name]
    # The final file is `trace-context.json`; nothing with `.tmp` may remain.
    assert leftovers == [], f"unexpected leftover tmp files: {leftovers}"


# ---------------------------------------------------------------------------
# Push / pop semantics
# ---------------------------------------------------------------------------


def test_push_pop_round_trip(tmp_path: Path) -> None:
    """push N spans then pop N times yields LIFO order; trace_id stable."""
    # Seed the file via the first push so we exercise the missing-file branch.
    tc.push_span(tmp_path, "1111111111111111")
    seeded = tc.read_trace_context(tmp_path)
    assert seeded is not None
    trace_id_after_first_push = seeded["traceId"]

    tc.push_span(tmp_path, "2222222222222222")
    tc.push_span(tmp_path, "3333333333333333")

    # Stack is now [1,2,3]; pop in LIFO order.
    assert tc.pop_span(tmp_path) == "3333333333333333"
    assert tc.pop_span(tmp_path) == "2222222222222222"
    assert tc.pop_span(tmp_path) == "1111111111111111"
    # Empty stack: pop returns None instead of raising.
    assert tc.pop_span(tmp_path) is None

    # trace_id was stable across the entire push/pop sequence.
    final = tc.read_trace_context(tmp_path)
    assert final is not None
    assert final["traceId"] == trace_id_after_first_push
    assert final["span_stack"] == []


def test_pop_when_file_missing_returns_none(tmp_path: Path) -> None:
    """pop_span on a project with no trace-context file returns None."""
    assert tc.pop_span(tmp_path) is None


def test_push_recovers_when_file_corrupted(tmp_path: Path) -> None:
    """Corrupted file => push starts a fresh context (new trace_id, new stack)."""
    path = tc.trace_context_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not-json{", encoding="utf-8")

    tc.push_span(tmp_path, "abcdefabcdefabcd")
    out = tc.read_trace_context(tmp_path)
    assert out is not None
    assert isinstance(out["traceId"], str)
    assert len(out["traceId"]) == 32
    assert out["span_stack"] == ["abcdefabcdefabcd"]


# ---------------------------------------------------------------------------
# current_trace_context
# ---------------------------------------------------------------------------


def test_current_trace_context_fresh_when_missing(tmp_path: Path) -> None:
    """Missing file => fresh trace_id, parent=None, NO file written."""
    trace_id, parent = tc.current_trace_context(tmp_path)
    assert isinstance(trace_id, str)
    assert len(trace_id) == 32
    assert parent is None
    # IMPORTANT: read path must not persist a file as a side effect.
    assert not tc.trace_context_path(tmp_path).exists()


def test_current_trace_context_returns_top_of_stack(tmp_path: Path) -> None:
    """Existing context with non-empty stack => parent is the top of the stack."""
    tc.push_span(tmp_path, "1111111111111111")
    tc.push_span(tmp_path, "2222222222222222")
    seeded = tc.read_trace_context(tmp_path)
    assert seeded is not None

    trace_id, parent = tc.current_trace_context(tmp_path)
    assert trace_id == seeded["traceId"]
    assert parent == "2222222222222222"


def test_current_trace_context_handles_empty_stack(tmp_path: Path) -> None:
    """Existing context with empty stack => parent is None, trace_id preserved."""
    seed_trace = "ffeeddccbbaa99887766554433221100"
    tc.write_trace_context(tmp_path, {"traceId": seed_trace, "span_stack": []})
    trace_id, parent = tc.current_trace_context(tmp_path)
    assert trace_id == seed_trace
    assert parent is None


def test_current_trace_context_falls_back_when_trace_id_invalid(tmp_path: Path) -> None:
    """Malformed (non-string) traceId in file => fresh trace returned."""
    tc.write_trace_context(tmp_path, {"traceId": 42, "span_stack": []})
    trace_id, parent = tc.current_trace_context(tmp_path)
    assert isinstance(trace_id, str) and len(trace_id) == 32
    assert parent is None


# ---------------------------------------------------------------------------
# Corruption -> framework_error fallback
# ---------------------------------------------------------------------------


def test_corruption_falls_back_to_fresh_trace(tmp_path: Path, monkeypatch) -> None:
    """A non-JSON file emits a framework_error event AND read returns None.

    We force the canonical observability import to fail so the stdlib
    NDJSON fallback writes the event line directly. This proves the
    fallback shape parity with `_lib/observability.append_framework_event`.
    """
    # Seed an unparseable file.
    path = tc.trace_context_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not valid json", encoding="utf-8")

    # Force the lazy import inside _emit_corruption_event to fail. We
    # patch the helper at module level so we control the import path.
    import importlib

    real_import = importlib.import_module

    def boom(name: str, *args, **kwargs):
        if name == "ai_engineering.state.observability":
            raise RuntimeError("simulated circular import")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", boom)
    # The function uses `from ... import ...`, not importlib, so we also
    # need to make the canonical helper unavailable. Easiest: pop the
    # module from sys.modules and shadow it with a broken stub.
    import sys

    sys.modules.pop("ai_engineering.state.observability", None)
    monkeypatch.setitem(sys.modules, "ai_engineering.state.observability", None)

    out = tc.read_trace_context(tmp_path)
    assert out is None

    # Stdlib fallback should have appended one line to framework-events.ndjson.
    events_path = tmp_path / tc.FRAMEWORK_EVENTS_REL
    assert events_path.exists()
    lines = events_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["kind"] == "framework_error"
    assert parsed["component"] == "state.trace_context"
    assert parsed["detail"]["error_code"] == "trace_context_corrupted"
    assert parsed["outcome"] == "failure"
    assert parsed["engine"] == "ai_engineering"
    # Schema-required fields all present.
    for required in (
        "schemaVersion",
        "timestamp",
        "project",
        "engine",
        "kind",
        "outcome",
        "component",
        "correlationId",
        "detail",
    ):
        assert required in parsed, f"missing required field: {required}"


def test_corruption_uses_canonical_helper_when_available(tmp_path: Path) -> None:
    """When `emit_framework_error` imports cleanly, the canonical helper writes the event.

    This is the "happy path" of the fallback chain: we land here in normal
    operation. The line should still validate against the unified schema.
    """
    from ai_engineering.state.event_schema import validate_event_schema

    # Seed an unparseable file.
    path = tc.trace_context_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("definitely-not-json", encoding="utf-8")

    out = tc.read_trace_context(tmp_path)
    assert out is None

    events_path = tmp_path / tc.FRAMEWORK_EVENTS_REL
    assert events_path.exists()
    lines = events_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    parsed = json.loads(lines[-1])
    assert parsed["kind"] == "framework_error"
    assert parsed["detail"]["error_code"] == "trace_context_corrupted"
    # And it conforms to the unified schema validator.
    assert validate_event_schema(parsed) is True


def test_empty_file_treated_as_missing_no_error_event(tmp_path: Path) -> None:
    """Zero-byte (or whitespace-only) file is the legitimate aborted-write
    state and must NOT emit a corruption error -- read just returns None."""
    path = tc.trace_context_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("   \n  ", encoding="utf-8")

    out = tc.read_trace_context(tmp_path)
    assert out is None

    events_path = tmp_path / tc.FRAMEWORK_EVENTS_REL
    # No event should have been emitted for an empty file.
    if events_path.exists():
        lines = events_path.read_text(encoding="utf-8").strip().splitlines()
        for line in lines:
            event = json.loads(line)
            assert event.get("detail", {}).get("error_code") != "trace_context_corrupted"


def test_corruption_for_non_dict_payload(tmp_path: Path) -> None:
    """A JSON array (valid JSON, wrong shape) is corruption: emit + None."""
    path = tc.trace_context_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    out = tc.read_trace_context(tmp_path)
    assert out is None
    events_path = tmp_path / tc.FRAMEWORK_EVENTS_REL
    assert events_path.exists()
    parsed = json.loads(events_path.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert parsed["detail"]["error_code"] == "trace_context_corrupted"


# ---------------------------------------------------------------------------
# clear_trace_context
# ---------------------------------------------------------------------------


def test_clear_removes_file(tmp_path: Path) -> None:
    """clear_trace_context unlinks the state file."""
    tc.write_trace_context(tmp_path, {"traceId": tc.new_trace_id(), "span_stack": []})
    path = tc.trace_context_path(tmp_path)
    assert path.exists()
    tc.clear_trace_context(tmp_path)
    assert not path.exists()


def test_clear_when_absent_is_noop(tmp_path: Path) -> None:
    """clear_trace_context on a missing file does not raise."""
    # Sanity: not present.
    assert not tc.trace_context_path(tmp_path).exists()
    # Should silently succeed.
    tc.clear_trace_context(tmp_path)
    assert not tc.trace_context_path(tmp_path).exists()


# ---------------------------------------------------------------------------
# Branch coverage: stdlib fallback edge cases
# ---------------------------------------------------------------------------


def _force_stdlib_fallback(monkeypatch) -> None:
    """Make the canonical observability helper unimportable so the stdlib path runs."""
    import sys

    sys.modules.pop("ai_engineering.state.observability", None)
    monkeypatch.setitem(sys.modules, "ai_engineering.state.observability", None)


def test_stdlib_fallback_chains_to_existing_events(tmp_path: Path, monkeypatch) -> None:
    """`_compute_prev_event_hash` reads the prior tail and stamps the chain.

    This exercises lines 179-196 of `trace_context.py` which only run on
    the stdlib fallback path AND require a prior NDJSON entry.
    """
    # Pre-seed the events file with one valid prior entry.
    events_path = tmp_path / tc.FRAMEWORK_EVENTS_REL
    events_path.parent.mkdir(parents=True, exist_ok=True)
    prior = {
        "schemaVersion": "1.0",
        "timestamp": "2026-05-04T00:00:00Z",
        "project": tmp_path.name,
        "engine": "ai_engineering",
        "kind": "framework_operation",
        "outcome": "success",
        "component": "test.seed",
        "correlationId": "seed",
        "detail": {},
    }
    events_path.write_text(json.dumps(prior, sort_keys=True) + "\n", encoding="utf-8")

    # Now corrupt the trace-context and force the stdlib path.
    _force_stdlib_fallback(monkeypatch)
    path = tc.trace_context_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not-json{{", encoding="utf-8")

    out = tc.read_trace_context(tmp_path)
    assert out is None

    lines = events_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    new_entry = json.loads(lines[-1])
    # The new entry should carry a prev_event_hash linking to the seed.
    assert new_entry.get("prev_event_hash") is not None
    assert isinstance(new_entry["prev_event_hash"], str)
    assert len(new_entry["prev_event_hash"]) == 64  # sha256 hex


def test_stdlib_fallback_handles_malformed_prior_tail(tmp_path: Path, monkeypatch) -> None:
    """Malformed prior tail in NDJSON => prev_event_hash is None (chain re-anchors)."""
    events_path = tmp_path / tc.FRAMEWORK_EVENTS_REL
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text("not-valid-json-line\n", encoding="utf-8")

    _force_stdlib_fallback(monkeypatch)
    path = tc.trace_context_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("garbage", encoding="utf-8")

    out = tc.read_trace_context(tmp_path)
    assert out is None
    lines = events_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    new_entry = json.loads(lines[-1])
    assert new_entry["prev_event_hash"] is None


def test_stdlib_fallback_handles_array_prior_tail(tmp_path: Path, monkeypatch) -> None:
    """Prior entry is a JSON array (valid JSON, wrong shape) => prev_event_hash=None."""
    events_path = tmp_path / tc.FRAMEWORK_EVENTS_REL
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text("[1,2,3]\n", encoding="utf-8")

    _force_stdlib_fallback(monkeypatch)
    path = tc.trace_context_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("garbage", encoding="utf-8")

    out = tc.read_trace_context(tmp_path)
    assert out is None
    new_entry = json.loads(events_path.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert new_entry["prev_event_hash"] is None


def test_push_recovers_when_span_stack_not_a_list(tmp_path: Path) -> None:
    """File present, traceId valid, but span_stack is the wrong type =>
    push resets the stack to a fresh single-element list."""
    seed_trace = "00112233445566778899aabbccddeeff"
    tc.write_trace_context(tmp_path, {"traceId": seed_trace, "span_stack": "not-a-list"})

    tc.push_span(tmp_path, "abcdefabcdefabcd")
    out = tc.read_trace_context(tmp_path)
    assert out is not None
    # trace_id preserved (it was valid); stack normalised to fresh list.
    assert out["traceId"] == seed_trace
    assert out["span_stack"] == ["abcdefabcdefabcd"]


def test_pop_returns_none_when_top_is_non_string(tmp_path: Path) -> None:
    """Defensive: a stack with a non-string at the top yields None on pop."""
    seed_trace = "ffeeddccbbaa99887766554433221100"
    tc.write_trace_context(
        tmp_path, {"traceId": seed_trace, "span_stack": ["aaaaaaaaaaaaaaaa", 42]}
    )
    # Top is the int 42 -- pop returns None because it's not a string.
    assert tc.pop_span(tmp_path) is None


def test_clear_logs_corruption_when_unlink_fails(tmp_path: Path, monkeypatch) -> None:
    """If unlink raises a non-FileNotFoundError, clear emits a corruption event."""
    tc.write_trace_context(tmp_path, {"traceId": tc.new_trace_id(), "span_stack": []})
    path = tc.trace_context_path(tmp_path)
    assert path.exists()

    real_unlink = Path.unlink

    def raising_unlink(self: Path, *args, **kwargs):
        if self == path:
            raise PermissionError("simulated EACCES")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", raising_unlink)

    # Should not raise -- corruption event is emitted via the canonical helper.
    tc.clear_trace_context(tmp_path)

    events_path = tmp_path / tc.FRAMEWORK_EVENTS_REL
    assert events_path.exists()
    parsed = json.loads(events_path.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert parsed["kind"] == "framework_error"
    assert parsed["detail"]["error_code"] == "trace_context_corrupted"


def test_atomic_write_cleans_tmp_on_fsync_failure(tmp_path: Path, monkeypatch) -> None:
    """If fsync raises mid-write, the tmp file must be unlinked (no leftover)."""
    real_fsync = os.fsync

    def boom_fsync(fd):
        raise OSError("simulated fsync failure")

    import os as _os

    monkeypatch.setattr(_os, "fsync", boom_fsync)

    runtime_dir = tmp_path / ".ai-engineering" / "state" / "runtime"
    try:
        tc.write_trace_context(tmp_path, {"traceId": tc.new_trace_id(), "span_stack": []})
    except OSError:
        # Expected: write_trace_context propagates the I/O failure.
        pass
    else:
        raise AssertionError("expected OSError to propagate from fsync failure")

    # Even though the write failed, no `.tmp` files should remain.
    if runtime_dir.exists():
        leftovers = [p for p in runtime_dir.iterdir() if p.suffix == ".tmp" or ".tmp" in p.name]
        assert leftovers == [], f"expected no `.tmp` leftovers, got {leftovers}"

    # Sanity: restore fsync so any teardown isn't impacted.
    monkeypatch.setattr(_os, "fsync", real_fsync)


def test_read_handles_oserror_on_read(tmp_path: Path, monkeypatch) -> None:
    """OSError during read_text => corruption event AND read returns None."""
    path = tc.trace_context_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"traceId":"x"}', encoding="utf-8")

    real_read_text = Path.read_text

    def boom_read(self: Path, *args, **kwargs):
        if self == path:
            raise OSError("simulated EIO")
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", boom_read)

    out = tc.read_trace_context(tmp_path)
    assert out is None

    events_path = tmp_path / tc.FRAMEWORK_EVENTS_REL
    assert events_path.exists()
    parsed = json.loads(events_path.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert parsed["kind"] == "framework_error"
    assert parsed["detail"]["error_code"] == "trace_context_corrupted"


# Force `os` import for the fsync-failure test above.
import os  # noqa: E402
