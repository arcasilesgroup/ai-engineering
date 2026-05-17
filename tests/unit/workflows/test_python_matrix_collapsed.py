"""spec-140 W2.T7 / D-140-03 — PR-blocking python matrix is collapsed to 3.12.

The PR hot-path used to run a 3-OS x 3-python (3.11 / 3.12 / 3.13) matrix on
every push. That fanned the build time out to ~57 jobs even when nothing
touched Python's stdlib surface. D-140-03 collapses the PR matrix to a
single python version (3.12) and moves the full python sweep to
``nightly-matrix.yml`` (advisory).

This drift gate parses ``.github/workflows/ci-check.yml`` and asserts every
matrix that declares ``python-version`` carries exactly ``["3.12"]`` so a
silent re-expansion (e.g. a copy/paste from an older branch) trips CI.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci-check.yml"

_EXPECTED_PYTHON_VERSIONS = ["3.12"]


@pytest.fixture(scope="module")
def workflow() -> dict:
    """Parse ``ci-check.yml`` once per test module."""
    assert WORKFLOW_PATH.exists(), f"missing workflow: {WORKFLOW_PATH}"
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def _collect_matrix_python_versions(workflow: dict) -> dict[str, list[str]]:
    """Return ``{job_name: [python-versions...]}`` for every job whose matrix
    declares a python version.

    Both ``matrix.python-version`` (plain list form) and ``matrix.include``
    (per-entry mapping form) are handled — both styles appear in the
    workflow today.
    """
    found: dict[str, list[str]] = {}
    jobs = workflow.get("jobs", {})
    for name, job in jobs.items():
        strategy = job.get("strategy") or {}
        matrix = strategy.get("matrix") or {}
        if "python-version" in matrix:
            versions = matrix["python-version"]
            if isinstance(versions, list):
                found[name] = [str(v) for v in versions]
        # `matrix.include` carries python-version per entry (framework-smoke).
        include = matrix.get("include") or []
        if include:
            include_versions = sorted(
                {
                    str(entry["python-version"])
                    for entry in include
                    if isinstance(entry, dict) and "python-version" in entry
                }
            )
            if include_versions:
                found.setdefault(name, [])
                merged = sorted(set(found[name] + include_versions))
                found[name] = merged
    return found


def test_every_python_matrix_collapsed_to_3_12(workflow: dict) -> None:
    """spec-140 D-140-03: every PR-blocking matrix uses python 3.12 only."""
    found = _collect_matrix_python_versions(workflow)
    assert found, (
        "expected at least one job with a python-version matrix in "
        f"{WORKFLOW_PATH}; got none. The collapse may have removed the "
        "matrix entirely."
    )
    drift: dict[str, list[str]] = {}
    for job, versions in found.items():
        if versions != _EXPECTED_PYTHON_VERSIONS:
            drift[job] = versions
    assert not drift, (
        "spec-140 D-140-03 drift: PR-blocking matrices must declare "
        f"python-version: {_EXPECTED_PYTHON_VERSIONS!r}. Drift:\n  "
        + "\n  ".join(f"{job}: {versions!r}" for job, versions in drift.items())
        + "\n(full sweep belongs in nightly-matrix.yml, not ci-check.yml)"
    )


def test_three_os_matrix_preserved(workflow: dict) -> None:
    """The 3-OS coverage matrix MUST survive the python collapse.

    The job-coverage contract is "1 python version x 3 operating systems"
    — collapsing the OS axis as well would silently strip the
    Linux/macOS/Windows divergence signal.
    """
    jobs_with_os: dict[str, list[str]] = {}
    for name, job in workflow.get("jobs", {}).items():
        strategy = job.get("strategy") or {}
        matrix = strategy.get("matrix") or {}
        if "os" in matrix and isinstance(matrix["os"], list):
            jobs_with_os[name] = sorted(str(v) for v in matrix["os"])
        include = matrix.get("include") or []
        if include:
            os_values = sorted(
                {str(entry["os"]) for entry in include if isinstance(entry, dict) and "os" in entry}
            )
            if os_values:
                jobs_with_os.setdefault(name, [])
                merged = sorted(set(jobs_with_os[name] + os_values))
                jobs_with_os[name] = merged
    expected = sorted(["ubuntu-latest", "macos-latest", "windows-latest"])
    missing: dict[str, list[str]] = {}
    for job, oses in jobs_with_os.items():
        if oses != expected:
            missing[job] = oses
    assert not missing, (
        "spec-140 W2: 3-OS coverage must be preserved on every matrix job. "
        "Drift:\n  " + "\n  ".join(f"{job}: {oses!r}" for job, oses in missing.items())
    )
