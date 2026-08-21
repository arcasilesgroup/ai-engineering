#!/usr/bin/env python3
"""The two numbers a council run owes, recomputed from the file rather than read out of it.

`EP-195` asks a second model to "find a measurable gap, not manufacture consensus", and
`docs/adr/0019` closes by saying no benchmark defines the improvement a council shows. Spec
023's `D-023-05` answers with two counts per run: how many gaps appeared only after the
anonymised cross-read, and how many findings were deleted for carrying no command or for
being refuted.

A model printing its own score is what rule 11 refuses, so this does not read the totals the
run wrote and print them back. It counts the entries under the two round-two headings itself
and refuses when its count and the run's stated total disagree. That disagreement is the only
thing this can catch and it is the thing worth catching: a run that says eleven and lists
four has either lost nine entries or invented nine, and either way the number closing a
deferral would be fiction.

It fails closed. An unparseable file, a missing heading, a total that is not a number and a
count that does not match are all non-zero. A repository with no `specs/*/council.md` at all
is not a failure and is not a pass either — it says so and exits zero, because a council that
has not run is not a council that lied.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

NEW_HEADING = "### Gaps no single lens named"
CUT_HEADING = "### Findings cut for carrying no command"
REFUTED_HEADING = "### Findings the cross-read refuted"
TOTALS_HEADING = "## The two counts"

_NEW_TOTAL = re.compile(r"^- Gaps that appeared only after the cross-read: \*\*(\d+)\*\*$", re.M)
_DELETED_TOTAL = re.compile(r"^- Findings deleted[^:]*: \*\*(\d+)\*\*$", re.M)

# The same schema, bound and shape as `tests/skill_eval.py`, because two spellings of a
# receipt is two receipts. A day: a count that ran last week says nothing about the file
# as it is now.
RECEIPT_SCHEMA = "urn:ai-engineering:check-evidence:1"
RECEIPT_MAX_AGE = 86_400

# A transcript larger than this is not a transcript. Bounded because this reads every
# matching file into memory to digest it, and an unbounded read is a check that can be
# turned into a way to stop the gate.
MAX_BYTES = 4_000_000


class Unreadable(ValueError):
    """The file exists and its shape cannot be trusted. Never a warning."""


def _section(body: str, heading: str) -> str:
    """The lines under one heading, stopping at the next heading of any level.

    Prepending the newline rather than testing for one: a conditional fallback here would
    return the whole document when the heading sits at position 0, and a file with no such
    section would read as having one. That is the fail-open direction."""

    found = ("\n" + body).partition("\n" + heading)[2]
    if not found:
        raise Unreadable(f"no {heading!r} section")
    return re.split(r"\n#{2,3} ", found, maxsplit=1)[0]


def entries(section: str) -> int:
    """Top-level bullets. A nested bullet is a command or a reason belonging to the one
    above it, and counting it would inflate the number this whole script exists to hold
    honest."""

    return sum(1 for line in section.splitlines() if line.startswith("- "))


def counts(body: str) -> tuple[int, int]:
    """(new, deleted), recomputed, refusing when the run's own totals disagree."""

    # Two causes, two sections, one total. A review found that the second count was labelled
    # "deleted for carrying no command or for being refuted" while the file only ever showed
    # refutations — the no-command cuts happen in round one and never reach the page — so the
    # number could not be the number its own label named. Both sections are required: an
    # absent one is an unreadable file and not a zero.
    measured = (
        entries(_section(body, NEW_HEADING)),
        entries(_section(body, CUT_HEADING)) + entries(_section(body, REFUTED_HEADING)),
    )
    totals = _section(body, TOTALS_HEADING)
    stated = (_NEW_TOTAL.search(totals), _DELETED_TOTAL.search(totals))
    if not all(stated):
        raise Unreadable(f"{TOTALS_HEADING!r} does not state both counts in the form it must")
    claimed = (int(stated[0].group(1)), int(stated[1].group(1)))
    if claimed != measured:
        raise Unreadable(
            f"the run states {claimed[0]} new and {claimed[1]} deleted, and the file lists "
            f"{measured[0]} and {measured[1]}"
        )
    return measured


def _receipt(files: int, new: int, deleted: int, started: str, digest: str) -> None:
    """Never raises. A receipt that could take the run down with it would make a record of
    a check into a way to fail the check."""

    where = ROOT / ".ai" / "receipts" / "council-counts.json"
    artifact = "sha256:" + hashlib.sha256(f"{new}/{deleted}".encode()).hexdigest()
    try:
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_text(
            json.dumps(
                {
                    "schema": RECEIPT_SCHEMA,
                    "schema_version": "1",
                    "kind": "automated",
                    "id": "council-counts",
                    "applicability": "applicable" if files else "not-applicable",
                    "command": "python tests/council_counts.py",
                    "tool_version": f"council-counts over {files} file(s)",
                    "input_digest": digest,
                    "artifact_digest": artifact,
                    "started_at": started,
                    "finished_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "max_age_seconds": RECEIPT_MAX_AGE,
                    "outcome": "PASS",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError as why:
        print(f"  the counts were taken and the receipt could not be written: {why}")
        return
    print(f"  receipt: {where.relative_to(ROOT)}")


def main() -> int:
    started = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    found = sorted(ROOT.glob("specs/*/council.md"))
    for path in found:
        # A council file that is a link, or whose directory is one, is a file this repository
        # did not write where it thinks it did. Refusing is the only answer a check can give.
        if path.is_symlink() or path.parent.is_symlink():
            print(f"  {path.relative_to(ROOT)} is a link, and a link is not a record")
            return 1
        if path.stat().st_size > MAX_BYTES:
            print(f"  {path.relative_to(ROOT)} is {path.stat().st_size} bytes, over {MAX_BYTES}")
            return 1
    digest = hashlib.sha256(b"".join(path.read_bytes() for path in found) or b"").hexdigest()
    if not found:
        print("  no council has run in this repository, so there is nothing to count")
        _receipt(0, 0, 0, started, "sha256:" + digest)
        print("RAN council=0/0")
        return 0

    new = deleted = 0
    for path in found:
        where = path.relative_to(ROOT)
        try:
            body = path.read_text(encoding="utf-8")
        except OSError as why:
            print(f"  {where} could not be read: {why}")
            return 1
        try:
            gained, lost = counts(body)
        except Unreadable as why:
            print(f"  {where}: {why}")
            return 1
        print(f"  {where.parent.name}  {gained} found only by the cross-read, {lost} deleted")
        new, deleted = new + gained, deleted + lost

    _receipt(len(found), new, deleted, started, "sha256:" + digest)
    print(f"RAN council={new}/{deleted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
