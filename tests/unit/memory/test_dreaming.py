"""spec-118 T-4.7 -- dreaming decay + supersedence + archival math."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

pytestmark = pytest.mark.memory


def test_decayed_constant_when_last_seen_none():
    from memory import dreaming

    assert dreaming._decayed(0.7, None, 0.97) == 0.7


def test_decayed_30_days_at_base_0_97():
    from memory import dreaming

    last_seen = datetime.now(tz=UTC) - timedelta(days=30)
    decayed = dreaming._decayed(1.0, last_seen, 0.97)
    assert 0.39 < decayed < 0.41  # 0.97**30 ≈ 0.4010


def test_archive_below_threshold(memory_project):
    from memory import dreaming, knowledge, store

    store.bootstrap(memory_project)
    with store.connect(memory_project) as conn:
        for h in ("a", "b", "c"):
            ko = knowledge.make_ko(text=h, kind="lesson", source_path="x", importance=0.5)
            knowledge.upsert_ko(conn, ko)
        conn.commit()

        decayed = [
            (ko.ko_hash, 0.05)
            for ko in [
                knowledge.make_ko(text="a", kind="lesson", source_path="x"),
                knowledge.make_ko(text="b", kind="lesson", source_path="x"),
            ]
        ] + [(knowledge.make_ko(text="c", kind="lesson", source_path="x").ko_hash, 0.5)]
        archived = dreaming.archive_below_threshold(conn, decayed, threshold=0.1)
        conn.commit()
    assert len(archived) == 2


def test_mark_supersedence_picks_highest_importance(memory_project):
    from memory import dreaming, knowledge, store

    store.bootstrap(memory_project)
    rep = knowledge.make_ko(text="rep", kind="lesson", source_path="x", importance=0.9)
    other = knowledge.make_ko(text="other", kind="lesson", source_path="y", importance=0.4)
    with store.connect(memory_project) as conn:
        knowledge.upsert_ko(conn, rep)
        knowledge.upsert_ko(conn, other)
        conn.commit()

        clusters = {0: [rep.ko_hash, other.ko_hash]}
        decayed_map = {rep.ko_hash: 0.9, other.ko_hash: 0.4}
        pairs = dreaming.mark_supersedence(conn, clusters, decayed_map)
        conn.commit()
        cur = conn.execute(
            "SELECT superseded_by FROM knowledge_objects WHERE ko_hash = ?",
            (other.ko_hash,),
        )
        result = cur.fetchone()[0]
    assert pairs == [(other.ko_hash, rep.ko_hash)]
    assert result == rep.ko_hash


def test_propose_promotions_never_writes_to_lessons(memory_project):
    from memory import dreaming

    decayed_map = {"hash-a": 0.8, "hash-b": 0.7, "hash-c": 0.5}
    clusters = {0: ["hash-a", "hash-b", "hash-c"]}
    promoted = dreaming.propose_promotions(memory_project, clusters, decayed_map)
    assert promoted  # at least one promotion meets threshold
    proposals = memory_project / dreaming.MEMORY_PROPOSALS_REL
    lessons = memory_project / ".ai-engineering" / "LESSONS.md"
    assert proposals.exists()
    assert not lessons.exists()  # NEVER auto-mutate LESSONS.md
    assert "LESSONS" not in str(dreaming.MEMORY_PROPOSALS_REL)


def test_run_dream_small_corpus_early_exit(memory_project):
    """< 30 KOs short-circuits HDBSCAN per D-118-05.

    Tightened with negative side-effect assertions: the early-exit branch
    must NOT write `memory-proposals.md` and must NOT mark any KO superseded.
    """
    from memory import dreaming, knowledge, store

    store.bootstrap(memory_project)
    with store.connect(memory_project) as conn:
        for i in range(5):
            ko = knowledge.make_ko(text=f"entry {i}", kind="lesson", source_path="LESSONS.md")
            knowledge.upsert_ko(conn, ko)
        conn.commit()
    report = dreaming.run_dream(memory_project)
    assert report.outcome == "noop_small_corpus"
    assert report.clusters_found == 0
    proposals = memory_project / ".ai-engineering" / "instincts" / "memory-proposals.md"
    assert proposals.exists() is False
    with store.connect(memory_project) as conn:
        superseded = conn.execute(
            "SELECT COUNT(*) FROM knowledge_objects WHERE superseded_by IS NOT NULL"
        ).fetchone()[0]
    assert superseded == 0


def test_cluster_with_hdbscan_returns_empty_below_threshold():
    """Cluster primitive itself short-circuits below HDBSCAN_MIN_TOTAL."""
    from memory import dreaming

    sparse = [(f"ko-{i}", [0.0] * 384) for i in range(5)]
    assert dreaming.cluster_with_hdbscan(sparse) == {}


def test_cluster_with_hdbscan_drops_noise_label():
    """`label == -1` (noise) entries must NOT appear as a cluster key."""
    import sys

    if "hdbscan" not in sys.modules:
        # hdbscan is in the [memory] extra; skip when unavailable so the
        # core test lane stays green.
        import pytest

        try:
            import hdbscan  # noqa: F401
        except ImportError:
            pytest.skip("hdbscan not installed; covered by [memory] extra lane")

    import numpy as np
    from memory import dreaming

    rng = np.random.RandomState(0)
    # 30+ vectors all far apart -> HDBSCAN labels everything -1.
    vectors = [(f"ko-{i}", rng.rand(384).astype("f4").tolist()) for i in range(30)]
    clusters = dreaming.cluster_with_hdbscan(vectors, min_cluster_size=5)
    assert -1 not in clusters


def test_proposals_path_constant_is_explicit():
    """WARN-5: MEMORY_PROPOSALS_REL must be a fixed Path, never derived."""
    from memory import dreaming

    assert (
        type(dreaming.MEMORY_PROPOSALS_REL)(".ai-engineering") / "instincts" / "memory-proposals.md"
    ) == dreaming.MEMORY_PROPOSALS_REL
