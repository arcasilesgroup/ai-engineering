#!/usr/bin/env python3
"""How many primary homes each commit on this branch touches.

`PO-16` says one primary home per commit, with one recorded exception: a commit moving a
count that another check forces it to move. The audit graded it CONTRADICTED and said why —
the widest commit on the branch touched twenty-one files across six homes, which is not the
exception, and the row is the audit grading the session that commissioned it.

Nothing measured it. So the rule and the practice could drift apart in either direction and
the only record of the gap was a sentence naming one commit, written once. This counts every
commit, names the widest, and prints how many exceed one home.

A home is the top-level area a path belongs to, because that is what the rule is about: a
commit that edits four files under `src/` is one change to the product, and a commit that
edits one file under `src/` and one under `.github/` is two decisions sharing a message.

It reports and never blocks. The rule is a practice, the exception is real and cannot be
recognised mechanically — a count moved because another check forced it looks exactly like a
count moved because somebody felt like it — and a gate that failed here would be a gate
asserting a judgement it cannot make. What it removes is the sentence going stale.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The homes, in the words `AGENTS.md` uses for them. A path outside all of them is its own
# top-level name, so a new area shows up as a home rather than silently joining another.
HOMES = ("src", "hooks", "tests", "policy", "docs", "specs", "surfaces", ".agents", ".github")


def git(*args: str) -> str:
    done = subprocess.run(
        ["git", *args], capture_output=True, text=True, cwd=str(ROOT), check=False
    )
    return done.stdout if done.returncode == 0 else ""


def home(path: str) -> str:
    head = path.split("/", 1)[0]
    return head if head in HOMES else (head or "root")


def homes(commit: str) -> set[str]:
    names = git("show", "--name-only", "--format=", commit).split()
    return {home(one) for one in names if one}


def main(argv: list[str]) -> int:
    ask = argparse.ArgumentParser(description="Primary homes per commit on this branch.")
    ask.add_argument("--since", default="main", help="the ref this branch left")
    args = ask.parse_args(argv)

    commits = git("rev-list", f"{args.since}..HEAD").split()
    if not commits:
        print(f"  no commit differs from {args.since}, so there is nothing to measure.")
        return 0

    spread = [(one, homes(one)) for one in commits]
    wide = [(one, seen) for one, seen in spread if len(seen) > 1]
    widest = max(spread, key=lambda pair: len(pair[1]))

    print(f"  {len(commits)} commit(s), {len(commits) - len(wide)} touching one home")
    print(f"  {len(wide)} touch more than one, which PO-16 allows only for a count another")
    print("  check forced to move — a judgement no command can make, so this counts and stops:")
    for one, seen in wide[:8]:
        print(f"    {one[:8]}  {len(seen)} homes: {', '.join(sorted(seen))}")
    if len(wide) > 8:
        print(f"    … and {len(wide) - 8} more")
    print(f"  widest: {widest[0][:8]} across {len(widest[1])} — {', '.join(sorted(widest[1]))}")
    print(f"RAN homes={len(wide)}")
    return 0


if __name__ == "__main__":  # pragma: no cover — the entry point, exercised by the lane
    sys.exit(main(sys.argv[1:]))
