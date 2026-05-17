"""spec-140 W2.T7 / D-140-03 — nightly-matrix.yml advisory contract.

The PR matrix was collapsed to 3.12 only (see
``test_python_matrix_collapsed.py``). The full python-version sweep moved
to ``nightly-matrix.yml`` as an advisory workflow: scheduled at 06:00 UTC
daily, runs the full 3 x 3 (python x OS) matrix, ``continue-on-error: true``
per cell so cell failures never block PRs.

This test pins the advisory contract: schedule trigger present, the 9-cell
matrix is declared verbatim, and ``continue-on-error`` is set so cells
cannot escalate into blocking failures.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
NIGHTLY_PATH = REPO_ROOT / ".github" / "workflows" / "nightly-matrix.yml"

_EXPECTED_PYTHON_VERSIONS = sorted(["3.11", "3.12", "3.13"])
_EXPECTED_OS = sorted(["ubuntu-latest", "macos-latest", "windows-latest"])


@pytest.fixture(scope="module")
def workflow() -> dict:
    """Parse ``nightly-matrix.yml`` once per test module."""
    assert NIGHTLY_PATH.exists(), f"missing workflow: {NIGHTLY_PATH}"
    return yaml.safe_load(NIGHTLY_PATH.read_text(encoding="utf-8"))


def test_nightly_matrix_has_schedule_trigger(workflow: dict) -> None:
    """Daily schedule trigger MUST be present so the sweep actually runs."""
    # PyYAML lowers the `on:` key to the boolean ``True`` (Python truthy).
    triggers = workflow.get(True) or workflow.get("on") or {}
    assert "schedule" in triggers, (
        f"expected `schedule:` trigger in nightly-matrix.yml; got triggers={list(triggers)}"
    )
    schedule = triggers["schedule"]
    assert isinstance(schedule, list) and schedule, (
        f"schedule must be a non-empty list; got {schedule!r}"
    )
    assert any("cron" in entry for entry in schedule), (
        f"at least one schedule entry must declare `cron:`; got {schedule!r}"
    )


def test_nightly_matrix_supports_manual_dispatch(workflow: dict) -> None:
    """``workflow_dispatch:`` MUST be supported so operators can trigger
    the sweep on demand (e.g. before a Python release upgrade)."""
    triggers = workflow.get(True) or workflow.get("on") or {}
    assert "workflow_dispatch" in triggers, (
        f"expected `workflow_dispatch:` trigger in nightly-matrix.yml; "
        f"got triggers={list(triggers)}"
    )


def test_nightly_matrix_declares_full_python_x_os_matrix(workflow: dict) -> None:
    """spec-140 D-140-03: full 3 python x 3 OS sweep (9 cells)."""
    jobs = workflow.get("jobs", {})
    assert "nightly-matrix" in jobs, f"expected a `nightly-matrix` job; got jobs={list(jobs)}"
    matrix = (jobs["nightly-matrix"].get("strategy") or {}).get("matrix") or {}

    python_versions = sorted(str(v) for v in matrix.get("python-version", []))
    assert python_versions == _EXPECTED_PYTHON_VERSIONS, (
        f"spec-140 D-140-03: nightly-matrix.yml must sweep {_EXPECTED_PYTHON_VERSIONS!r}; "
        f"got {python_versions!r}"
    )

    os_values = sorted(str(v) for v in matrix.get("os", []))
    assert os_values == _EXPECTED_OS, (
        f"spec-140 D-140-03: nightly-matrix.yml must cover {_EXPECTED_OS!r}; got {os_values!r}"
    )


def test_nightly_matrix_is_advisory(workflow: dict) -> None:
    """``continue-on-error: true`` MUST be set so the sweep never blocks PRs.

    The whole point of the W2 split is that PR-blocking gates run a single
    fast matrix and the long python sweep lives in an advisory workflow.
    A future edit that flips this flag silently undoes the split.
    """
    job = workflow.get("jobs", {}).get("nightly-matrix") or {}
    assert job.get("continue-on-error") is True, (
        "spec-140 D-140-03: nightly-matrix.yml job must set "
        "`continue-on-error: true` so cell failures stay advisory."
    )
