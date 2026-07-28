"""Behavioural tests for the PreToolUse token spend cap (spec-201 D-201-13).

Every test executes the real hook through ``_lib/run-hook.sh`` against a
``tmp_path`` project — nothing is mocked, so a passing test means the hook
genuinely blocked (or genuinely allowed) an agent dispatch.

Exit contract, mirroring ``no-verify-guard.py``:
    0 — allow (passthrough)
    2 — deny (over the configured cap)

Two properties are load-bearing and both are asserted here rather than
described:

* **Inert by default.** With no env var and no manifest key the cap is 0 and
  the hook can never deny, whatever the transcript says.
* **Bounded hot path.** PreToolUse is the sub-second path. A full
  ``aggregate_session_usage`` measured 176 ms on a real 76 MB transcript and
  grows without bound. The property asserted here is that cost does not
  scale with transcript size — a 40 MB transcript must cost about what a
  400-byte one costs — which only incremental / windowed accounting achieves.
  It is expressed as a ratio rather than a wall-clock budget because a shared
  CI runner measured 306 ms for the same code that costs ~60 ms locally, so an
  absolute threshold grades the runner instead of the hook. A generous
  absolute backstop is kept alongside it.
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOKS = REPO / ".ai-engineering" / "scripts" / "hooks"
RUN_HOOK = HOOKS / "_lib" / "run-hook.sh"
GUARD = HOOKS / "spend-cap-guard.py"

_STATE_REL = Path(".ai-engineering") / "runtime" / "spend-cap.json"

# Every test here drives the guard through `_lib/run-hook.sh`, which is the
# real launcher `.claude/settings.json` names. That launcher is POSIX-only —
# there is no `run-hook.ps1` twin — so on Windows there is nothing to invoke
# and the assertions would be measuring `bash` availability rather than the
# hook. The guard itself is stdlib-only and platform-neutral; it is the
# launcher, not the hook, that is unavailable. Same posture as
# `tests/integration/hooks/test_cursor_bridge.py`.
pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="_lib/run-hook.sh is the POSIX launcher; no PowerShell twin exists to drive",
)


def _assistant_line(tokens: int) -> str:
    """One transcript line shaped like a Claude Code assistant message."""
    return (
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "model": "claude-opus-5",
                    "usage": {
                        "input_tokens": tokens // 2,
                        "output_tokens": tokens - tokens // 2,
                    },
                },
            }
        )
        + "\n"
    )


def _write_transcript(path: Path, per_line: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(_assistant_line(t) for t in per_line), encoding="utf-8")


def _payload(transcript: Path | None, tool_name: str = "Agent") -> str:
    data: dict[str, object] = {
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": {"description": "dispatch a sub-agent"},
        "session_id": "spend-cap-test",
    }
    if transcript is not None:
        data["transcript_path"] = str(transcript)
    return json.dumps(data)


def _run(project: Path, payload: str, env: dict[str, str] | None = None):
    """Invoke the guard exactly as `.claude/settings.json` does."""
    environ = dict(os.environ)
    environ.update(
        {
            "CLAUDE_PROJECT_DIR": str(project),
            "HOME": str(project / "home"),
        }
    )
    environ.pop("CLAUDE_TRANSCRIPT_PATH", None)
    environ.pop("AIENG_MAX_SESSION_TOKENS", None)
    environ.update(env or {})
    return subprocess.run(
        ["bash", str(RUN_HOOK), str(GUARD)],
        input=payload,
        capture_output=True,
        text=True,
        env=environ,
        cwd=str(project),
        check=False,
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    runtime = tmp_path / ".ai-engineering" / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    (tmp_path / "home").mkdir(parents=True, exist_ok=True)
    # `run-hook.sh` resolves its interpreter per project root and this tmp
    # project has no `.venv`. Seed the resolver's own cache with the
    # interpreter running the suite so the launcher is exercised for real
    # rather than skipped on a host without a named python3.11+ on PATH.
    (runtime / "resolved-python.txt").write_text(sys.executable + "\n", encoding="utf-8")
    return tmp_path


def _set_manifest_cap(project: Path, body: str) -> None:
    (project / ".ai-engineering" / "manifest.yml").write_text(body, encoding="utf-8")


def _state(project: Path) -> dict:
    return json.loads((project / _STATE_REL).read_text(encoding="utf-8"))


# ── 1. DENY ──────────────────────────────────────────────────────────────────


def test_denies_a_dispatch_past_the_configured_cap(project: Path) -> None:
    """Over the cap: exit 2, and stderr names both the cap and the observed total."""
    transcript = project / "home" / "session.jsonl"
    _write_transcript(transcript, [4000, 4000, 4000])
    _set_manifest_cap(project, "performance:\n  budget:\n    max_session_tokens: 5000\n")

    result = _run(project, _payload(transcript))

    assert result.returncode == 2, result.stderr
    assert "5000" in result.stderr, result.stderr
    assert "12000" in result.stderr, result.stderr


def test_deny_emits_the_block_envelope(project: Path) -> None:
    """The deny writes the same stdout envelope shape as `no-verify-guard.py`."""
    transcript = project / "home" / "session.jsonl"
    _write_transcript(transcript, [9000])
    result = _run(project, _payload(transcript), {"AIENG_MAX_SESSION_TOKENS": "100"})

    assert result.returncode == 2, result.stderr
    envelope = json.loads(result.stdout)
    assert envelope["decision"] == "block"
    assert "reason" in envelope


# ── 2. ALLOW ─────────────────────────────────────────────────────────────────


def test_allows_a_dispatch_under_the_cap(project: Path) -> None:
    """Under the cap: exit 0 and the stdin payload passes through unchanged."""
    transcript = project / "home" / "session.jsonl"
    _write_transcript(transcript, [10, 10])
    payload = _payload(transcript)

    result = _run(project, payload, {"AIENG_MAX_SESSION_TOKENS": "1000000"})

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == json.loads(payload)


def test_non_agent_tool_calls_are_never_touched(project: Path) -> None:
    """The cap governs dispatches only — a Bash call passes through even over cap."""
    transcript = project / "home" / "session.jsonl"
    _write_transcript(transcript, [9999])
    result = _run(
        project,
        _payload(transcript, tool_name="Bash"),
        {"AIENG_MAX_SESSION_TOKENS": "1"},
    )
    assert result.returncode == 0, result.stderr


# ── 3. DISABLED BY DEFAULT ───────────────────────────────────────────────────


def test_disabled_by_default_regardless_of_transcript_total(project: Path) -> None:
    """No env var, no manifest key: 0 means off — it can never deny."""
    transcript = project / "home" / "session.jsonl"
    _write_transcript(transcript, [500_000, 500_000])
    _set_manifest_cap(project, "providers:\n  vcs: github\n")

    result = _run(project, _payload(transcript))

    assert result.returncode == 0, result.stderr


def test_explicit_zero_disables_even_with_a_manifest_cap(project: Path) -> None:
    """`AIENG_MAX_SESSION_TOKENS=0` is an escape hatch, not a fall-through."""
    transcript = project / "home" / "session.jsonl"
    _write_transcript(transcript, [9000])
    _set_manifest_cap(project, "performance:\n  budget:\n    max_session_tokens: 10\n")

    result = _run(project, _payload(transcript), {"AIENG_MAX_SESSION_TOKENS": "0"})

    assert result.returncode == 0, result.stderr


def test_env_var_beats_the_manifest_key(project: Path) -> None:
    """Env precedence: a permissive manifest cannot loosen a strict env cap."""
    transcript = project / "home" / "session.jsonl"
    _write_transcript(transcript, [900])
    _set_manifest_cap(project, "performance:\n  budget:\n    max_session_tokens: 10000000\n")

    result = _run(project, _payload(transcript), {"AIENG_MAX_SESSION_TOKENS": "100"})

    assert result.returncode == 2, result.stderr


# ── 4. FAIL-OPEN ─────────────────────────────────────────────────────────────


def test_missing_transcript_fails_open(project: Path) -> None:
    """No transcript is not a reason to block a dispatch."""
    result = _run(
        project,
        _payload(project / "home" / "nope.jsonl"),
        {"AIENG_MAX_SESSION_TOKENS": "1"},
    )
    assert result.returncode == 0, result.stderr


def test_unreadable_transcript_fails_open(project: Path) -> None:
    """A directory where a transcript should be is a broken input, not a deny."""
    bogus = project / "home" / "session.jsonl"
    bogus.mkdir(parents=True, exist_ok=True)
    result = _run(project, _payload(bogus), {"AIENG_MAX_SESSION_TOKENS": "1"})
    assert result.returncode == 0, result.stderr


def test_malformed_manifest_fails_open(project: Path) -> None:
    """A broken `manifest.yml` must never brick the dispatch path."""
    transcript = project / "home" / "session.jsonl"
    _write_transcript(transcript, [9000])
    _set_manifest_cap(project, "performance:\n  budget:\n   : [[[unclosed\n")

    result = _run(project, _payload(transcript))

    assert result.returncode == 0, result.stderr


def test_garbage_transcript_lines_fail_open(project: Path) -> None:
    """Unparseable transcript lines are skipped, never counted, never fatal."""
    transcript = project / "home" / "session.jsonl"
    transcript.parent.mkdir(parents=True, exist_ok=True)
    transcript.write_text("not json\n{\n" + _assistant_line(10), encoding="utf-8")

    result = _run(project, _payload(transcript), {"AIENG_MAX_SESSION_TOKENS": "1000"})

    assert result.returncode == 0, result.stderr


# ── 5. INCREMENTAL ACCOUNTING ────────────────────────────────────────────────


def test_second_invocation_reads_only_the_appended_delta(project: Path) -> None:
    """The cap accounts incrementally: prior total + delta, never a full re-read.

    The seeded state deliberately disagrees with the file's own contents (a
    prior total of 7 against 3 already-written lines worth 300). A full
    re-read would report 900; only incremental accounting reports 7 + 600.
    """
    transcript = project / "home" / "session.jsonl"
    _write_transcript(transcript, [100, 100, 100])
    state_path = project / _STATE_REL
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "transcript": str(transcript),
                "offset": transcript.stat().st_size,
                "cumulative_tokens": 7,
            }
        ),
        encoding="utf-8",
    )
    first_offset = transcript.stat().st_size

    with transcript.open("a", encoding="utf-8") as fh:
        for _ in range(3):
            fh.write(_assistant_line(200))

    result = _run(project, _payload(transcript), {"AIENG_MAX_SESSION_TOKENS": "1000000"})
    assert result.returncode == 0, result.stderr

    state = _state(project)
    assert state["offset"] > first_offset, "offset did not advance"
    assert state["offset"] == transcript.stat().st_size
    assert state["cumulative_tokens"] == 7 + 600, state
    assert state["transcript"] == str(transcript)


def test_a_rotated_transcript_resets_the_offset(project: Path) -> None:
    """A shrunk file (rotation) restarts accounting instead of reading past EOF."""
    transcript = project / "home" / "session.jsonl"
    _write_transcript(transcript, [100] * 5)
    state_path = project / _STATE_REL
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "transcript": str(transcript),
                "offset": transcript.stat().st_size * 10,
                "cumulative_tokens": 42,
            }
        ),
        encoding="utf-8",
    )

    result = _run(project, _payload(transcript), {"AIENG_MAX_SESSION_TOKENS": "1000000"})
    assert result.returncode == 0, result.stderr

    state = _state(project)
    assert state["offset"] == transcript.stat().st_size
    assert state["cumulative_tokens"] == 500


def test_switching_transcript_restarts_accounting(project: Path) -> None:
    """A different session's transcript never inherits the previous total."""
    old = project / "home" / "old.jsonl"
    new = project / "home" / "new.jsonl"
    _write_transcript(old, [100])
    _write_transcript(new, [50])
    state_path = project / _STATE_REL
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {"transcript": str(old), "offset": old.stat().st_size, "cumulative_tokens": 999}
        ),
        encoding="utf-8",
    )

    result = _run(project, _payload(new), {"AIENG_MAX_SESSION_TOKENS": "1000000"})
    assert result.returncode == 0, result.stderr

    state = _state(project)
    assert state["transcript"] == str(new)
    assert state["cumulative_tokens"] == 50


# ── 6. HOT PATH ──────────────────────────────────────────────────────────────


def test_hot_path_stays_under_the_budget_on_a_40mb_transcript(project: Path) -> None:
    """End to end under 250 ms against 40 MB — bounded reads, not a full scan.

    Measured baselines this budget derives from: `aggregate_session_usage`
    costs 176.0 ms on a real 76 MB transcript versus 1.32 ms for a bounded
    256 KB tail read, and an existing PreToolUse hook is already ~105 ms end
    to end. A naive full aggregate would put the dispatch path near 280 ms
    and grow without bound as the session lengthens.
    """
    transcript = project / "home" / "session.jsonl"
    transcript.parent.mkdir(parents=True, exist_ok=True)
    line = _assistant_line(100)
    chunk = line * 1000
    target = 40 * 1024 * 1024
    with transcript.open("w", encoding="utf-8") as fh:
        written = 0
        while written < target:
            fh.write(chunk)
            written += len(chunk)
    assert transcript.stat().st_size >= target

    small = project / "home" / "small.jsonl"
    _write_transcript(small, [100] * 10)

    env = {"AIENG_MAX_SESSION_TOKENS": "1000000000"}

    def _median_ms(target: Path) -> float:
        timings: list[float] = []
        for _ in range(3):
            # Fresh accounting each run: a retained offset would let the
            # second and third reads skip the file and flatter the result.
            (project / _STATE_REL).unlink(missing_ok=True)
            started = time.perf_counter()
            result = _run(project, _payload(target), env)
            timings.append((time.perf_counter() - started) * 1000)
            assert result.returncode == 0, result.stderr
        return statistics.median(timings)

    small_ms = _median_ms(small)
    big_ms = _median_ms(transcript)

    # The load-bearing property is boundedness, not a wall-clock number: a
    # 40 MB transcript must cost about what a 400-byte one costs, because the
    # hook reads a fixed window rather than the file. Expressed as a ratio so
    # it holds on a slow shared runner, where an absolute 250 ms budget
    # measures the runner rather than the hook (observed 306 ms on CI vs
    # ~60 ms locally for the identical code).
    assert big_ms <= small_ms * 2.0 + 100.0, (
        f"spend cap scales with transcript size: {big_ms:.1f} ms on 40 MB vs "
        f"{small_ms:.1f} ms on 400 B — the read is not bounded"
    )
    # Absolute backstop with CI slack, mirroring tests/perf/test_skill_lint_budget.py.
    assert big_ms <= 250.0 * 2.0, f"spend cap took {big_ms:.1f} ms median on a 40 MB transcript"
