"""Which receipt decides, when several of them ran.

`checkpoint._executed` carried 44 surviving mutants, and the comment inside it records a
defect worth a whole test file. It used to keep one receipt, assigned in a loop over
`sorted(...)`, so the winner was the *alphabetically last fresh receipt* while the variable
holding it was called `freshest`. With `adversarial-attacks.json` reporting FAIL and
`local-command-python.json` reporting PASS, the function returned PASS.

A failing check masked by a passing one whose filename sorts later. Nothing about that is
visible in the output, which is what makes it the shape this product exists to refuse
rather than an ordering preference — so the rule is now that **every fresh receipt is read
and the worst of them decides**, and these cases hold it in both directions.

The other half is age. A gate that ran last week over different code proves nothing about
this checkpoint, so an expired receipt is the same answer as no receipt at all: INCOMPLETE,
never PASS and never FAIL. Reading a stale one either way would be a verdict about code
that is no longer there.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ai_engineering import checkpoint

NOW = datetime(2026, 8, 18, 12, 0, 0, tzinfo=UTC)


def _receipt(root: Path, name: str, said: str, *, age: int = 0, bound: int = 3600) -> None:
    where = root / checkpoint.RECEIPTS
    where.mkdir(parents=True, exist_ok=True)
    finished = (NOW - timedelta(seconds=age)).strftime("%Y-%m-%dT%H:%M:%SZ")
    (where / f"{name}.json").write_text(
        json.dumps(
            {"id": name, "outcome": said, "finished_at": finished, "max_age_seconds": bound}
        ),
        encoding="utf-8",
    )


def _decided(root: Path):
    return checkpoint._executed(root, now=NOW)


def test_no_receipts_at_all_is_incomplete_rather_than_a_pass(tmp_path: Path):
    """Nothing ran, so nothing is known. A pass here would be the product asserting a green
    it never observed, which is the one thing it may not do."""

    assert _decided(tmp_path).status == "INCOMPLETE"


def test_one_fresh_passing_receipt_is_a_pass_and_names_itself(tmp_path: Path):
    _receipt(tmp_path, "gate", "PASS")

    decided = _decided(tmp_path)

    assert decided.status == "PASS"
    assert "gate" in decided.detail


def test_a_failing_receipt_is_not_masked_by_a_passing_one_that_sorts_later(tmp_path: Path):
    """The defect this file exists for, in the exact arrangement that produced it.
    `adversarial-attacks` reports FAIL and `local-command-python` reports PASS, and the
    second sorts later — so keeping one receipt from a loop over `sorted(...)` returned
    PASS while the variable was called `freshest`."""

    _receipt(tmp_path, "adversarial-attacks", "FAIL")
    _receipt(tmp_path, "local-command-python", "PASS")

    decided = _decided(tmp_path)

    assert decided.status == "FAIL"
    assert "adversarial-attacks" in decided.detail


def test_the_same_arrangement_the_other_way_round_still_fails(tmp_path: Path):
    """The order must not decide the verdict at all, so the failing name is made to sort
    first as well. A test that only used the original arrangement would pass against a fix
    that simply reversed the sort."""

    _receipt(tmp_path, "aaa-failing", "FAIL")
    _receipt(tmp_path, "zzz-passing", "PASS")

    assert _decided(tmp_path).status == "FAIL"


def test_any_outcome_that_is_not_pass_counts_as_a_failure(tmp_path: Path):
    """INCOMPLETE from a check that ran is not a pass. A gate that could not decide has not
    cleared this diff, and treating anything-but-FAIL as acceptable is how an undecidable
    result becomes a green one."""

    _receipt(tmp_path, "one", "INCOMPLETE")

    assert _decided(tmp_path).status == "FAIL"


def test_a_receipt_older_than_its_own_bound_is_the_same_as_no_receipt(tmp_path: Path):
    """Not a FAIL and not a PASS. A gate that ran last week over different code proves
    nothing about this checkpoint, and reading it either way is a verdict about code that is
    no longer there."""

    _receipt(tmp_path, "gate", "PASS", age=7200, bound=3600)

    assert _decided(tmp_path).status == "INCOMPLETE"


def test_a_stale_failure_is_also_ignored_rather_than_kept(tmp_path: Path):
    """The symmetry matters. Keeping an expired FAIL would block a diff on a finding nobody
    can reproduce, and the cure printed with it would be about code that has changed."""

    _receipt(tmp_path, "old", "FAIL", age=7200, bound=3600)
    _receipt(tmp_path, "new", "PASS")

    assert _decided(tmp_path).status == "PASS"


def test_a_receipt_with_no_age_bound_of_its_own_expires_the_second_it_is_written(tmp_path: Path):
    """The default bound is zero, so a receipt that does not say how long it stays valid is
    fresh for exactly the instant it finished and stale one second later. The alternative
    default — forever — would make one green run last the life of the repository, which is
    the failure this whole check exists to prevent."""

    where = tmp_path / checkpoint.RECEIPTS
    where.mkdir(parents=True, exist_ok=True)

    def unbounded(finished):
        (where / "gate.json").write_text(
            json.dumps(
                {
                    "id": "gate",
                    "outcome": "PASS",
                    "finished_at": finished.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            ),
            encoding="utf-8",
        )

    unbounded(NOW)
    assert _decided(tmp_path).status == "PASS"

    unbounded(NOW - timedelta(seconds=1))
    assert _decided(tmp_path).status == "INCOMPLETE"


def test_a_receipt_that_cannot_be_read_is_skipped_and_the_rest_still_decide(tmp_path: Path):
    """One corrupt file must not blind the check to the others. It is skipped rather than
    fatal, and if it was the only one the answer is INCOMPLETE — which is what no readable
    receipt means."""

    where = tmp_path / checkpoint.RECEIPTS
    where.mkdir(parents=True, exist_ok=True)
    (where / "broken.json").write_text("{not json", encoding="utf-8")
    _receipt(tmp_path, "gate", "FAIL")

    assert _decided(tmp_path).status == "FAIL"

    (where / "gate.json").unlink()
    assert _decided(tmp_path).status == "INCOMPLETE"


def test_a_receipt_with_an_unparseable_timestamp_is_skipped(tmp_path: Path):
    """The format is exact on purpose. A timestamp this cannot parse is a receipt whose age
    is unknown, and an unknown age is not a fresh one."""

    where = tmp_path / checkpoint.RECEIPTS
    where.mkdir(parents=True, exist_ok=True)
    (where / "gate.json").write_text(
        json.dumps(
            {"id": "gate", "outcome": "PASS", "finished_at": "yesterday", "max_age_seconds": 3600}
        ),
        encoding="utf-8",
    )

    assert _decided(tmp_path).status == "INCOMPLETE"
