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

Not in `just check`, and not a sentence either. It ran nowhere for as long as this file
said "run it when a guard's deny path changes, and before a release" — a judgement that
always comes out the same way, living in a docstring. It is a job in `check.yml` now, in
`ci-result`'s needs, with `anti_theatre` reading the `RAN guards=` line it prints so a
lane that stops running is a red rather than a silence.

Usage: python tests/mutation.py [-k <substring>]
"""

from __future__ import annotations

import ast
import hashlib
import os
import re
import signal
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
    ("hooks/chain.py", "re.fullmatch(m, tool", "re.match(m, tool", "a matcher that over-matches"),
    ("hooks/chain.py", "if not isinstance(body, dict):", "if False:", "an unreadable payload"),
    ("hooks/_wrap.py", "except BaseException", "except Exception", "a guard that crashes"),
    # The three that decide whether an action is allowed at all had no row between them, which
    # is the whole reason the old apparatus was aimed away from the target: a floor of 89 over
    # the package could move without any of these ever being touched. Each of these is a
    # boundary somebody could plausibly write wrong, in a file whose failure is silent.
    (
        "hooks/no_verify_guard.py",
        r"\bgit\b[^|;&]*\b(commit|push|merge|rebase|am)\b[^|;&]*--no-verify",
        r"\bgit\b[^|;&]*\bcommit\b[^|;&]*--no-verify",
        "--no-verify past a verb other than commit",
    ),
    (
        "hooks/self_protect.py",
        'if verb in WRITERS or (verb == "sed" and "-i" in words):',
        "if verb in WRITERS:",
        "sed -i as a writer",
    ),
    (
        "hooks/self_protect.py",
        "for match in REDIRECT.finditer(command):",
        "for match in []:",
        "a redirect aimed at a protected path",
    ),
    (
        "hooks/injection_guard.py",
        'text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")',
        "text = text",
        "the fold that stops a fullwidth letterform hiding a word",
    ),
    # Both rows named `accept.py`, and `accept.py` decides neither. Its `MAX_RENEWALS` has one
    # use — a line it prints — so mutating it measured a display string, and its copy of the
    # expiry comparison had already moved out from under the row, which is how the second one
    # came to name an edit the file no longer holds. `acceptance.py` is where a renewal is
    # refused and where an acceptance is called expired, so that is where the defects go.
    ("src/ai_engineering/acceptance.py", "MAX_RENEWALS = 2", "MAX_RENEWALS = 3", "renewals"),
    (
        "src/ai_engineering/acceptance.py",
        "e.expires < day",
        "e.expires <= day",
        "expiry, on the day itself",
    ),
    (
        "src/ai_engineering/audit.py",
        'prev = stored if isinstance(stored, str) else ""',
        "prev = prev",
        "the chain link",
    ),
    ("src/ai_engineering/spec.py", "max(used, default=0) + 1", "len(used) + 1", "spec numbering"),
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# The halves that can decide a row, cheapest first, and that order is the whole saving.
# Measured on a clean tree, per row: `tests/test_hooks.py` answers in 1.6 s and settles nine
# of the eleven guard rows; the adversarial run costs 12 s and settles one more; the whole
# suite costs 16 s to 115 s and settles the rest. `-x` is why a kill is cheap at any level —
# the expensive half only runs to the end for a mutant nothing catches, which is a red
# anyway. So there is no rule here about which file needs which half. There was, keyed on
# the `hooks/` prefix, and the measurement refused it: the adversarial suite kills three of
# the eleven guard rows and not eight, and the half that does the work is the guards' own
# test file. A list in cost order needs no such rule and cannot be wrong about a row.
HALVES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "guard tests",
        ("-m", "pytest", "-qx", "--no-header", "-p", "no:cacheprovider", "tests/test_hooks.py"),
    ),
    ("adversarial", (str(ROOT / "tests" / "adversarial" / "run.py"),)),
    ("the suite", ("-m", "pytest", "-qx", "--no-header", "-p", "no:cacheprovider")),
)

BLAME = ("MISSED", "NOT RUN", "FAILED", "E ", "ERROR", "INTERNALERROR", "!!!")
# And the case none of those catch, which the first attributed run found. Killing the mutant
# in `_wrap.py` means a `BaseException` reaching pytest, which reports it as a bare
# `KeyboardInterrupt` between bangs — so the only lines left were the banner and the summary,
# and the row printed "1 passed in 0.36s" as its reason for calling a mutant dead. A line
# naming an exception is a reason. A pass count is the opposite of one.
RAISED = re.compile(r"^[A-Za-z_][\w.]*(Error|Exception|Interrupt)\b")


def why(output: str) -> str:
    """The shortest line that says what went red, out of output that was being discarded."""
    lines = [line.strip(" !") for line in output.splitlines() if line.strip(" !")]
    for line in lines:
        if line.startswith(BLAME) or RAISED.match(line):
            return line[:100]
    return lines[-1][:100] if lines else "no output"


# Every half below runs over a tree with one mutant in it, and an interpreter that writes
# bytecode leaves that mutant in `__pycache__`. Python validates a cached file by the source's
# size and its modification time *in whole seconds*, and a one-token flip is the same length —
# `==` for `!=`, `Exception` for `BaseException` — so a mutant written and taken out again
# inside the same second leaves a cache that validates against the restored original. The
# source is then correct, `git diff` is empty, `digest()` below agrees, and the interpreter
# goes on running the mutant. Measured 2026-08-20: `import chain` exited 0 out of a clean
# worktree because the cached `if __name__ == "__main__"` had been flipped, and no test in the
# suite could run. A byte-identical clone was green, which is what proved the source innocent.
#
# So no child of this file writes bytecode. Purging afterwards would also work and is worse:
# it repairs a window rather than closing it, and the window is open for every mutant.
CLEAN_OF_BYTECODE = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def red(*command: str) -> str:
    """Empty when the command passed, and the line it failed on when it did not.

    `quiet()` was here and returned a bool over `capture_output=True`, so every byte that
    could say *why* was captured and thrown away. A mutant was then recorded as killed
    because something, somewhere, went red for thirteen seconds — a transient, an
    environment assertion, a ceiling — and no row could name the test that killed it. That
    is the same defect this file indicts in coverage: a number nobody can trace to a rule.
    """
    done = subprocess.run(
        list(command), cwd=ROOT, capture_output=True, text=True, env=CLEAN_OF_BYTECODE
    )
    return "" if done.returncode == 0 else why(done.stdout + done.stderr)


def killer(halves: tuple[tuple[str, tuple[str, ...]], ...] = HALVES) -> tuple[str, str]:
    """The first half to go red and the line it went red on; two empty strings when none did.

    Cheapest first and stop at the first red, because one red is the whole answer.
    """
    for name, argv in halves:
        line = red(sys.executable, *argv)
        if line:
            return name, line
    return "", ""


def unwind(*_: object) -> None:
    """Turn a termination signal into an exception, so the restore in `finally` still runs.

    Every mutant here is written into the real tree and taken out again by a `finally`, and
    `finally` unwinds on SIGINT because the interpreter raises. It does not unwind on SIGTERM
    or SIGHUP, which terminate the process where it stands — and a CI job timeout sends
    SIGTERM. The mutants are one-token edits nobody would spot in review: `except BaseException`
    becoming `except Exception` is the fail-open guard this product exists to prevent, and it
    would be sitting in a checkout where `git add -A` from any other session would stage it.

    SIGKILL and a power cut are still outside this. `restored()` below is what notices those.
    """
    raise SystemExit("mutation: terminated mid-mutant; the tree was restored on the way out")


def touched() -> str:
    """What git sees under the two trees this file edits, as bytes rather than as a verdict.

    Taken once before the first mutant and once after the last, and compared. The per-row
    sha256 already refuses a file that came back wrong, so this is the wider net: it catches
    a file this run left changed that no row names. Snapshotted rather than asserted empty,
    because a developer with honest uncommitted work under `hooks/` or `src/` must not be
    told they broke the harness.

    `status --porcelain` and not `diff`, and that is a finding rather than a preference. A
    run killed mid-mutant left `e.expires <= day` staged in `acceptance.py` while the working
    copy read correctly — the pre-commit gate had added the file while the mutant was live —
    so `git diff` was clean over a mutant one commit away from shipping. Porcelain shows both
    columns, which is the only view in which that state is visible at all.
    """
    done = subprocess.run(
        ["git", "status", "--porcelain", "--", "hooks/", "src/"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return done.stdout


def select(only: str) -> list[tuple[str, str, str, str]]:
    """The rows this run is about, chosen before anything is counted.

    The filter applies before anything is counted, and the score underneath it counts the
    selected rows: filter inside the loop and `just guards nothing` skips every row,
    appends no survivor, and prints "16 of 16 killed" while exiting 0. That is a green
    over zero mutants, which is the shape this repository exists to refuse, and it becomes
    load-bearing the moment a workflow passes a filter: one typo, or a rename of `hooks/`,
    and the gate measures nothing while reading exactly as it does now.
    """
    return [row for row in MUTANTS if not only or only in row[0] or only in row[3]]


def pristine(rows: list[tuple[str, str, str, str]]) -> str:
    """Empty when every selected row still names a real edit in a file no other run is inside.

    Checked before the baseline rather than at each row's turn, because the answer costs
    nothing and the alternative is two minutes of suite time before a refusal that was
    knowable at the start. It also tells the two cases apart. A row whose text simply moved
    is a row to fix; a file already holding this row's mutant is another run left inside this
    tree, which is not a thing to fix here — it is a thing to restore, and it happened: three
    guards and a record verb were found carrying live mutants from a run that had been killed,
    with the guard that refuses an unreadable payload reading `if False`.
    """
    for name, old, new, _ in rows:
        body = (ROOT / name).read_text(encoding="utf-8")
        if body.count(old) == 1:
            continue
        if old not in body and new in body:
            return (
                f"{name} already holds this row's mutant, so another run is inside this tree "
                f"or was killed in it. Restore it with `git checkout HEAD -- {name}` and read "
                "`git status` before measuring anything."
            )
        return (
            f"{name} does not hold {old!r} exactly once, so this row no longer names a real "
            "edit. Fix the row, not the count."
        )
    return ""


# ---------------------------------------------------------------- the generated half
#
# Sixteen defects a person chose answer "are the rules we thought of defended". They cannot
# answer "how much of this surface is defended at all", because their denominator is a
# judgement. This half generates its own denominator and scores against it.
#
# The surface is derived, never listed: whatever `chain.TABLE` routes to a blocking event,
# minus telemetry, plus the dispatcher and the wrapper every guard leaves through. A fifth
# blocking guard joins this measurement by being added to the one table it has to be added
# to anyway, so nobody can ship a guard and forget to score it.
FLOOR = 90

# Comparisons and branches only. No arithmetic, and no constants — deliberately, and it is
# what makes an exclusion register unnecessary. Mutating a numeric constant produces mostly
# equivalents (a slice at 80 or 81, a hash prefix at 16 or 17), and a denominator full of
# mutants nobody can kill forces either a register somebody maintains or a floor that lies.
# Two equivalents still get through — both early returns that turn out to be shortcuts — and
# a floor of 90 rather than 100 is what absorbs them.
FLIP = {
    "Lt": "<=",
    "LtE": "<",
    "Gt": ">=",
    "GtE": ">",
    "Eq": "!=",
    "NotEq": "==",
    "Is": "is not",
    "IsNot": "is",
    "In": "not in",
    "NotIn": "in",
}


def surface() -> list[Path]:
    sys.path.insert(0, str(ROOT / "hooks"))
    import chain

    blocking = {n for rows in chain.TABLE.values() for n, _ in rows} - set(chain.TELEMETRY)
    named = sorted(blocking) + ["chain", "_wrap"]
    found = [ROOT / "hooks" / f"{one}.py" for one in named]
    return [one for one in found if one.is_file()]


def spans(path: Path) -> list[tuple[str, int, int, int, str]]:
    """(kind, line, start, end, replacement) over the file's own text.

    The exact span the parser reports, never `ast.unparse`: unparsing drops every comment,
    and tests in this suite read guard source as text — a mutant killed because the comments
    vanished is a kill nobody earned, and an inflated numerator is the one failure a scorer
    must not have."""

    source = path.read_text(encoding="utf-8")
    starts = [0]
    for line in source.splitlines(True):
        starts.append(starts[-1] + len(line))
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            name = type(node.ops[0]).__name__
            if name not in FLIP:
                continue
            a = starts[node.left.end_lineno - 1] + node.left.end_col_offset
            b = starts[node.comparators[0].lineno - 1] + node.comparators[0].col_offset
            if "\n" in source[a:b]:
                continue
            found.append(("compare", node.lineno, a, b, f" {FLIP[name]} "))
        elif isinstance(node, ast.If) and not isinstance(node.test, ast.Constant):
            a = starts[node.test.lineno - 1] + node.test.col_offset
            b = starts[node.test.end_lineno - 1] + node.test.end_col_offset
            found.append(("branch", node.lineno, a, b, "False"))
    return sorted(set(found), key=lambda one: (one[1], one[2]))


def generated() -> int:
    """Score the derived surface, and refuse the floor rather than report under it."""

    killed, survivors = 0, []
    for path in surface():
        before = path.read_text(encoding="utf-8")
        was = digest(path)
        for kind, line, a, b, rep in spans(path):
            try:
                path.write_text(before[:a] + rep + before[b:], encoding="utf-8")
                half, said = killer()
            finally:
                path.write_text(before, encoding="utf-8")
            if digest(path) != was:
                sys.stderr.write(f"mutation: {path.name} was not restored. Check it.\n")
                return 1
            if half:
                killed += 1
            else:
                survivors.append(f"{path.name}:{line} {kind}")
            print(f"  {'killed  ' if half else 'SURVIVED'} {path.name}:{line} {kind}")
    total = killed + len(survivors)
    if not total:
        sys.stderr.write("mutation: the surface generated no mutants, which is not a pass.\n")
        return 1
    score = 100 * killed / total
    print(f"\n  {killed} of {total} generated mutants killed — {score:.1f}%, floor {FLOOR}")
    print(f"RAN generated={total}")
    for one in survivors:
        sys.stderr.write(f"  no test noticed: {one}\n")
    if score < FLOOR:
        sys.stderr.write(
            f"  {score:.1f}% is under the floor of {FLOOR}. Close a hole with a test. The "
            "floor only ever rises, and lowering it to fit the measurement is the defect "
            "the line ceiling was deleted for.\n"
        )
        return 1
    return 0


def main(only: str = "") -> int:
    for kill in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(kill, unwind)
    rows = select(only)
    if not rows:
        sys.stderr.write(f"mutation: no row names {only!r}, so nothing would be measured.\n")
        return 1
    leftover = pristine(rows)
    if leftover:
        sys.stderr.write(f"mutation: {leftover}\n")
        return 1
    half, line = killer()
    if half:
        sys.stderr.write(f"mutation: {half} is red before any mutant ({line}). Fix that first.\n")
        return 1
    survivors, opening = [], touched()
    for name, old, new, what in rows:
        path = ROOT / name
        before, was = path.read_text(encoding="utf-8"), digest(path)
        try:
            path.write_text(before.replace(old, new), encoding="utf-8")
            half, line = killer()
        finally:
            path.write_text(before, encoding="utf-8")
        if digest(path) != was:
            sys.stderr.write(f"mutation: {name} was not restored. Check it before committing.\n")
            return 1
        # The half and its line, because "killed" alone cannot tell a defended rule from
        # thirteen seconds of something unrelated being red.
        blame = f"  <- {half}: {line}" if half else ""
        print(f"  {'killed  ' if half else 'SURVIVED'} {name}  {what}{blame}")
        if not half:
            survivors.append(f"{name}: {old!r} -> {new!r} ({what})")

    print(f"\n  {len(rows) - len(survivors)} of {len(rows)} killed")
    # The line `tests/anti_theatre.py` reads as proof this ran at all. Without it the run
    # printed a sentence no reader in the repository matches, so a step that stopped
    # running — deleted, mis-filtered, renamed out from under its filter — was
    # indistinguishable from one that passed. That reader already refuses a count of zero;
    # until this line existed the writer simply never gave it one to refuse. Its own line,
    # nothing after the number: the pattern is anchored to the end of the line.
    print(f"RAN guards={len(rows)}")
    if touched() != opening:
        sys.stderr.write(
            "mutation: this run left hooks/ or src/ changed. Read `git diff` before "
            "anything commits it.\n"
        )
        return 1
    for line in survivors:
        sys.stderr.write(f"  no test noticed: {line}\n")
    if survivors:
        sys.stderr.write(
            "  A defect nothing caught is a rule with no test behind it. Write the test, "
            "or delete the rule and say so.\n"
        )
    if survivors:
        return 1
    # Only when the chosen defects all died: a generated score over a surface whose known
    # rules are already broken would be measuring the wrong thing first.
    return generated() if not only else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "-k" else ""))
