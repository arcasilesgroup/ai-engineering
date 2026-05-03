"""spec-118 T-2.2 -- hash-addressed Knowledge Object writer + ingest.

Knowledge Objects are sha256-keyed facts that survive sessions. Sources:
    * LESSONS.md (one KO per ## section)
    * decision-store.json (one KO per DEC-NNN)
    * instincts.yml (corrections / recoveries / workflows)
    * arbitrary text via add_custom()

Ingestion is idempotent: re-running on unchanged content does not duplicate;
the canonical-text sha256 is the primary key. last_seen_at refreshes on every
ingest to keep dreaming's decay accurate.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LESSONS_REL = Path(".ai-engineering") / "LESSONS.md"
DECISION_STORE_REL = Path(".ai-engineering") / "state" / "decision-store.json"
INSTINCTS_REL = Path(".ai-engineering") / "instincts" / "instincts.yml"

VALID_KINDS = frozenset(
    {"lesson", "decision", "correction", "recovery", "workflow", "spec_delta", "custom"}
)


@dataclass(frozen=True)
class KnowledgeObject:
    ko_hash: str
    canonical_text: str
    kind: str
    source_path: str
    source_anchor: str | None
    metadata: dict[str, Any]
    importance: float = 0.5


def _iso_now() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonicalize(text: str) -> str:
    """Normalize whitespace; sha256 must be stable across whitespace edits."""
    collapsed = re.sub(r"\s+", " ", text.strip())
    return collapsed


def hash_text(text: str) -> str:
    """sha256 of canonicalized text. The KO primary key."""
    canonical = _canonicalize(text)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def make_ko(
    *,
    text: str,
    kind: str,
    source_path: str,
    source_anchor: str | None = None,
    metadata: dict[str, Any] | None = None,
    importance: float = 0.5,
) -> KnowledgeObject:
    if kind not in VALID_KINDS:
        msg = f"unsupported KO kind: {kind!r}"
        raise ValueError(msg)
    canonical = _canonicalize(text)
    return KnowledgeObject(
        ko_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        canonical_text=canonical,
        kind=kind,
        source_path=source_path,
        source_anchor=source_anchor,
        metadata=metadata or {},
        importance=max(0.0, min(1.0, importance)),
    )


def upsert_ko(conn: sqlite3.Connection, ko: KnowledgeObject) -> bool:
    """Insert or refresh last_seen_at. Returns True if newly inserted."""
    now = _iso_now()
    cur = conn.execute("SELECT 1 FROM knowledge_objects WHERE ko_hash = ?", (ko.ko_hash,))
    exists = cur.fetchone() is not None
    if exists:
        conn.execute(
            "UPDATE knowledge_objects SET last_seen_at = ? WHERE ko_hash = ?",
            (now, ko.ko_hash),
        )
        return False
    conn.execute(
        """
        INSERT INTO knowledge_objects (
            ko_hash, canonical_text, kind, source_path, source_anchor,
            metadata, importance, created_at, last_seen_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ko.ko_hash,
            ko.canonical_text,
            ko.kind,
            ko.source_path,
            ko.source_anchor,
            json.dumps(ko.metadata, sort_keys=True),
            ko.importance,
            now,
            now,
        ),
    )
    return True


# ---------------------------------------------------------------------------
# Source-specific ingest
# ---------------------------------------------------------------------------

_LESSON_HEADING_RE = re.compile(r"^(#{2,3})\s+(.+?)\s*$", re.MULTILINE)


def _split_lessons(text: str) -> list[tuple[str, str]]:
    """Return [(anchor, body), ...] one per H2/H3 section."""
    matches = list(_LESSON_HEADING_RE.finditer(text))
    if not matches:
        return []
    out: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        anchor = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            out.append((anchor, body))
    return out


def ingest_lessons(conn: sqlite3.Connection, project_root: Path) -> int:
    """Upsert every section in LESSONS.md as a `lesson` KO. Returns added count."""
    path = project_root / LESSONS_REL
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    sections = _split_lessons(text)
    added = 0
    for anchor, body in sections:
        ko = make_ko(
            text=body,
            kind="lesson",
            source_path=str(LESSONS_REL),
            source_anchor=anchor,
            importance=0.7,
        )
        if upsert_ko(conn, ko):
            added += 1
    return added


def ingest_decisions(conn: sqlite3.Connection, project_root: Path) -> int:
    """Upsert every active DEC-NNN as a `decision` KO. Returns added count."""
    path = project_root / DECISION_STORE_REL
    if not path.exists():
        return 0
    try:
        store = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0
    decisions = store.get("decisions") if isinstance(store, dict) else store
    if not isinstance(decisions, list):
        return 0
    added = 0
    for entry in decisions:
        if not isinstance(entry, dict):
            continue
        if entry.get("status") not in (None, "active"):
            continue
        dec_id = entry.get("id")
        title = entry.get("title", "")
        description = entry.get("description") or entry.get("decision") or ""
        if not (dec_id and (title or description)):
            continue
        text = f"{title}\n\n{description}".strip()
        importance = {"high": 0.9, "medium": 0.6, "low": 0.4}.get(
            entry.get("criticality", "medium"), 0.6
        )
        ko = make_ko(
            text=text,
            kind="decision",
            source_path=str(DECISION_STORE_REL),
            source_anchor=str(dec_id),
            metadata={
                "category": entry.get("category"),
                "spec": entry.get("spec"),
                "source": entry.get("source"),
            },
            importance=importance,
        )
        if upsert_ko(conn, ko):
            added += 1
    return added


def _yaml_safe_load(text: str) -> Any:
    try:
        import yaml  # type: ignore[import-not-found]

        return yaml.safe_load(text)
    except Exception:
        return None


def ingest_instincts(conn: sqlite3.Connection, project_root: Path) -> int:
    """Upsert corrections/recoveries/workflows from instincts.yml."""
    path = project_root / INSTINCTS_REL
    if not path.exists():
        return 0
    parsed = _yaml_safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        return 0
    added = 0
    for family, ko_kind in (
        ("corrections", "correction"),
        ("recoveries", "recovery"),
        ("workflows", "workflow"),
    ):
        entries = parsed.get(family) or []
        if not isinstance(entries, list):
            continue
        for idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            text_parts = [
                str(entry.get("trigger") or ""),
                str(entry.get("action") or ""),
                str(entry.get("rule") or ""),
                str(entry.get("description") or ""),
            ]
            text = "\n".join(p for p in text_parts if p).strip()
            if not text:
                continue
            confidence = float(entry.get("confidence", 0.5) or 0.5)
            ko = make_ko(
                text=text,
                kind=ko_kind,
                source_path=str(INSTINCTS_REL),
                source_anchor=f"{family}[{idx}]",
                metadata={
                    "evidenceCount": entry.get("evidenceCount"),
                    "domain": entry.get("domain"),
                    "lastSeen": entry.get("lastSeen"),
                },
                importance=max(0.0, min(1.0, confidence)),
            )
            if upsert_ko(conn, ko):
                added += 1
    return added


def ingest_all(conn: sqlite3.Connection, project_root: Path) -> dict[str, int]:
    """Run every ingest source. Returns per-source added counts."""
    return {
        "lesson": ingest_lessons(conn, project_root),
        "decision": ingest_decisions(conn, project_root),
        "instinct": ingest_instincts(conn, project_root),
    }
