"""Tests for spec-120 §4.1 GenAI block + trace-context auto-fill in _lib (T-A5/A6).

Mirrors `tests/unit/state/test_observability_genai.py` for the
stdlib-only ``_lib.observability`` module that hooks load before
``pip install`` lands the package.

Two contracts under test:

  1. **Wire parity**: the ``detail.genai`` block emitted by the
     stdlib mirror has the same shape as the pkg side; the
     ``traceId`` / ``spanId`` auto-fill behaves identically; malformed
     ``usage`` is dropped silently with a ``framework_error`` written
     to the same NDJSON stream.

  2. **Stdlib-only**: the module continues to import nothing from
     ``ai_engineering.*`` (AST scan inherited from
     ``test_lib_trace_context.py``).

The module is loaded under a fresh module name (not on the package
import path) so the test does not pollute ``sys.modules`` for sibling
tests.
"""

from __future__ import annotations

import ast
import importlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
LIB_OBS_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "observability.py"


@pytest.fixture(scope="module")
def lib_obs():
    """Load the stdlib-only mirror as a regular module via the canonical path.

    Reuses the same `_lib.observability` import path that real hook
    scripts use so relative imports inside the module (`from . import
    trace_context`) resolve naturally. The hooks dir is inserted on
    sys.path once per test module.
    """
    hooks_dir = REPO / ".ai-engineering" / "scripts" / "hooks"
    if str(hooks_dir) not in sys.path:
        sys.path.insert(0, str(hooks_dir))
    return importlib.import_module("_lib.observability")


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Minimal project layout the _lib observability path needs."""
    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True)
    return tmp_path


# ---------------------------------------------------------------------------
# Stdlib-only contract (parity with test_lib_trace_context.py)
# ---------------------------------------------------------------------------


def test_lib_no_pkg_imports() -> None:
    """The `_lib` observability module must not import from `ai_engineering.*`.

    Mirrors the AST scan from `test_lib_trace_context.py`. Hooks run
    pre-pip-install in fresh checkouts and pre-commit contexts -- any
    pkg import would crash the hook.
    """
    source = LIB_OBS_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("ai_engineering"):
                    offenders.append(f"import {alias.name}")
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("ai_engineering")
        ):
            offenders.append(f"from {node.module} import ...")
    assert offenders == [], (
        f"_lib/observability.py must not import from ai_engineering.*; found: {offenders}"
    )


# ---------------------------------------------------------------------------
# T-A5: build_framework_event(usage=...) reshapes into detail.genai
# ---------------------------------------------------------------------------


def test_lib_emit_with_usage_writes_genai_block(project_root: Path, lib_obs) -> None:
    """The on-disk NDJSON line carries the OTel-mirroring `detail.genai` shape."""
    lib_obs.emit_skill_invoked(
        project_root,
        engine="claude_code",
        skill_name="brainstorm",
        component="hook.telemetry-skill",
        usage={
            "input_tokens": 1234,
            "output_tokens": 567,
            "model": "claude-sonnet-4-5",
            "system": "anthropic",
            "cost_usd": 0.0143,
        },
    )

    ndjson_path = lib_obs.framework_events_path(project_root)
    line = ndjson_path.read_text(encoding="utf-8").strip().splitlines()[-1]
    parsed = json.loads(line)

    genai = parsed["detail"]["genai"]
    assert genai["usage"]["input_tokens"] == 1234
    assert genai["usage"]["output_tokens"] == 567
    assert genai["usage"]["total_tokens"] == 1801
    assert genai["usage"]["cost_usd"] == 0.0143
    assert genai["system"] == "anthropic"
    assert genai["request"] == {"model": "claude-sonnet-4-5"}


def test_lib_total_tokens_auto_summed(project_root: Path, lib_obs) -> None:
    """`total_tokens` defaults to input + output when caller omits it."""
    event = lib_obs.build_framework_event(
        project_root,
        engine="claude_code",
        kind="skill_invoked",
        component="hook.telemetry-skill",
        detail={"skill": "ai-brainstorm"},
        usage={"input_tokens": 100, "output_tokens": 50},
    )
    assert event["detail"]["genai"]["usage"]["total_tokens"] == 150


def test_lib_explicit_total_tokens_preserved(project_root: Path, lib_obs) -> None:
    """A caller-provided `total_tokens` is preserved as-is."""
    event = lib_obs.build_framework_event(
        project_root,
        engine="claude_code",
        kind="skill_invoked",
        component="hook.telemetry-skill",
        detail={"skill": "ai-brainstorm"},
        usage={"input_tokens": 100, "output_tokens": 50, "total_tokens": 999},
    )
    assert event["detail"]["genai"]["usage"]["total_tokens"] == 999


def test_lib_no_usage_kwarg_no_genai_block(project_root: Path, lib_obs) -> None:
    """Without `usage`, the detail.genai block must not appear."""
    event = lib_obs.build_framework_event(
        project_root,
        engine="claude_code",
        kind="skill_invoked",
        component="hook.telemetry-skill",
        detail={"skill": "ai-brainstorm"},
    )
    assert "genai" not in event["detail"]


# ---------------------------------------------------------------------------
# T-A5: trace-context auto-fill semantics
# ---------------------------------------------------------------------------


def test_lib_auto_span_id_generated(project_root: Path, lib_obs) -> None:
    """`span_id` is auto-generated as 16-hex when not supplied."""
    event = lib_obs.build_framework_event(
        project_root,
        engine="claude_code",
        kind="skill_invoked",
        component="hook.telemetry-skill",
    )
    span_id = event["spanId"]
    assert isinstance(span_id, str) and len(span_id) == 16
    assert all(c in "0123456789abcdef" for c in span_id)


def test_lib_explicit_span_id_preserved(project_root: Path, lib_obs) -> None:
    """Caller-supplied `span_id` is forwarded verbatim."""
    event = lib_obs.build_framework_event(
        project_root,
        engine="claude_code",
        kind="skill_invoked",
        component="hook.telemetry-skill",
        span_id="abcdef0123456789",
    )
    assert event["spanId"] == "abcdef0123456789"


def test_lib_trace_id_inherited_from_context(project_root: Path, lib_obs) -> None:
    """A pre-existing trace-context.json supplies traceId on auto-fill."""
    # Use the _lib trace_context mirror so we don't cross-import the pkg side.
    from _lib import trace_context as lib_tc

    existing_trace = "00112233445566778899aabbccddeeff"
    existing_parent = "1111222233334444"
    lib_tc.write_trace_context(
        project_root,
        {"traceId": existing_trace, "span_stack": [existing_parent]},
    )

    event = lib_obs.build_framework_event(
        project_root,
        engine="claude_code",
        kind="skill_invoked",
        component="hook.telemetry-skill",
    )
    assert event["traceId"] == existing_trace
    assert event["parentSpanId"] == existing_parent


def test_lib_fresh_trace_id_when_no_context(project_root: Path, lib_obs) -> None:
    """No context file + None trace_id => fresh 32-hex traceId, no parentSpanId."""
    event = lib_obs.build_framework_event(
        project_root,
        engine="claude_code",
        kind="skill_invoked",
        component="hook.telemetry-skill",
    )
    trace_id = event["traceId"]
    assert isinstance(trace_id, str) and len(trace_id) == 32
    assert all(c in "0123456789abcdef" for c in trace_id)
    assert "parentSpanId" not in event  # root span -> omitted


# ---------------------------------------------------------------------------
# T-A6: emit helpers forward usage / span kwargs
# ---------------------------------------------------------------------------


def test_lib_emit_skill_invoked_forwards_span_kwargs(project_root: Path, lib_obs) -> None:
    """Caller-supplied span_id / parent_span_id reach the on-disk event."""
    lib_obs.emit_skill_invoked(
        project_root,
        engine="claude_code",
        skill_name="brainstorm",
        component="hook.telemetry-skill",
        span_id="abcdef0123456789",
        parent_span_id="0011223344556677",
        trace_id="ffeeddccbbaa99887766554433221100",
    )
    ndjson_path = lib_obs.framework_events_path(project_root)
    line = ndjson_path.read_text(encoding="utf-8").strip().splitlines()[-1]
    parsed = json.loads(line)
    assert parsed["spanId"] == "abcdef0123456789"
    assert parsed["parentSpanId"] == "0011223344556677"
    assert parsed["traceId"] == "ffeeddccbbaa99887766554433221100"


def test_lib_emit_agent_dispatched_with_usage(project_root: Path, lib_obs) -> None:
    """`emit_agent_dispatched` mirrors `emit_skill_invoked` for usage."""
    lib_obs.emit_agent_dispatched(
        project_root,
        engine="claude_code",
        agent_name="build",
        component="hook.dispatch",
        usage={"input_tokens": 200, "output_tokens": 100},
    )
    ndjson_path = lib_obs.framework_events_path(project_root)
    line = ndjson_path.read_text(encoding="utf-8").strip().splitlines()[-1]
    parsed = json.loads(line)
    genai = parsed["detail"]["genai"]
    assert genai["usage"]["input_tokens"] == 200
    assert genai["usage"]["output_tokens"] == 100
    assert genai["usage"]["total_tokens"] == 300


# ---------------------------------------------------------------------------
# T-A5: Malformed usage = best-effort skip + framework_error
# ---------------------------------------------------------------------------


def test_lib_malformed_usage_non_dict_skipped(project_root: Path, lib_obs) -> None:
    """Non-dict `usage` is dropped; framework_error is emitted instead."""
    event = lib_obs.build_framework_event(
        project_root,
        engine="claude_code",
        kind="skill_invoked",
        component="hook.telemetry-skill",
        detail={"skill": "ai-brainstorm"},
        usage=["not", "a", "dict"],
    )
    assert "genai" not in event["detail"]

    ndjson_path = lib_obs.framework_events_path(project_root)
    assert ndjson_path.exists()
    errors = [
        json.loads(line) for line in ndjson_path.read_text(encoding="utf-8").strip().splitlines()
    ]
    assert any(
        e.get("kind") == "framework_error"
        and e.get("detail", {}).get("error_code") == "genai_usage_malformed"
        for e in errors
    )


def test_lib_malformed_usage_missing_token_counts_skipped(project_root: Path, lib_obs) -> None:
    """`usage` lacking input_tokens/output_tokens is treated as malformed."""
    event = lib_obs.build_framework_event(
        project_root,
        engine="claude_code",
        kind="skill_invoked",
        component="hook.telemetry-skill",
        detail={"skill": "ai-brainstorm"},
        usage={"model": "claude-sonnet-4-5"},
    )
    assert "genai" not in event["detail"]

    ndjson_path = lib_obs.framework_events_path(project_root)
    errors = [
        json.loads(line) for line in ndjson_path.read_text(encoding="utf-8").strip().splitlines()
    ]
    assert any(
        e.get("kind") == "framework_error"
        and e.get("detail", {}).get("error_code") == "genai_usage_malformed"
        for e in errors
    )
