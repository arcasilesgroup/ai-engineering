"""Tests for ``_lib/transcript_usage.py`` (spec-120 follow-up Item C).

Spec-120 T-E2 had to be a NO-OP because the IDE-level hook payload never
carries per-call token usage. This module bridges the gap: Claude Code's
session transcript files DO carry ``usage`` blocks on every assistant
message, and we read them directly.

Pin three contracts:

1. ``read_latest_usage`` returns the LAST assistant message's usage.
2. ``aggregate_session_usage`` sums input/output across the whole transcript.
3. Missing transcript / malformed lines / non-assistant messages all degrade
   silently rather than raising.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
LIB_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "transcript_usage.py"


@pytest.fixture
def lib():
    sys.modules.pop("aieng_transcript_usage", None)
    spec = importlib.util.spec_from_file_location("aieng_transcript_usage", LIB_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _assistant_line(*, model: str, in_tok: int, out_tok: int) -> str:
    return json.dumps(
        {
            "type": "assistant",
            "message": {
                "model": model,
                "role": "assistant",
                "content": [],
                "usage": {
                    "input_tokens": in_tok,
                    "output_tokens": out_tok,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
            },
            "sessionId": "sess-1",
        }
    )


def _write_transcript(tmp: Path, lines: list[str]) -> Path:
    path = tmp / "transcript.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# read_latest_usage
# ---------------------------------------------------------------------------


def test_read_latest_usage_picks_most_recent_assistant_message(lib, tmp_path: Path) -> None:
    transcript = _write_transcript(
        tmp_path,
        [
            _assistant_line(model="claude-opus-4-7", in_tok=10, out_tok=20),
            json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}}),
            _assistant_line(model="claude-sonnet-4-5", in_tok=5, out_tok=99),
        ],
    )

    out = lib.read_latest_usage(transcript)

    assert out is not None
    assert out["input_tokens"] == 5
    assert out["output_tokens"] == 99
    assert out["total_tokens"] == 104
    assert out["model"] == "claude-sonnet-4-5"
    assert out["system"] == "anthropic"


# ---------------------------------------------------------------------------
# aggregate_session_usage
# ---------------------------------------------------------------------------


def test_aggregate_session_usage_sums_correctly(lib, tmp_path: Path) -> None:
    transcript = _write_transcript(
        tmp_path,
        [
            _assistant_line(model="claude-opus-4-7", in_tok=100, out_tok=200),
            _assistant_line(model="claude-opus-4-7", in_tok=50, out_tok=75),
            _assistant_line(model="claude-sonnet-4-5", in_tok=10, out_tok=15),
        ],
    )

    out = lib.aggregate_session_usage(transcript)

    assert out["input_tokens"] == 160
    assert out["output_tokens"] == 290
    assert out["total_tokens"] == 450
    assert out["model"] == "claude-sonnet-4-5"  # most recent
    assert out["system"] == "anthropic"


# ---------------------------------------------------------------------------
# Best-effort degradation
# ---------------------------------------------------------------------------


def test_missing_transcript_returns_none(lib, tmp_path: Path) -> None:
    # File doesn't exist
    out = lib.read_latest_usage(tmp_path / "nonexistent.jsonl")
    assert out is None


def test_aggregate_missing_transcript_returns_zero(lib, tmp_path: Path) -> None:
    out = lib.aggregate_session_usage(tmp_path / "nonexistent.jsonl")
    assert out["input_tokens"] == 0
    assert out["output_tokens"] == 0
    assert out["total_tokens"] == 0


def test_malformed_lines_skipped(lib, tmp_path: Path) -> None:
    transcript = _write_transcript(
        tmp_path,
        [
            "{not valid json",
            _assistant_line(model="claude-opus-4-7", in_tok=10, out_tok=20),
            "more garbage {",
            _assistant_line(model="claude-opus-4-7", in_tok=5, out_tok=5),
        ],
    )
    out = lib.aggregate_session_usage(transcript)
    assert out["input_tokens"] == 15
    assert out["output_tokens"] == 25


def test_non_assistant_messages_ignored(lib, tmp_path: Path) -> None:
    transcript = _write_transcript(
        tmp_path,
        [
            json.dumps(
                {
                    "type": "user",
                    "message": {"role": "user", "usage": {"input_tokens": 9999}},
                }
            ),
            json.dumps({"type": "system", "content": "boot"}),
            json.dumps({"type": "last-prompt", "leafUuid": "x", "sessionId": "s"}),
            _assistant_line(model="claude-opus-4-7", in_tok=10, out_tok=20),
        ],
    )
    out = lib.aggregate_session_usage(transcript)
    assert out["input_tokens"] == 10
    assert out["output_tokens"] == 20


def test_empty_transcript_returns_zero_aggregate(lib, tmp_path: Path) -> None:
    transcript = tmp_path / "empty.jsonl"
    transcript.write_text("", encoding="utf-8")
    out = lib.aggregate_session_usage(transcript)
    assert out["input_tokens"] == 0
    assert out["model"] == ""


# ---------------------------------------------------------------------------
# find_active_transcript
# ---------------------------------------------------------------------------


def test_find_active_transcript_uses_env_override(
    lib, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    explicit = tmp_path / "explicit.jsonl"
    explicit.write_text("", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_TRANSCRIPT_PATH", str(explicit))
    found = lib.find_active_transcript(tmp_path / "doesnt-matter")
    assert found == explicit


def test_find_active_transcript_resolves_via_session_slug(
    lib, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Build a fake ``$HOME/.claude/projects/<slug>/<sid>.jsonl`` layout and
    confirm the resolver picks it up."""
    fake_home = tmp_path / "home"
    project = tmp_path / "real-project"
    project.mkdir()
    slug = str(project.resolve()).replace("/", "-")
    transcripts_dir = fake_home / ".claude" / "projects" / slug
    transcripts_dir.mkdir(parents=True)
    sid_path = transcripts_dir / "sess-abc.jsonl"
    sid_path.write_text("", encoding="utf-8")

    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.delenv("CLAUDE_TRANSCRIPT_PATH", raising=False)

    found = lib.find_active_transcript(project, session_id="sess-abc")
    assert found == sid_path


def test_find_active_transcript_returns_none_when_dir_missing(
    lib, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "no-home"))
    monkeypatch.delenv("CLAUDE_TRANSCRIPT_PATH", raising=False)
    found = lib.find_active_transcript(tmp_path / "anything")
    assert found is None


def test_find_active_transcript_falls_back_to_most_recent(
    lib, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No matching session_id -> pick the newest *.jsonl in the slug dir."""
    fake_home = tmp_path / "home"
    project = tmp_path / "proj"
    project.mkdir()
    slug = str(project.resolve()).replace("/", "-")
    transcripts_dir = fake_home / ".claude" / "projects" / slug
    transcripts_dir.mkdir(parents=True)
    older = transcripts_dir / "older.jsonl"
    newer = transcripts_dir / "newer.jsonl"
    older.write_text("", encoding="utf-8")
    newer.write_text("", encoding="utf-8")
    import os

    os.utime(older, (1000, 1000))
    os.utime(newer, (2000, 2000))

    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.delenv("CLAUDE_TRANSCRIPT_PATH", raising=False)

    found = lib.find_active_transcript(project, session_id="not-on-disk")
    assert found == newer
