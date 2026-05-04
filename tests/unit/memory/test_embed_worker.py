"""Tests for the embed_worker module (P2.2 / 2026-05-04 gap closure).

The deferred Phase 3 worker — episodes were stuck on
``embedding_status='pending'`` so cross-session retrieval fell back to
text search instead of vector cosine. This module is the missing
background processor that drains the queue.

Tests stub the heavy ``semantic.embed_and_upsert_episode`` call so the
fastembed cold-load (~30 s) doesn't blow the test budget; the real
embed path is exercised in spec-118's existing
``tests/unit/memory/test_semantic.py``.
"""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[3]
EMBED_WORKER_PATH = REPO / ".ai-engineering" / "scripts" / "memory" / "embed_worker.py"
MEMORY_DIR = REPO / ".ai-engineering" / "scripts" / "memory"


def _load_worker_with_path():
    """Import embed_worker fresh with the canonical scripts dir on sys.path."""
    scripts_dir = str(MEMORY_DIR.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    sys.modules.pop("memory.embed_worker", None)
    sys.modules.pop("aieng_embed_worker_test", None)
    spec = importlib.util.spec_from_file_location("aieng_embed_worker_test", EMBED_WORKER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aieng_embed_worker_test"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def synthetic_db(tmp_path: Path) -> Path:
    """Build a tmp memory.db with N pending episode rows."""
    project_root = tmp_path / "synthetic-embed"
    state = project_root / ".ai-engineering" / "state"
    state.mkdir(parents=True)

    # Bootstrap the schema using the canonical store module so the
    # CHECK constraint on embedding_status matches production.
    sys.path.insert(0, str(MEMORY_DIR.parent))
    from memory import store

    store.bootstrap(project_root)
    with store.connect(project_root) as conn:
        for i in range(10):
            conn.execute(
                """
                INSERT INTO episodes (
                    episode_id, session_id, started_at, ended_at, duration_sec,
                    plane, active_specs, tools_used, skill_invocations,
                    agents_dispatched, files_touched, outcomes, summary,
                    importance, last_seen_at, embedding_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """,
                (
                    f"episode-{i:03d}-test",
                    f"session-{i:03d}",
                    "2026-05-04T00:00:00Z",
                    "2026-05-04T00:01:00Z",
                    60,
                    "test-plane",
                    "[]",
                    "{}",
                    "[]",
                    "[]",
                    "[]",
                    "{}",
                    f"summary text for episode {i}",
                    0.5,
                    "2026-05-04T00:01:00Z",
                ),
            )
        conn.commit()
    return project_root


def test_run_once_processes_all_pending(synthetic_db: Path) -> None:
    """10 pending rows + stubbed embedder → 10 succeeded, 0 failed."""
    mod = _load_worker_with_path()

    # Stub the actual embedder so the test does not touch fastembed/ONNX.
    # The stub returns rowid=1 for every call and flips embedding_status
    # to 'complete' to mirror production semantics.
    def fake_embed(project_root, *, episode_id, text, model_name=None):
        from memory import store

        with store.connect(project_root) as conn:
            conn.execute(
                "UPDATE episodes SET embedding_status = 'complete' WHERE episode_id = ?",
                (episode_id,),
            )
            conn.commit()
        return 1

    with patch("memory.semantic.embed_and_upsert_episode", side_effect=fake_embed):
        report = mod.run_once(synthetic_db, batch_size=64)

    assert report.processed == 10
    assert report.succeeded == 10
    assert report.failed == 0

    # All rows should be 'complete' after the run.
    db_path = synthetic_db / ".ai-engineering" / "state" / "memory.db"
    conn = sqlite3.connect(db_path)
    try:
        pending = conn.execute(
            "SELECT COUNT(*) FROM episodes WHERE embedding_status = 'pending'"
        ).fetchone()[0]
        complete = conn.execute(
            "SELECT COUNT(*) FROM episodes WHERE embedding_status = 'complete'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert pending == 0
    assert complete == 10


def test_run_once_empty_queue_exits_zero(tmp_path: Path) -> None:
    """Empty pending queue → processed=0, no error."""
    mod = _load_worker_with_path()

    project_root = tmp_path / "empty-embed"
    state = project_root / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    sys.path.insert(0, str(MEMORY_DIR.parent))
    from memory import store

    store.bootstrap(project_root)

    report = mod.run_once(project_root, batch_size=32)
    assert report.processed == 0
    assert report.succeeded == 0
    assert report.failed == 0


def test_hot_path_guard_blocks_runtime_invocation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``AIENG_HOOK_RUNTIME=1`` must raise HotPathInvocationError so a
    future hook author cannot accidentally import the worker into a
    runtime hook."""
    mod = _load_worker_with_path()
    from memory.semantic import HotPathInvocationError

    monkeypatch.setenv("AIENG_HOOK_RUNTIME", "1")
    with pytest.raises(HotPathInvocationError):
        mod.run_once(tmp_path, batch_size=1)


def test_run_once_marks_failed_on_embedder_exception(synthetic_db: Path) -> None:
    """When the underlying embedder raises, the row is flipped to 'failed'
    so the next sweep skips it instead of looping forever."""
    mod = _load_worker_with_path()

    def boom(*_args, **_kwargs):
        raise RuntimeError("ONNX runtime explode")

    with patch("memory.semantic.embed_and_upsert_episode", side_effect=boom):
        report = mod.run_once(synthetic_db, batch_size=64)

    assert report.processed == 10
    assert report.succeeded == 0
    assert report.failed == 10

    db_path = synthetic_db / ".ai-engineering" / "state" / "memory.db"
    conn = sqlite3.connect(db_path)
    try:
        pending = conn.execute(
            "SELECT COUNT(*) FROM episodes WHERE embedding_status = 'pending'"
        ).fetchone()[0]
        failed = conn.execute(
            "SELECT COUNT(*) FROM episodes WHERE embedding_status = 'failed'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert pending == 0
    assert failed == 10


def test_batch_size_caps_processed(synthetic_db: Path) -> None:
    """``batch_size`` controls the LIMIT clause; oversized queues drain
    in subsequent passes."""
    mod = _load_worker_with_path()

    def fake_embed(project_root, *, episode_id, text, model_name=None):
        from memory import store

        with store.connect(project_root) as conn:
            conn.execute(
                "UPDATE episodes SET embedding_status = 'complete' WHERE episode_id = ?",
                (episode_id,),
            )
            conn.commit()
        return 1

    with patch("memory.semantic.embed_and_upsert_episode", side_effect=fake_embed):
        report = mod.run_once(synthetic_db, batch_size=3)

    assert report.processed == 3
    assert report.succeeded == 3
    assert report.failed == 0


def test_scheduled_wrapper_exists() -> None:
    """The cron wrapper file must exist so operators have a deterministic
    schedule entry point."""
    wrapper = REPO / ".ai-engineering" / "scripts" / "scheduled" / "memory-embed.sh"
    assert wrapper.is_file(), "missing wrapper: .ai-engineering/scripts/scheduled/memory-embed.sh"
    text = wrapper.read_text(encoding="utf-8")
    assert "ai-eng memory embed --once" in text or "memory.cli embed --once" in text
