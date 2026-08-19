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
"""

from __future__ import annotations

import json
import sys
import time

# One home for the algorithm, and it is not this file. `checkpoint` has to decide whether the
# executed-checks receipt is about the code in front of it, and the only receipt in this tree
# bound to content is the one written here — but nothing under `src/` can import a file in
# `tests/`, so leaving the digest here meant a second copy of a hash in a second file.
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


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "record":
        return record(argv[1])
    if argv == ["trailer"]:
        return trailer()
    print(__doc__.strip().rsplit("\n\n", 1)[-1], file=sys.stderr)
    return 2


if __name__ == "__main__":  # pragma: no cover — the entry point, exercised by the lane
    sys.exit(main(sys.argv[1:]))
