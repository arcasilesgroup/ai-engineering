#!/usr/bin/env python3
"""What ran, against exactly these bytes, written where git will keep it.

`PO-14` asks that every commit run its module's cheap suite rather than the whole gate, and
`PO-10` asks that the practices the process removed stay removed. Both were graded
NO-EVIDENCE for one reason: a gate run is an ephemeral process, its receipts are ignored,
and nothing it leaves behind survives into the tree. So neither the rule nor a breach of it
could be read afterwards by anybody, including the person who did it.

A commit trailer survives. This script writes the receipt that a trailer can be built from,
and builds it — but only when the bytes that were checked are the bytes being committed. The
key is a digest over every tracked or about-to-be-tracked file, so it is the same set before
`git add` and after it, and any edit in between changes it. A trailer that appears whether or
not the run happened is the defect this repository is named after; this one is absent by
default and present only when a run is on record for this exact content.

Two modes, both cheap enough to sit on the commit path:

    record <suite>   after a suite passes, note it against the current content
    trailer          print the trailer for that content, or nothing and exit 1
    unrun            list the commits on this branch that carry no run receipt
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

# One home for the algorithm, and it is not this file. `checkpoint` has to decide whether the
# executed-checks receipt is about the code in front of it, and the only receipt in this tree
# bound to content is the one written here — but nothing under `src/` can import a file in
# `tests/`, so leaving the digest here meant a second copy of a hash in a second file.
# This runs as a command, not only under pytest: `commit-msg` invokes it with whatever
# interpreter is to hand, and the mutation harness runs it from a copied tree that is not a
# project at all. Neither has the package installed, so the import below died with
# `ModuleNotFoundError` and the script exited non-zero — which `commit-msg` reads as "no
# receipt" and writes no trailer for.
#
# That failure mode is the worst available: the instrument's breakage is indistinguishable
# from its negative answer. A tree where the package cannot be imported would report that
# nothing was ever run over anything, quietly and forever. `tests/pilot_register.py` carries
# the same line for the same reason, and this one was written without it.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_engineering.evidence import LISTING, RECEIPT_PARTS, content_digest, toplevel

__all__ = ["LISTING", "RECEIPT_PARTS", "content_digest", "toplevel"]


def record(suite: str) -> int:
    receipt = toplevel().joinpath(*RECEIPT_PARTS)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(
        json.dumps(
            {"suite": suite, "content": content_digest(), "at": int(time.time())},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


def trailer() -> int:
    try:
        receipt = json.loads(toplevel().joinpath(*RECEIPT_PARTS).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 1
    if receipt.get("content") != content_digest():
        return 1
    suite = str(receipt.get("suite", "")).strip()
    if not suite:
        return 1
    print(f"Ai-Eng-Ran: {suite} content={receipt['content'][:12]}")
    return 0


def unrun(base: str) -> int:
    """Which commits on this branch nobody ran anything over.

    Written the evening this instrument caught its own author. `5cca6b9e` was pushed over a
    red gate — I joined the gate and the commit with `;` rather than `&&`, so the commit did
    not depend on the gate passing, and `EXIT=1` printed directly above the push. The trailer
    was correctly absent from that commit and present on every neighbour, and nobody looked.

    A control whose answer nobody consumes is the same defect as a control that cannot
    decide, arriving from the other side. So the answer is printed, on every gate run, beside
    the other two numbers that were prose this morning.

    It reports and never blocks. A commit with no receipt is not a defect — a merge, a revert,
    a commit made before this instrument existed, and every commit on `main` all have none.
    What it is, is the one thing nobody could see.
    """

    listed = subprocess.run(
        # `separator=` matters: without it a present trailer carries a newline and every
        # commit that has one splits into two lines, so the commits that ran read as
        # malformed and the ones that did not read as fine. The inversion is the whole risk.
        [
            "git",
            "log",
            "--format=%H%x1f%(trailers:key=Ai-Eng-Ran,valueonly,separator=%x00)%x1f%s",
            f"{base}..HEAD",
        ],
        capture_output=True,
        text=True,
        cwd=str(toplevel()),
        check=False,
    ).stdout
    rows = [line.split("\x1f") for line in listed.splitlines() if line.strip()]
    if not rows:
        print(f"  no commit differs from {base}, so nothing was measured.")
        return 0
    missing = [(sha, subject) for sha, trailer, subject in rows if not trailer.strip()]
    print(
        f"  {len(rows)} commit(s) since {base}, {len(rows) - len(missing)} carrying a run receipt"
    )
    print(f"  {len(missing)} carry none, which means nothing was run over exactly those bytes:")
    for sha, subject in missing[:8]:
        print(f"    {sha[:8]}  {subject[:76]}")
    if len(missing) > 8:
        print(f"    … and {len(missing) - 8} more")
    print(f"RAN unrun={len(missing)}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "record":
        return record(argv[1])
    if argv == ["trailer"]:
        return trailer()
    if argv and argv[0] == "unrun":
        return unrun(argv[1] if len(argv) > 1 else "main")
    print(__doc__.strip().rsplit("\n\n", 1)[-1], file=sys.stderr)
    return 2


if __name__ == "__main__":  # pragma: no cover — the entry point, exercised by the lane
    sys.exit(main(sys.argv[1:]))
