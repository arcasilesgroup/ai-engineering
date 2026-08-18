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

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path


def toplevel() -> Path:
    """The repository this is being asked about, from where it is being asked.

    Not `parents[1]` of this file. `commit-msg` invokes the script by absolute path, and a
    checkout that vendors it — or a test that builds a repository in a temporary directory —
    would otherwise get a digest over *this* tree while committing to another one. A receipt
    that answers about the wrong repository is worse than no receipt.
    """

    found = subprocess.run(
        ("git", "rev-parse", "--show-toplevel"), capture_output=True, text=True, check=True
    )
    return Path(found.stdout.strip())


RECEIPT_PARTS = (".ai", "receipts", "ran.json")

# Ignored files are excluded, so a build directory or a virtualenv cannot move the digest.
# `--others` is what makes the set stable across `git add`: a file being added for the first
# time is "other" before the add and "cached" after it, and it has to be in both readings or
# every commit that adds a file would silently lose its trailer.
LISTING = ("git", "ls-files", "--cached", "--others", "--exclude-standard", "-z")


def content_digest() -> str:
    """One digest over the name and bytes of every file this commit could carry.

    Read from disk rather than from the index on purpose. The index answers "what is staged",
    and the question here is "what did the suite actually run over" — which is the working
    tree. Editing a file after the gate and before the commit has to break this, and reading
    the index would not notice.
    """

    root = toplevel()
    listed = subprocess.run(LISTING, capture_output=True, cwd=root, check=True).stdout
    running = hashlib.sha256()
    # The receipt is never part of what the receipt measures. `.ai/` is ignored in this
    # repository so it fell out anyway, and that is exactly the accident worth removing: in a
    # tree where it is not ignored, writing the receipt changes the digest the receipt just
    # recorded, and the trailer can never appear. A tool that cannot tell what it is looking
    # at from what it is looking through — the same defect, one level down.
    mine = "/".join(RECEIPT_PARTS).encode()
    for name in sorted(one for one in listed.split(b"\0") if one and one != mine):
        path = root / name.decode("utf-8", "surrogateescape")
        running.update(name)
        try:
            running.update(hashlib.sha256(path.read_bytes()).digest())
        except (OSError, ValueError):
            # A symlink to nowhere, a directory left by a removed submodule, an unreadable
            # file. Recorded as its own state rather than skipped: skipping would make two
            # different trees digest the same.
            running.update(b"\0unreadable")
    return running.hexdigest()


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
