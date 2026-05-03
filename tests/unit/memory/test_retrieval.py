"""spec-118 T-3.5 -- retrieval rerank math + filter behavior."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

pytestmark = pytest.mark.memory


def test_decay_arithmetic():
    from memory import retrieval

    now = datetime.now(tz=UTC)
    last_seen = now - timedelta(days=30)
    decayed, days = retrieval._decay(1.0, last_seen, base=0.97)
    # 0.97 ** 30 ≈ 0.4010
    assert 0.39 < decayed < 0.41
    assert 29 < days < 31


def test_decay_zero_age_keeps_importance():
    from memory import retrieval

    now = datetime.now(tz=UTC)
    decayed, days = retrieval._decay(0.5, now)
    assert decayed == pytest.approx(0.5, abs=1e-3)
    assert days < 0.001


def test_decay_none_last_seen_returns_zero_age():
    from memory import retrieval

    decayed, days = retrieval._decay(0.7, None)
    assert decayed == 0.7
    assert days == 0.0


def test_parse_since_relative():
    from memory import retrieval

    now = datetime.now(tz=UTC)
    seven_days = retrieval._parse_since("7d")
    assert seven_days is not None
    assert (now - seven_days).total_seconds() == pytest.approx(7 * 86400, abs=2)


def test_parse_since_iso():
    from memory import retrieval

    parsed = retrieval._parse_since("2026-01-15T00:00:00Z")
    assert parsed is not None
    assert parsed.year == 2026


def test_cosine_from_distance():
    from memory import retrieval

    assert retrieval._cosine_from_distance(0.0) == 1.0
    assert retrieval._cosine_from_distance(2.0) == -1.0
    assert retrieval._cosine_from_distance(1.0) == 0.0


def test_query_hash_stable_across_whitespace():
    from memory import retrieval

    a = retrieval._hash_query("hello   world")
    b = retrieval._hash_query("  hello world  ")
    assert a == b


def test_search_returns_no_vectors_when_vec0_unavailable(
    memory_project, monkeypatch, deterministic_embedder
):
    """If sqlite-vec is not loaded, search degrades gracefully."""
    from memory import retrieval, store

    monkeypatch.setattr(store, "ensure_vector_table", lambda *a, **kw: False)
    out = retrieval.search(memory_project, query="anything", top_k=5)
    assert out["status"] == "no_vectors"
    assert out["results"] == []
