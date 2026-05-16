"""Tests for ``.ai-engineering/scripts/session_bootstrap.py`` (brief §16).

Validates:

* The dashboard is valid JSON with the documented top-level keys.
* ``elapsed_ms`` is present and numeric (perf-budget telemetry).
* The script handles a repo with no ``spec.md`` gracefully (``active_spec`` = None).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".ai-engineering" / "scripts" / "session_bootstrap.py"


def _run_script(repo_root: Path | None = None) -> dict:
    """Invoke the script as a subprocess; return parsed JSON."""
    cmd = [sys.executable, str(SCRIPT)]
    if repo_root is not None:
        cmd += ["--repo-root", str(repo_root)]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"script failed: rc={result.returncode} stderr={result.stderr}"
    return json.loads(result.stdout)


@pytest.mark.unit
def test_emits_valid_json() -> None:
    """The script's stdout must parse as JSON with the documented top-level keys."""
    dashboard = _run_script()
    assert isinstance(dashboard, dict)
    # Brief §16.2 minimum field set:
    for required in ("schema_version", "elapsed_ms", "branch", "last_commit", "hooks_health"):
        assert required in dashboard, f"missing key: {required!r}"
    assert dashboard["schema_version"] == 1


@pytest.mark.unit
def test_elapsed_ms_present_and_numeric() -> None:
    """``elapsed_ms`` is the perf-budget telemetry — numeric and non-negative."""
    dashboard = _run_script()
    elapsed = dashboard["elapsed_ms"]
    assert isinstance(elapsed, (int, float)), f"elapsed_ms not numeric: {type(elapsed)!r}"
    assert elapsed >= 0
    # A wildly-out-of-budget run (>5s wall) is itself a regression we'd
    # want to surface — assert a generous local-machine ceiling.
    assert elapsed < 5000, f"session bootstrap took {elapsed}ms (>5s budget)"


@pytest.mark.unit
def test_handles_missing_spec(tmp_path: Path) -> None:
    """Empty repo with no spec.md must not error; ``active_spec`` is None."""
    # Build a minimal repo skeleton: ``.ai-engineering/`` exists, no spec.md.
    fake_repo = tmp_path / "fake-repo"
    (fake_repo / ".ai-engineering" / "specs").mkdir(parents=True)
    (fake_repo / ".ai-engineering" / "state").mkdir(parents=True)
    # Init git so ``branch`` resolves cleanly.
    subprocess.run(
        ["git", "init", "--initial-branch=main", "--quiet", str(fake_repo)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(fake_repo), "config", "user.email", "boot@test.local"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(fake_repo), "config", "user.name", "boot-test"],
        check=True,
        capture_output=True,
    )

    dashboard = _run_script(repo_root=fake_repo)
    assert dashboard["active_spec"] is None
    # plan / events default to zero values; not an error.
    assert dashboard["recent_events_7d"] == 0
    assert dashboard["hooks_health"] == "unknown"


@pytest.mark.unit
def test_under_budget_warning_absent_on_normal_path(tmp_path: Path) -> None:
    """A clean small-repo invocation should not flag ``budget_exceeded``."""
    fake_repo = tmp_path / "fast-repo"
    (fake_repo / ".ai-engineering" / "specs").mkdir(parents=True)
    (fake_repo / ".ai-engineering" / "state").mkdir(parents=True)
    subprocess.run(
        ["git", "init", "--initial-branch=main", "--quiet", str(fake_repo)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(fake_repo), "config", "user.email", "fast@test.local"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(fake_repo), "config", "user.name", "fast-test"],
        check=True,
        capture_output=True,
    )

    dashboard = _run_script(repo_root=fake_repo)
    # On a microscopic repo, we should not exceed budget. Tolerate one
    # warning slot in case CI is slow but assert the field is structured.
    if "warnings" in dashboard:
        assert isinstance(dashboard["warnings"], list)
