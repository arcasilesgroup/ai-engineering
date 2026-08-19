#!/usr/bin/env python3
"""Which review lens a diff routes to, computed rather than remembered.

`EP-251` asks that the motion lens load only where the diff carries real motion. The lens
says so in its own first paragraph, and so does the frontend one; the other eight say
nothing. So a reader could not tell a lens that is always worked from one that is
conditional, and nothing computed the difference — which made `ai-review` step 3, "skip a
lens the diff cannot touch and name the one you skipped", an instruction with nothing to
check the naming against.

`policy/review-lenses.toml` is the rule and this is the reader. Given a range it prints the
lenses that apply and the lenses that do not, each with the reason from the table, so a
reviewer's report can be read against a list somebody else can reproduce.

It never decides that a lens is unnecessary. A lens that does not apply is one the reviewer
should say they skipped; the difference between that and silently not working it is the whole
of what this closes.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "policy" / "review-lenses.toml"
LENSES = ROOT / ".agents" / "skills" / "ai-review" / "references"


def table() -> list[dict]:
    return tomllib.loads(TABLE.read_text(encoding="utf-8"))["lens"]


def shape(rows: list[dict]) -> list[str]:
    """Every way this table is not a rule. A lens with neither `always` nor `when` is a lens
    somebody has to guess about, and one with both is two rules disagreeing."""

    wrong = []
    on_disk = {path.name for path in LENSES.glob("*.md")}
    named = {str(row.get("file", "")) for row in rows}
    for missing in sorted(on_disk - named):
        wrong.append(f"{missing} is a lens with no row, so nothing says when it loads")
    for absent in sorted(named - on_disk):
        wrong.append(f"a row names {absent}, which is not in {LENSES.relative_to(ROOT)}")
    for row in rows:
        name = row.get("id", "<unnamed>")
        if bool(row.get("always")) == bool(row.get("when")):
            wrong.append(f"{name} is both always and conditional, or neither")
        if len(str(row.get("why", "")).strip()) < 20:
            wrong.append(f"{name} does not say why it loads when it does")
    return wrong


def changed(base: str) -> tuple[list[str], str]:
    """The names and the added lines of a range, which is everything the rules read."""

    names = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    ).stdout.split()
    patch = subprocess.run(
        ["git", "diff", "--unified=0", f"{base}...HEAD"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    ).stdout
    added = "\n".join(
        line[1:]
        for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    return names, added


def routes(row: dict, names: list[str], added: str) -> bool:
    """Does this lens load for this change?

    Paths first, then content where the row asks for it. Both halves must match: a stylesheet
    is a frontend change whether or not it animates, and the motion row is the reason the
    content half exists at all.
    """

    if row.get("always"):
        return True
    rule = row.get("when") or {}
    paths = [one for one in rule.get("paths", []) if one]
    if paths and not any(mark in name for name in names for mark in paths):
        return False
    content = [one for one in rule.get("content", []) if one]
    if content and not any(mark.casefold() in added.casefold() for mark in content):
        return False
    return bool(paths or content)


def main(argv: list[str]) -> int:
    ask = argparse.ArgumentParser(description="Which review lens this range routes to.")
    ask.add_argument("--base", default="main", help="the ref this branch left")
    args = ask.parse_args(argv)

    rows = table()
    broken = shape(rows)
    if broken:
        for line in broken:
            print(f"  {line}", file=sys.stderr)
        return 1

    names, added = changed(args.base)
    if not names:
        print(f"  no file differs from {args.base}, so this routed nothing.")
        return 0

    loads = [row for row in rows if routes(row, names, added)]
    skips = [row for row in rows if row not in loads]
    print(f"  {len(names)} file(s) changed against {args.base}")
    print(f"  {len(loads)} of {len(rows)} lenses load:")
    for row in loads:
        print(f"    load  {row['id']:15} {row['why'][:88]}")
    print(f"  {len(skips)} do not, and a report that does not name them is incomplete:")
    for row in skips:
        print(f"    skip  {row['id']:15} {row['why'][:88]}")
    print(f"RAN lenses={len(rows)}")
    return 0


if __name__ == "__main__":  # pragma: no cover — the entry point, exercised by the lane
    sys.exit(main(sys.argv[1:]))
