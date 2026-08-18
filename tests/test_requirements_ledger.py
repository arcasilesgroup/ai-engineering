"""The ledger is the membership, and this is what holds it to being one.

`docs/audit-2026-08-16.md` published "266 of 385 proven" and could not say which 266. Its
second and third passes re-measured in bulk and named only the notable movements, so the
counts were written down and the membership was not. Measuring it properly found the number
was 86 too high, and most of that gap was a single habit: ids swept into a compressed range
like `EP-141–EP-150` with no test, no file and no command behind any of them. One of that
range, `EP-147`, turned out to be not merely unevidenced but false.

So this file asks of the ledger exactly what the ledger asks of the tree. Every id present
once. Every verdict from a closed vocabulary. Every row naming the command that decides it —
because a row without one is how a range gets swept again, and a compressed range is how 86
requirements came to be published as proven.

What this cannot check, and says so rather than implying otherwise: whether the command in a
row still returns what it returned when the row was written. A file cannot run 385 commands
inside a unit test in the time a gate has. What it can do is refuse a row that names none.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs" / "requirements.toml"

# Closed on purpose. A seventh word would be somebody inventing a grade to fit a row, which
# is the move that produced "266": every id had to be one of three things, so the ones that
# fit none of them were swept into the nearest range.
VERDICTS = ("PROVEN", "INCOMPLETE", "NO-EVIDENCE", "CONTRADICTED", "BLOCKED", "UNFALSIFIABLE")

# The count the source research document carries. Fixed: the requirements are what they are,
# and a ledger that could quietly cover fewer of them would be the same defect one level up.
TOTAL = 385


COMMITMENTS = 26


def _ledger() -> dict:
    return tomllib.loads(LEDGER.read_text(encoding="utf-8"))


def rows() -> list[dict[str, str]]:
    return _ledger()["requirement"]


def commitments() -> list[dict[str, str]]:
    """The process commitments, held to exactly what the product requirements are held to.

    They are a separate array because they answer a different question — the requirements are
    about what the wheel does and these are about how work happens here — and one array of
    two kinds of thing is how a reader ends up counting the wrong total."""

    return _ledger()["commitment"]


def test_every_requirement_appears_exactly_once_and_none_is_missing():
    """The whole point of the file. A ledger with a gap is a count again."""

    ids = [row["id"] for row in rows()]

    assert len(ids) == TOTAL, f"the ledger carries {len(ids)} rows and there are {TOTAL}"
    assert len(set(ids)) == len(ids), "an id appears twice"
    expected = [f"EP-{n:03d}" for n in range(1, TOTAL + 1)]
    assert ids == expected, f"missing or out of order: {sorted(set(expected) - set(ids))}"


def test_every_verdict_is_one_of_six_words():
    """Six words, and a seventh is somebody inventing a grade to fit a row."""

    wrong = {row["id"]: row["verdict"] for row in rows() if row["verdict"] not in VERDICTS}

    assert not wrong, f"verdicts outside the vocabulary: {wrong}"


UNRECOVERABLE = "unrecoverable"

# What an unrecoverable row is allowed to carry instead of a command, exactly. Not a free
# sentence: a fixed word, so this stays a check rather than a reading.
NOTHING_TO_RUN = "none — the requirement text could not be located"


def test_every_row_names_the_command_that_decides_it():
    """A row without a command is a row nobody can check, which is where the 86 came from.

    Not the output: the command. A pasted result goes stale the day after it is pasted, and
    the reader who doubts a row wants to re-run it rather than read what somebody else saw.

    The exception is the sixty-four rows whose subject begins `unrecoverable`. Those say the
    requirement's own text could not be located in the source document, so there is nothing
    to check and no command can exist. They were given a `git grep` for their own id to
    satisfy this test, and it did what a search for an identifier always does: it found the
    identifier. Excluding the ledger and the audit fixed sixty-four of them and left two
    still passing on a comment that discusses the range `EP-141–EP-150` — which is the end
    of the road, because no search can tell a mention of a requirement from an
    implementation of one.

    So a row with nothing to run says so in a fixed phrase, and this test refuses a command
    on such a row rather than demanding one. A shape check that can be satisfied by theatre
    produces theatre, and this one had produced sixty-six pieces of it.
    """

    thin, staged = {}, {}
    for row in [*rows(), *commitments()]:
        evidence = row.get("evidence", "").strip()
        if row["subject"].startswith(UNRECOVERABLE):
            if evidence != NOTHING_TO_RUN:
                staged[row["id"]] = evidence[:60]
        elif len(evidence) < 8:
            thin[row["id"]] = evidence

    assert not thin, f"rows naming no command, or too little of one: {thin}"
    assert not staged, (
        f"{len(staged)} rows say the requirement text could not be located and still carry a "
        f"command: {', '.join(sorted(staged)[:8])}. There is nothing to run, and a search for "
        f'the row\'s own id finds the row. Write exactly "{NOTHING_TO_RUN}".'
    )


def test_every_row_says_what_the_requirement_asks():
    """A verdict against an unstated subject is a verdict about nothing.

    Where the subject could not be recovered from the source document at all, the row says
    exactly that — and those rows are `NO-EVIDENCE`, never `PROVEN`, because a requirement
    nobody can state is not one anybody can have met.
    """

    for row in rows():
        subject = row.get("subject", "").strip()
        assert len(subject) > 12, f"{row['id']} states no subject"
        if "unrecoverable" in subject:
            assert row["verdict"] == "NO-EVIDENCE", (
                f"{row['id']} claims {row['verdict']} for a requirement whose text nobody "
                "could locate. That is the exact move this ledger exists to undo."
            )


def test_a_verdict_that_needs_a_reason_carries_one():
    """Four of the six words are claims about why something is not proven, and each is the
    kind of claim that rots quietly. INCOMPLETE has to say which half; BLOCKED has to say
    what it waits on; CONTRADICTED has to name the contradiction; UNFALSIFIABLE has to say
    what cannot be observed. PROVEN needs no note, because its command is its argument."""

    # NO-EVIDENCE joined this list once the seven rows carrying it without a reason were
    # written. "There is no evidence" is a claim like any other and it has causes that differ
    # entirely: a file nobody can find, an editor nobody can run here, a decision that
    # predates its own instrument, a deliberate non-build. A row that says none of them reads
    # as an oversight, and four of the seven were not.
    #
    # The unrecoverable rows are excused below and only there, because their subject already
    # carries the reason in the word `unrecoverable`.
    owed = ("INCOMPLETE", "BLOCKED", "CONTRADICTED", "UNFALSIFIABLE", "NO-EVIDENCE")
    silent = [
        row["id"]
        for row in rows()
        if row["verdict"] in owed
        and len(row.get("note", "").strip()) < 12
        # A row whose subject already carries the reason is not silent. The unrecoverable
        # rows are all NO-EVIDENCE, which is not in this list, so nothing here is excused
        # by accident.
        and "unrecoverable" not in row.get("subject", "")
    ]

    assert not silent, (
        f"{len(silent)} rows grade a requirement as not proven and do not say why: {silent}"
    )


def test_the_audit_publishes_the_number_this_ledger_holds():
    """The two must agree, or the published total is a claim about nothing again.

    This is the check that would have caught the original defect: the audit stated 266 and
    nothing compared that number to a per-requirement record, because there was none. Now
    there is one, and the prose has to match it.
    """

    proven = sum(1 for row in rows() if row["verdict"] == "PROVEN")
    audit = (ROOT / "docs" / "audit-2026-08-16.md").read_text(encoding="utf-8")
    stated = re.findall(r"\*\*(\d+) of 385\*\*", audit)

    assert stated, "the audit publishes no total, so nothing binds it to this ledger"
    assert stated[-1] == str(proven), (
        f"the audit's latest published total is {stated[-1]} of 385 and this ledger holds "
        f"{proven} PROVEN. One of the two is wrong and neither may be assumed."
    )


@pytest.mark.parametrize("verdict", VERDICTS)
def test_no_verdict_in_the_vocabulary_is_dead_wood(verdict: str):
    """Every one of the six is in use. A word nothing is graded with is a word that reads
    like a distinction the ledger makes and does not."""

    assert any(row["verdict"] == verdict for row in rows()), (
        f"nothing is graded {verdict}: either remove it from the vocabulary or say why it "
        "is reserved"
    )


def test_every_process_commitment_appears_exactly_once_and_none_is_missing():
    """The second research document the goal names. Its status lived only in prose until
    this file, which is precisely the shape that let 86 product requirements be published as
    proven without evidence — so it gets the same treatment rather than a softer one."""

    ids = [row["id"] for row in commitments()]

    assert len(ids) == COMMITMENTS, f"the ledger carries {len(ids)} commitments, not {COMMITMENTS}"
    assert ids == [f"PO-{n:02d}" for n in range(1, COMMITMENTS + 1)], f"missing or unordered: {ids}"


def test_every_commitment_carries_a_verdict_a_command_and_a_reason_when_it_owes_one():
    """The same three rules, and the third is the one that bites hardest here: seven of the
    twenty-six are graded not-proven and every one of them has to say which half is missing.

    Two of those reasons are corrections to claims this repository made hours before the row
    was written — that is what an independent reader is for, and softening them here would be
    the defect the whole ledger exists to undo."""

    owed = ("INCOMPLETE", "BLOCKED", "CONTRADICTED", "UNFALSIFIABLE", "NO-EVIDENCE")
    for row in commitments():
        assert row["verdict"] in VERDICTS, f"{row['id']}: {row['verdict']!r} is not a verdict"
        assert len(row.get("evidence", "").strip()) >= 8, f"{row['id']} names no command"
        assert len(row.get("subject", "").strip()) > 12, f"{row['id']} states no subject"
        if row["verdict"] in owed:
            assert len(row.get("note", "").strip()) >= 12, (
                f"{row['id']} is graded {row['verdict']} and does not say why"
            )


REPORTS = {
    "evolution_proposal": ".ai/reports/evolution-proposal/index.html",
    "process_optimization": ".ai/reports/process-optimization-research/index.html",
}


def test_the_ledger_names_the_exact_bytes_it_was_measured_against():
    """Provenance, because coverage cannot be checked and this can.

    Neither numbering appears in the source documents — `EP-nnn` and `PO-nn` are this audit's
    own index, assigned by reading prose in order — so no command can confirm that 385 and 26
    are the right totals. They are a reading. What a command *can* confirm is that the reading
    was taken against these bytes and that nobody has edited a report underneath it since.

    Absence is not a pass. `.ai/.gitignore` begins with `*`, so neither report is in the
    repository and a fresh clone or a CI runner has neither file. That case says it cannot
    decide, which is a different answer from agreeing, and it is the honest one: on any
    machine but the one that measured them, the ledger's provenance is unverifiable and this
    test's silence would otherwise imply the opposite.
    """

    import hashlib

    pinned = _ledger()["sources"]
    for key, where in REPORTS.items():
        source = ROOT / where
        if not source.is_file():
            pytest.skip(f"{where} is not in this tree, so its digest cannot be checked here")
        actual = hashlib.sha256(source.read_bytes()).hexdigest()
        assert actual == pinned[key], (
            f"{where} has changed since the ledger was measured on {pinned['measured_at']}: "
            f"pinned {pinned[key][:16]}, found {actual[:16]}. Every verdict below was taken "
            "against the old bytes, so re-measure or restore the file — do not repin."
        )


def test_no_row_proves_itself_by_finding_its_own_id_in_this_file():
    """A search for `EP-350` across the tree finds `EP-350` in the ledger, every time.

    Sixty-six rows carried exactly that command. All sixty-six passed, and all sixty-six meant
    nothing: the file being searched is the file asking the question, so the answer was always
    yes and was always about itself. The verdicts were honest — every one of those rows says
    NO-EVIDENCE — but the command beside them was theatre, and a later reader running the
    answer key over every row rather than only the proven ones would have flipped sixty-six
    verdicts on a self-reference.

    This is the same defect as a tool that cannot tell what it is looking at from what it is
    looking through, pointed at the audit instead of at the product. So a command that hunts
    for a requirement id has to exclude the two documents that index every requirement id.
    """

    searching = re.compile(r"\b(git grep|grep -r|grep -R|rg)\b")
    guilty = []
    for row in [*rows(), *commitments()]:
        command = row.get("evidence", "")
        if row["id"] not in command or not searching.search(command):
            continue
        if "':!docs/requirements.toml'" not in command or "':!docs/audit-" not in command:
            guilty.append(row["id"])

    assert not guilty, (
        f"{len(guilty)} rows search the whole tree for their own id without excluding the "
        f"ledger and the audit, so they find themselves and pass: {', '.join(guilty[:8])}. "
        "Add ':!docs/requirements.toml' ':!docs/audit-*.md' to the pathspec."
    )
