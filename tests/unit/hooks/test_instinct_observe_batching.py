"""spec-139 M5.T2 — ``instinct-observe.py`` per-process write batching.

The PreToolUse + PostToolUse hooks both fire on every tool call. Naive
flush-per-event doubles the NDJSON write rate for the instinct ratchet.
The hook accumulates observations in a module-scope buffer and flushes
only when one of three triggers fires:

  * 50 events buffered (size threshold), OR
  * 5 seconds since the previous flush (time threshold), OR
  * SubagentStop / Stop event (natural drain point — ``hook_kind="stop"``).

This module pins each trigger independently so a future refactor that
weakens one trigger is caught at the contract level.

Cross-platform: tests reload the module fresh per case so the module-
scope buffer always starts empty. ``monkeypatch.setattr`` replaces the
real ``append_instinct_observation`` writer with a counter so the test
never touches the NDJSON file. ``monkeypatch.delenv`` keeps env state
hermetic across runs on every OS.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOK_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "instinct-observe.py"
HOOK_DIR = REPO / ".ai-engineering" / "scripts" / "hooks"


@pytest.fixture
def observe(monkeypatch: pytest.MonkeyPatch):
    """Reload instinct-observe fresh so the buffer starts empty.

    Module-scope state (``_OBSERVATION_BUFFER``, ``_BUFFER_LAST_FLUSH``)
    MUST start at the documented defaults; otherwise leakage from a
    previous test would make threshold assertions non-deterministic.
    """
    monkeypatch.delenv("AIENG_INSTINCT_BATCH_DISABLED", raising=False)
    monkeypatch.syspath_prepend(str(HOOK_DIR))
    sys.modules.pop("aieng_instinct_batch_test", None)
    spec = importlib.util.spec_from_file_location("aieng_instinct_batch_test", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Defence in depth: force the buffer empty even if the spec import
    # path somehow inherited a non-default value.
    module._OBSERVATION_BUFFER.clear()
    module._BUFFER_LAST_FLUSH = 0.0
    return module


def _enqueue(observe, count: int, *, project: Path = Path("/tmp/fake")) -> None:
    """Add ``count`` observation kwargs to the in-memory buffer."""
    for idx in range(count):
        observe._enqueue_observation(
            project_root=project,
            engine="claude_code",
            hook_event="PostToolUse",
            data={"tool_name": "Read", "idx": idx},
            session_id="sess-test",
        )


# ---------------------------------------------------------------------------
# Trigger 1 — 50-event size threshold.
# ---------------------------------------------------------------------------


def test_should_flush_fires_at_size_threshold(observe) -> None:
    """The 50-event size trigger MUST fire on the 50th event exactly.

    Pinning the boundary explicitly so a future drift from `>=` to `>`
    (which would silently raise the threshold to 51) is caught.
    """
    # 49 entries: still below threshold (and we're not at first-flush
    # because we'll set _BUFFER_LAST_FLUSH to a recent monotonic value).
    _enqueue(observe, 49)
    observe._BUFFER_LAST_FLUSH = 1000.0
    assert observe._should_flush(now=1000.5, hook_kind=None) is False

    # One more pushes the buffer over the 50-entry threshold.
    _enqueue(observe, 1)
    assert observe._should_flush(now=1000.5, hook_kind=None) is True


def test_should_flush_holds_below_threshold(observe) -> None:
    """At 10 events with recent flush + no stop signal, MUST NOT flush.

    The whole point of batching is to amortise small bursts; firing at
    every Nth event below 50 would weaken the contract.
    """
    _enqueue(observe, 10)
    observe._BUFFER_LAST_FLUSH = 1000.0
    # 1 s since last flush — well below the 5 s window.
    assert observe._should_flush(now=1001.0, hook_kind=None) is False


# ---------------------------------------------------------------------------
# Trigger 2 — 5-second time threshold.
# ---------------------------------------------------------------------------


def test_should_flush_fires_at_time_threshold(observe) -> None:
    """Five seconds since the last flush MUST trigger a drain.

    Bounded so a low-volume session (one tool call per minute) does not
    keep a partial buffer indefinitely.
    """
    _enqueue(observe, 5)
    observe._BUFFER_LAST_FLUSH = 1000.0
    # 5.0 s elapsed exactly — boundary; predicate uses ``>=`` so True.
    assert observe._should_flush(now=1005.0, hook_kind=None) is True


def test_should_flush_holds_inside_time_window(observe) -> None:
    """4.9 s since last flush + below size threshold → MUST NOT flush."""
    _enqueue(observe, 5)
    observe._BUFFER_LAST_FLUSH = 1000.0
    assert observe._should_flush(now=1004.9, hook_kind=None) is False


def test_should_flush_first_call_fires_when_anything_queued(observe) -> None:
    """First-flush special case: ``_BUFFER_LAST_FLUSH==0.0`` + queue non-empty.

    Holding a single observation for 5 s on the very first call would be
    a UX bug — the contract is to flush immediately the first time so
    short sessions never lose their only observation.
    """
    _enqueue(observe, 1)
    assert observe._BUFFER_LAST_FLUSH == 0.0
    assert observe._should_flush(now=0.01, hook_kind=None) is True


def test_should_flush_first_call_holds_when_queue_empty(observe) -> None:
    """First-flush special case MUST NOT fire on an empty buffer.

    Otherwise the import-time fast path would write a zero-entry batch
    every time the hook loads.
    """
    assert observe._BUFFER_LAST_FLUSH == 0.0
    assert len(observe._OBSERVATION_BUFFER) == 0
    assert observe._should_flush(now=0.01, hook_kind=None) is False


# ---------------------------------------------------------------------------
# Trigger 3 — SubagentStop / Stop natural drain point.
# ---------------------------------------------------------------------------


def test_should_flush_fires_on_stop_regardless_of_buffer_size(observe) -> None:
    """``hook_kind="stop"`` MUST drain whatever is buffered, even one entry.

    The SubagentStop cascade is the natural flush boundary — buffered
    observations from an in-flight sub-agent should land in the NDJSON
    chain before the parent session moves on.
    """
    _enqueue(observe, 1)
    observe._BUFFER_LAST_FLUSH = 1000.0
    # Just 0.5 s after last flush — below size AND time thresholds.
    assert observe._should_flush(now=1000.5, hook_kind="stop") is True


def test_should_flush_fires_on_stop_with_empty_buffer(observe) -> None:
    """Stop drain MUST be unconditional on ``hook_kind=="stop"``.

    Even with nothing buffered, the drain path is safe (``_flush_observations``
    is a no-op on empty) and surfacing "True" lets the caller take the
    same code path regardless of buffer state.
    """
    assert len(observe._OBSERVATION_BUFFER) == 0
    assert observe._should_flush(now=1.0, hook_kind="stop") is True


# ---------------------------------------------------------------------------
# Flush mechanics — events drained, buffer cleared.
# ---------------------------------------------------------------------------


def test_flush_drains_buffer_and_calls_writer_per_entry(
    observe, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``_flush_observations`` MUST call the writer once per queued event.

    The buffer collects kwargs dicts; flush dispatches each to
    ``append_instinct_observation``. After a successful flush the buffer
    is empty and ``_BUFFER_LAST_FLUSH`` advances.
    """
    calls: list[dict] = []

    def fake_append(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(observe, "append_instinct_observation", fake_append)

    _enqueue(observe, 3)
    assert len(observe._OBSERVATION_BUFFER) == 3

    observe._flush_observations()
    assert calls and len(calls) == 3
    assert observe._OBSERVATION_BUFFER == []
    assert observe._BUFFER_LAST_FLUSH > 0.0


def test_flush_requeues_remaining_on_partial_failure(
    observe, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the writer raises mid-drain, the failing + remaining entries MUST stay queued.

    This preserves order so the next flush retries in arrival order;
    silently dropping events would break the instinct ratchet contract.
    """
    calls = []

    def flaky_append(**kwargs):
        calls.append(kwargs)
        # Fail on the 2nd event (idx == 1) so entries 1 and 2 stay queued.
        if kwargs["data"]["idx"] == 1:
            raise RuntimeError("disk full")

    monkeypatch.setattr(observe, "append_instinct_observation", flaky_append)

    _enqueue(observe, 3)
    observe._flush_observations()

    # Writer attempted entry 0 (succeeded) and entry 1 (raised). Entries
    # 1 and 2 remain queued for retry, preserving their original order.
    assert len(calls) == 2
    assert len(observe._OBSERVATION_BUFFER) == 2
    assert observe._OBSERVATION_BUFFER[0]["data"]["idx"] == 1
    assert observe._OBSERVATION_BUFFER[1]["data"]["idx"] == 2
