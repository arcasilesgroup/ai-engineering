"""Every test a commit added, run against the code from before that commit.

`PO-12` asks that a commit's focal test fail before the change and pass after it. Nothing
has ever checked, and the audit's note said why: confirming it would mean two checkouts and
a targeted run per task, up to fifty-three times. That is a description of a script.

The check is the strongest one available about a test, and the only one that answers the
question a green suite cannot: *did this test need the change?* A test that passes against
the code from before the commit that introduced it proved nothing about that commit. It may
still be a good test of something — but it is not evidence for the change it shipped with,
and the commit message that cited it was citing a result it would have got anyway.

The failure it looks for is the whole point, so the two kinds are reported apart. A test
that runs and fails is a test that measured behaviour. A test that cannot even be collected
against the old source — because it names something that did not exist yet — is also red,
and honestly so, but it proves the symbol arrived rather than that the behaviour changed.

Each commit is examined in its own worktree, so nothing here can touch the tree somebody is
working in. The old source is laid over the new tests with `git checkout <parent> -- src
hooks`, which is the shape of the question: this commit's tests, last commit's product.
"""

from __future__ import annotations

import argparse
import ast
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The halves of the tree. `src` and `hooks` are the product; everything else — the policy
# tables, the skills, the workflows — is data or documentation that a test may legitimately
# read at either version without the question changing.
PRODUCT = ("src", "hooks")

ADDED_TEST = re.compile(r"^\+def (test_[A-Za-z0-9_]+)", re.MULTILINE)

# The one piece of product state that is bookkeeping rather than behaviour.
BOOKKEEPING = "REPO_CEILING"


def _is_bookkeeping(statement: ast.stmt) -> bool:
    return isinstance(statement, ast.Assign) and any(
        isinstance(target, ast.Name) and target.id == BOOKKEEPING for target in statement.targets
    )


ENGINE = "pytest==9.1.1"

# Long enough for the slowest module suite, short enough that a test waiting on a terminal
# fails rather than holding the run.
TIMEOUT = 600


def git(*args: str, cwd: Path | None = None) -> str:
    done = subprocess.run(
        ["git", *args], capture_output=True, text=True, cwd=str(cwd or ROOT), check=False
    )
    if done.returncode != 0:
        raise SystemExit(f"  REFUSED: git {' '.join(args)} failed: {done.stderr.strip()[:200]}")
    return done.stdout


def commits(since: str, last: int) -> list[str]:
    every = git("log", "--format=%H", "--reverse", f"{since}..HEAD").split()
    return every[-last:] if last else every


def added_tests(commit: str) -> dict[str, list[str]]:
    """Which test functions this commit introduced, per file.

    Modified tests are deliberately out of scope. A test whose body changed may have been
    tightened, loosened or moved, and asking whether *it* was red before the commit answers
    about a function that did not have this shape then. Added ones have no such ambiguity.
    """

    found: dict[str, list[str]] = {}
    files = [
        name
        for name in git("diff", "--name-only", f"{commit}^", commit, "--", "tests/").split()
        if name.endswith(".py") and Path(name).name.startswith("test_")
    ]
    for name in files:
        patch = git("diff", "-U0", f"{commit}^", commit, "--", name)
        names = ADDED_TEST.findall(patch)
        if names:
            found[name] = names
    return found


def _shape(source: str) -> str | None:
    """A module's code with every docstring and every comment gone.

    Read with `ast` rather than by matching lines, because the first version of this did
    match lines and flagged a commit whose entire product diff was the second and later
    lines of a docstring. A regex sees `#` at the start of a line; it cannot see that a
    string literal is the first statement in a function, which is the only thing that makes
    it a docstring. Comments never reach the tree at all, so nothing has to remove them.
    """

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        first = body[0] if body else None
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            node.body = body[1:] or [ast.Pass()]
    # And the ceiling, which is a number about the tree's size rather than about what the
    # tree does. Every commit that adds a line moves it, so leaving it in would make every
    # commit a behaviour change and this runner would demand red from all of them.
    tree.body = [statement for statement in tree.body if not _is_bookkeeping(statement)]
    return ast.dump(tree)


def changed_behaviour(commit: str) -> bool:
    """Did this commit change what the product does, or only what it says about itself?

    The distinction decides whether red is owed. A commit that adds tests over unchanged
    code is a characterisation commit — its tests are *supposed* to pass at the parent, and
    what proves them is the mutation score, not this. Calling that "proved nothing" would be
    this runner telling the truth in words that mean the opposite.

    In a repository where the comments outnumber the code, that distinction cannot be drawn
    by reading the diff. It is drawn by parsing both versions of every product file the
    commit touched and comparing what is left once the prose is gone.
    """

    names = git("diff", "--name-only", f"{commit}^", commit, "--", *PRODUCT).split()
    for name in names:
        if not name.endswith(".py"):
            return True
        try:
            after = git("show", f"{commit}:{name}")
        except SystemExit:
            return True  # deleted here, which is a change by any reading
        try:
            before = git("show", f"{commit}^:{name}")
        except SystemExit:
            return True  # new here
        one, two = _shape(before), _shape(after)
        if one is None or two is None or one != two:
            return True
    return False


def examine(commit: str, area: Path) -> tuple[str, str]:
    """Lay the parent's product under this commit's tests and see what happens."""

    subject = git("log", "-1", "--format=%s", commit).strip()
    tests = added_tests(commit)
    if not tests:
        return "NO TESTS ADDED", subject
    if not changed_behaviour(commit):
        count = sum(len(ones) for ones in tests.values())
        return f"PINS: {count} tests over unchanged behaviour, so red is not owed", subject

    tree = area / commit[:8]
    git("worktree", "add", "--detach", "-q", str(tree), commit)
    try:
        git("checkout", f"{commit}^", "--", *PRODUCT, cwd=tree)
        selected = [f"{name}::{one}" for name, ones in tests.items() for one in ones]
        done = subprocess.run(
            [
                "uv",
                "run",
                "--with",
                ENGINE,
                "pytest",
                "-q",
                "--no-header",
                "-p",
                "no:cacheprovider",
                *selected,
            ],
            capture_output=True,
            text=True,
            cwd=str(tree),
            timeout=TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return f"NO ANSWER in {TIMEOUT}s over {sum(map(len, tests.values()))} tests", subject
    finally:
        git("worktree", "remove", "--force", str(tree))

    count = sum(len(ones) for ones in tests.values())
    if done.returncode == 0:
        return f"PROVED NOTHING: {count} tests pass without the change", subject
    if "error" in done.stdout.lower() and " failed" not in done.stdout:
        return f"RED, by absence: {count} tests name something that did not exist yet", subject
    return f"RED: {count} tests fail against the old source", subject


def main(argv: list[str]) -> int:
    ask = argparse.ArgumentParser(description="Run each commit's new tests against its parent.")
    ask.add_argument("--since", default="main", help="the ref this branch left")
    ask.add_argument("--last", type=int, default=0, help="only the newest N commits")
    args = ask.parse_args(argv)

    if shutil.which("uv") is None:
        print("  SKIPPED: no uv here, so the pinned engine cannot be built.")
        return 0

    proved_nothing = []
    with tempfile.TemporaryDirectory() as area:
        for commit in commits(args.since, args.last):
            verdict, subject = examine(commit, Path(area))
            print(f"  {commit[:8]}  {verdict}")
            print(f"            {subject[:96]}")
            if verdict.startswith("PROVED NOTHING"):
                proved_nothing.append((commit[:8], subject))

    if proved_nothing:
        print()
        for commit, subject in proved_nothing:
            print(f"  PROVED NOTHING  {commit}  {subject[:80]}")
        print("  A test that passes against the code from before its own commit is not")
        print("  evidence for that commit. It may be a fine test of something else.")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover — the entry point, exercised by the lane
    sys.exit(main(sys.argv[1:]))
