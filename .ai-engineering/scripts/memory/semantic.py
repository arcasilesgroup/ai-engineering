"""spec-118 T-3.1 -- semantic embedding tier (fastembed + sqlite-vec).

The embedder is loaded lazily on first call so `memory.db` can be opened,
episodes written, and knowledge objects hashed without paying the ONNX model
load cost. Vec0 virtual table creation is delegated to `store.ensure_vector_table`.

Per D-118-06: refuse-to-start when an existing `vector_map` row records a
different embedding model or dim than the active embedder; the operator must
run `ai-eng memory repair --rebuild-vectors` to migrate.
"""

from __future__ import annotations

import os
import sqlite3
import struct
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class HotPathInvocationError(RuntimeError):
    """Raised when a runtime hook accidentally imports the embedder.

    `fastembed` cold-load is multi-hundred-millisecond (ONNX runtime init);
    even warm-call latency is 30-80 ms per query. That's lethal in a hook
    that fires on every PostToolUse / UserPromptSubmit / Stop. The runtime
    layer sets ``AIENG_HOOK_RUNTIME=1`` in its execution context; this
    function raises if a hook tries to take this path. Background CLI
    processes (``ai-eng memory ...``) do not set the env var and run
    normally.
    """


DEFAULT_MODEL_NAME = "BAAI/bge-small-en-v1.5"
DEFAULT_DIM = 384

_EMBED_MODEL: Any = None
_EMBED_MODEL_NAME: str | None = None


class EmbeddingDimMismatch(RuntimeError):
    """Raised when the active embedder dim does not match `vector_map`."""


def _iso_now() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _serialize_f32(vector: list[float]) -> bytes:
    """Pack a float32 vector into the binary form sqlite-vec expects."""
    return struct.pack(f"{len(vector)}f", *vector)


def _assert_not_hot_path() -> None:
    """Refuse to load the embedder from inside a runtime hook.

    Hooks set ``AIENG_HOOK_RUNTIME=1`` as part of their execution context;
    importing this module from a hook is fine (audit, model_name constants,
    `assert_compatible_dim`, `upsert_vector` against pre-computed vectors —
    none of these need the ONNX model). What is NOT fine is calling
    `_get_embedder` / `embed_batch` / `query_vector` from a hook, because
    those force the multi-hundred-ms model load on the hot path. Detected
    via env var to keep the check zero-cost on the CLI happy path.
    """
    if os.environ.get("AIENG_HOOK_RUNTIME") == "1":
        msg = (
            "fastembed must not be loaded from a runtime hook (AIENG_HOOK_RUNTIME=1 "
            "set). Defer embedding to the background CLI (memory_cmd) instead."
        )
        raise HotPathInvocationError(msg)


def _get_embedder(model_name: str = DEFAULT_MODEL_NAME):
    """Lazy import + cache the fastembed model. ONNX weights download on first use."""
    global _EMBED_MODEL, _EMBED_MODEL_NAME
    _assert_not_hot_path()
    if _EMBED_MODEL is None or model_name != _EMBED_MODEL_NAME:
        from fastembed import TextEmbedding  # type: ignore[import-not-found]

        _EMBED_MODEL = TextEmbedding(model_name=model_name)
        _EMBED_MODEL_NAME = model_name
    return _EMBED_MODEL


def embed_batch(texts: list[str], *, model_name: str = DEFAULT_MODEL_NAME) -> list[list[float]]:
    """Return one float vector per input text. Order preserved."""
    if not texts:
        return []
    embedder = _get_embedder(model_name)
    return [list(v) for v in embedder.embed(texts)]


def assert_compatible_dim(
    conn: sqlite3.Connection,
    *,
    model_name: str = DEFAULT_MODEL_NAME,
    dim: int = DEFAULT_DIM,
) -> None:
    """Refuse-to-start guard: existing rows must match (model, dim)."""
    cur = conn.execute(
        "SELECT DISTINCT embedding_model, embedding_dim FROM vector_map "
        "WHERE embedding_model != ? OR embedding_dim != ? LIMIT 1",
        (model_name, dim),
    )
    row = cur.fetchone()
    if row is None:
        return
    msg = (
        f"vector_map carries embedding_model={row[0]!r} dim={row[1]} which differs "
        f"from active embedder ({model_name}, dim={dim}). Run "
        "`ai-eng memory repair --rebuild-vectors` to migrate."
    )
    raise EmbeddingDimMismatch(msg)


def upsert_vector(
    conn: sqlite3.Connection,
    *,
    target_kind: str,
    target_id: str,
    vector: list[float],
    model_name: str = DEFAULT_MODEL_NAME,
    dim: int = DEFAULT_DIM,
) -> int:
    """Insert into `vector_map` + `memory_vectors`. Returns rowid."""
    if len(vector) != dim:
        msg = f"vector length {len(vector)} does not match dim {dim}"
        raise ValueError(msg)
    cur = conn.execute(
        """
        INSERT OR IGNORE INTO vector_map (
            target_kind, target_id, embedding_model, embedding_dim, created_at
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (target_kind, target_id, model_name, dim, _iso_now()),
    )
    rowid = cur.lastrowid
    if not rowid:
        cur2 = conn.execute(
            "SELECT rowid FROM vector_map WHERE target_kind=? AND target_id=? AND embedding_model=?",
            (target_kind, target_id, model_name),
        )
        rowid = cur2.fetchone()[0]
    conn.execute(
        "INSERT OR REPLACE INTO memory_vectors(rowid, embedding) VALUES (?, ?)",
        (rowid, _serialize_f32(vector)),
    )
    return int(rowid)


def embed_and_upsert_episode(
    project_root: Path,
    *,
    episode_id: str,
    text: str,
    model_name: str = DEFAULT_MODEL_NAME,
) -> int | None:
    """Embed an episode summary and upsert to vec0. Returns rowid or None.

    Per F-118-H2: when vec0 is unavailable we flip ``embedding_status='failed'``
    on the episode row so `ai-eng memory status` does not report it as `pending`
    forever and subsequent embed-all sweeps skip it.
    """
    from memory import store

    store.bootstrap(project_root)
    with store.connect(project_root) as conn:
        if not store.ensure_vector_table(conn, dim=DEFAULT_DIM):
            conn.execute(
                "UPDATE episodes SET embedding_status = 'failed' WHERE episode_id = ?",
                (episode_id,),
            )
            conn.commit()
            return None
        assert_compatible_dim(conn, model_name=model_name, dim=DEFAULT_DIM)
        [vector] = embed_batch([text], model_name=model_name)
        rowid = upsert_vector(
            conn,
            target_kind="episode",
            target_id=episode_id,
            vector=vector,
            model_name=model_name,
            dim=DEFAULT_DIM,
        )
        conn.execute(
            "UPDATE episodes SET embedding_status = 'complete' WHERE episode_id = ?",
            (episode_id,),
        )
        conn.commit()
        return rowid


def embed_and_upsert_ko(
    project_root: Path,
    *,
    ko_hash: str,
    text: str,
    model_name: str = DEFAULT_MODEL_NAME,
) -> int | None:
    from memory import store

    store.bootstrap(project_root)
    with store.connect(project_root) as conn:
        if not store.ensure_vector_table(conn, dim=DEFAULT_DIM):
            return None
        assert_compatible_dim(conn, model_name=model_name, dim=DEFAULT_DIM)
        [vector] = embed_batch([text], model_name=model_name)
        rowid = upsert_vector(
            conn,
            target_kind="knowledge_object",
            target_id=ko_hash,
            vector=vector,
            model_name=model_name,
            dim=DEFAULT_DIM,
        )
        conn.commit()
        return rowid


def query_vector(query: str, *, model_name: str = DEFAULT_MODEL_NAME) -> list[float]:
    """Embed a single query string for similarity search."""
    [v] = embed_batch([query], model_name=model_name)
    return v


def warmup(model_name: str = DEFAULT_MODEL_NAME) -> dict[str, Any]:
    """Pre-download ONNX weights. Returns model metadata."""
    embedder = _get_embedder(model_name)
    # Force a small embed to ensure weights are fully downloaded and cached.
    [_] = embedder.embed(["warmup"])
    return {"model_name": model_name, "dim": DEFAULT_DIM, "warmed_at": _iso_now()}
