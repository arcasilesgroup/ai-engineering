"""spec-127 M1 (sub-002 T-G.1): hot-path budget for ``skill_lint --check``.

D-127-08 budget: ≤200 ms wall-time over the live canonical surface. With
25% CI tolerance per brief §14.3, the hard ceiling is 250 ms.

Surface as of spec-201 sub-007 (D-201-15): the portability walk covers
every ``*.md`` under `.claude/skills/` (135 — 54 SKILL.md, 58 handlers,
18 references, 5 shared) plus every `.claude/agents/*.md` (19) = **154
files**; the structure / token-budget / front-loading walks stay on the
73-file SKILL.md-and-agents corpus (they parse SKILL.md frontmatter that
handlers and shared documents do not carry).

Widening cost, measured not assumed: the portability walk went 25.5 ms
at 73 files to 57.7 ms at 154 (+32.2 ms). Three post-widening
three-run medians on the reference dev host: 201.1 / 185.6 / 207.8 ms,
inside the 250 ms ceiling with roughly 20% headroom (was ~35%). The
budget constants are therefore UNCHANGED — a pre-emptive raise would be
a silent gate weakening (D-127-08).

The test invokes the CLI in a child process via ``subprocess.run`` so
import cost is included in the measurement (mirrors the pre-commit
hook invocation path). Three runs are timed; the median is asserted
against the ceiling so a single transient blip on a busy CI runner
does not flake the gate.
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
BUDGET_MS = 200.0
CI_TOLERANCE = 1.25  # 25% slack per brief §14.3
HARD_CEILING_MS = BUDGET_MS * CI_TOLERANCE


@pytest.mark.perf
def test_skill_lint_check_under_budget() -> None:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{TOOLS_DIR}{os.pathsep}{existing}" if existing else str(TOOLS_DIR)

    timings: list[float] = []
    for _ in range(3):
        started = time.perf_counter()
        result = subprocess.run(
            [sys.executable, "-m", "skill_lint", "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        timings.append(elapsed_ms)
        # Exit code may be 0/1/2 depending on the grade vector; we
        # only care about wall-time here.
        assert result.returncode in {0, 1, 2}, (
            f"unexpected returncode {result.returncode}: {result.stderr}"
        )

    median_ms = statistics.median(timings)
    assert median_ms <= HARD_CEILING_MS, (
        f"skill_lint --check median {median_ms:.1f} ms exceeds "
        f"{HARD_CEILING_MS:.1f} ms ceiling (timings={timings})"
    )
