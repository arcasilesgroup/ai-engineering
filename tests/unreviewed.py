#!/usr/bin/env python3
"""Which commits on this branch no closed block review covers.

`PO-04` asks that the per-task checkpoint be atomic, revertible and labelled unreviewed, and
the audit graded it INCOMPLETE because the word appears once in the whole history, on an
audit-doc commit, and never on a task checkpoint.

That measurement was looking where the approved plan says never to look. `specs/010/plan.md`
is explicit: "`UNREVIEWED` is derived from the absence of a clean block review and gate; a
commit message, model statement, test label, or metadata field cannot turn it into approval."
A trailer saying `unreviewed` would be the one thing the plan forbids — a metadata field
standing in for a review — and writing one would have satisfied the row while contradicting
the document it answers to.

So it is derived. The block hand-offs in `docs/audit-2026-08-16.md` each name a base and a
final HEAD, and every one of them carries a reviewer, a repair and a gate. A commit inside one
of those ranges has been through a closed review; every other commit on this branch has not,
and that is the label — computed, not written, and true the moment a block closes without
anybody editing a commit.

It reports and never blocks. Unreviewed is the ordinary state of work in flight, and a gate
that failed on it would be a gate demanding a review before the block it belongs to has
closed — which is the amplification the whole block cadence exists to remove.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs" / "audit-2026-08-16.md"

# `| base | \`abc1234\` |` and `| final HEAD | \`def5678\` |`, which is the shape the hand-off
# tables already use. Read rather than re-declared: a second list of ranges would be a second
# place for them to disagree.
FIELD = re.compile(r"^\|\s*(base|final HEAD)\s*\|\s*`([^`]+)`\s*\|", re.M)

# The reviewer's own row, read as free text because that is what it is. A hand-off can be
# written for a range nobody reviewed — the table would be complete and every field filled —
# and crediting it would let anybody clear this report by typing one table. So a block counts
# only where the disposition says a person found something or found nothing, and these are the
# words for having looked at all.
DISPOSITION = re.compile(r"^\|\s*reviewer disposition\s*\|\s*([^|]*)\|", re.M)
NOBODY = ("none", "not reviewed", "no review", "pending", "n/a", "-", "")


def git(*args: str) -> str:
    done = subprocess.run(
        ["git", *args], capture_output=True, text=True, cwd=str(ROOT), check=False
    )
    return done.stdout if done.returncode == 0 else ""


def blocks() -> list[tuple[str, str, str, bool]]:
    """Every hand-off on record, as (name, base, final HEAD, somebody looked)."""

    try:
        body = AUDIT.read_text(encoding="utf-8")
    except OSError:
        return []
    found = []
    for chunk in body.split("### Block ")[1:]:
        name = chunk.split("\n", 1)[0].split("—")[0].strip()
        fields = dict(FIELD.findall(chunk))
        said = DISPOSITION.search(chunk)
        looked = said is not None and said.group(1).strip().casefold() not in NOBODY
        if "base" in fields and "final HEAD" in fields:
            found.append((name, fields["base"], fields["final HEAD"], looked))
    return found


def reviewed() -> set[str]:
    """Every commit inside a closed block's reviewed range, by full sha.

    A range whose ends this clone cannot resolve contributes nothing rather than everything:
    an unresolvable base would otherwise make `base..head` mean "the whole history", and every
    commit would read as reviewed by a block that reviewed none of them.
    """

    covered: set[str] = set()
    for name, base, head, looked in blocks():
        if not looked:
            # A hand-off whose reviewer row says nobody did is a record of a block that
            # closed, not of a block that was reviewed. Counting it would make this report
            # clearable by typing a table, which is the shape it exists to refuse.
            print(f"    not credited  Block {name}: its hand-off names no reviewer")
            continue
        span = git("rev-list", f"{base}..{head}").split()
        if span:
            covered.update(span)
            covered.update(git("rev-parse", head).split())
    return covered


def main(argv: list[str]) -> int:
    ask = argparse.ArgumentParser(description="Which commits no closed block review covers.")
    ask.add_argument("--since", default="main", help="the ref this branch left")
    args = ask.parse_args(argv)

    on_branch = git("rev-list", f"{args.since}..HEAD").split()
    if not on_branch:
        print(f"  no commit differs from {args.since}, so there is nothing to label.")
        return 0

    covered = reviewed()
    unreviewed = [one for one in on_branch if one not in covered]

    reviewed_blocks = [one for one in blocks() if one[3]]
    print(
        f"  {len(blocks())} hand-off(s) on record, {len(reviewed_blocks)} naming a reviewer, "
        f"covering {len(covered)} commit(s)"
    )
    print(f"  {len(on_branch)} commit(s) on this branch, of which {len(unreviewed)} are")
    print("  UNREVIEWED — derived from the absence of a closed review, never written into one:")
    for one in unreviewed[:12]:
        print(f"    {one[:8]}  {git('log', '-1', '--format=%s', one).strip()[:78]}")
    if len(unreviewed) > 12:
        print(f"    … and {len(unreviewed) - 12} more")
    print(f"RAN unreviewed={len(unreviewed)}")
    return 0


if __name__ == "__main__":  # pragma: no cover — the entry point, exercised by the lane
    sys.exit(main(sys.argv[1:]))
