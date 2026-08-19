#!/usr/bin/env python3
"""Break the product on purpose, and fail if nothing notices.

Coverage says a line ran. It never says anything would have noticed the line being wrong,
and this repository has the receipt: a guard measured at 89% whose only rule had never
fired once. So the number that means something is this one — how many deliberate defects
the suite catches — and it is a number, so it is a script and not a paragraph.

mutmut was tried first and cannot run this tree. It copies `source_paths` and the tests
into a `mutants/` sandbox and runs pytest there, while this suite reads `hooks/*.py` by
path, `.agents/skills/`, `policy/surfaces.toml` and `git-hooks/` — none of which the
sandbox contains. Every one is a test deselected during the run that exists to judge the
tests. It also never completed a run here, so whether it exits non-zero on a survivor is
a thing nobody has observed, and that is the whole question a gate asks.

Not in `just check`: one mutant costs a full suite run. Run it when a guard's deny path
changes, and before a release.

Usage: python tests/mutation.py [-k <substring>]
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Each row is a defect somebody could actually write, and the boundary or constant it
# lands on. That is not a style preference: of the thirteen mutants that survived the
# first pass over this suite, almost every one was a boundary or a constant, because a
# test written for the far side of a rule never visits its edge.
MUTANTS: list[tuple[str, str, str, str]] = [
    ("hooks/loop_guard.py", "if seen >= repeats:", "if seen > repeats:", "the repeat cap"),
    ("hooks/loop_guard.py", "REPEATS = 3", "REPEATS = 4", "how many repeats are a loop"),
    ("hooks/loop_guard.py", "[-60:]", "[:60]", "which end of a path discriminates it"),
    ("hooks/loop_guard.py", "FAILURES = 5", "FAILURES = 6", "how many failures are a wall"),
    ("hooks/change_scope_guard.py", "BUDGET = 3", "BUDGET = 4", "the fourth file trips the gate"),
    (
        "hooks/change_scope_guard.py",
        "if len(files) <= budget:",
        "if len(files) < budget:",
        "its edge",
    ),
    ("hooks/chain.py", "re.fullmatch(m, tool", "re.match(m, tool", "a matcher that over-matches"),
    ("hooks/chain.py", "if not isinstance(body, dict):", "if False:", "an unreadable payload"),
    ("hooks/_wrap.py", "except BaseException", "except Exception", "a guard that crashes"),
    ("src/ai_engineering/accept.py", "MAX_RENEWALS = 2", "MAX_RENEWALS = 3", "renewals"),
    ("src/ai_engineering/accept.py", '"")) < today', '"")) <= today', "expiry, on the day"),
    (
        "src/ai_engineering/contract.py",
        "if len(lines) > CEILING:",
        "if len(lines) >= CEILING:",
        "the skill cap",
    ),
    (
        "src/ai_engineering/audit.py",
        'prev = event.get("hash", "")',
        "prev = prev",
        "the chain link",
    ),
    ("src/ai_engineering/spec.py", "max(used, default=0) + 1", "len(used) + 1", "spec numbering"),
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quiet(*command: str) -> bool:
    return subprocess.run(list(command), cwd=ROOT, capture_output=True).returncode == 0


def run_suite() -> bool:
    """Both halves, in the order that costs least, and the cheap one is the adversarial run.
    pytest alone leaves every guard threshold alive: the budgets and the windows are only
    ever crossed by the adversarial suite, which pytest does not collect — the first run of
    this file said so, six survivors in the two guards whose edges live over there.

    A mutant is killed when either half goes red, so this is a conjunction and swapping its
    two sides cannot change an answer, only the bill. It used to run pytest first, above a
    docstring that already claimed the opposite; thirteen seconds now decide most rows
    before sixty are spent on them. -x because one red is the whole answer."""
    fast = quiet(sys.executable, str(ROOT / "tests" / "adversarial" / "run.py"))
    return fast and quiet(
        sys.executable, "-m", "pytest", "-qx", "--no-header", "-p", "no:cacheprovider"
    )


def main(only: str = "") -> int:
    if not run_suite():
        sys.stderr.write("mutation: the suite is red before any mutant. Fix that first.\n")
        return 1
    survivors = []
    for name, old, new, what in MUTANTS:
        if only and only not in name and only not in what:
            continue
        path = ROOT / name
        before, was = path.read_text(encoding="utf-8"), digest(path)
        if before.count(old) != 1:
            sys.stderr.write(
                f"mutation: {name} does not hold {old!r} exactly once, so this row no "
                f"longer names a real edit. Fix the row, not the count.\n"
            )
            return 1
        try:
            path.write_text(before.replace(old, new), encoding="utf-8")
            killed = not run_suite()
        finally:
            path.write_text(before, encoding="utf-8")
        if digest(path) != was:
            sys.stderr.write(f"mutation: {name} was not restored. Check it before committing.\n")
            return 1
        print(f"  {'killed  ' if killed else 'SURVIVED'} {name}  {what}")
        if not killed:
            survivors.append(f"{name}: {old!r} -> {new!r} ({what})")

    print(f"\n  {len(MUTANTS) - len(survivors)} of {len(MUTANTS)} killed")
    for line in survivors:
        sys.stderr.write(f"  no test noticed: {line}\n")
    if survivors:
        sys.stderr.write(
            "  A defect nothing caught is a rule with no test behind it. Write the test, "
            "or delete the rule and say so.\n"
        )
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "-k" else ""))
