"""spec-201 sub-003: end-to-end cost attribution, transcript -> CLI.

This is the executable form of parent-plan gate T-19 ("``ai-eng audit tokens``
shows a non-zero ``cost_usd`` attributed to the correct engine"). The literal
gate is **not satisfiable against a live Claude Code session**: Claude Code
transcripts carry no cost field of any spelling (verified across the 25 most
recent local transcripts), which the spec itself concedes at D-201-13. Rather
than fabricate a number from a hardcoded price table -- which would rot on
every provider price change and put an invented figure into the very audit
plane this spec is trying to make trustworthy -- the pipeline is proven
against a synthetic OpenAI-compatible transcript, and the honest Claude Code
outcome is pinned alongside it so a future contributor cannot quietly "fix"
the zero.

The full chain exercised here:

    transcript (usage.cost_usd, model)
      -> _lib.transcript_usage.aggregate_session_usage
      -> runtime-stop._emit_session_token_rollup
      -> _lib.observability.emit_framework_operation(session_id=, usage=)
      -> framework-events.ndjson  (top-level sessionId + detail.genai)
      -> ai_engineering.state.audit_rollup.session_token_rollup
      -> ai-eng audit tokens --by session --json

Before this sub-spec the chain broke twice over: the event carried no
``sessionId`` (so the rollup skipped it entirely) and wrote its tokens as flat
``detail`` keys the rollup never reads. A ``sess-e2e`` row could not appear at
all.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

REPO = Path(__file__).resolve().parents[2]
RUNTIME_STOP_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "runtime-stop.py"

runner = CliRunner()


@pytest.fixture
def rstop(monkeypatch: pytest.MonkeyPatch):
    """Load ``runtime-stop.py`` fresh (hyphenated filename needs the loader)."""
    monkeypatch.syspath_prepend(str(REPO / ".ai-engineering" / "scripts" / "hooks"))
    sys.modules.pop("aieng_runtime_stop_e2e", None)
    spec = importlib.util.spec_from_file_location("aieng_runtime_stop_e2e", RUNTIME_STOP_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated project root, pinned as cwd so the CLI never sees the real repo."""
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("CLAUDE_TRANSCRIPT_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _write_transcript(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    model: str,
    messages: list[tuple[int, int]],
    cost: float | None,
) -> None:
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
    path = project_root / "transcript.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_TRANSCRIPT_PATH", str(path))


def _audit_tokens_rows() -> list[dict]:
    result = runner.invoke(create_app(), ["audit", "tokens", "--by", "session", "--json"])
    assert result.exit_code == 0, result.output
    payload_line = next(
        line for line in reversed(result.output.splitlines()) if line.strip().startswith("[")
    )
    rows = json.loads(payload_line)
    assert isinstance(rows, list)
    return rows


@pytest.mark.integration
def test_openai_compatible_transcript_yields_nonzero_cost(
    rstop, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cost-bearing transcript surfaces a non-zero USD figure in the CLI."""
    _write_transcript(
        project,
        monkeypatch,
        model="gpt-4o",
        messages=[(100, 200), (50, 75)],
        cost=0.0143,
    )

    rstop._emit_session_token_rollup(project, session_id="sess-e2e", correlation_id="corr-e2e")

    rows = {row["session_id"]: row for row in _audit_tokens_rows()}

    # Existence is itself the fix: with no top-level sessionId this row could
    # not appear at all, which is why 378 live rollup events were invisible.
    assert "sess-e2e" in rows, f"session row missing entirely: {rows}"
    row = rows["sess-e2e"]

    assert row["cost_usd"] > 0.0
    assert row["cost_usd"] == pytest.approx(0.0286)  # 2 messages x 0.0143
    assert row["input_tokens"] == 150
    assert row["output_tokens"] == 275
    assert row["total_tokens"] == 425
    assert row["genai_system"] == "openai"


@pytest.mark.integration
def test_claude_code_transcript_is_honestly_costless(
    rstop, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The documented Claude Code outcome: real tokens, ``cost_usd`` 0.0.

    Claude Code reports no per-request cost, so the pipeline reports none.
    Pinning this prevents a future contributor from "fixing" the zero with a
    fabricated price table -- explicitly refused scope (spec-201 Risk 1).
    """
    _write_transcript(
        project,
        monkeypatch,
        model="claude-opus-5",
        messages=[(41, 17870)],
        cost=None,
    )

    rstop._emit_session_token_rollup(
        project, session_id="sess-claude-e2e", correlation_id="corr-e2e"
    )

    rows = {row["session_id"]: row for row in _audit_tokens_rows()}

    assert "sess-claude-e2e" in rows, f"session row missing entirely: {rows}"
    row = rows["sess-claude-e2e"]

    assert row["total_tokens"] == 17911
    assert row["cost_usd"] == 0.0
    assert row["genai_system"] == "anthropic"


@pytest.mark.integration
def test_summary_event_does_not_double_count_its_members(
    rstop, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Members carrying the same usage as the summary must not double the row.

    Live streams carry no per-event usage today; the moment they do, a naive
    sum would report exactly 2x. Proven end-to-end, not just in the unit.
    """
    _write_transcript(
        project,
        monkeypatch,
        model="gpt-4o",
        messages=[(100, 200)],
        cost=0.01,
    )
    ndjson = project / ".ai-engineering" / "state" / "framework-events.ndjson"
    ndjson.parent.mkdir(parents=True, exist_ok=True)
    with ndjson.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "kind": "skill_invoked",
                    "engine": "claude_code",
                    "timestamp": "2026-05-04T00:00:00Z",
                    "component": "hook.telemetry-skill",
                    "outcome": "success",
                    "correlationId": "corr-member",
                    "schemaVersion": "1.0",
                    "project": "test",
                    "spanId": "0123456789abcdef",
                    "sessionId": "sess-dup",
                    "detail": {
                        "skill": "ai-build",
                        "genai": {
                            "system": "openai",
                            "request": {"model": "gpt-4o"},
                            "usage": {
                                "input_tokens": 100,
                                "output_tokens": 200,
                                "total_tokens": 300,
                                "cost_usd": 0.01,
                            },
                        },
                    },
                }
            )
            + "\n"
        )

    rstop._emit_session_token_rollup(project, session_id="sess-dup", correlation_id="corr-e2e")

    row = {r["session_id"]: r for r in _audit_tokens_rows()}["sess-dup"]

    assert row["total_tokens"] == 300, "summary must max-merge with its members, not add"
    assert row["cost_usd"] == pytest.approx(0.01)
    assert row["events"] == 2
