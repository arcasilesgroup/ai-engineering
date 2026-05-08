"""Best-effort token usage extraction from Claude Code transcript files.

Spec-120 T-E2 was a NO-OP because the IDE-level hook payload never carried
per-call token counts; the schema slots existed but no real numbers ever
flowed through. This module wires up the missing data source: Claude Code's
session transcripts.

Transcript layout (verified on 2026-05-04 against
``/Users/soydachi/.claude/projects/-Users-<...>-ai-engineering/<session-id>.jsonl``)
-- one JSON object per line. Lines come in several ``type``s, of which we
care about ``"assistant"``::

    {
      "type": "assistant",
      "message": {
        "model": "claude-opus-4-7",
        "id": "...",
        "role": "assistant",
        "content": [...],
        "stop_reason": "...",
        "usage": {
          "input_tokens": 6,
          "output_tokens": 589,
          "cache_creation_input_tokens": 169020,
          "cache_read_input_tokens": 0,
          "service_tier": "standard",
          ...
        }
      },
      "sessionId": "...",
      "timestamp": "...",
      ...
    }

Other line types (``user``, ``attachment``, ``system``, ``last-prompt``,
``permission-mode``, ``ai-title``, ``file-history-snapshot``) do not carry
``usage`` and are skipped.

Path convention: Claude Code writes transcripts to
``${HOME}/.claude/projects/<slug>/<session-id>.jsonl``, where ``<slug>`` is
the absolute project path with ``/`` replaced by ``-``. We accept an
explicit ``CLAUDE_TRANSCRIPT_PATH`` env override for forward-compat.

Sealed contract: stdlib-only. Best-effort everywhere -- a missing transcript
or a malformed line is never an error; the caller decides whether to emit a
``framework_error`` or stay silent.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

__all__ = [
    "aggregate_session_usage",
    "find_active_transcript",
    "iter_assistant_usages",
    "read_latest_usage",
]


def _project_slug(project_root: Path) -> str:
    """Return the Claude Code transcripts directory name for ``project_root``.

    Convention: replace every path separator in the absolute path with ``-``.
    E.g. POSIX ``/Users/.../ai-engineering`` -> ``-Users-...-ai-engineering``.

    Cross-OS: Windows absolute paths use ``\\`` separators and a drive-letter
    colon (``C:\\Users\\...``). The slug must be a single valid path
    component on the destination filesystem, so we strip both ``/`` and
    ``\\`` (the only two POSIX/NTFS separators) plus ``:`` (illegal in NTFS
    path components). The POSIX result is unchanged because ``\\`` and
    ``:`` never appear in absolute POSIX paths.
    """
    abs_path = str(project_root.resolve())
    return abs_path.replace("/", "-").replace("\\", "-").replace(":", "-")


def _transcripts_root() -> Path | None:
    """Return ``~/.claude/projects`` if it exists, else ``None``."""
    home = os.environ.get("HOME") or os.path.expanduser("~")
    if not home:
        return None
    candidate = Path(home) / ".claude" / "projects"
    return candidate if candidate.is_dir() else None


def find_active_transcript(
    project_root: Path,
    *,
    session_id: str | None = None,
) -> Path | None:
    """Locate the transcript file for the active session, best-effort.

    Resolution order:

    1. ``CLAUDE_TRANSCRIPT_PATH`` env var (explicit override).
    2. ``<HOME>/.claude/projects/<slug>/<session_id>.jsonl`` if both inputs
       are available and the file exists.
    3. The most recently modified ``*.jsonl`` under
       ``<HOME>/.claude/projects/<slug>/`` (latest session).

    Returns ``None`` when nothing matches.
    """
    env_path = os.environ.get("CLAUDE_TRANSCRIPT_PATH", "").strip()
    if env_path:
        candidate = Path(env_path)
        if candidate.is_file():
            return candidate

    root = _transcripts_root()
    if root is None:
        return None

    slug_dir = root / _project_slug(project_root)
    if not slug_dir.is_dir():
        return None

    if session_id:
        direct = slug_dir / f"{session_id}.jsonl"
        if direct.is_file():
            return direct

    # Fall back to the most recent transcript in the slug dir.
    try:
        candidates = [p for p in slug_dir.glob("*.jsonl") if p.is_file()]
    except OSError:
        return None
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def iter_assistant_usages(transcript_path: Path):
    """Yield ``(usage_dict, model)`` tuples for every assistant message that
    carries a ``usage`` block. Malformed lines and non-assistant messages are
    silently skipped."""
    try:
        fh = transcript_path.open("r", encoding="utf-8")
    except OSError:
        return
    try:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(obj, dict) or obj.get("type") != "assistant":
                continue
            msg = obj.get("message")
            if not isinstance(msg, dict):
                continue
            usage = msg.get("usage")
            if not isinstance(usage, dict):
                continue
            yield usage, str(msg.get("model") or "")
    finally:
        fh.close()


def read_latest_usage(transcript_path: Path) -> dict | None:
    """Return the latest assistant ``usage`` block (with ``model`` and
    ``system`` injected), shaped for the canonical emit helpers.

    Returns ``None`` when the transcript is missing, unreadable, or carries
    no assistant ``usage`` blocks.
    """
    if not transcript_path.is_file():
        return None
    latest_usage: dict | None = None
    latest_model = ""
    for usage, model in iter_assistant_usages(transcript_path):
        latest_usage = usage
        latest_model = model
    if latest_usage is None:
        return None
    return _shape_usage(latest_usage, latest_model)


def aggregate_session_usage(transcript_path: Path) -> dict:
    """Sum ``input_tokens`` and ``output_tokens`` across every assistant
    message in the transcript. Returns the canonical shape::

        {
          "input_tokens": int,
          "output_tokens": int,
          "total_tokens": int,
          "model": str,        # most recent assistant model
          "system": "anthropic",
        }

    Empty transcripts produce a zeroed payload (NOT ``None``) so callers can
    safely merge into a rollup dict.
    """
    total_in = 0
    total_out = 0
    latest_model = ""
    if transcript_path.is_file():
        for usage, model in iter_assistant_usages(transcript_path):
            total_in += _safe_int(usage.get("input_tokens"))
            total_out += _safe_int(usage.get("output_tokens"))
            if model:
                latest_model = model
    return {
        "input_tokens": total_in,
        "output_tokens": total_out,
        "total_tokens": total_in + total_out,
        "model": latest_model,
        "system": "anthropic",
    }


def _shape_usage(usage: dict, model: str) -> dict:
    in_tok = _safe_int(usage.get("input_tokens"))
    out_tok = _safe_int(usage.get("output_tokens"))
    return {
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "total_tokens": in_tok + out_tok,
        "model": model,
        "system": "anthropic",
    }


def _safe_int(value: object) -> int:
    if isinstance(value, bool):  # bool is an int subclass; reject it
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0
