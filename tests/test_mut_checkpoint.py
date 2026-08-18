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

import pytest

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


# A row is the receipts on disk and the answer they must produce together. One table,
# because "which receipt decides" is one question and ten copies of it let ten assertions
# drift apart — which is how the defect above survived in the first place.
#
# Each receipt is (name, outcome, seconds of age, bound in seconds).

FRESH = 3600


@pytest.mark.parametrize(
    ("receipts", "status", "names"),
    [
        # Nothing ran, so nothing is known. A pass here would be the product asserting a
        # green it never observed, which is the one thing it may not do.
        pytest.param([], "INCOMPLETE", None, id="no receipts at all"),
        pytest.param([("gate", "PASS", 0, FRESH)], "PASS", "gate", id="one fresh pass"),
        # The defect this file exists for, in the exact arrangement that produced it.
        # Keeping one receipt from a loop over `sorted(...)` returned PASS while the
        # variable holding it was called `freshest`.
        pytest.param(
            [("adversarial-attacks", "FAIL", 0, FRESH), ("local-command-python", "PASS", 0, FRESH)],
            "FAIL",
            "adversarial-attacks",
            id="a failure masked by a pass sorting later",
        ),
        # The same arrangement reversed, so a fix that merely inverted the sort would not
        # pass this file.
        pytest.param(
            [("aaa-failing", "FAIL", 0, FRESH), ("zzz-passing", "PASS", 0, FRESH)],
            "FAIL",
            "aaa-failing",
            id="and with the failure sorting first",
        ),
        # A gate that could not decide has not cleared this diff. Treating anything-but-FAIL
        # as acceptable is how an undecidable result becomes a green one.
        pytest.param(
            [("one", "INCOMPLETE", 0, FRESH)], "FAIL", None, id="an outcome that is not PASS"
        ),
        # A gate that ran last week over different code proves nothing about this
        # checkpoint, and reading it either way is a verdict about code that is gone.
        pytest.param(
            [("gate", "PASS", 7200, FRESH)], "INCOMPLETE", None, id="a pass past its bound"
        ),
        # The symmetry matters: keeping an expired FAIL blocks a diff on a finding nobody
        # can reproduce, with a cure about code that has changed.
        pytest.param(
            [("old", "FAIL", 7200, FRESH), ("new", "PASS", 0, FRESH)],
            "PASS",
            "new",
            id="a stale failure beside a fresh pass",
        ),
    ],
)
def test_every_fresh_receipt_is_read_and_the_worst_of_them_decides(
    tmp_path: Path, receipts, status, names
):
    for name, said, age, bound in receipts:
        _receipt(tmp_path, name, said, age=age, bound=bound)

    decided = _decided(tmp_path)

    assert decided.status == status
    if names is not None:
        assert names in decided.detail


def test_a_receipt_that_cannot_be_read_is_skipped_and_the_rest_still_decide(tmp_path: Path):
    """One corrupt file must not blind the check to the others — and if it was the only one,
    the answer is INCOMPLETE, which is what no readable receipt means. Two states from one
    fixture, so it is not a row."""

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
            {"id": "gate", "outcome": "PASS", "finished_at": "yesterday", "max_age_seconds": FRESH}
        ),
        encoding="utf-8",
    )

    assert _decided(tmp_path).status == "INCOMPLETE"


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
