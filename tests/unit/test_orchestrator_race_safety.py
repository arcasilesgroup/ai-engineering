"""Unit tests for ``ai_engineering.policy.orchestrator`` race safety.

RED phase for spec-104 T-2.11 (D-104-01 + R-5 race risk):

    > R-5 — Race entre Wave 1 fixers y Wave 2 checkers. Si Wave 2 arrancara
    > antes de Wave 1 terminar, fixers escribiendo archivos que checkers leen.
    > Mitigación: orchestrator espera explícitamente `wave1.return_code == 0`
    > antes de spawnear Wave 2; integration test con sleep injection en
    > Wave 1 verifica Wave 2 no arranca.

Phase-0 notes refine the contract:

    > Race-safety invariant (R-5 / T-2.11/T-2.12): orchestrator holds
    > `wave1_complete: threading.Event` and `assert wave1_complete.is_set()`
    > before `run_wave2`.

This file pins four invariants. Three of them exercise behaviour and will
fail with ``ImportError`` until T-2.2 / T-2.4 land the orchestrator module
(plain RED). The fourth is a source-level grep that ``pytest.skip``s while
``orchestrator.py`` does not exist, so test collection stays green during
Phase 0/1 — mirroring the skip-friendly pattern from
``tests/integration/test_spec104_orthogonality.py``.

Target module (does not exist yet — created in T-2.2 / T-2.4 / T-2.12):

    ``src/ai_engineering/policy/orchestrator.py`` exposing at least:

        wave1_complete: threading.Event   # owned by the orchestrator instance
        def run_wave1(staged_files) -> Wave1Result
        def run_wave2(staged_files) -> Wave2Result
        def run_gate(...) -> ...   # entry point that signals wave1_complete

    The exact public shape is intentionally narrow here: these tests assert
    only the race-safety contract, not the fixer/checker semantics (those
    belong to the wave1/wave2 unit tests in T-2.1 / T-2.3).

TDD CONSTRAINT: this file is IMMUTABLE after T-2.11 lands. T-2.12 GREEN
implements ``orchestrator.py`` to satisfy these tests; never weaken or
reshape the assertions to make implementation easier.
"""

from __future__ import annotations

import contextlib
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Path constants — anchored at the repo root regardless of cwd.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATOR_PATH = REPO_ROOT / "src" / "ai_engineering" / "policy" / "orchestrator.py"


# ---------------------------------------------------------------------------
# Test 1 — Wave 2 does not start before Wave 1 returns
# ---------------------------------------------------------------------------


def test_wave2_does_not_start_before_wave1_returns() -> None:
    """With sleep injected into Wave 1, Wave 2 MUST NOT start until Wave 1 returns.

    Instrumentation:
      * Patch ``run_wave1`` so that it records its start timestamp, sleeps
        ``WAVE1_SLEEP_SECONDS`` to widen the race window, then records its
        end timestamp before returning.
      * Patch ``run_wave2`` so that it records its start timestamp.
      * Drive ``run_gate`` end-to-end and assert
        ``wave2_start_ts >= wave1_end_ts`` (strict happens-before).

    The patched callables share a tiny, thread-safe dict so we read the
    timestamps without coupling to a particular result type. The contract
    being asserted here is only ordering — Wave 1 must finish (returning
    control) before Wave 2 begins. spec-104 R-5: a fixer mid-write while
    a checker reads the file is exactly the bug this test forbids.

    This test fails with ``ImportError`` until T-2.2 / T-2.4 land.
    """
    # Arrange — import the orchestrator module (RED until T-2.2/T-2.4).
    from ai_engineering.policy import orchestrator

    timestamps: dict[str, float] = {}
    timestamps_lock = threading.Lock()
    wave1_sleep_seconds = 0.25  # >> typical scheduler jitter, < CI test budget

    def fake_run_wave1(*args: object, **kwargs: object) -> object:
        with timestamps_lock:
            timestamps["wave1_start"] = time.monotonic()
        time.sleep(wave1_sleep_seconds)
        with timestamps_lock:
            timestamps["wave1_end"] = time.monotonic()
        # Return a benign object; Wave 1 success is not the contract under
        # test. Real Wave1Result shape is exercised in T-2.1.
        return mock.MagicMock(return_code=0, ok=True)

    def fake_run_wave2(*args: object, **kwargs: object) -> object:
        with timestamps_lock:
            timestamps["wave2_start"] = time.monotonic()
        return mock.MagicMock(return_code=0, ok=True)

    # Act — drive the orchestrator's public entry point. We deliberately
    # do not pin its exact signature here; this test asserts ordering, so
    # any callable named ``run_gate`` exposed by the module will do.
    with (
        mock.patch.object(orchestrator, "run_wave1", side_effect=fake_run_wave1),
        mock.patch.object(orchestrator, "run_wave2", side_effect=fake_run_wave2),
    ):
        run_gate = getattr(orchestrator, "run_gate", None)
        assert run_gate is not None, (
            "orchestrator must expose a callable ``run_gate`` so callers can "
            "invoke the gate; T-2.12 GREEN must satisfy this contract."
        )
        # Call with the most permissive shape; T-2.12 may add required
        # parameters, in which case this test must be updated as part of
        # the same RED change set (it is locked here to enforce ordering
        # semantics, not the call signature). Signature mismatch is
        # acceptable during RED — but only if it signals the orchestrator
        # wrapper was reached. We still need the timestamps to be
        # populated to assert ordering; if not, the test must fail.
        with contextlib.suppress(TypeError):
            run_gate()

    # Assert — wave1 completed before wave2 started.
    assert "wave1_start" in timestamps, (
        "run_gate must invoke run_wave1; got no wave1_start timestamp"
    )
    assert "wave1_end" in timestamps, (
        "run_wave1 must return before run_wave2 is dispatched; no wave1_end recorded"
    )
    assert "wave2_start" in timestamps, (
        "run_gate must invoke run_wave2 after run_wave1; got no wave2_start timestamp"
    )
    assert timestamps["wave2_start"] >= timestamps["wave1_end"], (
        "RACE: Wave 2 started before Wave 1 returned. "
        f"wave1_end={timestamps['wave1_end']:.6f}s, "
        f"wave2_start={timestamps['wave2_start']:.6f}s, "
        f"delta={timestamps['wave2_start'] - timestamps['wave1_end']:.6f}s. "
        "Per D-104-01, Wave 2 MUST wait for Wave 1 completion."
    )


# ---------------------------------------------------------------------------
# Test 2 — Wave 1 completion is signaled via an explicit threading.Event
# ---------------------------------------------------------------------------


def test_wave1_complete_event_signaled_explicitly() -> None:
    """Orchestrator MUST encode the wave-1→wave-2 happens-before via an Event.

    Per phase-0-notes.md §1:

        Race-safety invariant (R-5 / T-2.11/T-2.12): orchestrator holds
        ``wave1_complete: threading.Event`` and ``assert wave1_complete.is_set()``
        before ``run_wave2``.

    Contract pinned here:
      * ``orchestrator`` module exposes a ``threading.Event`` named
        ``wave1_complete`` (or ``asyncio.Event`` if the orchestrator goes
        async — both are accepted via duck-typed ``is_set`` + ``set``).
      * Before ``run_wave2`` runs, the event MUST have been ``set()``.
      * After ``run_wave2`` runs, the event remains ``set()`` for the
        lifetime of the gate invocation (no double-flip mid-run).

    We instrument ``run_wave2`` to capture ``wave1_complete.is_set()`` at
    the moment Wave 2 begins. Implicit/emergent ordering (e.g. relying on
    Python GIL or function return value) is NOT acceptable — the contract
    must be encoded as an explicit synchronisation primitive that
    downstream callers can wait on (spec-105 risk-accept will read this
    event in some edge cases).

    This test fails with ``ImportError`` until T-2.2 / T-2.12 land.
    """
    # Arrange
    from ai_engineering.policy import orchestrator

    # Locate the event. Accept either a module-level attribute or a getter
    # function that returns the orchestrator's current event.
    event = getattr(orchestrator, "wave1_complete", None)
    if event is None:
        # Some implementations may scope the event onto an Orchestrator
        # class instance — accept a factory ``_make_wave1_complete()`` if
        # exposed, but only if it returns a fresh Event-like object.
        factory = getattr(orchestrator, "_make_wave1_complete", None)
        assert factory is not None, (
            "orchestrator must expose a module-level ``wave1_complete`` "
            "threading.Event (or asyncio.Event) so the wave-1→wave-2 "
            "happens-before is encoded explicitly. None found."
        )
        event = factory()

    # Duck-type the event API: must support ``is_set`` and ``set``.
    assert callable(getattr(event, "is_set", None)), (
        "wave1_complete must support ``is_set()`` (threading.Event or asyncio.Event interface)."
    )
    assert callable(getattr(event, "set", None)), (
        "wave1_complete must support ``set()`` so the orchestrator can "
        "signal Wave 1 completion explicitly."
    )

    # Snapshot the event state across the run.
    states: dict[str, bool] = {}

    def fake_run_wave1(*args: object, **kwargs: object) -> object:
        # Pre-condition: event is unset before Wave 1 runs.
        states["before_wave1"] = bool(event.is_set())
        return mock.MagicMock(return_code=0, ok=True)

    def fake_run_wave2(*args: object, **kwargs: object) -> object:
        # Critical assertion target: event MUST be set before Wave 2.
        states["at_wave2_start"] = bool(event.is_set())
        return mock.MagicMock(return_code=0, ok=True)

    # Reset event to unset for the test (in case earlier runs left it set).
    if event.is_set():
        clearer = getattr(event, "clear", None)
        assert callable(clearer), (
            "wave1_complete must support ``clear()`` so the orchestrator "
            "can reset state between gate runs. None found."
        )
        clearer()

    # Act
    with (
        mock.patch.object(orchestrator, "run_wave1", side_effect=fake_run_wave1),
        mock.patch.object(orchestrator, "run_wave2", side_effect=fake_run_wave2),
    ):
        run_gate = getattr(orchestrator, "run_gate", None)
        assert run_gate is not None, "orchestrator must expose run_gate"
        with contextlib.suppress(TypeError):
            run_gate()

    # Assert — event was unset before Wave 1, set before Wave 2 started.
    assert "before_wave1" in states, "fake_run_wave1 was never invoked by run_gate"
    assert "at_wave2_start" in states, "fake_run_wave2 was never invoked by run_gate"
    assert states["before_wave1"] is False, (
        "wave1_complete must be unset at the START of run_gate; "
        f"observed is_set()={states['before_wave1']}. The orchestrator "
        "must clear or freshly-create the event each invocation."
    )
    assert states["at_wave2_start"] is True, (
        "RACE / contract violation: Wave 2 started while wave1_complete "
        "was still unset. The orchestrator must call ``wave1_complete.set()`` "
        "AFTER run_wave1 returns and BEFORE dispatching run_wave2. "
        "Implicit/emergent ordering is not sufficient — the explicit "
        "Event signal is the contract per phase-0-notes.md §1."
    )


# ---------------------------------------------------------------------------
# Test 3 — Wave 2 reads the post-Wave-1 file state (no stale reads)
# ---------------------------------------------------------------------------


def test_wave2_files_match_wave1_post_state(tmp_path: Path) -> None:
    """Files Wave 2 reads MUST reflect Wave 1's modifications.

    The orchestrator's Wave 1 fixers (``ruff format``, ``ruff check --fix``,
    ``ai-eng spec verify --fix``) mutate files in place. Wave 2 checkers
    (``gitleaks``, ``ty``, ``pytest-smoke``, ``validate``, ``docs-gate``)
    read those same files. If Wave 2 reads start before Wave 1 fsyncs/returns,
    checkers see stale content — a checker may pass on a pre-fix file while
    a fixer is still mutating it (or worse, fail on intermediate state).

    Instrumentation:
      * Create a real file in ``tmp_path``.
      * Patched ``run_wave1`` mutates the file (writes "POST_WAVE1") and
        returns a result.
      * Patched ``run_wave2`` reads the file and stores its content.
      * Assert the content Wave 2 saw equals "POST_WAVE1" exactly — never
        the pre-mutation content.

    This is the file-system view of the ordering contract from test 1: not
    just monotonic timestamps, but the actual data Wave 2 sees on disk.

    This test fails with ``ImportError`` until T-2.2 / T-2.4 land.
    """
    # Arrange
    from ai_engineering.policy import orchestrator

    target_file = tmp_path / "wave1_artifact.txt"
    target_file.write_text("PRE_WAVE1", encoding="utf-8")

    captured: dict[str, str] = {}

    def fake_run_wave1(*args: object, **kwargs: object) -> object:
        # Wave 1 mutates the file. A small sleep around the write makes
        # any premature Wave 2 read deterministically observable.
        time.sleep(0.05)
        target_file.write_text("POST_WAVE1", encoding="utf-8")
        time.sleep(0.05)
        return mock.MagicMock(return_code=0, ok=True)

    def fake_run_wave2(*args: object, **kwargs: object) -> object:
        # Wave 2 reads what Wave 1 wrote. If the orchestrator races, this
        # read may observe "PRE_WAVE1".
        captured["wave2_read"] = target_file.read_text(encoding="utf-8")
        return mock.MagicMock(return_code=0, ok=True)

    # Act
    with (
        mock.patch.object(orchestrator, "run_wave1", side_effect=fake_run_wave1),
        mock.patch.object(orchestrator, "run_wave2", side_effect=fake_run_wave2),
    ):
        run_gate = getattr(orchestrator, "run_gate", None)
        assert run_gate is not None, "orchestrator must expose run_gate"
        with contextlib.suppress(TypeError):
            run_gate()

    # Assert
    assert "wave2_read" in captured, (
        "fake_run_wave2 was never invoked; orchestrator did not dispatch Wave 2"
    )
    assert captured["wave2_read"] == "POST_WAVE1", (
        "STALE READ: Wave 2 observed pre-Wave-1 file content. "
        f"Got {captured['wave2_read']!r}, expected 'POST_WAVE1'. "
        "Per D-104-01, Wave 2 readers MUST see the post-Wave-1 file state."
    )
    # Defensive: the on-disk file is the post-Wave-1 state (no other writer).
    assert target_file.read_text(encoding="utf-8") == "POST_WAVE1"


# ---------------------------------------------------------------------------
# Test 4 — Source-level invariant assertion present in run_gate
# ---------------------------------------------------------------------------


def test_orchestrator_invariant_assertion_present() -> None:
    """``orchestrator.run_gate`` MUST encode ``assert wave1_complete...`` explicitly.

    Behaviour-only tests (1-3) prove the runtime contract holds for the
    happy path under instrumentation, but they cannot prove the contract
    is encoded as a defensive invariant in the source — a future refactor
    could accidentally drop the synchronisation while still passing the
    behavioural tests under typical scheduling.

    This test reads ``orchestrator.py`` as text and asserts the presence
    of an explicit invariant of the form ``assert wave1_complete`` (or an
    equivalent that names the same primitive). It is the source-level
    backstop required by the plan:

        T-2.12: Confirm wave2 gate is explicit; add
        ``assert wave1_complete.is_set()`` invariant in ``run_wave2``.

    Skip-friendly during Phase 0/1: when the orchestrator file does not
    yet exist, ``pytest.skip`` so test collection remains green — same
    pattern as ``tests/integration/test_spec104_orthogonality.py``.

    Once T-2.2 lands the file, the skip turns into a real assertion.
    T-2.12 GREEN adds the invariant line that satisfies this test.
    """
    if not ORCHESTRATOR_PATH.exists():
        pytest.skip(
            "orchestrator.py not yet created — gate at T-2.2 / T-2.12. "
            "Test will engage automatically once Phase 2 GREEN lands."
        )

    source = ORCHESTRATOR_PATH.read_text(encoding="utf-8")

    # Strip Python comments so a stray ``# assert wave1_complete`` in
    # documentation prose cannot satisfy the contract — the assertion
    # must be live code.
    code_lines: list[str] = []
    for raw_line in source.splitlines():
        # Naive strip: drop everything from a ``#`` that is not inside a
        # string. We intentionally do not parse with ast here because we
        # want the lexical form ``assert wave1_complete`` regardless of
        # function nesting / class scope.
        in_single = False
        in_double = False
        cleaned_chars: list[str] = []
        i = 0
        while i < len(raw_line):
            ch = raw_line[i]
            if ch == "'" and not in_double:
                in_single = not in_single
                cleaned_chars.append(ch)
            elif ch == '"' and not in_single:
                in_double = not in_double
                cleaned_chars.append(ch)
            elif ch == "#" and not in_single and not in_double:
                break  # rest of line is a comment
            else:
                cleaned_chars.append(ch)
            i += 1
        code_lines.append("".join(cleaned_chars))
    code_text = "\n".join(code_lines)

    # Accept either ``assert wave1_complete`` or ``assert wave1_complete.is_set()``
    # or ``assert self.wave1_complete...`` — any live ``assert`` statement
    # that names the synchronisation primitive in run_gate / run_wave2 scope.
    assert "assert wave1_complete" in code_text or "assert self.wave1_complete" in code_text, (
        "orchestrator.py does NOT contain an explicit "
        "``assert wave1_complete...`` invariant. Per T-2.12 (and the plan's "
        "Risk-5 mitigation), the wave-1→wave-2 happens-before MUST be encoded "
        "as a defensive assertion in source — not just emergent from runtime "
        "ordering. Add ``assert wave1_complete.is_set()`` (or equivalent) "
        "inside ``run_wave2`` (or at the top of ``run_gate`` before dispatch)."
    )
