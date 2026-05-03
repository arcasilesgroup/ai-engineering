"""spec-118 T-3.5 -- semantic embed + sqlite-vec upsert."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.memory


def test_query_vector_deterministic(memory_project, deterministic_embedder):
    from memory import semantic

    a = semantic.query_vector("hello world")
    b = semantic.query_vector("hello world")
    c = semantic.query_vector("hello worlds")
    assert a == b
    assert a != c


def test_serialize_f32_byte_count():
    from memory import semantic

    v = [0.0, 1.0, -1.0, 0.5]
    blob = semantic._serialize_f32(v)
    assert len(blob) == 4 * 4  # 4 floats × 4 bytes


def test_assert_compatible_dim_passes_when_empty(memory_project, deterministic_embedder):
    from memory import semantic, store

    store.bootstrap(memory_project)
    with store.connect(memory_project) as conn:
        semantic.assert_compatible_dim(conn)  # empty vector_map -> no raise


def test_assert_compatible_dim_raises_on_mismatch(memory_project):
    from memory import semantic, store

    store.bootstrap(memory_project)
    with store.connect(memory_project) as conn:
        conn.execute(
            """
            INSERT INTO vector_map (target_kind, target_id, embedding_model, embedding_dim, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("episode", "ep-1", "BAAI/bge-large-en-v1.5", 1024, "2026-01-01T00:00:00Z"),
        )
        conn.commit()
        with pytest.raises(semantic.EmbeddingDimMismatch):
            semantic.assert_compatible_dim(conn)


def test_upsert_vector_length_check(memory_project):
    from memory import semantic, store

    store.bootstrap(memory_project)
    with store.connect(memory_project) as conn:
        with pytest.raises(ValueError, match="vector length"):
            semantic.upsert_vector(
                conn,
                target_kind="episode",
                target_id="ep-1",
                vector=[0.1, 0.2],  # wrong dim
            )
