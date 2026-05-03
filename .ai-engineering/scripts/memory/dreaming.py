"""spec-118 T-4.1 -- consolidation loop (decay + cluster + supersede + propose).

Pipeline (per spec-118):
    1. apply_decay     -> importance' = importance * decay_base ** days_since_last_seen
    2. cluster         -> HDBSCAN over knowledge_object embeddings
    3. mark supersede  -> per cluster, lower-importance dups get superseded_by = representative
    4. archive         -> any KO with decayed_importance < archive_threshold flips archived=1
    5. propose         -> high-confidence clusters get a candidate written to memory-proposals.md

D-118-04: NEVER mutate LESSONS.md. Promotion candidates land in
`.ai-engineering/instincts/memory-proposals.md` for human review.
D-118-05: small-corpus early-exit at < HDBSCAN_MIN_TOTAL knowledge objects.
WARN-5: explicit MEMORY_PROPOSALS_REL constant; never resolve dynamically.
"""

from __future__ import annotations

import sqlite3
import struct
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

DECAY_BASE = 0.97
ARCHIVE_THRESHOLD = 0.1
HDBSCAN_MIN_TOTAL = 30
DEFAULT_MIN_CLUSTER_SIZE = 3
SECONDS_PER_DAY = 86400.0

MEMORY_PROPOSALS_REL = Path(".ai-engineering") / "instincts" / "memory-proposals.md"


@dataclass(frozen=True)
class DreamReport:
    decay_factor: float
    decayed_count: int
    clusters_found: int
    promoted_count: int
    retired_count: int
    proposals_path: str
    duration_ms: int
    outcome: str
    dry_run: bool


def _iso_now() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _decayed(importance: float, last_seen: datetime | None, base: float) -> float:
    if last_seen is None:
        return importance
    days = max(0.0, (datetime.now(tz=UTC) - last_seen).total_seconds() / SECONDS_PER_DAY)
    return importance * (base**days)


def _deserialize_f32(blob: bytes, dim: int) -> list[float]:
    return list(struct.unpack(f"{dim}f", blob))


def apply_decay(
    conn: sqlite3.Connection, *, base: float = DECAY_BASE
) -> tuple[int, list[tuple[str, float]]]:
    """Return (count, [(ko_hash, decayed_importance), ...]).

    Does not mutate the database; callers decide whether to archive based on
    the decayed values. The original `importance` stays as the canonical
    weight; archival flips the `archived` column.
    """
    rows = conn.execute(
        "SELECT ko_hash, importance, last_seen_at FROM knowledge_objects WHERE archived = 0"
    ).fetchall()
    out: list[tuple[str, float]] = []
    for r in rows:
        decayed = _decayed(r["importance"], _parse_iso(r["last_seen_at"]), base)
        out.append((r["ko_hash"], decayed))
    return len(rows), out


def archive_below_threshold(
    conn: sqlite3.Connection,
    decayed: list[tuple[str, float]],
    *,
    threshold: float = ARCHIVE_THRESHOLD,
    dry_run: bool = False,
) -> list[str]:
    """Flip archived=1 for KOs whose decayed_importance < threshold."""
    candidates = [h for h, d in decayed if d < threshold]
    if not dry_run and candidates:
        conn.executemany(
            "UPDATE knowledge_objects SET archived = 1 WHERE ko_hash = ?",
            [(h,) for h in candidates],
        )
    return candidates


def _load_active_vectors(conn: sqlite3.Connection, dim: int = 384) -> list[tuple[str, list[float]]]:
    """Pull every active KO with a vector. Returns [(ko_hash, vector), ...]."""
    cur = conn.execute(
        """
        SELECT ko.ko_hash, mv.embedding
        FROM knowledge_objects ko
        JOIN vector_map vm
            ON vm.target_kind = 'knowledge_object' AND vm.target_id = ko.ko_hash
        JOIN memory_vectors mv ON mv.rowid = vm.rowid
        WHERE ko.archived = 0
        """
    )
    out: list[tuple[str, list[float]]] = []
    for r in cur.fetchall():
        try:
            out.append((r["ko_hash"], _deserialize_f32(bytes(r["embedding"]), dim)))
        except struct.error:
            continue
    return out


def cluster_with_hdbscan(
    vectors: list[tuple[str, list[float]]],
    *,
    min_cluster_size: int = DEFAULT_MIN_CLUSTER_SIZE,
) -> dict[int, list[str]]:
    """Return {cluster_id: [ko_hash, ...]}. -1 means noise (unclustered)."""
    if len(vectors) < HDBSCAN_MIN_TOTAL:
        return {}
    try:
        import hdbscan  # type: ignore[import-not-found]
        import numpy as np
    except ImportError:
        return {}
    matrix = np.array([v for _, v in vectors], dtype=np.float32)
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        metric="euclidean",
        cluster_selection_method="eom",
    )
    labels = clusterer.fit_predict(matrix)
    clusters: dict[int, list[str]] = {}
    for (ko_hash, _), label in zip(vectors, labels, strict=True):
        if label == -1:
            continue
        clusters.setdefault(int(label), []).append(ko_hash)
    return clusters


def mark_supersedence(
    conn: sqlite3.Connection,
    clusters: dict[int, list[str]],
    decayed_map: dict[str, float],
    *,
    dry_run: bool = False,
) -> list[tuple[str, str]]:
    """Within each cluster, the highest decayed_importance becomes the rep.

    Other members get `superseded_by = rep_hash`. Returns [(superseded, rep)].
    """
    pairs: list[tuple[str, str]] = []
    for members in clusters.values():
        if len(members) < 2:
            continue
        ranked = sorted(members, key=lambda h: decayed_map.get(h, 0.0), reverse=True)
        rep = ranked[0]
        for other in ranked[1:]:
            pairs.append((other, rep))
    if not dry_run and pairs:
        conn.executemany(
            "UPDATE knowledge_objects SET superseded_by = ? WHERE ko_hash = ?",
            [(rep, sup) for sup, rep in pairs],
        )
    return pairs


def propose_promotions(
    project_root: Path,
    clusters: dict[int, list[str]],
    decayed_map: dict[str, float],
    *,
    promotion_threshold: float = 0.6,
    dry_run: bool = False,
) -> list[str]:
    """Write candidate promotions to memory-proposals.md. Returns rep hashes.

    Per D-118-04 NEVER mutate LESSONS.md. Per WARN-5 the path is a fixed
    constant, resolved against project_root. Format mirrors the existing
    `instincts/proposals.md` review pattern.
    """
    promoted: list[str] = []
    rep_blocks: list[str] = []
    for cid, members in clusters.items():
        if len(members) < 2:
            continue
        ranked = sorted(members, key=lambda h: decayed_map.get(h, 0.0), reverse=True)
        rep = ranked[0]
        rep_score = decayed_map.get(rep, 0.0)
        if rep_score < promotion_threshold:
            continue
        promoted.append(rep)
        rep_blocks.append(
            f"- **cluster {cid}**: representative `{rep}` (score={rep_score:.3f}, "
            f"members={len(members)})\n"
        )

    if not promoted:
        return []
    target = project_root / MEMORY_PROPOSALS_REL
    if dry_run:
        return promoted
    target.parent.mkdir(parents=True, exist_ok=True)
    header = f"\n## Dream cycle {_iso_now()}\n\n"
    body = "".join(rep_blocks)
    if not target.exists():
        target.write_text(
            "# Memory Promotion Proposals\n\n"
            "spec-118 dreaming writes candidate lesson promotions here for "
            "human review. LESSONS.md is never auto-mutated (D-118-04).\n",
            encoding="utf-8",
        )
    with target.open("a", encoding="utf-8") as f:
        f.write(header)
        f.write(body)
    return promoted


def run_dream(
    project_root: Path,
    *,
    dry_run: bool = False,
    decay_only: bool = False,
    min_cluster_size: int = DEFAULT_MIN_CLUSTER_SIZE,
    decay_base: float = DECAY_BASE,
) -> DreamReport:
    """End-to-end consolidation. Emits one `memory_event/dream_run` audit record."""
    from memory import audit, store

    started = time.monotonic()
    store.bootstrap(project_root)
    proposals_path = project_root / MEMORY_PROPOSALS_REL

    with store.connect(project_root) as conn:
        decayed_count, decayed = apply_decay(conn, base=decay_base)
        decayed_map = dict(decayed)

        if decay_only:
            retired_count = 0
            clusters: dict[int, list[str]] = {}
            promoted: list[str] = []
        else:
            retired = archive_below_threshold(conn, decayed, dry_run=dry_run)
            retired_count = len(retired)

            if decayed_count < HDBSCAN_MIN_TOTAL:
                clusters = {}
            else:
                store.ensure_vector_table(conn)
                # spec-118 D-118-06: refuse-to-start on dim mismatch (consolidation path).
                from memory import semantic

                semantic.assert_compatible_dim(conn)
                vectors = _load_active_vectors(conn)
                clusters = cluster_with_hdbscan(vectors, min_cluster_size=min_cluster_size)
            mark_supersedence(conn, clusters, decayed_map, dry_run=dry_run)
            promoted = propose_promotions(project_root, clusters, decayed_map, dry_run=dry_run)

        if not dry_run:
            conn.commit()

    if decayed_count < HDBSCAN_MIN_TOTAL:
        outcome = "noop_small_corpus"
    elif decay_only:
        outcome = "decay_only"
    else:
        outcome = "ok"

    duration_ms = int((time.monotonic() - started) * 1000)
    audit.emit_dream_run(
        project_root,
        decay_factor=decay_base,
        clusters_found=len(clusters),
        promoted_count=len(promoted),
        retired_count=retired_count,
        duration_ms=duration_ms,
        outcome=outcome,
        source="cli",
    )

    return DreamReport(
        decay_factor=decay_base,
        decayed_count=decayed_count,
        clusters_found=len(clusters),
        promoted_count=len(promoted),
        retired_count=retired_count,
        proposals_path=str(proposals_path),
        duration_ms=duration_ms,
        outcome=outcome,
        dry_run=dry_run,
    )
