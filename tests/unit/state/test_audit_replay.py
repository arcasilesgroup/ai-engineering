"""Unit tests for ``ai_engineering.state.audit_replay`` (spec-120 T-C5; spec-148).

Covers the public API surface and the legacy event handling:

* :func:`build_span_tree` -- forest assembly with nested children, an
  orphan whose parent is missing, and the session-vs-trace selector.
* :func:`walk_tree` -- DFS pre-order with depth threading.
* :func:`render_text` -- indent matches depth.
* :func:`render_json` -- round-trips through ``json.dumps``.
* :func:`token_rollup` -- sums every node in the visited subtree.

spec-148: the span tree is built directly from ``framework-events.ndjson``
(no SQLite). Each test writes a tmp NDJSON so the suite is hermetic and
never touches the project's real audit log.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from ai_engineering.state.audit_replay import (
    SpanNode,
    build_span_tree,
    render_json,
    render_text,
    token_rollup,
    walk_tree,
)
from ai_engineering.state.audit_rollup import NDJSON_REL

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hex16(seed: str) -> str:
    """Return a deterministic 16-hex span_id derived from ``seed``."""
    return hashlib.sha256(seed.encode()).hexdigest()[:16]


def _hex32(seed: str) -> str:
    """Return a deterministic 32-hex trace_id derived from ``seed``."""
    return hashlib.sha256(seed.encode()).hexdigest()[:32]


def _make_event(
    *,
    index: int,
    span_id: str,
    parent_span_id: str | None = None,
    trace_id: str | None = "trace-A",
    session_id: str | None = "session-A",
    kind: str = "skill_invoked",
    component: str = "hook.telemetry-skill",
    outcome: str = "success",
    detail: dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Build a minimal-but-complete synthetic event."""
    base_ts = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=index)
    iso_ts = timestamp if timestamp is not None else base_ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    event: dict[str, Any] = {
        "kind": kind,
        "engine": "claude_code",
        "timestamp": iso_ts,
        "component": component,
        "outcome": outcome,
        "correlationId": f"corr-{index:04d}",
        "schemaVersion": "1.0",
        "project": "ai-engineering",
        "spanId": span_id,
        "detail": detail if detail is not None else {"skill": "ai-brainstorm"},
    }
    if trace_id is not None:
        event["traceId"] = _hex32(trace_id) if not trace_id.startswith("0") else trace_id
    if session_id is not None:
        event["sessionId"] = session_id
    if parent_span_id is not None:
        event["parentSpanId"] = parent_span_id
    return event


def _genai_detail(
    *,
    input_tokens: int = 100,
    output_tokens: int = 50,
    total_tokens: int = 150,
    cost_usd: float = 0.001,
) -> dict[str, Any]:
    """Build a ``detail`` dict with a populated ``genai`` block."""
    return {
        "skill": "ai-brainstorm",
        "genai": {
            "system": "anthropic",
            "request": {"model": "claude-sonnet-4-5"},
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd,
            },
        },
    }


def _seed_ndjson(project_root: Path, events: list[dict[str, Any]]) -> Path:
    """Write ``events`` as NDJSON and return the path (spec-148: no SQLite)."""
    target = project_root / NDJSON_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(event, sort_keys=True) + "\n" for event in events)
    target.write_text(body, encoding="utf-8")
    return target


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Anchor a fresh project root with the standard state dir."""
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


# ---------------------------------------------------------------------------
# build_span_tree
# ---------------------------------------------------------------------------


def test_tree_built_from_synthetic_chain(project_root: Path) -> None:
    """5 events: root, two children of root, A has one child, plus an orphan.

    Expected: 2 roots -- the real root, and the orphan whose parent is
    not in the result set.
    """
    span_root = _hex16("root")
    span_a = _hex16("A")
    span_b = _hex16("B")
    span_a_child = _hex16("A-child")
    span_orphan = _hex16("orphan")
    missing_parent = _hex16("missing-parent")

    events = [
        _make_event(index=0, span_id=span_root),
        _make_event(index=1, span_id=span_a, parent_span_id=span_root),
        _make_event(index=2, span_id=span_b, parent_span_id=span_root),
        _make_event(index=3, span_id=span_a_child, parent_span_id=span_a),
        _make_event(index=4, span_id=span_orphan, parent_span_id=missing_parent),
    ]
    ndjson_path = _seed_ndjson(project_root, events)
    roots = build_span_tree(ndjson_path, session_id="session-A")

    assert len(roots) == 2
    # Real root sorts first by ts (index=0); orphan last (index=4).
    assert roots[0].span_id == span_root
    assert roots[1].span_id == span_orphan
    assert len(roots[0].children) == 2
    assert {c.span_id for c in roots[0].children} == {span_a, span_b}
    a_node = next(c for c in roots[0].children if c.span_id == span_a)
    assert len(a_node.children) == 1
    assert a_node.children[0].span_id == span_a_child


def test_dfs_walk_order(project_root: Path) -> None:
    """DFS pre-order yields parent before children, sorted by ts."""
    span_root = _hex16("root")
    span_a = _hex16("A")
    span_b = _hex16("B")
    span_a_child = _hex16("A-child")

    events = [
        _make_event(index=0, span_id=span_root),
        _make_event(index=1, span_id=span_a, parent_span_id=span_root),
        _make_event(index=2, span_id=span_a_child, parent_span_id=span_a),
        _make_event(index=3, span_id=span_b, parent_span_id=span_root),
    ]
    ndjson_path = _seed_ndjson(project_root, events)
    roots = build_span_tree(ndjson_path, session_id="session-A")

    visited = [node.span_id for node in walk_tree(roots)]
    # Pre-order: root, A, A-child, B (A sorts before B by ts).
    assert visited == [span_root, span_a, span_a_child, span_b]


def test_orphan_legacy_event_emitted_as_root(project_root: Path) -> None:
    """Events without parent_span_id all become roots, sorted by ts."""
    events = [
        _make_event(index=0, span_id=_hex16("first")),
        _make_event(index=1, span_id=_hex16("second")),
        _make_event(index=2, span_id=_hex16("third")),
    ]
    ndjson_path = _seed_ndjson(project_root, events)
    roots = build_span_tree(ndjson_path, session_id="session-A")

    assert len(roots) == 3
    assert [r.span_id for r in roots] == [
        _hex16("first"),
        _hex16("second"),
        _hex16("third"),
    ]
    assert all(not r.children for r in roots)


def test_token_rollup_sums_subtree(project_root: Path) -> None:
    """3 nodes with usage; rollup is the elementwise sum."""
    span_root = _hex16("root")
    span_a = _hex16("A")
    span_b = _hex16("B")

    events = [
        _make_event(
            index=0,
            span_id=span_root,
            detail=_genai_detail(input_tokens=10, output_tokens=5, total_tokens=15, cost_usd=0.01),
        ),
        _make_event(
            index=1,
            span_id=span_a,
            parent_span_id=span_root,
            detail=_genai_detail(input_tokens=20, output_tokens=8, total_tokens=28, cost_usd=0.02),
        ),
        _make_event(
            index=2,
            span_id=span_b,
            parent_span_id=span_root,
            detail=_genai_detail(input_tokens=30, output_tokens=11, total_tokens=41, cost_usd=0.03),
        ),
    ]
    ndjson_path = _seed_ndjson(project_root, events)
    roots = build_span_tree(ndjson_path, session_id="session-A")

    rollup = token_rollup(roots)
    assert rollup["input_tokens"] == 60
    assert rollup["output_tokens"] == 24
    assert rollup["total_tokens"] == 84
    assert rollup["cost_usd"] == pytest.approx(0.06)


def _summary_detail(*, input_tokens: int, output_tokens: int, total_tokens: int, cost_usd: float):
    """A ``session_token_rollup`` detail: it restates the whole session."""
    detail = _genai_detail(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cost_usd=cost_usd,
    )
    detail["operation"] = "session_token_rollup"
    return detail


def test_token_rollup_reduces_repeated_session_summaries_with_max(
    project_root: Path,
) -> None:
    """Four per-turn summaries are one cumulative series, not four sessions.

    ``ai-eng audit replay`` shared ``ai-eng audit tokens``' defect: each turn's
    ``session_token_rollup`` restates the cumulative session total, and summing
    them reported the sum of a monotone series. Live evidence for session
    ``69b84fb2``: ``[170922, 189500, 360422, 720844]`` rendered as 1441688
    (spec-201 B1).
    """
    events = [
        _make_event(
            index=index,
            span_id=_hex16(f"summary-{index}"),
            detail=_summary_detail(
                input_tokens=inp,
                output_tokens=out,
                total_tokens=total,
                cost_usd=cost,
            ),
        )
        for index, (inp, out, total, cost) in enumerate(
            [
                (120000, 50922, 170922, 0.10),
                (130000, 59500, 189500, 0.20),
                (250000, 110422, 360422, 0.40),
                (500000, 220844, 720844, 0.80),
            ]
        )
    ]
    ndjson_path = _seed_ndjson(project_root, events)
    roots = build_span_tree(ndjson_path, session_id="session-A")

    rollup = token_rollup(roots)

    assert rollup["total_tokens"] == 720844, "the cumulative total, not the sum of the series"
    assert rollup["input_tokens"] == 500000
    assert rollup["output_tokens"] == 220844
    assert rollup["cost_usd"] == pytest.approx(0.80)


def test_token_rollup_summary_never_undercounts_members(project_root: Path) -> None:
    """Excluding summaries from the sum must not drop real member usage."""
    events = [
        _make_event(
            index=0,
            span_id=_hex16("member-1"),
            detail=_genai_detail(input_tokens=400, output_tokens=200, total_tokens=600),
        ),
        _make_event(
            index=1,
            span_id=_hex16("member-2"),
            detail=_genai_detail(input_tokens=400, output_tokens=200, total_tokens=600),
        ),
        _make_event(
            index=2,
            span_id=_hex16("summary-1"),
            detail=_summary_detail(
                input_tokens=100, output_tokens=50, total_tokens=150, cost_usd=0.01
            ),
        ),
        _make_event(
            index=3,
            span_id=_hex16("summary-2"),
            detail=_summary_detail(
                input_tokens=200, output_tokens=100, total_tokens=300, cost_usd=0.02
            ),
        ),
    ]
    ndjson_path = _seed_ndjson(project_root, events)
    roots = build_span_tree(ndjson_path, session_id="session-A")

    rollup = token_rollup(roots)

    assert rollup["total_tokens"] == 1200  # member sum wins over summary max
    # cost = max(member_sum 2x0.001, summary_max 0.02): the larger source wins
    # per field, so a summary can still supply a cost members never carried.
    assert rollup["cost_usd"] == pytest.approx(0.02)


def test_token_rollup_ignores_missing_usage(project_root: Path) -> None:
    """Nodes without genai usage contribute zero to the sums."""
    events = [
        _make_event(index=0, span_id=_hex16("a")),  # no genai
        _make_event(
            index=1,
            span_id=_hex16("b"),
            detail=_genai_detail(input_tokens=10, output_tokens=5, total_tokens=15, cost_usd=0.01),
        ),
    ]
    ndjson_path = _seed_ndjson(project_root, events)
    roots = build_span_tree(ndjson_path, session_id="session-A")

    rollup = token_rollup(roots)
    assert rollup["input_tokens"] == 10
    assert rollup["output_tokens"] == 5
    assert rollup["total_tokens"] == 15
    assert rollup["cost_usd"] == pytest.approx(0.01)


# ---------------------------------------------------------------------------
# render_json / render_text
# ---------------------------------------------------------------------------


def test_render_json_round_trips(project_root: Path) -> None:
    """``json.dumps(render_json(...))`` succeeds and parses back."""
    span_root = _hex16("root")
    span_a = _hex16("A")
    events = [
        _make_event(index=0, span_id=span_root, detail=_genai_detail()),
        _make_event(index=1, span_id=span_a, parent_span_id=span_root),
    ]
    ndjson_path = _seed_ndjson(project_root, events)
    roots = build_span_tree(ndjson_path, session_id="session-A")

    envelope = render_json(roots)
    serialised = json.dumps(envelope, default=str)
    parsed = json.loads(serialised)
    assert "trees" in parsed
    assert len(parsed["trees"]) == 1
    assert parsed["trees"][0]["span_id"] == span_root
    assert parsed["trees"][0]["children"][0]["span_id"] == span_a
    # genai block populated for the root, absent for the child.
    assert parsed["trees"][0]["genai"] is not None
    assert parsed["trees"][0]["genai"]["system"] == "anthropic"
    assert parsed["trees"][0]["children"][0]["genai"] is None


def test_render_text_indents_by_depth(project_root: Path) -> None:
    """Indent (leading spaces) matches ``2 * depth`` for each line."""
    span_root = _hex16("root")
    span_a = _hex16("A")
    span_a_child = _hex16("A-child")
    events = [
        _make_event(index=0, span_id=span_root),
        _make_event(index=1, span_id=span_a, parent_span_id=span_root),
        _make_event(index=2, span_id=span_a_child, parent_span_id=span_a),
    ]
    ndjson_path = _seed_ndjson(project_root, events)
    roots = build_span_tree(ndjson_path, session_id="session-A")

    text = render_text(roots, color=False)
    lines = text.splitlines()
    assert len(lines) == 3
    # Depth 0 -> no leading whitespace; depth 1 -> 2 spaces; depth 2 -> 4 spaces.
    assert not lines[0].startswith(" ")
    assert lines[1].startswith("  ") and not lines[1].startswith("   ")
    assert lines[2].startswith("    ") and not lines[2].startswith("     ")


def test_render_text_color_wraps_outcome(project_root: Path) -> None:
    """``color=True`` wraps the outcome cell in ANSI escapes."""
    events = [
        _make_event(index=0, span_id=_hex16("ok"), outcome="success"),
        _make_event(index=1, span_id=_hex16("fail"), outcome="failure"),
        _make_event(index=2, span_id=_hex16("warn"), outcome="degraded"),
        _make_event(index=3, span_id=_hex16("plain"), outcome="other"),
    ]
    ndjson_path = _seed_ndjson(project_root, events)
    roots = build_span_tree(ndjson_path, session_id="session-A")

    text = render_text(roots, color=True)
    assert "\033[32m" in text  # green for success
    assert "\033[31m" in text  # red for failure
    assert "\033[33m" in text  # yellow for degraded
    assert "\033[0m" in text


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------


def test_build_span_tree_requires_session_or_trace_exclusive(project_root: Path) -> None:
    """Both / neither of session_id / trace_id raises ValueError."""
    ndjson_path = _seed_ndjson(project_root, [_make_event(index=0, span_id=_hex16("only"))])
    with pytest.raises(ValueError, match="exactly one"):
        build_span_tree(ndjson_path, session_id="x", trace_id="y")
    with pytest.raises(ValueError, match="exactly one"):
        build_span_tree(ndjson_path)


def test_build_span_tree_filters_by_trace_id(project_root: Path) -> None:
    """``--trace`` selector returns only the matching trace's events."""
    span_a = _hex16("A")
    span_b = _hex16("B")

    events = [
        _make_event(index=0, span_id=span_a, trace_id="trace-A"),
        _make_event(index=1, span_id=span_b, trace_id="trace-B"),
    ]
    ndjson_path = _seed_ndjson(project_root, events)
    roots = build_span_tree(ndjson_path, trace_id=_hex32("trace-A"))
    assert len(roots) == 1
    assert roots[0].span_id == span_a


def test_build_span_tree_returns_empty_for_unknown_filter(project_root: Path) -> None:
    """Filter that matches nothing returns an empty list (not None)."""
    ndjson_path = _seed_ndjson(project_root, [_make_event(index=0, span_id=_hex16("only"))])
    roots = build_span_tree(ndjson_path, session_id="does-not-exist")
    assert roots == []


# ---------------------------------------------------------------------------
# SpanNode + helpers
# ---------------------------------------------------------------------------


def test_spannode_dataclass_defaults() -> None:
    """SpanNode has sensible defaults for children / depth."""
    node = SpanNode(span_id="abc", parent_span_id=None, event={"span_id": "abc"})
    assert node.children == []
    assert node.depth == 0


def test_walk_tree_handles_empty_input() -> None:
    """Walking an empty forest yields nothing without raising."""
    assert list(walk_tree([])) == []


def test_render_text_handles_empty_forest() -> None:
    """``render_text`` on an empty forest returns the empty string."""
    assert render_text([], color=False) == ""


def test_render_json_handles_empty_forest() -> None:
    """``render_json`` on an empty forest returns ``{"trees": []}``."""
    assert render_json([]) == {"trees": []}


def test_token_rollup_handles_empty_forest() -> None:
    """``token_rollup`` on an empty forest returns the zero state."""
    assert token_rollup([]) == {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
    }
