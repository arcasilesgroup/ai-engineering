"""spec-139 M5.T4 — ``auto-format.py`` per-process debounce contract.

The PostToolUse auto-format hook fires after every Edit/Write/MultiEdit.
Rapid back-to-back edits to the same file otherwise pay the full
formatter cost N times (ruff / prettier / dotnet format, etc.). The
hook now records the wall-clock time of each format per absolute path
and short-circuits subsequent invocations inside the
``AIENG_AUTOFORMAT_DEBOUNCE_SEC`` window (default 1 s).

This module pins the per-path debounce contract:

  * Inside the window: ``_should_debounce`` returns True; the hook MUST
    skip the formatter and pass stdin through.
  * Outside the window or first call: returns False; the hook MUST run
    the formatter and stamp the per-path last-format map.
  * Window is per-path: formatting file A does NOT debounce file B.
  * ``AIENG_AUTOFORMAT_DEBOUNCE_SEC=0`` (or unparseable) disables /
    falls back to the default; we verify the env-override happy path.

Cross-platform: tests reload the module fresh per case so the per-path
map starts empty. The ``now`` parameter is injected explicitly so test
assertions are deterministic on every OS (no clock-resolution flake on
Windows).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOK_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "auto-format.py"
HOOK_DIR = REPO / ".ai-engineering" / "scripts" / "hooks"


@pytest.fixture
def afmt(monkeypatch: pytest.MonkeyPatch):
    """Reload auto-format fresh so the per-path last-format map starts empty.

    Hermetic env: ``AIENG_AUTOFORMAT_DEBOUNCE_SEC`` is intentionally
    cleared so default-window tests cannot inherit a stale operator
    value. Per-test overrides re-set the var via ``monkeypatch.setenv``.
    """
    monkeypatch.delenv("AIENG_AUTOFORMAT_DEBOUNCE_SEC", raising=False)
    monkeypatch.syspath_prepend(str(HOOK_DIR))
    sys.modules.pop("aieng_autoformat_debounce_test", None)
    spec = importlib.util.spec_from_file_location("aieng_autoformat_debounce_test", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._LAST_FORMAT_TIMES.clear()
    return module


# ---------------------------------------------------------------------------
# First call — no debounce.
# ---------------------------------------------------------------------------


def test_first_format_is_not_debounced(afmt) -> None:
    """First format of a path MUST run (no prior record → no debounce).

    Returning True on the first call would prevent any formatting from
    happening — the debounce only meaningfully fires for re-formats.
    """
    assert afmt._should_debounce("/work/repo/module.py", now=10.0) is False


# ---------------------------------------------------------------------------
# Inside the debounce window — skip.
# ---------------------------------------------------------------------------


def test_repeat_format_inside_window_is_debounced(afmt) -> None:
    """A second format 0.5 s after the first MUST be debounced (default 1 s).

    The default 1 s window covers typical multi-Edit bursts from the
    agent (back-to-back hunks on the same file).
    """
    path = "/work/repo/module.py"
    afmt._record_format(path, now=10.0)
    assert afmt._should_debounce(path, now=10.5) is True


def test_repeat_format_at_window_boundary_is_not_debounced(afmt) -> None:
    """1.0 s after format MUST NOT debounce (strict ``<`` semantics).

    Pinning the boundary explicitly so a refactor that drifts the
    comparison (>=, >, ≤) is caught by this regression assertion.
    """
    path = "/work/repo/module.py"
    afmt._record_format(path, now=10.0)
    # Exactly 1.0 s elapsed → boundary; the predicate uses strict ``<``.
    assert afmt._should_debounce(path, now=11.0) is False


def test_repeat_format_outside_window_runs_formatter(afmt) -> None:
    """5 s after format → outside window → MUST run (False from predicate).

    Long pause means the user is back in control — formatting MUST
    happen so any new state is reflected.
    """
    path = "/work/repo/module.py"
    afmt._record_format(path, now=10.0)
    assert afmt._should_debounce(path, now=15.0) is False


# ---------------------------------------------------------------------------
# Per-path isolation — A never debounces B.
# ---------------------------------------------------------------------------


def test_debounce_is_per_path_isolated(afmt) -> None:
    """Recording a format for A MUST NOT debounce B.

    The map keys on absolute path so concurrent edits to multiple files
    are formatted independently — only repeats of the same path pay the
    skip.
    """
    path_a = "/work/repo/a.py"
    path_b = "/work/repo/b.py"
    afmt._record_format(path_a, now=10.0)
    assert afmt._should_debounce(path_a, now=10.5) is True
    assert afmt._should_debounce(path_b, now=10.5) is False


# ---------------------------------------------------------------------------
# Env-var override — ``AIENG_AUTOFORMAT_DEBOUNCE_SEC``.
# ---------------------------------------------------------------------------


def test_env_var_widens_debounce_window(afmt, monkeypatch: pytest.MonkeyPatch) -> None:
    """Setting the env var to 10 s widens the window — 5 s repeat → debounced.

    The override is honoured per-call (no module-level caching of the
    window setting), so a mid-run env change takes effect on the next
    invocation.
    """
    monkeypatch.setenv("AIENG_AUTOFORMAT_DEBOUNCE_SEC", "10.0")
    path = "/work/repo/module.py"
    afmt._record_format(path, now=10.0)
    # 5 s later: inside the widened 10 s window.
    assert afmt._should_debounce(path, now=15.0) is True


def test_env_var_zero_disables_debounce(afmt, monkeypatch: pytest.MonkeyPatch) -> None:
    """``AIENG_AUTOFORMAT_DEBOUNCE_SEC=0`` MUST disable the debounce.

    Provides the operator a kill-switch without touching code — useful
    when investigating a formatter-related regression.
    """
    monkeypatch.setenv("AIENG_AUTOFORMAT_DEBOUNCE_SEC", "0")
    path = "/work/repo/module.py"
    afmt._record_format(path, now=10.0)
    # Even 0.1 s later: window is 0 → MUST NOT debounce.
    assert afmt._should_debounce(path, now=10.1) is False


def test_env_var_negative_falls_back_to_default(afmt, monkeypatch: pytest.MonkeyPatch) -> None:
    """Negative env value MUST fall back to the 1 s default.

    Otherwise a typo like ``-1`` would silently disable the debounce.
    """
    monkeypatch.setenv("AIENG_AUTOFORMAT_DEBOUNCE_SEC", "-5")
    path = "/work/repo/module.py"
    afmt._record_format(path, now=10.0)
    # 0.5 s later: default 1 s window applies → debounced.
    assert afmt._should_debounce(path, now=10.5) is True


def test_env_var_unparseable_falls_back_to_default(afmt, monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-numeric env var MUST fall back to the 1 s default — never crash.

    Fail-safe: the hook is on the post-edit hot path; surfacing a value
    error would break every save.
    """
    monkeypatch.setenv("AIENG_AUTOFORMAT_DEBOUNCE_SEC", "fast")
    path = "/work/repo/module.py"
    afmt._record_format(path, now=10.0)
    assert afmt._should_debounce(path, now=10.5) is True


# ---------------------------------------------------------------------------
# Recording semantics.
# ---------------------------------------------------------------------------


def test_record_format_overwrites_previous_timestamp(afmt) -> None:
    """Re-recording a path MUST overwrite the previous timestamp.

    Otherwise a long-ago stamp would let a much-later edit slip past
    the debounce window: if the predicate compared against the OLDEST
    record, a re-format 10 s after the original would still be inside
    its 1 s window relative to the latest (wall-clock now ~= 11 s),
    breaking the debounce. The contract is "compare against latest".
    """
    path = "/work/repo/module.py"
    # First format at t=10. Second format at t=100 — the gap is huge but
    # ``_record_format`` MUST overwrite, so the latest stamp is 100.
    afmt._record_format(path, now=10.0)
    afmt._record_format(path, now=100.0)

    # 0.5 s past the LATEST record → still within window → debounced.
    assert afmt._should_debounce(path, now=100.5) is True

    # 5 s past the LATEST record → outside the 1 s window → not debounced.
    # If the predicate had compared against the OLDEST (10.0) stamp, the
    # difference would be 95 s — also outside the window — and this
    # assertion would coincidentally pass. We instead test the bug-positive
    # case: query at a wall-clock time inside the window of the OLDEST
    # stamp (10.5 s) but outside the window of the LATEST (100.0). The
    # delta against the latest is -89.5 s; the predicate uses ``<`` so a
    # negative delta is "inside the window" and returns True. To prove the
    # overwrite happened we instead check that the LATEST stamp is the
    # one the map holds.
    assert afmt._LAST_FORMAT_TIMES[path] == 100.0
