"""Tests for ``_lib/instincts.py`` fail-open behaviour (spec-120 follow-up).

Pin the regressions that produced the 8713 ``Unterminated string starting at:
line 1 column 1 (char 0)`` ``framework_error`` events on this project:

* ``_load_meta`` was a bare ``json.loads(read_text())`` -- a concurrent writer
  could leave the file truncated, the hook would raise, and ``run_hook_safe``
  would log a ``hook_execution_failed`` event. Now it returns the default
  meta and logs a one-line stderr diagnostic instead.
* ``_load_yaml_or_json`` had the same bare-load shape for the JSON fallback
  path. Same fix.
* ``_write_ndjson`` truncated the destination before writing the new bytes,
  so a reader that landed mid-call saw partial / empty content. Now writes
  go through a sibling ``.tmp`` and ``os.replace`` so the swap is atomic.
* ``append_instinct_observation`` is the public entry point for the hook.
  Even with all the above guards, an unexpected failure must be swallowed
  so the PostToolUse chain stays green.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
INSTINCTS_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "instincts.py"


@pytest.fixture
def instincts(monkeypatch: pytest.MonkeyPatch):
    """Load the stdlib ``_lib/instincts.py`` fresh per test."""
    sys.modules.pop("aieng_instincts_lib", None)
    spec = importlib.util.spec_from_file_location("aieng_instincts_lib", INSTINCTS_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "instincts").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


# ---------------------------------------------------------------------------
# _load_meta fail-open
# ---------------------------------------------------------------------------


def test_load_meta_tolerates_truncated_meta_json(instincts, project: Path) -> None:
    """Truncated meta.json (the canonical Unterminated string scenario) must
    return the default meta dict, not raise."""
    instincts.ensure_instinct_artifacts(project)
    meta_path = project / ".ai-engineering" / "instincts" / "meta.json"
    # Mid-write truncation: half-of-an-object content.
    meta_path.write_text('{"sche', encoding="utf-8")

    out = instincts._load_meta(project)

    # No exception. Default meta dict shape.
    assert out["schemaVersion"] == "1.0"
    assert out["lastExtractedAt"] is None
    assert out["deltaThreshold"] == 10


def test_load_meta_tolerates_empty_meta_json(instincts, project: Path) -> None:
    """Empty meta.json (zero bytes) must return the default meta dict."""
    instincts.ensure_instinct_artifacts(project)
    meta_path = project / ".ai-engineering" / "instincts" / "meta.json"
    meta_path.write_text("", encoding="utf-8")

    out = instincts._load_meta(project)

    assert out["schemaVersion"] == "1.0"
    assert out["lastExtractedAt"] is None


def test_load_meta_tolerates_non_dict_payload(instincts, project: Path) -> None:
    """A list / scalar payload at the meta path must not crash ``meta.update``."""
    instincts.ensure_instinct_artifacts(project)
    meta_path = project / ".ai-engineering" / "instincts" / "meta.json"
    meta_path.write_text("[1, 2, 3]", encoding="utf-8")

    out = instincts._load_meta(project)

    assert out["schemaVersion"] == "1.0"


# ---------------------------------------------------------------------------
# _load_yaml_or_json fail-open
# ---------------------------------------------------------------------------


def test_load_yaml_or_json_tolerates_truncated_payload(
    instincts, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Force the no-yaml fallback path; corrupt JSON must return ``{}``."""
    monkeypatch.setattr(instincts, "_HAS_YAML", False)
    path = project / "instincts.json"
    path.write_text("{not-real-json", encoding="utf-8")

    out = instincts._load_yaml_or_json(path)

    assert out == {}


def test_load_yaml_or_json_returns_empty_for_missing_file(instincts, project: Path) -> None:
    out = instincts._load_yaml_or_json(project / "does-not-exist.yml")
    assert out == {}


# ---------------------------------------------------------------------------
# _write_ndjson atomicity
# ---------------------------------------------------------------------------


def test_write_ndjson_atomic_via_tmp(instincts, project: Path) -> None:
    """The ``.tmp`` sibling must show up if we monkey ``os.replace`` to no-op,
    proving the writer goes through the staged-file swap path."""
    target = project / "obs.ndjson"
    target.write_text("OLD", encoding="utf-8")

    # Patch os.replace so we can observe the .tmp without it being moved.
    import os as real_os

    seen_replacements: list[tuple[str, str]] = []
    original_replace = real_os.replace

    def fake_replace(src, dst):  # type: ignore[no-untyped-def]
        seen_replacements.append((str(src), str(dst)))
        return original_replace(src, dst)

    instincts.os.replace = fake_replace  # type: ignore[attr-defined]
    try:
        instincts._write_ndjson(target, [{"k": "v"}])
    finally:
        instincts.os.replace = original_replace  # type: ignore[attr-defined]

    assert seen_replacements, "writer never went through os.replace"
    src, dst = seen_replacements[0]
    assert src.endswith(".tmp")
    assert dst == str(target)
    # Final content reflects the new payload, not the old "OLD" sentinel.
    assert json.loads(target.read_text(encoding="utf-8").strip()) == {"k": "v"}


def test_write_ndjson_concurrent_reader_never_sees_partial(instincts, project: Path) -> None:
    """The historical bug: a reader that lands while the writer is mid-write
    saw a truncated file. With atomic replace, the file is either pre-write
    contents OR post-write contents, never empty / partial.

    Spawn a reader thread that reads in a tight loop while the writer rewrites
    the file. The reader records every snapshot it sees; assert that none is
    parseable-but-truncated (which would be ``Unterminated string`` territory).
    """
    target = project / "obs.ndjson"
    initial = [{"i": i} for i in range(5)]
    instincts._write_ndjson(target, initial)

    stop = threading.Event()
    snapshots: list[str] = []

    def reader() -> None:
        while not stop.is_set():
            try:
                snapshots.append(target.read_text(encoding="utf-8"))
            except OSError:
                continue

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    try:
        # Write a much larger payload many times; with non-atomic write, this
        # would race the reader badly. We just want to assert no snapshot is
        # ever a partial (mid-flush) view of either payload.
        bigger = [{"i": i, "blob": "x" * 200} for i in range(100)]
        for _ in range(20):
            instincts._write_ndjson(target, bigger)
            instincts._write_ndjson(target, initial)
    finally:
        stop.set()
        t.join(timeout=2.0)

    # Every snapshot must parse to one of the two states: 5 lines or 100 lines.
    valid_lengths = {5, 100}
    for snap in snapshots:
        if not snap.strip():
            continue  # empty file before first write is acceptable
        lines = [ln for ln in snap.splitlines() if ln.strip()]
        # Each line must be parseable JSON (no torn writes).
        for ln in lines:
            json.loads(ln)
        assert len(lines) in valid_lengths, (
            f"Reader observed a partial snapshot with {len(lines)} lines: "
            f"atomic-replace contract broken"
        )


# ---------------------------------------------------------------------------
# append_instinct_observation defensive top-level
# ---------------------------------------------------------------------------


def test_append_observation_fail_open_on_corruption(instincts, project: Path) -> None:
    """Even if every read path raises, the public entry point returns None
    without propagating the exception. The hook contract is fail-open."""
    instincts.ensure_instinct_artifacts(project)
    # Corrupt all three artefacts.
    (project / ".ai-engineering" / "instincts" / "meta.json").write_text(
        "{not-json", encoding="utf-8"
    )
    (project / ".ai-engineering" / "instincts" / "instincts.yml").write_text(
        "[: not yaml :]", encoding="utf-8"
    )
    (project / ".ai-engineering" / "state" / "instinct-observations.ndjson").write_text(
        '{"truncated', encoding="utf-8"
    )

    # Ought to return a dict (the new observation) and NOT raise -- corruption
    # of meta and instincts.yml shouldn't bubble up because they're loaded
    # fail-open. The observation file's malformed line is skipped by
    # ``_read_ndjson``.
    out = instincts.append_instinct_observation(
        project,
        engine="claude_code",
        hook_event="PostToolUse",
        data={"tool_name": "Bash", "tool_input": {"command": "echo hi"}},
        session_id="sess-x",
    )
    assert out is not None
    assert out["tool"] == "Bash"


def test_append_observation_swallows_unexpected_exception(
    instincts, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If something deep in the stack raises an unexpected error type, the
    top-level guard must still swallow it and return None."""

    def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("synthetic deep failure")

    monkeypatch.setattr(instincts, "prune_instinct_observations", boom)

    out = instincts.append_instinct_observation(
        project,
        engine="claude_code",
        hook_event="PostToolUse",
        data={"tool_name": "Bash", "tool_input": {"command": "x"}},
    )
    assert out is None


# ---------------------------------------------------------------------------
# End-to-end: actual hook script under the original failure pattern
# ---------------------------------------------------------------------------


def test_hook_script_exits_zero_on_corrupt_meta(tmp_path: Path) -> None:
    """Run ``instinct-observe.py`` against a project whose meta.json is the
    canonical truncated payload that produced the 8713 framework_error events.
    The hook must exit 0 (fail-open contract) -- no traceback to stderr that
    matches the hook_execution_failed shape."""
    import os
    import subprocess

    project = tmp_path
    (project / ".ai-engineering" / "instincts").mkdir(parents=True, exist_ok=True)
    (project / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    (project / ".ai-engineering" / "instincts" / "meta.json").write_text('{"sche', encoding="utf-8")
    (project / ".claude").mkdir(parents=True, exist_ok=True)

    script = REPO / ".ai-engineering" / "scripts" / "hooks" / "instinct-observe.py"
    payload = json.dumps(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "echo hi"},
            "hook_event_name": "PostToolUse",
        }
    )
    env = os.environ.copy()
    env["AIENG_HOOK_ENGINE"] = "claude_code"
    env["AIENG_HOOK_INTEGRITY_MODE"] = "off"
    env["CLAUDE_PROJECT_DIR"] = str(project)
    result = subprocess.run(
        [sys.executable, str(script)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(project),
        timeout=10,
    )
    assert result.returncode == 0, (
        f"hook exited {result.returncode}: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
