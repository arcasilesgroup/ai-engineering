"""spec-131 S7 (sub-007 T-7.9): hot-path budget for ``spec_lint --check``.

R-131-13 budget: ≤500 ms wall-time per invocation against the canonical
``.ai-engineering/specs/spec.md``. With 25 % CI tolerance per brief
§14.3, the hard ceiling is 625 ms. Realistic measurement on the
sub-007 reference machine is ~150 ms so the budget has ~4x headroom.

The test invokes the CLI in a child process via ``subprocess.run`` so
import cost is included (mirrors the pre-commit hook invocation path).
Three runs are timed; the median is asserted against the ceiling so a
single transient blip on a busy CI runner does not flake the gate.
"""

from __future__ import annotations

import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "tools"
BUDGET_MS = 500.0
CI_TOLERANCE = 1.25  # 25% slack per brief §14.3
HARD_CEILING_MS = BUDGET_MS * CI_TOLERANCE


@pytest.mark.perf
def test_spec_lint_check_under_budget() -> None:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{TOOLS_DIR}{os.pathsep}{existing}" if existing else str(TOOLS_DIR)

    timings: list[float] = []
    for _ in range(3):
        started = time.perf_counter()
        result = subprocess.run(
            [sys.executable, "-m", "spec_lint", "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        timings.append(elapsed_ms)
        # Exit code may be 0 or 1 depending on the canonical spec
        # state; we only care about wall-time here.
        assert result.returncode in {0, 1}, (
            f"unexpected returncode {result.returncode}: {result.stderr}"
        )

    median_ms = statistics.median(timings)
    assert median_ms <= HARD_CEILING_MS, (
        f"spec_lint --check median {median_ms:.1f} ms exceeds "
        f"{HARD_CEILING_MS:.1f} ms ceiling (timings={timings})"
    )
