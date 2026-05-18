"""spec-139 M5.T3 — Stop hook convergence-skip predicate contract.

``runtime-stop.py`` runs the Ralph convergence checker on every Stop
event. In an autopilot run the Stop hook fires once per sub-agent
cascade — running ruff + pytest-collect every time is the dominant
hot-path tax (D-139-03). The skip predicate short-circuits when ALL
three clauses hold:

  (a) ``.convergence-lastrun`` sentinel touched < 30 s ago, AND
  (b) ``git diff --quiet --staged`` returns 0 (no staged work), AND
  (c) ``ctx.agent_kind == "subagent"`` (Stop is a sub-agent cascade).

This module pins the per-clause contract: when ANY single clause is
false the skip MUST NOT fire — partial information is worse than no
skip at all.

Cross-platform: tests use ``tmp_path`` for filesystem state,
``monkeypatch`` for env hermeticity, and stub ``subprocess.run`` so the
suite does not depend on the host ``git`` binary or repo state. The
hook is loaded by file path via importlib so the test does not pin a
particular sys.path layout.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOK_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "runtime-stop.py"
HOOK_DIR = REPO / ".ai-engineering" / "scripts" / "hooks"


@pytest.fixture
def rstop(monkeypatch: pytest.MonkeyPatch):
    """Reload runtime-stop fresh so module-scope state starts clean.

    The hook lives outside the importable package tree, so it is loaded
    by file path. ``sys.modules.pop`` + a new spec guarantees fresh
    module globals per test.
    """
    monkeypatch.delenv("AIENG_RALPH_DISABLED", raising=False)
    monkeypatch.delenv("AIENG_RALPH_BLOCK", raising=False)
    monkeypatch.delenv("AIENG_RALPH_MAX_RETRIES", raising=False)
    monkeypatch.syspath_prepend(str(HOOK_DIR))
    sys.modules.pop("aieng_rstop_skip_test", None)
    spec = importlib.util.spec_from_file_location("aieng_rstop_skip_test", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Standard project layout: ``.ai-engineering/runtime/`` exists."""
    (tmp_path / ".ai-engineering" / "runtime").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _make_completed(returncode: int) -> Any:
    """Build a minimal ``subprocess.CompletedProcess``-shaped stub."""

    class _Stub:
        def __init__(self, rc: int) -> None:
            self.returncode = rc
            self.stdout = b""
            self.stderr = b""

    return _Stub(returncode)


def _stub_git_clean(monkeypatch: pytest.MonkeyPatch, *, clean: bool) -> None:
    """Pin ``subprocess.run`` so ``git diff --quiet --staged`` returns ``clean``."""

    def fake_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        # Only intercept git invocations; everything else delegates to the real
        # call so we never destabilise the surrounding hook stack.
        if isinstance(cmd, list) and cmd and cmd[0] == "git":
            return _make_completed(0 if clean else 1)
        return subprocess.run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)


def _touch_recent(project: Path, rstop, *, age_sec: float = 5.0) -> None:
    """Touch ``.convergence-lastrun`` ``age_sec`` seconds in the past."""
    sentinel = rstop._convergence_lastrun_path(project)
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.touch()
    past = time.time() - age_sec
    import os

    os.utime(sentinel, (past, past))


# ---------------------------------------------------------------------------
# Happy path — all three clauses true.
# ---------------------------------------------------------------------------


def test_skip_fires_when_all_three_clauses_hold(
    rstop, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """spec-139 M5.T3: subagent + recent run + clean index → skip."""
    _touch_recent(project, rstop, age_sec=5.0)
    _stub_git_clean(monkeypatch, clean=True)

    assert rstop.should_skip_convergence(project, agent_kind="subagent") is True


# ---------------------------------------------------------------------------
# Negative tests — each clause individually false.
# ---------------------------------------------------------------------------


def test_skip_does_not_fire_when_event_is_main_thread(
    rstop, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Clause (c) false: top-level user Stop MUST run convergence.

    Even when the sentinel is fresh and the index is clean, a main-thread
    Stop is the operator's natural inspection point — convergence MUST
    fire so the user receives accurate feedback.
    """
    _touch_recent(project, rstop, age_sec=5.0)
    _stub_git_clean(monkeypatch, clean=True)

    assert rstop.should_skip_convergence(project, agent_kind="main") is False


def test_skip_does_not_fire_when_sentinel_is_old(
    rstop, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Clause (a) false: sentinel older than 30 s window → MUST run.

    Boundary chosen at 120 s to avoid filesystem-resolution flake on
    Windows / FAT (2 s mtime granularity).
    """
    _touch_recent(project, rstop, age_sec=120.0)
    _stub_git_clean(monkeypatch, clean=True)

    assert rstop.should_skip_convergence(project, agent_kind="subagent") is False


def test_skip_does_not_fire_when_sentinel_missing(
    rstop, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Clause (a) false: no sentinel → first-run; MUST execute convergence.

    The first Stop after process start has no recorded convergence; the
    skip cannot fire because we cannot prove the work was already done.
    """
    # Do NOT touch the sentinel.
    _stub_git_clean(monkeypatch, clean=True)

    assert rstop.should_skip_convergence(project, agent_kind="subagent") is False


def test_skip_does_not_fire_when_staged_index_dirty(
    rstop, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Clause (b) false: ``git diff --staged`` returned non-zero → MUST run.

    Staged work is uncommitted progress; running convergence ensures the
    user sees any lint / test regression before turn-end.
    """
    _touch_recent(project, rstop, age_sec=5.0)
    _stub_git_clean(monkeypatch, clean=False)

    assert rstop.should_skip_convergence(project, agent_kind="subagent") is False


def test_skip_does_not_fire_when_git_unavailable(
    rstop, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``git`` not installed → ``_git_staged_clean`` returns False → MUST run.

    Fail-safe: we cannot prove the index is clean without git, so we run
    convergence rather than serve a stale skip.
    """
    _touch_recent(project, rstop, age_sec=5.0)

    def raise_fnf(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(cmd, list) and cmd and cmd[0] == "git":
            raise FileNotFoundError("git")
        return subprocess.run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", raise_fnf)

    assert rstop.should_skip_convergence(project, agent_kind="subagent") is False


def test_skip_does_not_fire_when_git_times_out(
    rstop, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``git`` hanging past the 1 s bound → fail-safe; run convergence.

    Bounded subprocess: the 1 s timeout in ``_git_staged_clean`` protects
    the Stop hook from a stuck git process. Timeout → run convergence.
    """
    _touch_recent(project, rstop, age_sec=5.0)

    def raise_timeout(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(cmd, list) and cmd and cmd[0] == "git":
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=1.0)
        return subprocess.run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", raise_timeout)

    assert rstop.should_skip_convergence(project, agent_kind="subagent") is False


# ---------------------------------------------------------------------------
# Sentinel helpers — touch + recent-window probe.
# ---------------------------------------------------------------------------


def test_touch_creates_sentinel_inside_runtime_dir(rstop, project: Path) -> None:
    """``_touch_convergence_sentinel`` MUST land inside ``.ai-engineering/runtime/``.

    The canonical runtime dir is the gitignored session-state directory
    (CLAUDE.md "Runtime Layer Tunables"). Writing the sentinel anywhere
    else would leak into the source tree.
    """
    rstop._touch_convergence_sentinel(project)
    sentinel = rstop._convergence_lastrun_path(project)
    assert sentinel.exists()
    assert sentinel.parent.name == "runtime"
    assert sentinel.parent.parent.name == ".ai-engineering"


def test_convergence_recently_ran_window_boundary(rstop, project: Path) -> None:
    """The 30 s window is half-open: < 30 s → True, >= 30 s → False.

    Pinning the boundary explicitly so a future refactor that drifts the
    comparison (>=, >, ≤) is caught by a regression-class assertion.
    """
    sentinel = rstop._convergence_lastrun_path(project)
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.touch()

    # Inside the window (5 s ago) — True.
    assert rstop._convergence_recently_ran(project, now=time.time()) is True

    # Exactly 30 s ago — boundary; the predicate uses strict ``<`` so this
    # should evaluate to False (window-closed).
    sentinel_mtime = sentinel.stat().st_mtime
    boundary_now = sentinel_mtime + rstop._CONVERGENCE_SKIP_WINDOW_SEC
    assert rstop._convergence_recently_ran(project, now=boundary_now) is False

    # Well past the window (60 s ago) — False.
    past_now = sentinel_mtime + 60.0
    assert rstop._convergence_recently_ran(project, now=past_now) is False
