"""spec-118 T-2.6 -- knowledge object hashing and idempotent ingest."""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.memory


def test_hash_is_stable_across_whitespace(memory_project):
    from memory import knowledge

    a = knowledge.hash_text("  hello   world  ")
    b = knowledge.hash_text("hello world")
    assert a == b


def test_hash_changes_on_content_change(memory_project):
    from memory import knowledge

    a = knowledge.hash_text("hello world")
    b = knowledge.hash_text("hello worlds")
    assert a != b


def test_make_ko_rejects_unknown_kind():
    from memory import knowledge

    with pytest.raises(ValueError, match="unsupported KO kind"):
        knowledge.make_ko(text="x", kind="bogus", source_path="p")


def test_upsert_is_idempotent(memory_project):
    from memory import knowledge, store

    store.bootstrap(memory_project)
    ko = knowledge.make_ko(text="rule X", kind="lesson", source_path="LESSONS.md")
    with store.connect(memory_project) as conn:
        first = knowledge.upsert_ko(conn, ko)
        second = knowledge.upsert_ko(conn, ko)
        conn.commit()
        cur = conn.execute(
            "SELECT COUNT(*) FROM knowledge_objects WHERE ko_hash = ?", (ko.ko_hash,)
        )
        count = cur.fetchone()[0]
    assert first is True
    assert second is False
    assert count == 1


def test_ingest_lessons_parses_h2_h3(memory_project):
    from memory import knowledge, store

    store.bootstrap(memory_project)
    lessons = memory_project / ".ai-engineering" / "LESSONS.md"
    lessons.write_text(
        "# Top\n\n## Section A\n\nbody A.\n\n### Sub B\n\nbody B.\n",
        encoding="utf-8",
    )
    with store.connect(memory_project) as conn:
        added = knowledge.ingest_lessons(conn, memory_project)
        conn.commit()
        cur = conn.execute("SELECT COUNT(*) FROM knowledge_objects WHERE kind='lesson'")
        count = cur.fetchone()[0]
    assert added == 2
    assert count == 2


def test_ingest_decisions_skips_inactive(memory_project):
    from memory import knowledge, store

    store.bootstrap(memory_project)
    ds = memory_project / ".ai-engineering" / "state" / "decision-store.json"
    ds.write_text(
        json.dumps(
            {
                "decisions": [
                    {
                        "id": "DEC-001",
                        "title": "active one",
                        "description": "x",
                        "status": "active",
                    },
                    {
                        "id": "DEC-002",
                        "title": "old one",
                        "description": "y",
                        "status": "superseded",
                    },
                ]
            }
        )
    )
    with store.connect(memory_project) as conn:
        added = knowledge.ingest_decisions(conn, memory_project)
        conn.commit()
        cur = conn.execute("SELECT source_anchor FROM knowledge_objects WHERE kind='decision'")
        anchors = {row[0] for row in cur.fetchall()}
    assert added == 1
    assert anchors == {"DEC-001"}
