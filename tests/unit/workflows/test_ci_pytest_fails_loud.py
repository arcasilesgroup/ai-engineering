"""CI test invocations must fail loud — a piped pytest must not mask its exit.

A pipeline like ``pytest ... | tee log`` returns the LAST command's exit
status (``tee`` = 0), so a failing test suite can report success. GitHub's
default bash shell enables ``pipefail`` implicitly, but relying on that is
fragile: a shell change or a copy-pasted step elsewhere silently reintroduces
the footgun. This gate makes the guarantee explicit and durable — any workflow
step that pipes pytest output MUST set ``pipefail`` in the same run block (or
not pipe at all).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


def _run_blocks() -> list[tuple[str, str, str]]:
    """Return (workflow_file, job_name, run_text) for every step with a run."""
    blocks: list[tuple[str, str, str]] = []
    for wf in sorted(WORKFLOWS_DIR.glob("*.yml")):
        data = yaml.safe_load(wf.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            continue
        for job_name, job in (data.get("jobs") or {}).items():
            if not isinstance(job, dict):
                continue
            for step in job.get("steps") or []:
                if isinstance(step, dict) and isinstance(step.get("run"), str):
                    blocks.append((wf.name, job_name, step["run"]))
    return blocks


def _pipes_pytest(run_text: str) -> bool:
    """True if a pytest invocation is piped into a downstream command."""
    # Join shell line-continuations so a multi-line pytest call reads as one.
    joined = run_text.replace("\\\n", " ")
    for line in joined.splitlines():
        if "pytest" in line and "|" in line.split("pytest", 1)[1]:
            return True
    return False


_RUN_BLOCKS = _run_blocks()
_PIPED_PYTEST = [b for b in _RUN_BLOCKS if _pipes_pytest(b[2])]


def test_workflow_run_blocks_discovered() -> None:
    """Guard against the scanner silently finding nothing (path/parse drift)."""
    assert _RUN_BLOCKS, f"no workflow run steps discovered under {WORKFLOWS_DIR}"


@pytest.mark.parametrize(
    "wf,job,run_text",
    _PIPED_PYTEST,
    ids=[f"{wf}:{job}" for wf, job, _ in _PIPED_PYTEST],
)
def test_piped_pytest_sets_pipefail(wf: str, job: str, run_text: str) -> None:
    assert "pipefail" in run_text, (
        f"{wf} job {job!r}: pytest output is piped without `set -o pipefail`. "
        "The pipeline returns the downstream command's exit code (e.g. tee=0), "
        "masking test failures. Add `set -o pipefail` to the run block or drop "
        "the pipe."
    )
