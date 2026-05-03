"""spec-118 T-3.3 -- top-K retrieval with decay-aware rerank.

Score formula: `decayed_importance(item, now) * cosine_similarity(query, item)`.
Decay: `importance * 0.97 ** days_since_last_seen` (D-118 spec / dreaming.py).
Cosine similarity is delegated to sqlite-vec (`vec_distance_cosine`).

Filters: kind ('episode' | 'knowledge'), since (ISO date or '7d').
Optional MMR placeholder; v1 returns top-K by combined score.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import struct
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

DEFAULT_TOP_K = 10
DECAY_BASE = 0.97
SECONDS_PER_DAY = 86400.0


@dataclass(frozen=True)
class Hit:
    target_kind: str
    target_id: str
    score: float
    cosine: float
    decayed_importance: float
    importance: float
    days_old: float
    summary: str | None
    source_path: str | None


def _iso_now() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_since(value: str | None) -> datetime | None:
    """Parse a relative window (`7d`/`2h`/`30m`) or ISO-8601 timestamp.

    Earlier versions silently returned None for malformed input (e.g.
    ``since="last week"`` or ``since="7days"``), and ``search()`` then treated
    None as "no filter" — callers had no way to distinguish "no filter" from
    "bad filter". Now raises ValueError on unparseable input so the caller can
    surface a clear error.
    """
    if not value:
        return None
    m = re.fullmatch(r"(\d+)([dhm])", value.strip())
    if m:
        n, unit = int(m.group(1)), m.group(2)
        delta = {"d": timedelta(days=n), "h": timedelta(hours=n), "m": timedelta(minutes=n)}[unit]
        return datetime.now(tz=UTC) - delta
    parsed = _parse_iso(value)
    if parsed is None:
        raise ValueError(f"Invalid `since` value {value!r}; expected '7d'/'2h'/'30m' or ISO-8601")
    return parsed


def _serialize_f32(vector: list[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


def _decay(
    importance: float, last_seen: datetime | None, *, base: float = DECAY_BASE
) -> tuple[float, float]:
    """Return (decayed_importance, days_old)."""
    if last_seen is None:
        return importance, 0.0
    now = datetime.now(tz=UTC)
    days = max(0.0, (now - last_seen).total_seconds() / SECONDS_PER_DAY)
    return importance * (base**days), days


def _cosine_from_distance(distance: float) -> float:
    """sqlite-vec returns cosine distance; convert to similarity."""
    return max(-1.0, min(1.0, 1.0 - distance))


def _hash_query(query: str) -> str:
    canonical = re.sub(r"\s+", " ", query.strip())
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _resolve_episode(
    conn: sqlite3.Connection, episode_id: str
) -> tuple[str | None, str | None, datetime | None, float]:
    row = conn.execute(
        "SELECT summary, last_seen_at, importance FROM episodes WHERE episode_id = ?",
        (episode_id,),
    ).fetchone()
    if row is None:
        return None, None, None, 0.0
    return row["summary"], None, _parse_iso(row["last_seen_at"]), float(row["importance"])


def _resolve_ko(
    conn: sqlite3.Connection, ko_hash: str
) -> tuple[str | None, str | None, datetime | None, float]:
    row = conn.execute(
        "SELECT canonical_text, source_path, last_seen_at, importance, archived "
        "FROM knowledge_objects WHERE ko_hash = ?",
        (ko_hash,),
    ).fetchone()
    if row is None or row["archived"]:
        return None, None, None, 0.0
    return (
        row["canonical_text"],
        row["source_path"],
        _parse_iso(row["last_seen_at"]),
        float(row["importance"]),
    )


def search(
    project_root: Path,
    *,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    kind_filter: str | None = None,
    since: str | None = None,
    session_id: str | None = None,
) -> dict:
    """Top-K retrieval. Returns dict suitable for JSON serialization."""
    from memory import audit, semantic, store

    started = time.monotonic()
    store.bootstrap(project_root)

    with store.connect(project_root) as conn:
        if not store.ensure_vector_table(conn, dim=semantic.DEFAULT_DIM):
            return {
                "status": "no_vectors",
                "message": "sqlite-vec extension not available",
                "results": [],
            }

        # spec-118 D-118-06: refuse-to-start on dim mismatch (read path).
        semantic.assert_compatible_dim(conn)

        try:
            since_dt = _parse_since(since)
        except ValueError as exc:
            return {
                "status": "bad_input",
                "message": str(exc),
                "results": [],
            }

        query_vec = semantic.query_vector(query)
        # Expand pool when kind/since filters discard most candidates so we don't
        # return an empty result while matching items exist further down the
        # ranked list. Earlier versions used a fixed `max(top_k * 5, 20)` pool
        # which silently returned zero results when knowledge objects were
        # outnumbered by episodes (or vice versa) in the corpus.
        pool_cap = 1000
        candidate_pool = max(top_k * 5, 20)
        hits: list[Hit] = []
        seen_ids: set[tuple[str, str]] = set()
        while True:
            cur = conn.execute(
                """
                SELECT vm.target_kind, vm.target_id, mv.distance
                FROM memory_vectors mv
                JOIN vector_map vm ON mv.rowid = vm.rowid
                WHERE mv.embedding MATCH ?
                  AND k = ?
                ORDER BY mv.distance
                """,
                (_serialize_f32(query_vec), candidate_pool),
            )
            candidates = cur.fetchall()
            for row in candidates:
                target_kind = row["target_kind"]
                if kind_filter == "episode" and target_kind != "episode":
                    continue
                if kind_filter == "knowledge" and target_kind != "knowledge_object":
                    continue
                target_id = row["target_id"]
                key = (target_kind, target_id)
                if key in seen_ids:
                    continue
                seen_ids.add(key)
                if target_kind == "episode":
                    summary, source_path, last_seen, importance = _resolve_episode(conn, target_id)
                else:
                    summary, source_path, last_seen, importance = _resolve_ko(conn, target_id)
                if summary is None:
                    continue
                if since_dt is not None and last_seen is not None and last_seen < since_dt:
                    continue
                cosine = _cosine_from_distance(float(row["distance"]))
                decayed, days_old = _decay(importance, last_seen)
                # Negative cosine means "worse than orthogonal"; multiplying
                # by importance shouldn't invert that signal. Earlier versions
                # let high-importance dissimilar rows score below truly
                # worthless rows, breaking the rerank.
                score = decayed * max(0.0, cosine)
                hits.append(
                    Hit(
                        target_kind=target_kind,
                        target_id=target_id,
                        score=score,
                        cosine=cosine,
                        decayed_importance=decayed,
                        importance=importance,
                        days_old=days_old,
                        summary=summary,
                        source_path=source_path,
                    )
                )
            if len(hits) >= top_k or candidate_pool >= pool_cap or len(candidates) < candidate_pool:
                break
            candidate_pool = min(candidate_pool * 2, pool_cap)

        # Recency tie-break for the cosine==0 cluster (otherwise all-zero
        # scores collapse the rerank order).
        hits.sort(key=lambda h: (h.score, -h.days_old), reverse=True)
        top = hits[:top_k]

        # Bump retrieval_count + last_seen_at on returned items.
        now = _iso_now()
        for h in top:
            if h.target_kind == "episode":
                conn.execute(
                    "UPDATE episodes SET retrieval_count = retrieval_count + 1, last_seen_at = ? "
                    "WHERE episode_id = ?",
                    (now, h.target_id),
                )
            else:
                conn.execute(
                    "UPDATE knowledge_objects SET retrieval_count = retrieval_count + 1, last_seen_at = ? "
                    "WHERE ko_hash = ?",
                    (now, h.target_id),
                )

        retrieval_id = uuid4().hex
        query_hash = _hash_query(query)
        duration_ms = int((time.monotonic() - started) * 1000)
        results_payload = [
            {
                "target_kind": h.target_kind,
                "target_id": h.target_id,
                "score": round(h.score, 6),
                "cosine": round(h.cosine, 6),
                "decayed_importance": round(h.decayed_importance, 6),
                "importance": round(h.importance, 6),
                "days_old": round(h.days_old, 3),
                "summary": h.summary,
                "source_path": h.source_path,
            }
            for h in top
        ]
        conn.execute(
            """
            INSERT INTO retrieval_log (
                retrieval_id, query_text, query_hash, session_id, requested_at,
                top_k, kind_filter, since_filter, results, duration_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                retrieval_id,
                query,
                query_hash,
                session_id,
                now,
                top_k,
                kind_filter,
                since,
                json.dumps(results_payload, sort_keys=True),
                duration_ms,
            ),
        )
        conn.commit()

    audit.emit_memory_retrieved(
        project_root,
        retrieval_id=retrieval_id,
        query_hash=query_hash,
        top_k=top_k,
        result_count=len(top),
        duration_ms=duration_ms,
        session_id=session_id,
        source="cli",
    )

    return {
        "status": "ok",
        "retrieval_id": retrieval_id,
        "query_hash": query_hash,
        "duration_ms": duration_ms,
        "result_count": len(top),
        "results": results_payload,
    }
