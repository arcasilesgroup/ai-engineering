"""Hot-path budget enforcement (brief §14.3 / spec-127 follow-up).

Brief §14.3 fixes the seven user-facing surfaces that gate the green
path of the framework:

| Surface | Budget | Hard ceiling |
|---|---|---|
| pre-commit hook         | 1.0s |  1.5s |
| pre-push hook           | 5.0s |  7.0s |
| ``/ai-start``           | 0.5s |  2.0s |
| ``/ai-commit``          | 1.5s |  3.0s |
| ``/ai-pr``              | 8.0s | 15.0s |
| ``/ai-verify`` (PASS)   | 1.0s |  3.0s |
| ``/ai-cleanup``         | 1.5s |  3.0s |

Two surfaces ship in this PR: pre-commit and pre-push (both mediated by
``ai-eng gate run --cache-aware --json --mode=local``). The remaining
five depend on deterministic helpers (``session_bootstrap.py``,
``commit_compose.py``, ``pr_body_compose.py``) that ship in this same
work. They are wired as ``xfail`` placeholders so the file structure
exists today and the conversion is mechanical when the helpers land.

CI tolerance per brief §14.3: regression > 25% blocks the PR. We assert
the hard-ceiling values directly (which already include the 25% slack
on top of the budget). Three runs are taken; the median is asserted to
absorb a single transient blip on a busy CI runner.

Opt-in: gated by ``-m perf`` or ``AIENG_RUN_PERF=1`` per
``tests/perf/conftest.py``.
"""

from __future__ import annotations

import os
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "tools"

# Per brief §14.3 (budget · hard ceiling). Hard ceiling already includes
# the 25 % CI tolerance.
PRE_COMMIT_CEILING_S = 1.5
PRE_PUSH_CEILING_S = 7.0


def _has_ai_eng() -> bool:
    """Return True when the ``ai-eng`` console script is on PATH.

    The pre-commit / pre-push budgets only make sense when the
    orchestrator is installed. Runners that don't have it (smoke
    matrix on a stripped-down image) skip rather than fail.
    """
    return shutil.which("ai-eng") is not None


def _make_staged_set(tmp_path: Path, count: int = 5) -> Path:
    """Init a tiny git repo with ``count`` staged files.

    Mirrors the pre-commit hook's input shape: small staged set, no
    history beyond an empty initial commit. We deliberately avoid
    invoking the hooks themselves — the budget is for the orchestrator
    that runs *inside* the hook, not the wrapper.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "--initial-branch=main", "--quiet", str(repo)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "perf@test.local"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "perf-test"],
        check=True,
        capture_output=True,
    )
    for i in range(count):
        f = repo / f"file_{i}.py"
        f.write_text(f'"""Generated stub {i}."""\n\nVALUE = {i}\n', encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repo), "add", "."],
        check=True,
        capture_output=True,
    )
    return repo


def _time_orchestrator(repo: Path, mode: str, runs: int = 3) -> list[float]:
    """Time ``ai-eng gate run`` ``runs`` times. Returns elapsed seconds.

    ``--mode=local`` runs the local fast slice which is what the
    pre-commit / pre-push hooks both invoke. Failing exit codes are
    accepted (an orchestrator that flags findings still met the
    budget). What we measure is wall-clock, not pass/fail.
    """
    timings: list[float] = []
    env = os.environ.copy()
    env["GIT_PAGER"] = "cat"
    for _ in range(runs):
        started = time.perf_counter()
        subprocess.run(
            ["ai-eng", "gate", "run", "--cache-aware", "--json", f"--mode={mode}"],
            cwd=repo,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        timings.append(time.perf_counter() - started)
    return timings


@pytest.mark.perf
def test_pre_commit_under_1s(tmp_path: Path) -> None:
    """Pre-commit gate must finish under 1.5 s p50 (1.0 s budget + 25 %)."""
    if not _has_ai_eng():
        pytest.skip("ai-eng console script not installed in this venv")

    repo = _make_staged_set(tmp_path)
    timings = _time_orchestrator(repo, mode="local", runs=3)
    median_s = statistics.median(timings)
    assert median_s <= PRE_COMMIT_CEILING_S, (
        f"pre-commit gate median {median_s:.2f}s exceeds "
        f"{PRE_COMMIT_CEILING_S:.2f}s ceiling (timings={timings})"
    )


@pytest.mark.perf
def test_pre_push_under_5s(tmp_path: Path) -> None:
    """Pre-push gate must finish under 7.0 s p50 (5.0 s budget + 25 %).

    The local-mode orchestrator is what the pre-push hook runs. CI
    matrix uses ``--mode=ci``; we only enforce the local-hot-path
    budget here (CI's authoritative gate has its own SLA).
    """
    if not _has_ai_eng():
        pytest.skip("ai-eng console script not installed in this venv")

    repo = _make_staged_set(tmp_path, count=5)
    timings = _time_orchestrator(repo, mode="local", runs=3)
    median_s = statistics.median(timings)
    assert median_s <= PRE_PUSH_CEILING_S, (
        f"pre-push gate median {median_s:.2f}s exceeds "
        f"{PRE_PUSH_CEILING_S:.2f}s ceiling (timings={timings})"
    )


# ---------------------------------------------------------------------------
# Aspirational placeholders — five remaining surfaces from brief §14.3
# table. Each one is wired as ``xfail`` so the file structure exists and
# the conversion is a one-line flip when the deterministic helper lands.
# ---------------------------------------------------------------------------


@pytest.mark.perf
@pytest.mark.xfail(
    reason="depends on session_bootstrap.py exit codes + JSON dashboard wiring",
    strict=False,
)
def test_ai_start_under_500ms() -> None:
    """``/ai-start`` (banner mode) must finish under 2.0 s ceiling.

    Today: SKILL.md walks an LLM through 7 of 9 data-shuffling steps.
    Target: invoke ``python3 .ai-engineering/scripts/session_bootstrap.py``
    and assert ``elapsed_ms`` field plus subprocess wall-clock.
    """
    started = time.perf_counter()
    result = subprocess.run(
        [sys.executable, ".ai-engineering/scripts/session_bootstrap.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=5,
    )
    elapsed_s = time.perf_counter() - started
    assert result.returncode == 0
    assert elapsed_s <= 2.0


@pytest.mark.perf
@pytest.mark.xfail(
    reason="depends on commit_compose.py + branch_slug.py landing in /ai-commit",
    strict=False,
)
def test_ai_commit_under_3s() -> None:
    """``/ai-commit`` must finish under 3.0 s ceiling on the no-LLM path."""
    pytest.fail("commit_compose.py wired but no end-to-end harness yet")


@pytest.mark.perf
@pytest.mark.xfail(
    reason="depends on pr_body_compose.py + doc_gate.py landing in /ai-pr",
    strict=False,
)
def test_ai_pr_under_15s() -> None:
    """``/ai-pr`` (deterministic compose mode) must finish under 15 s ceiling."""
    pytest.fail("pr_body_compose.py wired but no end-to-end harness yet")


@pytest.mark.perf
@pytest.mark.xfail(
    reason="depends on /ai-verify Markdown-out path landing",
    strict=False,
)
def test_ai_verify_pass_under_3s() -> None:
    """``/ai-verify`` PASS path must finish under 3.0 s ceiling."""
    pytest.fail("verify-fast PASS path not wired yet")


@pytest.mark.perf
@pytest.mark.xfail(
    reason="depends on cleanup-run.py landing in /ai-cleanup",
    strict=False,
)
def test_ai_cleanup_under_3s() -> None:
    """``/ai-cleanup`` must finish under 3.0 s ceiling."""
    pytest.fail("cleanup-run.py not yet wired")
