"""When a scoped run may stand for the whole tree, as tests that fail.

`anti_theatre` has always refused `PARTIAL`, on the argument that one mutated file standing
in for all of them is the theatre this reader exists to catch. The argument was right and it
made the gate impossible: measured on 2026-08-16, a whole-tree mutation run is 20,816
mutants and 121 minutes against a job capped at 30, so the lane never finished, never printed
a score, and was reported as `cancelled` on every commit. A gate nobody has ever seen the
output of is not a gate.

The split is the cure and this file is where its edge cases live: the whole tree runs on a
schedule, the pull request runs over its own diff, and `PARTIAL` counts only against a
receipt showing the whole-tree run completed inside the window. Every way that receipt can
lie is a test here, because a receipt nobody checks is worse than no receipt — it is the
same green with a document stapled to it.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import anti_theatre  # noqa: E402  — the reader under test lives beside this file

ROOT = Path(__file__).resolve().parents[1]


def _receipt(path: Path, **overrides) -> Path:
    record = {
        "name": "mutation-nightly",
        "status": "completed",
        "conclusion": "failure",
        "completed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    record.update(overrides)
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def _log(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_a_scoped_run_is_refused_when_nothing_proves_the_whole_tree_ran(tmp_path):
    """The rule as it stood, and it still stands: with no receipt, PARTIAL is not a pass."""

    log = _log(tmp_path / "mutate.log", "PARTIAL mutants=41\n")

    with pytest.raises(SystemExit):
        anti_theatre.main(log, ROOT, ("mutants",))


def test_a_scoped_run_counts_against_a_whole_tree_run_that_finished_inside_the_window(tmp_path):
    """And the receipt is read, not trusted: `completed_at` decides, and it is compared."""

    log = _log(tmp_path / "mutate.log", "PARTIAL mutants=41\n")
    receipt = _receipt(tmp_path / "nightly.json")

    assert anti_theatre.main(log, ROOT, ("mutants",), receipt) == 0


def test_a_whole_tree_run_older_than_its_bound_stops_standing_for_anything(tmp_path):
    """Four days, then the scoped run is on its own. A receipt with no expiry is a receipt
    that gets truer the longer nobody looks at it."""

    log = _log(tmp_path / "mutate.log", "PARTIAL mutants=41\n")
    stale = datetime.now(UTC) - timedelta(hours=anti_theatre.WHOLE_TREE_MAX_AGE_HOURS + 1)
    receipt = _receipt(tmp_path / "nightly.json", completed_at=stale.isoformat())

    with pytest.raises(SystemExit):
        anti_theatre.main(log, ROOT, ("mutants",), receipt)


def test_a_run_that_never_finished_is_not_a_run(tmp_path):
    """The exact shape the real lane had for weeks: started, killed at its cap, and the API
    still answers with a record. `status` is what separates the two, and the record for a
    run that timed out says `in_progress` at the moment it is read."""

    log = _log(tmp_path / "mutate.log", "PARTIAL mutants=41\n")
    receipt = _receipt(tmp_path / "nightly.json", status="in_progress")

    with pytest.raises(SystemExit):
        anti_theatre.main(log, ROOT, ("mutants",), receipt)


def test_a_receipt_that_is_not_json_refuses_rather_than_crashing(tmp_path):
    """A reader whose whole job is to refuse a false green may not fall over on a malformed
    input and take the job with it."""

    log = _log(tmp_path / "mutate.log", "PARTIAL mutants=41\n")
    broken = tmp_path / "nightly.json"
    broken.write_text("not json at all", encoding="utf-8")

    with pytest.raises(SystemExit):
        anti_theatre.main(log, ROOT, ("mutants",), broken)


def test_a_missing_receipt_is_the_same_answer_as_a_broken_one(tmp_path):
    """Absent and unreadable are two states and one verdict here: neither proves the whole
    tree was measured, so neither may let PARTIAL through."""

    log = _log(tmp_path / "mutate.log", "PARTIAL mutants=41\n")

    with pytest.raises(SystemExit):
        anti_theatre.main(log, ROOT, ("mutants",), tmp_path / "never-written.json")


def test_a_whole_tree_run_needs_no_receipt_and_never_did(tmp_path):
    """The unscoped path is untouched. `RAN` still means what it meant, and a log carrying
    it passes with nothing else supplied."""

    log = _log(tmp_path / "mutate.log", "RAN mutants=20816\n")

    assert anti_theatre.main(log, ROOT, ("mutants",)) == 0


def test_zero_is_still_not_a_pass_however_it_is_spelled(tmp_path):
    """`PARTIAL mutants=0` is a scoped run that measured nothing. The receipt says the whole
    tree was measured recently; it says nothing about this diff, and this diff is what the
    pull request is asking about."""

    log = _log(tmp_path / "mutate.log", "PARTIAL mutants=0\n")
    receipt = _receipt(tmp_path / "nightly.json")

    with pytest.raises(SystemExit):
        anti_theatre.main(log, ROOT, ("mutants",), receipt)
