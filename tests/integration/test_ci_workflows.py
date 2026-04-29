"""Integration tests for spec-114 CI workflow artifacts (T-2.9..T-2.10).

Spec-114 G-4 introduces `.github/workflows/test-hooks-matrix.yml` —
a cross-OS matrix that runs only the hook test surface (D-114-04) on
ubuntu-latest, macos-latest, and windows-latest. Per spec-110 Article
VI every `uses:` reference in the workflow must pin a 40-character
SHA (no mutable tags).

The tests parse the YAML and assert the structural contract without
shelling out to actionlint — keeping the suite fast and offline.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "test-hooks-matrix.yml"

# 40-char lowercase hex SHA — git's full commit hash.
_SHA_RE = re.compile(r"^[a-f0-9]{40}$")


def _load_workflow() -> dict[str, Any]:
    assert WORKFLOW_PATH.exists(), f"missing workflow: {WORKFLOW_PATH}"
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def _iter_uses(node: Any) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "uses" and isinstance(value, str):
                found.append(value)
            else:
                found.extend(_iter_uses(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_iter_uses(item))
    return found


# ---------------------------------------------------------------------------
# T-2.9 RED — workflow exists with the right matrix and the right test surface
# ---------------------------------------------------------------------------


def test_test_hooks_matrix_workflow_present() -> None:
    """The workflow exists, runs on the three OS images, and targets hook tests only."""
    wf = _load_workflow()
    assert "name" in wf, "workflow must have a top-level name"

    # YAML parses `on:` as Python True (boolean). The PyYAML loader returns
    # `True: {...}` for `on:`. Find the trigger key tolerantly.
    triggers = wf.get("on") if "on" in wf else wf.get(True)
    assert isinstance(triggers, dict), f"workflow must declare on: triggers, got {triggers!r}"
    assert "push" in triggers and "pull_request" in triggers, "must run on push and PR"

    jobs = wf.get("jobs", {})
    assert jobs, "workflow must declare at least one job"
    # Find the matrix job (only one expected).
    matrix_jobs = [
        (name, body)
        for name, body in jobs.items()
        if isinstance(body, dict) and body.get("strategy", {}).get("matrix")
    ]
    assert matrix_jobs, "workflow must define a matrix strategy"
    job_name, job = matrix_jobs[0]

    matrix = job["strategy"]["matrix"]
    os_list = matrix.get("os", [])
    for required in ("ubuntu-latest", "macos-latest", "windows-latest"):
        assert required in os_list, f"matrix.os must include {required}; got {os_list}"

    # The job runs pytest only on the hook surface per D-114-04.
    steps = job.get("steps", [])
    test_steps = [
        step for step in steps if isinstance(step, dict) and "pytest" in str(step.get("run", ""))
    ]
    assert test_steps, "workflow must invoke pytest"
    pytest_invocations = " ".join(str(step.get("run", "")) for step in test_steps)
    for path in (
        "tests/unit/_lib",
        "tests/unit/hooks",
        "tests/integration/test_codex_hooks.py",
        "tests/integration/test_gemini_hooks.py",
        "tests/integration/test_copilot_",
    ):
        assert path in pytest_invocations, (
            f"pytest invocation must target {path}; full invocation:\n{pytest_invocations}"
        )

    # Spec-110 Article VI: every uses: pins a 40-char SHA.
    uses_refs = _iter_uses(wf)
    assert uses_refs, "workflow must reference at least one action"
    for ref in uses_refs:
        if "@" not in ref:
            raise AssertionError(f"uses ref missing @: {ref}")
        _, _, sha = ref.partition("@")
        assert _SHA_RE.match(sha), f"uses ref must pin 40-char SHA: {ref}"

    # Smoke: the matrix job runs against itself via runs-on.
    assert "runs-on" in job, f"matrix job {job_name} must declare runs-on"
