"""Tests for spec 030 / B-030-3: finding-granular revalidation.

After a correction, `--revalidate <finding-id>` re-reads the specific file's diff and marks
the finding `fixed` only when the change actually removed the trigger, without re-running
the whole lane. A touched file whose diff keeps the trigger is INCOMPLETE, never silently
fixed (deepsec's `revalidate`).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_engineering import revalidate  # noqa: E402


def _finding(trigger: str) -> dict:
    return {"id": "F-1", "trigger": trigger, "file": "src/app.py"}


def test_a_diff_that_removes_the_trigger_marks_fixed():
    finding = _finding("password = getenv('DB_PASS', 'root')")
    before = "password = getenv('DB_PASS', 'root')\n"
    after = "password = getenv('DB_PASS', 'root-default')\n"
    assert revalidate.apply(finding, before, after) is True


def test_a_touched_file_that_keeps_the_trigger_is_incomplete():
    finding = _finding("password = getenv('DB_PASS', 'root')")
    before = "password = getenv('DB_PASS', 'root')\n"
    after = "password = getenv('DB_PASS', 'root')\nuser = 'admin'\n"  # touched but trigger stays
    assert revalidate.apply(finding, before, after) is False


def test_a_file_not_touched_stays_open():
    finding = _finding("password = getenv('DB_PASS', 'root')")
    # No diff at all for this file: nothing was corrected.
    assert revalidate.apply(finding, "password = getenv('DB_PASS', 'root')\n",
                            "password = getenv('DB_PASS', 'root')\n") is False


def test_a_finding_whose_trigger_was_never_present_is_incomplete():
    finding = _finding("TRIGGER-NOT-IN-BEFORE")
    assert revalidate.apply(finding, "x = 1\n", "x = 2\n") is False