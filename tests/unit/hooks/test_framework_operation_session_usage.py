"""spec-201 sub-003: ``emit_framework_operation`` must be able to carry a
session identity and a GenAI usage block.

Ground truth that motivated this file: of 5,147 live ``framework_operation``
events in ``framework-events.ndjson``, **zero** carry a top-level ``sessionId``
-- because the entry point simply had no way to pass one. ``session_token_rollup``
events were therefore invisible to
:func:`ai_engineering.state.audit_rollup.session_token_rollup`, which groups by
``sessionId``. Nothing anywhere asserted the field, which is exactly how it
shipped that way.

Both twins are asserted in ONE file so the "functional-parallel, not a byte
copy" claim about ``_lib/observability.py`` vs
``ai_engineering.state.observability`` is executable rather than aspirational.

No new shaping logic is under test here: ``build_framework_event`` already maps
``session_id`` -> top-level ``sessionId`` and ``usage`` -> ``detail.genai``.
What is pinned is that ``emit_framework_operation`` forwards them.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.state import observability as pip_obs

REPO = Path(__file__).resolve().parents[3]
NDJSON_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"

CANONICAL_USAGE = {
    "input_tokens": 10,
    "output_tokens": 5,
    "total_tokens": 15,
    "cost_usd": 0.02,
    "model": "gpt-4o",
    "system": "openai",
}


@pytest.fixture(scope="module")
def hook_obs():
    """Load the stdlib-only ``_lib.observability`` mirror hooks actually use."""
    hooks_dir = REPO / ".ai-engineering" / "scripts" / "hooks"
    if str(hooks_dir) not in sys.path:
        sys.path.insert(0, str(hooks_dir))
    return importlib.import_module("_lib.observability")


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
    return tmp_path


@pytest.fixture(autouse=True)
def patched_project_name(project_root: Path):
    """Skip manifest loading on the pip side; only a stable name is needed."""
    with patch.object(pip_obs, "_project_name", return_value=project_root.name):
        yield


def _read_events(project_root: Path) -> list[dict]:
    path = project_root / NDJSON_REL
    if not path.is_file():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _operations(project_root: Path) -> list[dict]:
    return [e for e in _read_events(project_root) if e.get("kind") == "framework_operation"]


def _emitters(hook_obs):
    """The two functional-parallel entry points, labelled for test ids."""
    return {"pip": pip_obs.emit_framework_operation, "hook": hook_obs.emit_framework_operation}


@pytest.fixture(params=["pip", "hook"])
def emit(request, hook_obs):
    return _emitters(hook_obs)[request.param]


# ---------------------------------------------------------------------------
# (a) session_id lands at the TOP LEVEL of the event -- the never-asserted field
# ---------------------------------------------------------------------------


def test_session_id_lands_at_top_level(emit, project_root: Path) -> None:
    emit(
        project_root,
        operation="session_token_rollup",
        component="hook.runtime-stop",
        source="hook",
        session_id="sess-x",
    )

    ops = _operations(project_root)
    assert len(ops) == 1, f"expected one framework_operation, got {ops}"
    assert ops[0]["sessionId"] == "sess-x"


# ---------------------------------------------------------------------------
# (b) omitting session_id is unchanged -- the 26 existing call sites are safe
# ---------------------------------------------------------------------------


def test_session_id_omitted_still_emits_valid_event(emit, project_root: Path) -> None:
    emit(
        project_root,
        operation="spec_shipped",
        component="cli.spec",
    )

    ops = _operations(project_root)
    assert len(ops) == 1
    assert ops[0].get("sessionId") is None
    assert ops[0]["detail"]["operation"] == "spec_shipped"


# ---------------------------------------------------------------------------
# (c) usage is reshaped into the canonical detail.genai block
# ---------------------------------------------------------------------------


def test_usage_becomes_canonical_genai_block(emit, project_root: Path) -> None:
    emit(
        project_root,
        operation="session_token_rollup",
        component="hook.runtime-stop",
        session_id="sess-usage",
        usage=dict(CANONICAL_USAGE),
    )

    ops = _operations(project_root)
    assert len(ops) == 1
    genai = ops[0]["detail"]["genai"]
    assert genai["usage"]["input_tokens"] == 10
    assert genai["usage"]["output_tokens"] == 5
    assert genai["usage"]["total_tokens"] == 15
    assert genai["usage"]["cost_usd"] == pytest.approx(0.02)
    assert genai["system"] == "openai"
    assert genai["request"]["model"] == "gpt-4o"


# ---------------------------------------------------------------------------
# (d) malformed usage never raises and never suppresses the operation event
# ---------------------------------------------------------------------------


def test_malformed_usage_does_not_raise_or_suppress(emit, project_root: Path) -> None:
    emit(
        project_root,
        operation="session_token_rollup",
        component="hook.runtime-stop",
        session_id="sess-bad",
        usage={"output_tokens": 5},  # missing input_tokens
    )

    ops = _operations(project_root)
    assert len(ops) == 1
    assert "genai" not in ops[0]["detail"]
    assert ops[0]["sessionId"] == "sess-bad"


# ---------------------------------------------------------------------------
# (e) operation + metadata still round-trip
# ---------------------------------------------------------------------------


def test_metadata_and_operation_round_trip(emit, project_root: Path) -> None:
    emit(
        project_root,
        operation="session_token_rollup",
        component="hook.runtime-stop",
        outcome="success",
        correlation_id="corr-roundtrip",
        session_id="sess-meta",
        usage=dict(CANONICAL_USAGE),
        metadata={"events": 7, "usage_source": "merged"},
    )

    ops = _operations(project_root)
    assert len(ops) == 1
    detail = ops[0]["detail"]
    assert detail["operation"] == "session_token_rollup"
    assert detail["events"] == 7
    assert detail["usage_source"] == "merged"
    assert ops[0]["correlationId"] == "corr-roundtrip"
    assert ops[0]["outcome"] == "success"
