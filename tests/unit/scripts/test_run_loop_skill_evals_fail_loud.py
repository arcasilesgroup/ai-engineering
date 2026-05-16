"""RED test: --regression with missing baseline must fail loud (D-136-07).

Closes the silent gate-degradation footgun: pre-spec-136 the script
returned 0 with only a stderr warning when the baseline was absent,
leaving the CI gate green-but-empty.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "run_loop_skill_evals.py"


def test_regression_with_missing_baseline_fails_loud(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--skill",
            "all",
            "--regression",
            "--baseline",
            str(missing),
            "--corpus-root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, (
        f"expected exit 2 (operational error); got {result.returncode}. stderr: {result.stderr!r}"
    )
    assert "baseline" in result.stderr.lower()


def test_no_regression_with_missing_baseline_still_passes(tmp_path: Path) -> None:
    """First-run capture flow preserved when --regression is NOT requested."""
    missing = tmp_path / "does-not-exist.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--skill",
            "all",
            "--baseline",
            str(missing),
            "--corpus-root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
