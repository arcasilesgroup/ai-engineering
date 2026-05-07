"""Span tree builder + walker for the SQLite audit index (spec-120 §4.4).

Reads rows from the ``events`` table maintained by
:mod:`ai_engineering.state.audit_index` and reconstructs the per-trace
or per-session span tree that the linear NDJSON stream encodes via
``parentSpanId``. Provides text/JSON renderers and a token rollup for
the walk so the ``ai-eng audit replay`` CLI can present a session as a
human-readable, indented sequence of nested events.

Public API
----------
* :class:`SpanNode` -- one per row, threaded with ``children`` and
  ``depth`` for DFS rendering.
* :func:`build_span_tree` -- forest of :class:`SpanNode` for either a
  ``session_id`` OR a ``trace_id`` (exactly one required).
* :func:`walk_tree` -- pre-order DFS iterator that sets
  :attr:`SpanNode.depth` as it walks.
* :func:`render_text` -- indented text rendering, one line per node,
  with optional ANSI colour for the outcome cell.
* :func:`render_json` -- JSON-serializable tree dump consumable by
  future viewers.
* :func:`token_rollup` -- sum input/output/total tokens and cost across
  every node in the forest.

Legacy event handling
---------------------
Events emitted before spec-120 carry no ``traceId`` and no
``parentSpanId``. They are therefore invisible to ``--trace`` filters
(which require a non-NULL ``trace_id``). They remain visible to
``--session`` filters when their ``session_id`` matches; in that case
they surface as roots (no parent) and sort alongside any "real" roots
by ``ts_unix_ms``. Orphan events whose ``parent_span_id`` points at a
``span_id`` that is NOT present in the result set are likewise treated
as roots so the forensic surface stays complete.

Stdlib-only by design (``sqlite3`` + ``json`` + ``dataclasses``). No
third-party dependencies.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# ANSI colour codes used by :func:`render_text` when ``color=True``. The
# palette matches the conventional success/warning/failure trio without
# pulling in a third-party colour lib.
_ANSI_RESET = "\033[0m"
_ANSI_GREEN = "\033[32m"
_ANSI_YELLOW = "\033[33m"
_ANSI_RED = "\033[31m"

# Width budgets used by :func:`render_text`. Narrow enough to fit a typical
# 120-column terminal once the indent and timestamp cells are accounted for.
_KIND_WIDTH = 24
_COMPONENT_WIDTH = 32
_OUTCOME_WIDTH = 7

# SQL columns selected for span-tree construction. Keeping the projection
# explicit keeps the contract with audit_index.py honest -- if the schema
# adds a column we want, this list is the only place to update.
_EVENT_COLUMNS = (
    "span_id",
    "trace_id",
    "parent_span_id",
    "correlation_id",
    "session_id",
    "timestamp",
    "ts_unix_ms",
    "engine",
    "kind",
    "component",
    "outcome",
    "source",
    "prev_event_hash",
    "genai_system",
    "genai_model",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cost_usd",
    "detail_json",
)


# ---------------------------------------------------------------------------
# Node type
# ---------------------------------------------------------------------------


@dataclass
class SpanNode:
    """One node in the span tree.

    Attributes
    ----------
    span_id:
        Primary key from the ``events`` table -- either the canonical
        ``spanId`` or the deterministic synthetic 16-hex hash used by
        :mod:`audit_index` for legacy events without a ``spanId``.
    parent_span_id:
        Logical parent ``span_id``. ``None`` means a root span; an
        unrecognised parent (orphan) is also treated as a root by
        :func:`build_span_tree`.
    event:
        Raw row from the ``events`` table, keyed by column name. Includes
        the ``detail_json`` text blob -- callers who need decoded detail
        should ``json.loads`` it themselves.
    children:
        Direct logical children, sorted by ``ts_unix_ms`` ascending.
    depth:
        Zero-based tree depth set by :func:`walk_tree` during the DFS.
        The default value of 0 is a placeholder; rely on ``walk_tree``
        rather than ``SpanNode.depth`` if you build trees by hand.
    """

    span_id: str
    parent_span_id: str | None
    event: dict[str, Any]
    children: list[SpanNode] = field(default_factory=list)
    depth: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
    """Normalise a SQLite row into a column-keyed dict.

    Tolerates both ``sqlite3.Row`` (which behaves like a mapping when the
    connection has its row factory set) and a plain tuple (the default).
    Tests that build SpanNodes by hand can pass any dict that satisfies
    the schema -- this helper is only used on the SQL boundary.
    """
    if isinstance(row, dict):
        return dict(row)
    keys_callable = getattr(row, "keys", None)
    if keys_callable is not None:
        # sqlite3.Row exposes column names via ``.keys()`` and indexes by
        # name -- iteration yields values, so we can't use ``key in row``.
        return {key: row[key] for key in keys_callable()}
    # Plain tuple path -- pair positionally with the column projection used
    # in :func:`_fetch_rows`.
    return dict(zip(_EVENT_COLUMNS, row, strict=True))


def _fetch_rows(
    conn: sqlite3.Connection,
    *,
    session_id: str | None,
    trace_id: str | None,
) -> list[dict[str, Any]]:
    """Run the filtered SELECT and return rows as column-keyed dicts.

    Exactly one of ``session_id`` / ``trace_id`` is set when this is
    called -- :func:`build_span_tree` validates that contract before us.
    Rows are returned in arbitrary order; sorting happens during tree
    assembly so children land in their parent's ts_unix_ms-ascending list.
    """
    columns = ", ".join(_EVENT_COLUMNS)
    if session_id is not None:
        sql = f"SELECT {columns} FROM events WHERE session_id = ?"
        params: tuple[Any, ...] = (session_id,)
    else:
        sql = f"SELECT {columns} FROM events WHERE trace_id = ?"
        params = (trace_id,)
    cur = conn.execute(sql, params)
    return [_row_to_dict(row) for row in cur.fetchall()]


def _ts_unix_ms_or_zero(event: dict[str, Any]) -> int:
    """Return ``ts_unix_ms`` coerced to int, defaulting to 0 on miss.

    Legacy events sometimes carry NULL or non-integer timestamps; sort
    keys must be totally ordered so we collapse those to 0 (which
    naturally sorts oldest-first / first-seen).
    """
    raw = event.get("ts_unix_ms")
    if isinstance(raw, bool):
        return 0
    if isinstance(raw, int):
        return raw
    try:
        return int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _short_timestamp(event: dict[str, Any]) -> str:
    """Return a compact timestamp suitable for a one-line text rendering.

    Prefers the ISO ``timestamp`` column when present (trimmed to the
    seconds component), falling back to the empty string on miss so the
    text rendering stays predictable even for malformed legacy rows.
    """
    ts = event.get("timestamp")
    if not isinstance(ts, str) or not ts:
        return ""
    # Strip fractional seconds and timezone suffix for the inline display.
    head = ts.split(".", 1)[0].split("+", 1)[0].split("Z", 1)[0]
    return head


def _summary_for(event: dict[str, Any]) -> str:
    """Return a short free-text summary line for the rendering.

    The schema doesn't carry a dedicated ``summary`` field so we surface
    the most useful detail we have: the span_id (helpful for grepping
    forward / backward through the same NDJSON) plus a hint when the
    event is a known LLM call (``genai_system``).
    """
    parts: list[str] = []
    span_id = event.get("span_id")
    if isinstance(span_id, str) and span_id:
        parts.append(f"span={span_id}")
    genai_system = event.get("genai_system")
    if isinstance(genai_system, str) and genai_system:
        parts.append(f"genai={genai_system}")
    return " ".join(parts)


def _color_outcome(outcome: str) -> str:
    """Return ``outcome`` wrapped in ANSI for the conventional palette.

    ``failure`` -> red, ``success`` -> green, ``degraded``/``warning``
    -> yellow, anything else -> plain. Never raises -- unknown outcomes
    just render as-is.
    """
    lower = outcome.lower() if isinstance(outcome, str) else ""
    if lower == "failure":
        return f"{_ANSI_RED}{outcome}{_ANSI_RESET}"
    if lower == "success":
        return f"{_ANSI_GREEN}{outcome}{_ANSI_RESET}"
    if lower in {"degraded", "warning"}:
        return f"{_ANSI_YELLOW}{outcome}{_ANSI_RESET}"
    return outcome


# ---------------------------------------------------------------------------
# Tree construction
# ---------------------------------------------------------------------------


def build_span_tree(
    conn: sqlite3.Connection,
    *,
    session_id: str | None = None,
    trace_id: str | None = None,
) -> list[SpanNode]:
    """Build a forest of :class:`SpanNode` trees from the SQLite index.

    Exactly one of ``session_id`` / ``trace_id`` must be supplied; passing
    both, or passing neither, raises :class:`ValueError`. The choice is
    delegated up to the CLI which validates the user input separately.

    Algorithm
    ---------
    1. SELECT every row whose ``session_id`` (or ``trace_id``) matches.
    2. Build a ``span_id -> SpanNode`` index over the result set.
    3. For each node with a ``parent_span_id`` that resolves to another
       node in the index, append it as a child of its parent.
    4. Roots = nodes with no ``parent_span_id``, OR whose parent is not
       in the index (orphans). Both cases sort by ``ts_unix_ms`` so the
       caller sees a deterministic ordering.
    5. Each node's ``children`` list is sorted by ``ts_unix_ms`` so the
       walk reads top-to-bottom in event order.

    Parameters
    ----------
    conn:
        A live :class:`sqlite3.Connection` -- typically returned by
        :func:`audit_index.open_index_readonly`.
    session_id:
        Filter on the ``session_id`` column. Mutually exclusive with
        ``trace_id``. Passing both / neither raises :class:`ValueError`.
    trace_id:
        Filter on the ``trace_id`` column. Mutually exclusive with
        ``session_id``.

    Returns
    -------
    list[SpanNode]
        Roots of the forest, ts_unix_ms-ascending. Empty list when no
        rows match the filter.

    Raises
    ------
    ValueError
        If both or neither of ``session_id`` / ``trace_id`` is supplied.
    """
    if (session_id is None) == (trace_id is None):
        raise ValueError("build_span_tree requires exactly one of session_id / trace_id")

    rows = _fetch_rows(conn, session_id=session_id, trace_id=trace_id)
    if not rows:
        return []

    # First pass: build the lookup keyed by span_id. Rows missing a
    # ``span_id`` are pathological (audit_index always synthesises one)
    # but we guard anyway so a corrupt row never NRE's the build.
    nodes: dict[str, SpanNode] = {}
    for row in rows:
        span_id_raw = row.get("span_id")
        if not isinstance(span_id_raw, str) or not span_id_raw:
            continue
        parent_raw = row.get("parent_span_id")
        parent_id = parent_raw if isinstance(parent_raw, str) and parent_raw else None
        nodes[span_id_raw] = SpanNode(
            span_id=span_id_raw,
            parent_span_id=parent_id,
            event=row,
        )

    # Second pass: hang children off their parent when the parent is in
    # this result set. Anything else becomes a root.
    roots: list[SpanNode] = []
    for node in nodes.values():
        parent_id = node.parent_span_id
        if parent_id is not None and parent_id in nodes:
            nodes[parent_id].children.append(node)
        else:
            roots.append(node)

    # Sort children + roots by ts_unix_ms ascending. Stable sort keeps
    # rows with identical timestamps in their original SELECT order.
    for node in nodes.values():
        node.children.sort(key=lambda n: _ts_unix_ms_or_zero(n.event))
    roots.sort(key=lambda n: _ts_unix_ms_or_zero(n.event))
    return roots


# ---------------------------------------------------------------------------
# Walking
# ---------------------------------------------------------------------------


def walk_tree(roots: list[SpanNode]) -> Iterator[SpanNode]:
    """Yield every node in the forest, pre-order DFS, depth-aware.

    Each node's :attr:`SpanNode.depth` is updated in place as the walk
    descends so renderers can read the value off the yielded node
    directly. The depth assignment is deterministic regardless of the
    starting depth -- roots are at depth 0, their children at depth 1,
    etc.
    """
    stack: list[tuple[SpanNode, int]] = [(node, 0) for node in reversed(roots)]
    while stack:
        node, depth = stack.pop()
        node.depth = depth
        yield node
        # Push children in reverse so they pop off the stack in order.
        for child in reversed(node.children):
            stack.append((child, depth + 1))


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_text(roots: list[SpanNode], *, color: bool = True) -> str:
    """Render the forest as indented text -- one line per node.

    Format per line::

        {indent}{timestamp} · {kind:<24} · {component:<32} · {outcome:<7} · {summary}

    ``indent`` is two spaces per depth level. ``color`` toggles ANSI on
    the outcome cell -- callers that pipe to a non-TTY (or tests) should
    pass ``color=False``.
    """
    lines: list[str] = []
    for node in walk_tree(roots):
        event = node.event
        indent = "  " * node.depth
        ts = _short_timestamp(event)
        kind = str(event.get("kind") or "").ljust(_KIND_WIDTH)
        component = str(event.get("component") or "").ljust(_COMPONENT_WIDTH)
        outcome_raw = str(event.get("outcome") or "")
        outcome_cell = outcome_raw.ljust(_OUTCOME_WIDTH)
        if color:
            outcome_cell = _color_outcome(outcome_cell)
        summary = _summary_for(event)
        lines.append(f"{indent}{ts} · {kind} · {component} · {outcome_cell} · {summary}")
    return "\n".join(lines)


def render_json(roots: list[SpanNode]) -> dict[str, Any]:
    """Return a JSON-serializable tree dump.

    Each node renders as::

        {
          "span_id":        ...,
          "parent_span_id": ... or None,
          "kind":           ...,
          "component":      ...,
          "outcome":        ...,
          "timestamp":      ...,
          "ts_unix_ms":     ...,
          "genai":          {...} or null,
          "children":       [...]
        }

    Top-level shape is ``{"trees": [...]}`` so the wider envelope (token
    rollup, etc.) can sit alongside it without restructuring callers.
    """
    return {"trees": [_render_node_json(root) for root in roots]}


def _render_node_json(node: SpanNode) -> dict[str, Any]:
    """Recursively serialise one node + its children for ``render_json``."""
    event = node.event
    genai_system = event.get("genai_system")
    genai_model = event.get("genai_model")
    input_tokens = event.get("input_tokens")
    output_tokens = event.get("output_tokens")
    total_tokens = event.get("total_tokens")
    cost_usd = event.get("cost_usd")

    has_genai = any(
        value is not None
        for value in (
            genai_system,
            genai_model,
            input_tokens,
            output_tokens,
            total_tokens,
            cost_usd,
        )
    )
    genai: dict[str, Any] | None
    if has_genai:
        genai = {
            "system": genai_system,
            "model": genai_model,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd,
            },
        }
    else:
        genai = None

    return {
        "span_id": node.span_id,
        "parent_span_id": node.parent_span_id,
        "kind": event.get("kind"),
        "component": event.get("component"),
        "outcome": event.get("outcome"),
        "timestamp": event.get("timestamp"),
        "ts_unix_ms": event.get("ts_unix_ms"),
        "genai": genai,
        "children": [_render_node_json(child) for child in node.children],
    }


# ---------------------------------------------------------------------------
# Token rollup
# ---------------------------------------------------------------------------


def token_rollup(roots: list[SpanNode]) -> dict[str, Any]:
    """Sum token usage and cost across the forest.

    Walks every node in pre-order DFS and sums non-NULL values for
    ``input_tokens``, ``output_tokens``, ``total_tokens``, ``cost_usd``.
    Missing fields contribute zero.

    Returns
    -------
    dict
        ``{"input_tokens": int, "output_tokens": int, "total_tokens": int, "cost_usd": float}``
    """
    total_in = 0
    total_out = 0
    total_total = 0
    total_cost = 0.0
    for node in walk_tree(roots):
        event = node.event
        in_tokens = event.get("input_tokens")
        out_tokens = event.get("output_tokens")
        tot_tokens = event.get("total_tokens")
        cost = event.get("cost_usd")
        if isinstance(in_tokens, int) and not isinstance(in_tokens, bool):
            total_in += in_tokens
        if isinstance(out_tokens, int) and not isinstance(out_tokens, bool):
            total_out += out_tokens
        if isinstance(tot_tokens, int) and not isinstance(tot_tokens, bool):
            total_total += tot_tokens
        if isinstance(cost, (int, float)) and not isinstance(cost, bool):
            total_cost += float(cost)
    return {
        "input_tokens": total_in,
        "output_tokens": total_out,
        "total_tokens": total_total,
        "cost_usd": total_cost,
    }


__all__ = [
    "SpanNode",
    "build_span_tree",
    "render_json",
    "render_text",
    "token_rollup",
    "walk_tree",
]
