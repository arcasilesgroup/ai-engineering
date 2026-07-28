"""Tests for the session token rollup wiring inside ``runtime-stop.py``
(spec-120 T-E1; spec-148 files-only; spec-201 sub-003 cost attribution).

Pins ``_emit_session_token_rollup`` against the append-only NDJSON audit
log (no SQLite). Best-effort contract:

1. **Session has NDJSON events** -> a single ``framework_operation`` event
   with ``detail.operation = "session_token_rollup"`` and the rollup payload.
2. **No events for the session_id** -> silent skip (no operation, no error).
3. **No NDJSON + no transcript** -> silent skip (nothing to roll up).
4. **session_id is None** -> silent skip.

spec-201 sub-003 changed the payload shape, deliberately and without a shim
(CLAUDE.md §13.3 / §13.7 -- one canonical store per datum):

* The event now carries a **top-level ``sessionId``**. Without it the rollup
  is invisible to ``session_token_rollup``, which groups by that field --
  which is why 378 live rollup events never appeared in ``audit tokens``.
* Token counts moved from flat ``detail`` keys (``input_tokens``,
  ``output_tokens``, ``total_tokens``, ``cost_usd``, ``genai_model``,
  ``genai_system``) into the canonical ``detail.genai`` block, which is the
  only slot ``audit_rollup._usage`` reads.
* ``genai.system`` is derived from the transcript's real model string with an
  ``"unknown"`` floor. The old unconditional ``"anthropic"`` default was
  confidently wrong for every non-Anthropic driver.

Transcripts are always pointed at ``tmp_path`` via ``CLAUDE_TRANSCRIPT_PATH``
so no test ever reads the operator's real ``$HOME``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
RUNTIME_STOP_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "runtime-stop.py"
NDJSON_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"


def _project_slug(project: Path) -> str:
    """Cross-OS Claude Code transcripts slug (mirrors ``_lib.transcript_usage``)."""
    return str(project.resolve()).replace("/", "-").replace("\\", "-").replace(":", "-")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _no_ambient_transcript(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never inherit an operator transcript; tests opt in explicitly."""
    monkeypatch.delenv("CLAUDE_TRANSCRIPT_PATH", raising=False)


@pytest.fixture
def rstop(monkeypatch: pytest.MonkeyPatch):
    """Load the runtime-stop module fresh in each test for monkey-safety."""
    monkeypatch.syspath_prepend(str(REPO / ".ai-engineering" / "scripts" / "hooks"))
    sys.modules.pop("aieng_runtime_stop", None)
    spec = importlib.util.spec_from_file_location("aieng_runtime_stop", RUNTIME_STOP_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _read_events(project_root: Path) -> list[dict]:
    path = project_root / NDJSON_REL
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _seed_ndjson(project_root: Path, *, session_id: str, totals: dict) -> None:
    """Append one ``skill_invoked`` NDJSON event carrying a usage block.

    spec-148: the rollup is computed directly from this NDJSON, not a
    SQLite projection.
    """
    path = project_root / NDJSON_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    usage = {
        "input_tokens": totals["input_tokens"],
        "output_tokens": totals["output_tokens"],
        "total_tokens": totals["total_tokens"],
    }
    if totals.get("cost_usd") is not None:
        usage["cost_usd"] = totals["cost_usd"]
    event = {
        "kind": "skill_invoked",
        "engine": "claude_code",
        "timestamp": "2026-05-04T00:00:00Z",
        "component": "hook.telemetry-skill",
        "outcome": "success",
        "correlationId": "corr-1",
        "schemaVersion": "1.0",
        "project": "test",
        "spanId": "0123456789abcdef",
        "sessionId": session_id,
        "detail": {
            "skill": "ai-brainstorm",
            "genai": {
                "system": "anthropic",
                "request": {"model": "claude-opus-4.7"},
                "usage": usage,
            },
        },
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event) + "\n")


def _write_transcript(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    model: str,
    messages: list[tuple[int, int]],
    cost: float | None = None,
) -> Path:
    """Write a synthetic Claude-shaped transcript and point the resolver at it.

    ``cost`` is stamped on every assistant message when supplied. Claude Code
    itself never writes a cost field -- a cost-bearing transcript models the
    OpenAI-compatible path (spec-201 Risk 1).
    """
    lines = []
    for in_tok, out_tok in messages:
        usage: dict = {
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        if cost is not None:
            usage["cost_usd"] = cost
        lines.append(
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "model": model,
                        "role": "assistant",
                        "content": [],
                        "usage": usage,
                    },
                }
            )
        )
    path = tmp_path / "transcript.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_TRANSCRIPT_PATH", str(path))
    return path


def _rollup_event(project_root: Path) -> dict:
    events = _read_events(project_root)
    rollups = [
        e
        for e in events
        if e.get("kind") == "framework_operation"
        and (e.get("detail") or {}).get("operation") == "session_token_rollup"
    ]
    assert len(rollups) == 1, f"expected exactly one rollup event, got {events}"
    return rollups[0]


# ---------------------------------------------------------------------------
# Branch 1: session has NDJSON events
# ---------------------------------------------------------------------------


def test_session_rollup_emits_framework_operation_when_events_found(rstop, project: Path) -> None:
    """Happy path: NDJSON has an event for the session -> one
    ``framework_operation`` event with the rollup payload."""
    session_id = "sess-happy"
    totals = {
        "input_tokens": 1000,
        "output_tokens": 250,
        "total_tokens": 1250,
        "cost_usd": 0.0125,
    }
    _seed_ndjson(project, session_id=session_id, totals=totals)

    rstop._emit_session_token_rollup(project, session_id=session_id, correlation_id="corr-test")

    event = _rollup_event(project)
    detail = event["detail"]

    # spec-201 sub-003: the identity that makes the event visible to the rollup.
    assert event["sessionId"] == session_id

    # Non-token facts stay on `detail`.
    assert detail["operation"] == "session_token_rollup"
    assert detail["session_id"] == session_id
    assert detail["events"] == 1
    assert detail["started_at"] == "2026-05-04T00:00:00Z"
    assert detail["ended_at"] == "2026-05-04T00:00:00Z"
    assert detail["usage_source"] == "ndjson"
    assert event["component"] == "hook.runtime-stop"
    assert event["correlationId"] == "corr-test"

    # Tokens live ONLY in the canonical genai block.
    usage = detail["genai"]["usage"]
    assert usage["input_tokens"] == 1000
    assert usage["output_tokens"] == 250
    assert usage["total_tokens"] == 1250
    assert usage["cost_usd"] == pytest.approx(0.0125)

    # No transcript -> no model signal -> honest "unknown", never "anthropic".
    assert detail["genai"]["system"] == "unknown"
    assert "request" not in detail["genai"]


def test_session_rollup_drops_the_flat_token_keys(rstop, project: Path) -> None:
    """BREAKING, no shim: the flat ``detail`` token keys are gone.

    Writing tokens both flat and under ``genai`` would violate single-source-
    of-truth-per-datum; ``audit_rollup`` only ever read the ``genai`` slot.
    """
    session_id = "sess-flat"
    _seed_ndjson(
        project,
        session_id=session_id,
        totals={
            "input_tokens": 10,
            "output_tokens": 20,
            "total_tokens": 30,
            "cost_usd": 0.5,
        },
    )

    rstop._emit_session_token_rollup(project, session_id=session_id, correlation_id="corr-test")

    detail = _rollup_event(project)["detail"]
    for gone in (
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "cost_usd",
        "genai_model",
        "genai_system",
    ):
        assert gone not in detail, f"flat key {gone!r} must not survive on detail"


# ---------------------------------------------------------------------------
# Transcript-driven cost + system attribution (spec-201 sub-003)
# ---------------------------------------------------------------------------


def test_session_rollup_carries_transcript_cost_and_openai_system(
    rstop, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An OpenAI-compatible transcript supplies both the cost and the system."""
    _write_transcript(
        tmp_path,
        monkeypatch,
        model="gpt-4o",
        messages=[(100, 200), (50, 75)],
        cost=0.01,
    )

    rstop._emit_session_token_rollup(project, session_id="sess-openai", correlation_id="corr-test")

    event = _rollup_event(project)
    detail = event["detail"]
    assert event["sessionId"] == "sess-openai"
    assert detail["usage_source"] == "transcript"

    genai = detail["genai"]
    assert genai["system"] == "openai"
    assert genai["request"]["model"] == "gpt-4o"
    assert genai["usage"]["input_tokens"] == 150
    assert genai["usage"]["output_tokens"] == 275
    assert genai["usage"]["total_tokens"] == 425
    assert genai["usage"]["cost_usd"] == pytest.approx(0.02)


def test_session_rollup_omits_cost_when_no_source_reports_one(
    rstop, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The honest Claude Code outcome: tokens yes, cost absent -- NOT ``0.0``.

    ``cost_usd`` must be missing from the usage block rather than reported as
    zero, so "the provider reports no cost" never renders as "free".
    """
    _write_transcript(
        tmp_path,
        monkeypatch,
        model="claude-opus-5",
        messages=[(100, 200)],
    )

    rstop._emit_session_token_rollup(project, session_id="sess-claude", correlation_id="corr-test")

    genai = _rollup_event(project)["detail"]["genai"]
    assert genai["system"] == "anthropic"
    assert genai["request"]["model"] == "claude-opus-5"
    assert genai["usage"]["total_tokens"] == 300
    assert "cost_usd" not in genai["usage"]


def test_session_rollup_merges_ndjson_and_transcript(
    rstop, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both sources present -> max-merge tokens, ndjson cost as the fallback."""
    _seed_ndjson(
        project,
        session_id="sess-merged",
        totals={
            "input_tokens": 10,
            "output_tokens": 20,
            "total_tokens": 30,
            "cost_usd": 0.0125,
        },
    )
    _write_transcript(
        tmp_path,
        monkeypatch,
        model="claude-opus-5",
        messages=[(1000, 2000)],
    )

    rstop._emit_session_token_rollup(project, session_id="sess-merged", correlation_id="corr-test")

    detail = _rollup_event(project)["detail"]
    assert detail["usage_source"] == "merged"
    usage = detail["genai"]["usage"]
    # Transcript wins on tokens (larger), ndjson supplies the only cost signal.
    assert usage["input_tokens"] == 1000
    assert usage["output_tokens"] == 2000
    assert usage["total_tokens"] == 3000
    assert usage["cost_usd"] == pytest.approx(0.0125)
    assert detail["genai"]["system"] == "anthropic"


def test_session_rollup_prefers_transcript_cost_over_ndjson(
    rstop, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Per-request provider cost is the primary source when it exists."""
    _seed_ndjson(
        project,
        session_id="sess-cost-pref",
        totals={
            "input_tokens": 1,
            "output_tokens": 1,
            "total_tokens": 2,
            "cost_usd": 0.99,
        },
    )
    _write_transcript(
        tmp_path,
        monkeypatch,
        model="gpt-4o",
        messages=[(10, 10)],
        cost=0.25,
    )

    rstop._emit_session_token_rollup(
        project, session_id="sess-cost-pref", correlation_id="corr-test"
    )

    usage = _rollup_event(project)["detail"]["genai"]["usage"]
    assert usage["cost_usd"] == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# Branch 2: NDJSON exists, no event for this session_id
# ---------------------------------------------------------------------------


def test_session_rollup_silent_skip_when_no_event_for_session(rstop, project: Path) -> None:
    """NDJSON has events for another session -> no event emitted at all
    (neither framework_operation nor framework_error)."""
    _seed_ndjson(
        project,
        session_id="sess-other",
        totals={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2, "cost_usd": 0.0},
    )

    rstop._emit_session_token_rollup(project, session_id="sess-missing", correlation_id="corr-test")

    events = _read_events(project)
    rollup_kinds = {(e.get("kind"), (e.get("detail") or {}).get("operation")) for e in events}
    assert ("framework_operation", "session_token_rollup") not in rollup_kinds
    assert not any(
        e.get("kind") == "framework_error"
        and (e.get("detail") or {}).get("error_code") == "session_rollup_skipped"
        for e in events
    )


# ---------------------------------------------------------------------------
# Branch 3: no NDJSON + no transcript -> silent skip (spec-148 change)
# ---------------------------------------------------------------------------


def test_session_rollup_silent_when_no_ndjson_and_no_transcript(rstop, project: Path) -> None:
    """spec-148: no NDJSON (and no transcript) -> nothing to roll up; the
    hook stays silent (no framework_operation, no framework_error). This
    replaces the old SQLite-missing -> framework_error behavior; an empty
    repo simply has no events to summarise."""
    assert not (project / NDJSON_REL).exists()

    rstop._emit_session_token_rollup(
        project, session_id="sess-no-events", correlation_id="corr-test"
    )

    events = _read_events(project)
    assert not any(
        e.get("kind") == "framework_operation"
        and (e.get("detail") or {}).get("operation") == "session_token_rollup"
        for e in events
    )
    assert not any(
        e.get("kind") == "framework_error"
        and (e.get("detail") or {}).get("error_code") == "session_rollup_skipped"
        for e in events
    )


# ---------------------------------------------------------------------------
# Branch 4: session_id is None -> silent
# ---------------------------------------------------------------------------


def test_session_rollup_silent_when_session_id_missing(rstop, project: Path) -> None:
    """No session_id from the IDE payload -> nothing meaningful to roll up;
    hook stays silent (no ``framework_operation`` and no ``framework_error``)."""
    rstop._emit_session_token_rollup(project, session_id=None, correlation_id="corr-test")

    events = _read_events(project)
    assert events == []
