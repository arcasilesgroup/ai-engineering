#!/usr/bin/env python3
"""Whether a commit has the exact-HEAD workflow receipts spec 010's Task 53 requires.

`specs/010/plan.md` reserves the shipped transition until "both live exact-HEAD workflow
proofs pass": each workflow with `headSha == "$sha"`, `status == completed`, and
`conclusion == success`. It says these shell queries are the separate live readiness proof and
are deliberately not part of the pytest gate, because a gate that needed the network would
fail on a machine that has none.

So this is a command, not a case, and it is written because the reason P0 sits in `draft` was
recorded as "two required lanes are red for reasons the branch cannot resolve from inside".
That was true when it was written. It has not been true for a day, and nothing re-measured it
— the thirteenth instance of the shape `docs/adr/0014` names, and the one that matters most,
because it is the sentence holding the whole phase where it is.

It decides nothing. Task 53 needs a specific candidate commit that also closes the ceiling to
zero slack, accepts three MADRs, refreshes the Intent and sets the status — and then separate
push consent. What this answers is only the half nobody could see: whether the live receipts
this repository requires are obtainable here at all, and at which commits they already exist.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The two the plan names. Read here rather than discovered, because a workflow that stopped
# running would otherwise make this report cleaner rather than emptier.
REQUIRED = ("check", "install")


def runs(branch: str, limit: int) -> list[dict]:
    if shutil.which("gh") is None:
        return []
    done = subprocess.run(
        [
            "gh",
            "run",
            "list",
            "--branch",
            branch,
            "--limit",
            str(limit),
            "--json",
            "headSha,workflowName,status,conclusion",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        return json.loads(done.stdout)
    except ValueError:
        return []


def proven(rows: list[dict]) -> dict[str, set[str]]:
    """Per commit, which required workflows completed successfully at that exact sha.

    `status == completed` matters as much as the conclusion: a cancelled run has no
    conclusion and an in-flight one has none yet, and either would read as absent rather than
    as failed if only the conclusion were asked for.
    """

    found: dict[str, set[str]] = {}
    for row in rows:
        name = str(row.get("workflowName", ""))
        if name not in REQUIRED:
            continue
        if row.get("status") != "completed" or row.get("conclusion") != "success":
            continue
        found.setdefault(str(row.get("headSha", ""))[:40], set()).add(name)
    return {sha: names for sha, names in found.items() if names >= set(REQUIRED)}


def static() -> list[tuple[str, bool, str]]:
    """The conditions Task 53 names that do not need the network, each measured.

    Written because the answer surprised me: every one of them is met except the status word
    itself. A reader who had been told "P0 is blocked" would have gone looking for work, and
    the work is one transition and one person's consent.
    """

    import hashlib
    import json
    import re

    sys.path.insert(0, str(ROOT / "src"))
    from ai_engineering import contract

    spec = ROOT / "specs" / "010-governed-agentic-engineering-foundation" / "spec.md"
    body = spec.read_text(encoding="utf-8")
    tree = contract.repo_lines(ROOT)
    slack = contract.REPO_CEILING - tree

    def status(path) -> str:
        found = re.search(r'(?m)^status:\s*"?(\w+)', path.read_text(encoding="utf-8"))
        return found.group(1) if found else "?"

    madrs = [next((ROOT / "docs" / "adr").glob(f"{one}-*.md")) for one in ("0005", "0006", "0007")]
    digest = hashlib.sha256(spec.read_bytes()).hexdigest()
    intent = (ROOT / ".ai" / "intent.md").read_text(encoding="utf-8")

    return [
        ("ceiling closed to zero slack", slack == 0, f"{contract.REPO_CEILING:,} against {tree:,}"),
        (
            "MADRs 0005, 0006 and 0007 accepted",
            all(status(one) == "accepted" for one in madrs),
            ", ".join(f"{one.name[:4]} {status(one)}" for one in madrs),
        ),
        (
            "spec 004 superseded",
            status(ROOT / "specs" / "004-solution-intent-home" / "spec.md") == "superseded",
            status(ROOT / "specs" / "004-solution-intent-home" / "spec.md"),
        ),
        ("the Intent names this spec digest", digest[:12] in intent, digest[:12]),
        ("spec 010 status is not draft", status(spec) != "draft", status(spec)),
    ]


def main(argv: list[str]) -> int:
    ask = argparse.ArgumentParser(description="Exact-HEAD workflow receipts, per commit.")
    ask.add_argument("--branch", default="ledger-and-records")
    ask.add_argument("--limit", type=int, default=100)
    args = ask.parse_args(argv)

    rows = runs(args.branch, args.limit)
    if not rows:
        # Not a pass and not a failure. A machine with no `gh`, or no authentication, has
        # observed nothing about this branch, and saying so is the whole of what it can say.
        print("  UNDECIDED: no run list was readable here, so no receipt was observed.")
        print("  This needs `gh` and an authenticated account; absence is not an answer.")
        return 0

    complete = proven(rows)
    print(f"  {len(rows)} run(s) listed on {args.branch}")
    print(
        f"  {len(complete)} commit(s) carry both {' and '.join(REQUIRED)} green at their own HEAD:"
    )
    for sha in sorted(complete):
        print(f"    {sha[:8]}")
    if not complete:
        print("    none — the live half of Task 53 cannot be satisfied from what is on record")
    print()
    print("  Task 53's static conditions, which need no network:")
    unmet = 0
    for what, met, detail in static():
        unmet += not met
        print(f"    {'met    ' if met else 'NOT MET'}  {what:36} {detail}")
    print(
        f"  {unmet} unmet. This reports and decides nothing: the transition itself is a "
        "person's, and so is the consent to push the commit that makes it."
    )
    print(f"RAN own_head={len(complete)} unmet={unmet}")
    return 0


if __name__ == "__main__":  # pragma: no cover — the entry point, run by a person
    sys.exit(main(sys.argv[1:]))
