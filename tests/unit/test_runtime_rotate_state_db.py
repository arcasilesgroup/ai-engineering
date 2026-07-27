"""RED→GREEN: stale ``state.db`` removal in the cleanup-runtime path.

spec-148 retired the embedded SQLite ``state.db`` (files-only); the sole
sanctioned reader is the one-shot export migration in ``ai-eng update``,
which exports-then-deletes it. A pre-spec-148 ``state.db`` can still linger
on disk in an already-migrated install (no live writer touches it). The
``cleanup runtime`` surface (``runtime_rotate.py``) must reap that stale
artifact — and its WAL/SHM siblings — going forward.

These tests pin the behaviour of ``_remove_stale_state_db(root)``:

* a stale ``state.db`` (+ ``-wal`` / ``-shm``) in a tmp root is removed;
* the live JSON sources of truth (install-state / decision-store /
  ownership-map) are NEVER touched;
* idempotent — a second pass over a clean tree is a silent no-op;
* ``main()`` wires the reap into the rotation summary payload.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _module_path() -> Path:
    """Path to the canonical ``runtime_rotate.py`` script under test."""
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / ".ai-engineering" / "scripts" / "runtime_rotate.py"


@pytest.fixture
def runtime_rotate():
    """Import ``runtime_rotate`` by file path (script-style import)."""
    path = _module_path()
    assert path.exists(), f"runtime_rotate.py missing at {path}"
    spec = importlib.util.spec_from_file_location("runtime_rotate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def state_dir(tmp_path: Path) -> Path:
    """A tmp ``.ai-engineering/state/`` skeleton."""
    d = tmp_path / ".ai-engineering" / "state"
    d.mkdir(parents=True)
    return d


def test_removes_stale_state_db_and_siblings(runtime_rotate, tmp_path: Path, state_dir: Path):
    """A stale ``state.db`` plus its WAL/SHM siblings are reaped."""
    db = state_dir / "state.db"
    wal = state_dir / "state.db-wal"
    shm = state_dir / "state.db-shm"
    db.write_bytes(b"SQLite format 3\x00stale")
    wal.write_bytes(b"wal")
    shm.write_bytes(b"shm")

    result = runtime_rotate._remove_stale_state_db(tmp_path)

    assert not db.exists(), "stale state.db must be removed"
    assert not wal.exists(), "state.db-wal sibling must be removed"
    assert not shm.exists(), "state.db-shm sibling must be removed"
    assert result["deleted"] == 3


def test_no_state_db_is_silent_noop(runtime_rotate, tmp_path: Path, state_dir: Path):
    """A tree with no ``state.db`` reaps nothing (idempotent)."""
    result = runtime_rotate._remove_stale_state_db(tmp_path)
    assert result["deleted"] == 0
    assert result["bytes_freed"] == 0


def test_never_touches_live_json_sources_of_truth(runtime_rotate, tmp_path: Path, state_dir: Path):
    """install-state / decision-store / ownership-map JSON SoTs are preserved."""
    db = state_dir / "state.db"
    db.write_bytes(b"stale")
    sot_files = {
        "install-state.json": {"version": 1},
        "decision-store.json": {"decisions": []},
        "ownership-map.json": {"paths": []},
    }
    for name, payload in sot_files.items():
        (state_dir / name).write_text(json.dumps(payload), encoding="utf-8")

    runtime_rotate._remove_stale_state_db(tmp_path)

    assert not db.exists(), "stale state.db must be removed"
    for name, payload in sot_files.items():
        path = state_dir / name
        assert path.exists(), f"{name} (a live JSON SoT) must NOT be deleted"
        assert json.loads(path.read_text(encoding="utf-8")) == payload


def test_main_payload_includes_state_db_reap(runtime_rotate, tmp_path, monkeypatch):
    """``main()`` wires the reap into the rotation summary payload."""
    # Repoint the module-level ROOT/derived paths at a clean tmp root so the
    # real rotation runs against an isolated tree (no side effects on the repo).
    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    runtime_dir = tmp_path / ".ai-engineering" / "runtime"
    runtime_dir.mkdir(parents=True)
    (state / "state.db").write_bytes(b"stale")

    monkeypatch.setattr(runtime_rotate, "ROOT", tmp_path)
    monkeypatch.setattr(runtime_rotate, "RUNTIME_DIR", runtime_dir)
    monkeypatch.setattr(runtime_rotate, "TOOL_OUTPUTS_DIR", runtime_dir / "tool-outputs")
    monkeypatch.setattr(runtime_rotate, "AUTOPILOT_DIR", runtime_dir / "autopilot")
    monkeypatch.setattr(runtime_rotate, "TOOL_HISTORY", runtime_dir / "tool-history.ndjson")

    rc = runtime_rotate.main([])

    assert rc == 0
    assert not (state / "state.db").exists(), "main() should reap the stale state.db"


# ---------------------------------------------------------------------------
# spec-200 D-200-06 — reap the orphaned legacy ``state/runtime/`` directory
# ---------------------------------------------------------------------------


def test_removes_legacy_runtime_dir(runtime_rotate, tmp_path: Path, state_dir: Path):
    """The orphaned ``state/runtime/`` tree is reaped once nothing writes it.

    spec-125 relocated the runtime subtree; spec-200 D-200-03 moved the last
    writers off the old path. What remains on an upgraded machine is an orphan
    directory holding transient session files. It is gitignored, so git never
    sees it — but ``test_forbidden_dirs_absent`` asserts on the filesystem, so
    a developer who keeps the orphan keeps failing that guard on correct code.
    """
    legacy = state_dir / "runtime"
    legacy.mkdir()
    (legacy / "session-pointer.json").write_text('{"session_id": "x"}', encoding="utf-8")
    (legacy / "trace-context.json").write_text('{"traceId": "y"}', encoding="utf-8")

    result = runtime_rotate._remove_legacy_runtime_dir(tmp_path)

    assert not legacy.exists(), "the orphaned state/runtime/ tree must be removed"
    assert result["deleted"] == 1
    assert result["bytes_freed"] > 0


def test_no_legacy_runtime_dir_is_silent_noop(runtime_rotate, tmp_path: Path, state_dir: Path):
    """A tree with no legacy runtime dir reaps nothing (idempotent)."""
    first = runtime_rotate._remove_legacy_runtime_dir(tmp_path)
    assert first == {"deleted": 0, "bytes_freed": 0}

    legacy = state_dir / "runtime"
    legacy.mkdir()
    (legacy / "trace-context.json").write_text("{}", encoding="utf-8")
    runtime_rotate._remove_legacy_runtime_dir(tmp_path)
    second = runtime_rotate._remove_legacy_runtime_dir(tmp_path)
    assert second == {"deleted": 0, "bytes_freed": 0}, "a second pass must be a no-op"


def test_legacy_runtime_reap_spares_unknown_entries(
    runtime_rotate, tmp_path: Path, state_dir: Path
):
    """An unrecognised file blocks the reap — never destroy operator data.

    The reaper removes a whole directory tree rather than named files, so it
    confirms scope first. Anything not on the known-transient list means a human
    (or an unknown writer) put something there, and a cleanup pass is the wrong
    place to find out what it was.
    """
    legacy = state_dir / "runtime"
    legacy.mkdir()
    (legacy / "trace-context.json").write_text("{}", encoding="utf-8")
    surprise = legacy / "operator-notes.txt"
    surprise.write_text("do not delete me", encoding="utf-8")

    result = runtime_rotate._remove_legacy_runtime_dir(tmp_path)

    assert legacy.exists(), "an unknown entry must block the reap"
    assert surprise.read_text(encoding="utf-8") == "do not delete me"
    assert result["deleted"] == 0


def test_legacy_runtime_reap_never_touches_state_root(
    runtime_rotate, tmp_path: Path, state_dir: Path
):
    """The audit ledgers and JSON SoTs at ``state/`` root are never in scope."""
    legacy = state_dir / "runtime"
    legacy.mkdir()
    (legacy / "trace-context.json").write_text("{}", encoding="utf-8")
    sot_files = {
        "install-state.json": {"version": 1},
        "decision-store.json": {"decisions": []},
        "framework-events.ndjson": None,
    }
    for name, payload in sot_files.items():
        path = state_dir / name
        if payload is None:
            path.write_text('{"schema":"framework_event/1"}\n', encoding="utf-8")
        else:
            path.write_text(json.dumps(payload), encoding="utf-8")

    runtime_rotate._remove_legacy_runtime_dir(tmp_path)

    assert not legacy.exists()
    for name in sot_files:
        assert (state_dir / name).exists(), f"{name} at state/ root must NOT be touched"


def test_main_payload_includes_legacy_runtime_reap(runtime_rotate, tmp_path, monkeypatch):
    """``main()`` wires the legacy-dir reap into the rotation summary payload."""
    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    runtime_dir = tmp_path / ".ai-engineering" / "runtime"
    runtime_dir.mkdir(parents=True)
    legacy = state / "runtime"
    legacy.mkdir()
    (legacy / "trace-context.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(runtime_rotate, "ROOT", tmp_path)
    monkeypatch.setattr(runtime_rotate, "RUNTIME_DIR", runtime_dir)
    monkeypatch.setattr(runtime_rotate, "TOOL_OUTPUTS_DIR", runtime_dir / "tool-outputs")
    monkeypatch.setattr(runtime_rotate, "AUTOPILOT_DIR", runtime_dir / "autopilot")
    monkeypatch.setattr(runtime_rotate, "TOOL_HISTORY", runtime_dir / "tool-history.ndjson")

    rc = runtime_rotate.main([])

    assert rc == 0
    assert not legacy.exists(), "main() should reap the orphaned state/runtime/ dir"
