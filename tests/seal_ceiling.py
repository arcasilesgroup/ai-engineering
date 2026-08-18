"""Close `REPO_CEILING` onto the tree, resolving the fixed point the number creates.

The ceiling counts every committed line and it is itself a committed line, so writing a new
value changes the thing the value describes. Measure 77,700, write it, and the tree holds
77,700 only if the edit happened to be exactly as wide as the one it replaced. It never is.

Every commit in this session therefore cost the same manual dance — stage, measure, write,
measure again, adjust, gate — three or four calls where the arithmetic is fixed and a person
was doing it by hand fifty times a day. This is that arithmetic.

It converges in two or three passes, because each rewrite changes the file by at most a few
characters. It refuses rather than looping, and refuses rather than guessing: a ceiling that
will not settle means something else is writing to the tree while this runs, and a number
taken during that is a number about neither state.

    python tests/seal_ceiling.py            # close it onto the tree
    python tests/seal_ceiling.py --check    # say whether it is closed; write nothing
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "ai_engineering" / "contract.py"
PINNED = ROOT / "tests" / "test_contracts.py"

# Two or three is what convergence takes. Ten means something else is writing.
MAX_PASSES = 10


def measured() -> int:
    sys.path.insert(0, str(ROOT / "src"))
    from ai_engineering import contract

    return contract.repo_lines(ROOT)


def written() -> int:
    found = re.search(r"(?m)^REPO_CEILING = ([0-9_]+)$", SOURCE.read_text(encoding="utf-8"))
    if found is None:
        raise SystemExit("  REFUSED: contract.py holds no REPO_CEILING to close")
    return int(found.group(1).replace("_", ""))


def rewrite(value: int) -> None:
    spelled = f"{value:_}"
    body = SOURCE.read_text(encoding="utf-8")
    SOURCE.write_text(
        re.sub(r"(?m)^REPO_CEILING = [0-9_]+$", f"REPO_CEILING = {spelled}", body),
        encoding="utf-8",
    )
    # The suite pins the number as well, deliberately: a ceiling that moved without anybody
    # noticing is the thing it exists to prevent. Both homes move together or the gate reds.
    pinned = PINNED.read_text(encoding="utf-8")
    PINNED.write_text(
        re.sub(r"contract\.REPO_CEILING == [0-9_]+", f"contract.REPO_CEILING == {spelled}", pinned),
        encoding="utf-8",
    )
    _forget(SOURCE)
    _forget(PINNED)


def _forget(source: Path) -> None:
    """Drop the compiled copy of a file this script just rewrote.

    CPython decides a `.pyc` is current from the source's modification time *and its size*,
    and this script's edit is almost always the same size — `77_870` and `77_889` are the
    same number of bytes. Two writes inside one clock second with an unchanged length are
    therefore invisible to that check, and the next process imports the old constant while
    the file on disk holds the new one.

    That is not hypothetical: it cost an hour here. The gate reported a ceiling of 77,870
    against a tree of 77,889 while `grep` on the same file printed 77,889, and every
    explanation reached for — a stale wheel, a mutation run rewriting the tree, a second
    install on the path — was wrong. A control that reads a number nobody can see is worse
    than one that fails, so the cache entry goes rather than the trust in it."""

    for cached in (source.parent / "__pycache__").glob(f"{source.stem}.*.pyc"):
        cached.unlink(missing_ok=True)


def stage() -> None:
    # `contract.repo_lines` reads the index, so an unstaged file is a file it cannot see —
    # which is how a run reports a number smaller than the tree it is about to gate.
    subprocess.run(["git", "add", "-A"], cwd=str(ROOT), check=True)


def main(argv: list[str]) -> int:
    ask = argparse.ArgumentParser(description="Close the line ceiling onto the tree.")
    ask.add_argument("--check", action="store_true", help="report only; write nothing")
    args = ask.parse_args(argv)

    stage()
    if args.check:
        now, held = measured(), written()
        if now == held:
            print(f"  PASS  the ceiling is closed onto the tree at {held:,}")
            return 0
        print(f"  FAIL  the tree holds {now:,} lines against a ceiling of {held:,}")
        print("  Next action: run `just seal`, then read the diff before committing it.")
        return 1

    started = written()
    for _ in range(MAX_PASSES):
        stage()
        now = measured()
        if now == written():
            moved = "unchanged" if now == started else f"{started:,} to {now:,}"
            print(f"  RAN ceiling={now:,}  ({moved})")
            return 0
        rewrite(now)
    print(f"  REFUSED: the ceiling did not settle in {MAX_PASSES} passes.")
    print("  Something else is writing to this tree; a number taken now is about neither state.")
    return 1


if __name__ == "__main__":  # pragma: no cover — the entry point, exercised by the gate
    sys.exit(main(sys.argv[1:]))
