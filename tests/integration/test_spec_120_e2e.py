"""End-to-end integration test for spec-120 observability modernization (T-D1).

Drives the full pipeline introduced by Phases A/B/C against a synthetic
5-event nested session emitted through the **real** ``emit_*`` helpers
(no mocking) and verifies the four spec-120 CLI subcommands plus the OTLP
exporter envelope shape.

Test sequence:

1. Bootstrap a fresh ``tmp_path`` project root with
   ``.ai-engineering/state/`` and a generated trace context.
2. Emit five events (S1..S5) covering nested skill / agent dispatch +
   independent root, mirroring the spec-120 §4.4 replay contract.
3. Run ``ai-eng audit index --json`` and assert ``rows_indexed == 5``.
4. Run ``ai-eng audit query "SELECT COUNT(*) FROM events" --json`` and
   assert the count.
5. Run ``ai-eng audit tokens --by skill --json`` and assert the per-skill
   token sums.
6. Run ``ai-eng audit replay --session sess-spec120 --json`` and assert
   tree shape + token rollup totals.
7. Run ``ai-eng audit otel-export --trace <trace_id> --out <file>`` and
   assert the OTLP/JSON envelope shape.

Hard constraints (per spec-120 Phase D plan):

* Hits real production code -- no mocking of ``emit_*``, ``build_index``,
  ``build_span_tree``, ``build_otlp_spans``.
* Pins ``cwd`` at ``tmp_path`` via :meth:`MonkeyPatch.chdir` so the CLI's
  :func:`_resolve_project_root` lands inside the temp directory.
* Does not touch the audit-chain canary surface
  (``audit_chain.py`` / ``hooks-manifest.json``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app
from ai_engineering.state.observability import (
    emit_agent_dispatched,
    emit_skill_invoked,
)
from ai_engineering.state.trace_context import (
    new_trace_id,
    pop_span,
    push_span,
    write_trace_context,
)

runner = CliRunner()

_SESSION_ID = "sess-spec120"
_ENGINE = "ai_engineering"
_COMPONENT = "test.spec120-e2e"


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


def _extract_json(output: str, *, prefix: str) -> Any:
    """Pluck the first stdout line that starts with ``prefix`` and parse it.

    Typer-mediated CLI output is mixed with banners / progress lines, so
    the actual JSON envelope is the last (or only) line that begins with
    ``{`` or ``[``. Mirrors the extraction pattern used by the unit tests.
    """
    candidates = [line.strip() for line in output.splitlines() if line.strip().startswith(prefix)]
    if not candidates:
        raise AssertionError(f"no JSON line starting with {prefix!r} in output:\n{output}")
    # Prefer the last match -- intermediate banners that look JSON-ish
    # would precede the real payload in pathological cases. The CLI
    # emits exactly one JSON line per command today.
    return json.loads(candidates[-1])


@pytest.fixture()
def seeded_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    """Seed a 5-event nested session under ``tmp_path`` and return metadata.

    Returned dict keys:

    * ``project_root`` -- ``tmp_path`` (also the cwd while the test runs).
    * ``trace_id`` -- 32-hex trace identifier shared by E1..E4.
    * ``spans`` -- ``{"S1": ..., "S2": ..., "S3": ..., "S4": ..., "S5": ...}``
      mapping logical names to the wire ``spanId`` values.

    Span tree:

    * S1 (root, ai-build skill)
       * S2 (ai-explore agent)
          * S3 (ai-verify skill)
       * S4 (ai-review skill)
    * S5 (independent root, ai-commit skill)

    Token totals (input/output):

    * ai-build:    100 / 50
    * ai-explore:  200 / 80   (agent_dispatched)
    * ai-verify:    50 / 20
    * ai-review:    30 / 10
    * ai-commit:    20 /  5

    Sum across the session: input = 400, output = 165.
    """
    project_root = tmp_path
    state_dir = project_root / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.chdir(project_root)

    trace_id = new_trace_id()
    write_trace_context(
        project_root,
        {"traceId": trace_id, "span_stack": []},
    )

    # E1: root skill_invoked (ai-build)
    e1 = emit_skill_invoked(
        project_root,
        engine=_ENGINE,
        skill_name="ai-build",
        component=_COMPONENT,
        session_id=_SESSION_ID,
        usage={
            "input_tokens": 100,
            "output_tokens": 50,
            "model": "claude-sonnet-4-5",
            "system": "anthropic",
        },
    )
    s1 = e1.span_id
    assert s1 is not None
    push_span(project_root, s1)

    # E2: agent_dispatched under S1 (ai-explore)
    e2 = emit_agent_dispatched(
        project_root,
        engine=_ENGINE,
        agent_name="ai-explore",
        component=_COMPONENT,
        session_id=_SESSION_ID,
        parent_span_id=s1,
        usage={"input_tokens": 200, "output_tokens": 80},
    )
    s2 = e2.span_id
    assert s2 is not None
    push_span(project_root, s2)

    # E3: skill_invoked under S2 (ai-verify)
    e3 = emit_skill_invoked(
        project_root,
        engine=_ENGINE,
        skill_name="ai-verify",
        component=_COMPONENT,
        session_id=_SESSION_ID,
        parent_span_id=s2,
        usage={"input_tokens": 50, "output_tokens": 20},
    )
    s3 = e3.span_id
    assert s3 is not None
    pop_span(project_root)  # pop S2

    # E4: skill_invoked under S1 (ai-review) -- sibling of S2
    e4 = emit_skill_invoked(
        project_root,
        engine=_ENGINE,
        skill_name="ai-review",
        component=_COMPONENT,
        session_id=_SESSION_ID,
        parent_span_id=s1,
        usage={"input_tokens": 30, "output_tokens": 10},
    )
    s4 = e4.span_id
    assert s4 is not None

    # Pop S1 and reset the trace context so E5 lands as an independent
    # root. Without this, the helper would auto-inherit S1 as parent
    # (current_trace_context still sees S1 on the stack) and the replay
    # would fold S5 under S1 instead of treating it as a sibling root.
    pop_span(project_root)
    new_trace = new_trace_id()
    write_trace_context(project_root, {"traceId": new_trace, "span_stack": []})

    # E5: independent root skill_invoked (ai-commit) -- shares session,
    # fresh trace anchor (we let the helper auto-fill from the cleared
    # context, which now points at the brand-new ``new_trace`` id).
    e5 = emit_skill_invoked(
        project_root,
        engine=_ENGINE,
        skill_name="ai-commit",
        component=_COMPONENT,
        session_id=_SESSION_ID,
        usage={"input_tokens": 20, "output_tokens": 5},
    )
    s5 = e5.span_id
    assert s5 is not None

    return {
        "project_root": project_root,
        "trace_id": trace_id,
        "spans": {"S1": s1, "S2": s2, "S3": s3, "S4": s4, "S5": s5},
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_spec_120_e2e_full_pipeline(seeded_session: dict[str, Any]) -> None:
    """Index, query, tokens, replay, and otel-export run green end-to-end.

    Asserts each subcommand's output shape against the seeded 5-event
    session. Drives every spec-120 CLI surface introduced by Phases B/C
    via the real Typer app -- no mocking, no shortcuts.
    """
    project_root = seeded_session["project_root"]
    trace_id = seeded_session["trace_id"]
    spans = seeded_session["spans"]

    # ---- Stage 1: audit index --------------------------------------------
    app = create_app()
    result = runner.invoke(app, ["audit", "index", "--json"])
    assert result.exit_code == 0, result.output
    index_payload = _extract_json(result.output, prefix="{")
    assert index_payload["rows_indexed"] == 5, index_payload
    assert index_payload["rows_total"] == 5, index_payload
    assert index_payload["rebuilt"] is False

    # ---- Stage 2: audit query --------------------------------------------
    result = runner.invoke(
        app,
        ["audit", "query", "SELECT COUNT(*) AS n FROM events", "--json"],
    )
    assert result.exit_code == 0, result.output
    rows = _extract_json(result.output, prefix="[")
    assert isinstance(rows, list) and len(rows) == 1, rows
    assert rows[0].get("n") == 5, rows

    # ---- Stage 3: audit tokens --by skill --------------------------------
    result = runner.invoke(app, ["audit", "tokens", "--by", "skill", "--json"])
    assert result.exit_code == 0, result.output
    rollup_rows = _extract_json(result.output, prefix="[")
    assert isinstance(rollup_rows, list)
    by_skill = {row["skill"]: row for row in rollup_rows}
    # ai-explore is an agent, NOT a skill -- it must NOT appear here.
    assert "ai-explore" not in by_skill, by_skill
    for skill_name, expected_in, expected_out in (
        ("ai-build", 100, 50),
        ("ai-verify", 50, 20),
        ("ai-review", 30, 10),
        ("ai-commit", 20, 5),
    ):
        assert skill_name in by_skill, (skill_name, by_skill)
        row = by_skill[skill_name]
        assert row["input_tokens"] == expected_in, (skill_name, row)
        assert row["output_tokens"] == expected_out, (skill_name, row)

    # ---- Stage 4: audit replay --session ---------------------------------
    result = runner.invoke(
        app,
        ["audit", "replay", "--session", _SESSION_ID, "--json"],
    )
    assert result.exit_code == 0, result.output
    replay_payload = _extract_json(result.output, prefix="{")

    tokens = replay_payload.get("tokens", {})
    assert tokens.get("input_tokens") == 400, replay_payload
    assert tokens.get("output_tokens") == 165, replay_payload

    trees = replay_payload.get("trees", [])
    # Two roots: S1 and S5.
    assert len(trees) == 2, trees
    roots_by_span = {tree["span_id"]: tree for tree in trees}
    assert spans["S1"] in roots_by_span, roots_by_span
    assert spans["S5"] in roots_by_span, roots_by_span

    s1_tree = roots_by_span[spans["S1"]]
    s1_children_ids = {child["span_id"] for child in s1_tree["children"]}
    assert s1_children_ids == {spans["S2"], spans["S4"]}, s1_tree

    # S2 should have S3 as its sole child.
    s2_node = next(child for child in s1_tree["children"] if child["span_id"] == spans["S2"])
    assert [c["span_id"] for c in s2_node["children"]] == [spans["S3"]], s2_node

    # S5 is an independent root with no children.
    assert roots_by_span[spans["S5"]]["children"] == [], roots_by_span[spans["S5"]]

    # ---- Stage 5: audit otel-export --------------------------------------
    out_path = project_root / "otel-export.json"
    result = runner.invoke(
        app,
        ["audit", "otel-export", "--trace", trace_id, "--out", str(out_path)],
    )
    assert result.exit_code == 0, result.output
    assert out_path.exists(), result.output

    envelope = json.loads(out_path.read_text(encoding="utf-8"))
    assert isinstance(envelope, dict), envelope
    assert "resourceSpans" in envelope, envelope
    assert isinstance(envelope["resourceSpans"], list), envelope


def test_spec_120_e2e_replay_tree_shape(seeded_session: dict[str, Any]) -> None:
    """Focused tree-shape assertion isolated from the full pipeline.

    Distinct from :func:`test_spec_120_e2e_full_pipeline` so a regression
    in the span-tree builder surfaces with a tighter failure signal.
    """
    spans = seeded_session["spans"]

    app = create_app()
    # Build the index first so the replay command sees populated rows.
    runner.invoke(app, ["audit", "index"])

    result = runner.invoke(app, ["audit", "replay", "--session", _SESSION_ID, "--json"])
    assert result.exit_code == 0, result.output

    payload = _extract_json(result.output, prefix="{")
    trees = payload.get("trees", [])
    assert len(trees) == 2, trees

    roots_by_span = {tree["span_id"]: tree for tree in trees}
    s1_tree = roots_by_span[spans["S1"]]

    # Children of S1 should be S2 and S4.
    s1_children_ids = {c["span_id"] for c in s1_tree["children"]}
    assert s1_children_ids == {spans["S2"], spans["S4"]}, s1_tree

    # S2's child should be S3 alone.
    s2_node = next(c for c in s1_tree["children"] if c["span_id"] == spans["S2"])
    assert [c["span_id"] for c in s2_node["children"]] == [spans["S3"]], s2_node

    # S4 has no children.
    s4_node = next(c for c in s1_tree["children"] if c["span_id"] == spans["S4"])
    assert s4_node["children"] == [], s4_node

    # S5 is a sibling root with no children.
    s5_tree = roots_by_span[spans["S5"]]
    assert s5_tree["children"] == [], s5_tree


def test_spec_120_e2e_otlp_shape(seeded_session: dict[str, Any]) -> None:
    """OTLP/JSON envelope adheres to the spec-120 §4.5 wire contract.

    Asserts the minimum portable shape: ``resourceSpans`` outer list,
    ``scopeSpans[0].scope.name == "ai-engineering"``, every span carries
    the OTLP-required fields (``traceId`` / ``spanId`` / ``name`` /
    ``startTimeUnixNano`` as a string / ``kind`` / ``status`` /
    ``attributes`` list of ``{key, value}`` dicts), and at least one span
    surfaces the GenAI semantic-convention attributes.
    """
    project_root = seeded_session["project_root"]
    trace_id = seeded_session["trace_id"]

    app = create_app()
    # Build the index so otel-export has rows.
    runner.invoke(app, ["audit", "index"])

    out_path = project_root / "spans.json"
    result = runner.invoke(
        app,
        ["audit", "otel-export", "--trace", trace_id, "--out", str(out_path)],
    )
    assert result.exit_code == 0, result.output
    assert out_path.exists()

    envelope = json.loads(out_path.read_text(encoding="utf-8"))

    resource_spans = envelope.get("resourceSpans")
    assert isinstance(resource_spans, list) and resource_spans, envelope

    scope_spans = resource_spans[0].get("scopeSpans")
    assert isinstance(scope_spans, list) and scope_spans, resource_spans
    scope_block = scope_spans[0]
    assert scope_block.get("scope", {}).get("name") == "ai-engineering", scope_block

    spans = scope_block.get("spans", [])
    assert spans, scope_block

    for span in spans:
        # OTLP/JSON required minima -- mirrors spec-120 §4.5.
        assert isinstance(span.get("traceId"), str) and span["traceId"], span
        assert isinstance(span.get("spanId"), str) and span["spanId"], span
        assert isinstance(span.get("name"), str) and span["name"], span
        # ``startTimeUnixNano`` MUST be a string per the protobuf-JSON
        # convention (large integers are not safely round-trippable).
        assert isinstance(span.get("startTimeUnixNano"), str), span
        assert span.get("kind"), span
        status = span.get("status")
        assert isinstance(status, dict) and "code" in status, span
        attrs = span.get("attributes")
        assert isinstance(attrs, list), span
        for attr in attrs:
            assert isinstance(attr, dict), attr
            assert "key" in attr and "value" in attr, attr

    # At least one span must carry the GenAI semantic-convention markers
    # (``gen_ai.system`` and ``gen_ai.usage.input_tokens``) -- every event
    # in the seeded session has a usage block, so this is a hard check.
    flat_attrs: set[str] = set()
    for span in spans:
        for attr in span.get("attributes", []):
            flat_attrs.add(attr["key"])
    assert "gen_ai.system" in flat_attrs, flat_attrs
    assert "gen_ai.usage.input_tokens" in flat_attrs, flat_attrs
