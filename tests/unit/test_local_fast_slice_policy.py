"""RED tests for spec-104 T-4.2 — local fast-slice gate policy (D-104-02).

Per D-104-02, the orchestrator's Wave 2 supports two execution modes:

    * ``mode="local"`` (fast-slice, default): runs ONLY the 5 cheap checkers
      that protect minimum integrity in <=60s — gitleaks, ruff, ty,
      pytest-smoke, validate.
    * ``mode="ci"`` (authoritative): adds semgrep, pip-audit, pytest-full
      to the local set for a total of 8 checkers.

Local mode MUST exclude semgrep (network-bound full-source scan), pip-audit
(network-bound dependency vulnerability check), and pytest-full (matrix
coverage cost) because (a) they exceed the 60s local budget, (b) they
require network access, and (c) the CI matrix already runs them
authoritatively before merge.

Target API (does not exist yet — created in T-4.3):

    - ``ai_engineering.policy.orchestrator.run_wave2(
        staged_files: list[Path], mode: str = "local"
      ) -> Wave2Result``
        Filters its checker set per ``mode`` and propagates the mode kwarg
        down to each per-check runner so that downstream behaviour
        (cache key partitioning, log tagging, etc.) can branch on it.

Tests in this file assert the policy contract:

    1. Local mode MUST NOT invoke ``semgrep``.
    2. Local mode MUST NOT invoke ``pip-audit``.
    3. Local mode MUST NOT invoke ``pytest-full`` (only ``pytest-smoke``
       runs locally).
    4. CI mode MUST invoke all 8 checkers including the 3 extras.
    5. Invalid mode strings raise ``ValueError`` OR fall back to local
       with a warning.
    6. ``mode`` defaults to ``"local"`` when the kwarg is omitted.
    7. The active mode is propagated to each per-check runner via the
       ``mode`` kwarg (so cache keys / logs can partition by mode).
    8. Local mode invokes EXACTLY 5 checkers (count assertion — guards
       against silent additions to the fast-slice set).

TDD CONSTRAINT: this file is IMMUTABLE after T-4.2 lands. T-4.3 GREEN
phase may only add behaviour to satisfy these assertions; it must NEVER
edit them.

Each test currently fails with ``ImportError`` because
``ai_engineering.policy.orchestrator`` does not exist yet. Once T-2.4
introduces the module, the tests transition to assertion failures on
mode-aware filter logic until T-4.3 lands the policy filter.
"""

from __future__ import annotations

import threading
import warnings
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Constants documenting the D-104-02 policy contract.
# ---------------------------------------------------------------------------

# Local-mode fast-slice checkers (D-104-02, ≤60s budget).
_LOCAL_CHECKERS: frozenset[str] = frozenset(
    {
        "gitleaks",
        "ruff",
        "ty",
        "pytest-smoke",
        "validate",
    }
)

# CI-only authoritative checkers (D-104-02 — local fast-slice excludes these).
_CI_ONLY_CHECKERS: frozenset[str] = frozenset(
    {
        "semgrep",
        "pip-audit",
        "pytest-full",
    }
)

# Full CI checker set = local fast-slice + CI-only authoritative.
_CI_CHECKERS: frozenset[str] = _LOCAL_CHECKERS | _CI_ONLY_CHECKERS

# Expected exact counts for the count-based assertions in tests 4 and 8.
_EXPECTED_LOCAL_COUNT: int = 5
_EXPECTED_CI_COUNT: int = 8


# ---------------------------------------------------------------------------
# Helpers — record per-check invocation and observed mode propagation.
# ---------------------------------------------------------------------------


class _CheckerInvocationLog:
    """Thread-safe accumulator that records which checks ran and with
    which mode kwarg. Used to assert (a) the filter (which checks ran)
    and (b) propagation (the mode value passed down to each runner)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.invoked: list[str] = []
        self.modes: dict[str, str] = {}

    def record(self, check_name: str, mode: str | None) -> None:
        with self._lock:
            self.invoked.append(check_name)
            if mode is not None:
                self.modes[check_name] = mode

    def invoked_set(self) -> set[str]:
        with self._lock:
            return set(self.invoked)


def _make_recording_runner(log: _CheckerInvocationLog):
    """Return a fake ``_run_one_checker`` that records the check name and
    the ``mode`` kwarg (if propagated) into ``log``."""

    def fake_runner(check_name: str, *_args: Any, **kwargs: Any) -> dict[str, Any]:
        # Mode may be propagated as a positional or keyword arg; we accept
        # whichever convention GREEN ends up using as long as something
        # surfaces it. The test for propagation reads ``log.modes``.
        observed_mode = kwargs.get("mode")
        log.record(check_name, observed_mode)
        return {"check": check_name, "findings": [], "cache_hit": False}

    return fake_runner


# ---------------------------------------------------------------------------
# 1. Local mode does NOT invoke semgrep.
# ---------------------------------------------------------------------------


def test_orchestrator_local_mode_excludes_semgrep(tmp_path: Path) -> None:
    """``run_wave2(mode="local")`` MUST NOT invoke semgrep (D-104-02).

    Semgrep is a full-source scan that exceeds the 60s local budget and
    requires Docker/Python deps not guaranteed locally. CI authoritative
    runs it in the security job before merge.
    """
    from ai_engineering.policy import orchestrator
    from ai_engineering.policy.orchestrator import run_wave2

    log = _CheckerInvocationLog()

    with mock.patch.object(
        orchestrator,
        "_run_one_checker",
        side_effect=_make_recording_runner(log),
        create=True,
    ):
        run_wave2(staged_files=[tmp_path / "f.py"], mode="local")

    assert "semgrep" not in log.invoked_set(), (
        "Local mode MUST NOT invoke semgrep (D-104-02 fast-slice policy); "
        f"observed checks: {sorted(log.invoked_set())}"
    )


# ---------------------------------------------------------------------------
# 2. Local mode does NOT invoke pip-audit.
# ---------------------------------------------------------------------------


def test_orchestrator_local_mode_excludes_pip_audit(tmp_path: Path) -> None:
    """``run_wave2(mode="local")`` MUST NOT invoke pip-audit (D-104-02).

    pip-audit is network-bound (queries PyPI advisory DB) and is unstable
    on offline workstations. CI security job has reliable network and
    runs it before merge.
    """
    from ai_engineering.policy import orchestrator
    from ai_engineering.policy.orchestrator import run_wave2

    log = _CheckerInvocationLog()

    with mock.patch.object(
        orchestrator,
        "_run_one_checker",
        side_effect=_make_recording_runner(log),
        create=True,
    ):
        run_wave2(staged_files=[tmp_path / "f.py"], mode="local")

    assert "pip-audit" not in log.invoked_set(), (
        "Local mode MUST NOT invoke pip-audit (D-104-02 fast-slice "
        f"policy — network-bound); observed checks: {sorted(log.invoked_set())}"
    )


# ---------------------------------------------------------------------------
# 3. Local mode does NOT invoke pytest-full (only pytest-smoke).
# ---------------------------------------------------------------------------


def test_orchestrator_local_mode_excludes_pytest_full(tmp_path: Path) -> None:
    """Local mode MUST run ``pytest-smoke`` (subset) but NEVER
    ``pytest-full`` (D-104-02).

    The full test matrix runs in CI across 3 OS x 3 Python versions; the
    local fast-slice runs only smoke-marked tests for sub-second feedback.
    """
    from ai_engineering.policy import orchestrator
    from ai_engineering.policy.orchestrator import run_wave2

    log = _CheckerInvocationLog()

    with mock.patch.object(
        orchestrator,
        "_run_one_checker",
        side_effect=_make_recording_runner(log),
        create=True,
    ):
        run_wave2(staged_files=[tmp_path / "f.py"], mode="local")

    invoked = log.invoked_set()
    assert "pytest-full" not in invoked, (
        "Local mode MUST NOT invoke pytest-full (D-104-02 fast-slice "
        f"policy — matrix runs in CI); observed checks: {sorted(invoked)}"
    )
    assert "pytest-smoke" in invoked, (
        f"Local mode MUST invoke pytest-smoke (the fast subset); observed checks: {sorted(invoked)}"
    )


# ---------------------------------------------------------------------------
# 4. CI mode invokes all 8 checks including the 3 CI-only extras.
# ---------------------------------------------------------------------------


def test_orchestrator_ci_mode_includes_all_8_checks(tmp_path: Path) -> None:
    """``run_wave2(mode="ci")`` MUST invoke all 8 checkers (D-104-02).

    CI mode = local fast-slice (5) + CI-only authoritative (3). The 3
    extras are semgrep, pip-audit, pytest-full — verifying these are
    present asserts the upgrade path from local→ci works correctly.
    """
    from ai_engineering.policy import orchestrator
    from ai_engineering.policy.orchestrator import run_wave2

    log = _CheckerInvocationLog()

    with mock.patch.object(
        orchestrator,
        "_run_one_checker",
        side_effect=_make_recording_runner(log),
        create=True,
    ):
        run_wave2(staged_files=[tmp_path / "f.py"], mode="ci")

    invoked = log.invoked_set()
    assert invoked == set(_CI_CHECKERS), (
        "CI mode MUST invoke EXACTLY the 8 D-104-02 authoritative checkers; "
        f"expected {sorted(_CI_CHECKERS)}, got {sorted(invoked)}"
    )
    assert len(log.invoked) == _EXPECTED_CI_COUNT, (
        f"CI mode MUST invoke exactly {_EXPECTED_CI_COUNT} checkers; "
        f"got {len(log.invoked)}: {sorted(log.invoked)}"
    )
    # Each CI-only extra MUST appear (defensive — set equality already
    # implies this but the explicit per-extra assertion gives a clearer
    # failure message if one is silently dropped).
    for extra in _CI_ONLY_CHECKERS:
        assert extra in invoked, (
            f"CI mode missing required CI-only checker {extra!r}; "
            f"observed checks: {sorted(invoked)}"
        )


# ---------------------------------------------------------------------------
# 5. Invalid mode strings raise ValueError OR fall back to local with warn.
# ---------------------------------------------------------------------------


def test_orchestrator_invalid_mode_raises_or_falls_back(tmp_path: Path) -> None:
    """``run_wave2(mode="invalid")`` MUST either raise ``ValueError`` or
    fall back to local mode with a ``UserWarning``.

    Both behaviours are acceptable per D-104-02 (the spec leaves the
    failure mode to the implementer's discretion); the test asserts that
    SOMETHING explicit happens — silently running CI mode or an empty
    set is NOT acceptable.
    """
    from ai_engineering.policy import orchestrator
    from ai_engineering.policy.orchestrator import run_wave2

    log = _CheckerInvocationLog()

    with mock.patch.object(
        orchestrator,
        "_run_one_checker",
        side_effect=_make_recording_runner(log),
        create=True,
    ):
        # Acceptable behaviour A: raises ValueError immediately.
        try:
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                run_wave2(staged_files=[tmp_path / "f.py"], mode="invalid")
        except ValueError:
            # Behaviour A — explicit reject. PASS.
            assert log.invoked == [], (
                "When ``mode='invalid'`` raises ValueError, NO checkers "
                f"should have been invoked; got {log.invoked}"
            )
            return
        else:
            # Behaviour B — fallback to local with a warning.
            assert log.invoked_set() == set(_LOCAL_CHECKERS), (
                "Fallback path MUST run the LOCAL checker set, not CI or "
                f"empty; expected {sorted(_LOCAL_CHECKERS)}, got "
                f"{sorted(log.invoked_set())}"
            )
            assert any(issubclass(w.category, (UserWarning, RuntimeWarning)) for w in captured), (
                "Fallback path MUST emit a UserWarning/RuntimeWarning "
                "explaining the unknown mode; no warning observed."
            )


# ---------------------------------------------------------------------------
# 6. ``mode`` defaults to "local" when the kwarg is omitted.
# ---------------------------------------------------------------------------


def test_local_mode_default_when_unspecified(tmp_path: Path) -> None:
    """``run_wave2(staged_files=[...])`` without the ``mode`` kwarg MUST
    default to local mode (D-104-02 — fast-slice is the ergonomic default
    for /ai-commit and /ai-pr pre-push).
    """
    from ai_engineering.policy import orchestrator
    from ai_engineering.policy.orchestrator import run_wave2

    log = _CheckerInvocationLog()

    with mock.patch.object(
        orchestrator,
        "_run_one_checker",
        side_effect=_make_recording_runner(log),
        create=True,
    ):
        # No ``mode=`` kwarg — exercising the default path.
        run_wave2(staged_files=[tmp_path / "f.py"])

    invoked = log.invoked_set()
    assert invoked == set(_LOCAL_CHECKERS), (
        "Calling run_wave2 without a ``mode`` kwarg MUST default to "
        f"local; expected {sorted(_LOCAL_CHECKERS)}, got {sorted(invoked)}"
    )
    assert len(log.invoked) == _EXPECTED_LOCAL_COUNT, (
        f"Default-mode invocation MUST run exactly {_EXPECTED_LOCAL_COUNT} "
        f"checkers; got {len(log.invoked)}"
    )
    # And the CI-only extras MUST be absent.
    for extra in _CI_ONLY_CHECKERS:
        assert extra not in invoked, (
            f"Default mode (local) MUST NOT include CI-only checker "
            f"{extra!r}; observed: {sorted(invoked)}"
        )


# ---------------------------------------------------------------------------
# 7. The mode kwarg is propagated to each per-check runner.
# ---------------------------------------------------------------------------


def test_mode_propagated_to_each_runner(tmp_path: Path) -> None:
    """Each ``_run_one_checker`` invocation MUST receive the active mode
    via the ``mode`` kwarg.

    Propagation is required so that downstream concerns (cache key
    partitioning, structured logging, telemetry) can branch on the mode
    without re-reading the orchestrator state. This test exercises both
    local and ci modes to assert the propagation is correct in each.
    """
    from ai_engineering.policy import orchestrator
    from ai_engineering.policy.orchestrator import run_wave2

    for active_mode in ("local", "ci"):
        log = _CheckerInvocationLog()

        with mock.patch.object(
            orchestrator,
            "_run_one_checker",
            side_effect=_make_recording_runner(log),
            create=True,
        ):
            run_wave2(staged_files=[tmp_path / "f.py"], mode=active_mode)

        # The expected checker set depends on the active mode.
        expected = set(_LOCAL_CHECKERS) if active_mode == "local" else set(_CI_CHECKERS)
        invoked = log.invoked_set()
        assert invoked == expected, (
            f"For mode={active_mode!r} expected checker set "
            f"{sorted(expected)}; got {sorted(invoked)}"
        )

        # Every invoked checker MUST have received the active mode.
        for check in invoked:
            assert check in log.modes, (
                f"Mode kwarg MUST be propagated to every runner; "
                f"checker {check!r} did NOT receive a mode kwarg in "
                f"mode={active_mode!r}. Observed propagated modes: "
                f"{log.modes}"
            )
            assert log.modes[check] == active_mode, (
                f"Checker {check!r} received mode={log.modes[check]!r} "
                f"but the active orchestrator mode was {active_mode!r}; "
                "propagation MUST be faithful."
            )


# ---------------------------------------------------------------------------
# 8. Local mode invokes EXACTLY 5 checkers (count assertion).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "explicit_mode_kwarg",
    [
        # Both the explicit kwarg and the omitted/default path must land
        # at exactly 5 checkers — guarding against silent additions in
        # either dispatch route.
        True,
        False,
    ],
    ids=["mode='local' explicit", "mode kwarg omitted (default)"],
)
def test_local_mode_check_count_is_5(tmp_path: Path, explicit_mode_kwarg: bool) -> None:
    """Local mode MUST invoke exactly 5 checkers (D-104-02 fast-slice).

    This is a count-only guard against silent regressions: if a future
    change tries to push semgrep / pip-audit / pytest-full back into the
    local set, this assertion fails loudly.
    """
    from ai_engineering.policy import orchestrator
    from ai_engineering.policy.orchestrator import run_wave2

    log = _CheckerInvocationLog()

    with mock.patch.object(
        orchestrator,
        "_run_one_checker",
        side_effect=_make_recording_runner(log),
        create=True,
    ):
        if explicit_mode_kwarg:
            run_wave2(staged_files=[tmp_path / "f.py"], mode="local")
        else:
            run_wave2(staged_files=[tmp_path / "f.py"])

    assert len(log.invoked) == _EXPECTED_LOCAL_COUNT, (
        "Local mode MUST invoke EXACTLY "
        f"{_EXPECTED_LOCAL_COUNT} checkers (D-104-02); got "
        f"{len(log.invoked)}: {sorted(log.invoked)}. If you intentionally "
        "expanded the fast-slice set, update this constant AND "
        ".ai-engineering/contexts/gate-policy.md AND the spec D-104-02 "
        "table — never silently."
    )
    # And the count of unique checks must equal the count of invocations
    # (no checker double-runs in a single wave).
    assert len(log.invoked_set()) == _EXPECTED_LOCAL_COUNT, (
        "Local mode MUST run each checker exactly once per wave; "
        f"observed duplicate invocations: {log.invoked}"
    )


# ---------------------------------------------------------------------------
# Module-level invariant: every test imports ``run_wave2``. While the
# orchestrator module is missing (T-2.4 GREEN pending) every test fails
# RED with ImportError, which is the desired RED-phase signal. Once the
# orchestrator lands, the failures shift to the policy-filter assertions
# above until T-4.3 GREEN wires mode-aware dispatch.
# ---------------------------------------------------------------------------
