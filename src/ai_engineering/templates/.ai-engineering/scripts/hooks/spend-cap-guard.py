#!/usr/bin/env python3
"""PreToolUse hook: token-denominated session spend cap (spec-201 D-201-13).

Denies an agent DISPATCH once the session's observed token spend reaches the
configured cap. Registered on ``PreToolUse`` with matcher ``Agent`` because the
existing dispatch observer (``observe.py``) fires on ``PostToolUse`` — after
the dispatch has already happened — so it can account but can never block.

Exit codes:
- 0 — passthrough (under the cap, cap disabled, or anything unknowable).
- 2 — deny (the session's observed spend reached the cap).

Unit is TOKENS, not currency: a per-request cost exists only on the
OpenAI-compatible path, so a USD cap would be absent on the surface used most.
Tokens are present on every path.

**Disabled by default.** ``performance.budget.max_session_tokens`` ships as
``0`` and ``0`` means "no cap". A non-zero shipped default would begin denying
dispatches in every consumer repository at a number nobody chose. Resolution
order (env wins, mirroring ``_lib/ioc_eval._fail_closed_enabled``):

1. ``AIENG_MAX_SESSION_TOKENS`` — a positive integer caps; a literal ``0``
   disables even when the manifest configures a cap.
2. ``manifest.yml`` ``performance.budget.max_session_tokens``.
3. ``0`` (disabled).

**Bounded accounting.** PreToolUse is the sub-second hot path, and a full
``aggregate_session_usage`` costs 176 ms on a real 76 MB transcript and grows
without bound as the session lengthens. This hook therefore never re-reads a
transcript: it persists ``{transcript, offset, cumulative_tokens}`` under
``.ai-engineering/runtime/`` and, on each dispatch, sums only the assistant
usage blocks appended since the previous one. On first sight of a transcript
it reads a bounded trailing window instead of the whole file, so a single
invocation is O(window) regardless of transcript size. The cap is a hot-path
guard, not an accountant — ``ai-eng audit tokens`` owns exact totals.

Fails OPEN everywhere except the deny decision itself: a missing transcript, an
unreadable one, a malformed manifest or any unexpected error passes the
dispatch through. A broken config must never brick the dispatch path.

Stdlib-only (no ``ai_engineering.*`` imports) — same sealed contract as the
rest of ``.ai-engineering/scripts/hooks/``.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import passthrough_stdin
from _lib.hook_common import run_hook_safe
from _lib.hook_context import get_hook_context
from _lib.runtime_state import _env_int, read_json, runtime_dir, write_json
from _lib.transcript_usage import find_active_transcript

_CAP_ENV = "AIENG_MAX_SESSION_TOKENS"
_MANIFEST_RELATIVE = Path(".ai-engineering") / "manifest.yml"
_STATE_NAME = "spend-cap.json"

# First-sight read window. 256 KiB measured at ~1.3 ms against the same
# transcripts a full aggregate scans in 93-176 ms.
_COLD_START_WINDOW = 256 * 1024

# The dispatch tool this cap governs. Matches `observe.py`'s PostToolUse
# matcher, one event earlier.
_DISPATCH_TOOL = "Agent"


def _manifest_cap(project_root: Path) -> int:
    """Read ``performance.budget.max_session_tokens``; 0 on any failure.

    Lazy ``import yaml`` inside one broad ``except`` so a missing PyYAML, an
    unreadable file or a parse error all land on "no cap" rather than an
    exception on the hot path.
    """
    try:
        import yaml

        payload = yaml.safe_load((project_root / _MANIFEST_RELATIVE).read_text(encoding="utf-8"))
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0
    performance = payload.get("performance")
    if not isinstance(performance, dict):
        return 0
    budget = performance.get("budget")
    if not isinstance(budget, dict):
        return 0
    raw = budget.get("max_session_tokens")
    if isinstance(raw, bool) or not isinstance(raw, int) or raw <= 0:
        return 0
    return raw


def resolve_cap(project_root: Path) -> int:
    """Return the session token cap. ``0`` means disabled — never deny."""
    raw = (os.environ.get(_CAP_ENV) or "").strip()
    if raw == "0":
        return 0
    env_cap = _env_int(_CAP_ENV, 0)
    if env_cap > 0:
        return env_cap
    return _manifest_cap(project_root)


def _resolve_transcript(ctx) -> Path | None:
    """The active transcript: the payload's own path, else the session's."""
    candidate = ctx.data.get("transcript_path")
    if isinstance(candidate, str) and candidate.strip():
        path = Path(candidate)
        if path.is_file():
            return path
    return find_active_transcript(ctx.project_root, session_id=ctx.session_id)


def _safe_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(value)


def _tokens_in(text: str) -> int:
    """Sum ``input_tokens + output_tokens`` over assistant lines in ``text``."""
    total = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict) or obj.get("type") != "assistant":
            continue
        message = obj.get("message")
        if not isinstance(message, dict):
            continue
        usage = message.get("usage")
        if not isinstance(usage, dict):
            continue
        total += _safe_int(usage.get("input_tokens")) + _safe_int(usage.get("output_tokens"))
    return total


def account(transcript: Path, state: dict | None) -> tuple[int, int]:
    """Return ``(cumulative_tokens, offset)`` after folding in the new bytes.

    Reads the bytes appended since ``state["offset"]`` when the state belongs
    to this transcript and still fits inside it. Otherwise treats the file as
    unseen and reads a bounded trailing window, so first sight of a 40 MB
    transcript costs the same as first sight of a 4 KB one.
    """
    size = transcript.stat().st_size
    prior_tokens = 0
    start = max(0, size - _COLD_START_WINDOW)
    drop_partial_first_line = start > 0

    if isinstance(state, dict) and str(state.get("transcript") or "") == str(transcript):
        offset = _safe_int(state.get("offset"))
        if 0 <= offset <= size:
            prior_tokens = _safe_int(state.get("cumulative_tokens"))
            start = offset
            drop_partial_first_line = False

    if start >= size:
        return prior_tokens, size

    with transcript.open("rb") as handle:
        handle.seek(start)
        buf = handle.read()

    # Never consume a half-written trailing line: stop at the last newline so
    # the next dispatch re-reads it complete.
    end = buf.rfind(b"\n")
    if end == -1:
        return prior_tokens, start
    buf = buf[: end + 1]
    new_offset = start + len(buf)

    text = buf.decode("utf-8", errors="replace")
    if drop_partial_first_line:
        _, _, text = text.partition("\n")
    return prior_tokens + _tokens_in(text), new_offset


def _deny(cap: int, observed: int) -> None:
    sys.stderr.write(
        f"[spend-cap-guard] refusing Agent dispatch: session spend {observed} tokens "
        f"reached the cap of {cap}.\n"
        f"[spend-cap-guard] raise {_CAP_ENV} / performance.budget.max_session_tokens, "
        "or start a fresh session.\n"
    )
    sys.stderr.flush()
    sys.stdout.write(
        json.dumps(
            {
                "decision": "block",
                "reason": (
                    f"session token spend {observed} reached the configured cap {cap} "
                    "(spec-201 D-201-13)."
                ),
            }
        )
    )
    sys.stdout.flush()
    sys.exit(2)


def main() -> None:
    ctx = get_hook_context()
    if ctx.data.get("tool_name") != _DISPATCH_TOOL:
        passthrough_stdin(ctx.data)
        return

    cap = resolve_cap(ctx.project_root)
    transcript = _resolve_transcript(ctx)
    if transcript is None or not transcript.is_file():
        passthrough_stdin(ctx.data)
        return

    state_path = runtime_dir(ctx.project_root) / _STATE_NAME
    try:
        cumulative, offset = account(transcript, read_json(state_path))
        write_json(
            state_path,
            {
                "transcript": str(transcript),
                "offset": offset,
                "cumulative_tokens": cumulative,
            },
        )
    except OSError:
        # Accounting is best-effort; an I/O failure must not block a dispatch.
        passthrough_stdin(ctx.data)
        return

    if cap > 0 and cumulative >= cap:
        _deny(cap, cumulative)
    passthrough_stdin(ctx.data)


if __name__ == "__main__":
    run_hook_safe(
        main,
        component="hook.spend-cap",
        hook_kind="pre-tool-use",
        script_path=Path(__file__),
    )
