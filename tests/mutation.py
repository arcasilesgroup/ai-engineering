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
        "src/ai_engineering/contract.py",
        "if len(lines) > CEILING:",
        "if len(lines) >= CEILING:",
        "the skill cap",
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


# The two halves that can decide a row, cheapest first. Named, because a bare boolean
# cannot say which one said no — and a floor of 100 is worth exactly what the attribution
# behind each kill is worth.
HALVES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("adversarial", (str(ROOT / "tests" / "adversarial" / "run.py"),)),
    ("pytest", ("-m", "pytest", "-qx", "--no-header", "-p", "no:cacheprovider")),
)

# What a half's output looks like when it is the thing that said no. `tests/adversarial/run.py`
# prints `MISSED` for a guard that did not fire and `NOT RUN` for a case that raised before
# reaching a verdict; pytest prints `FAILED` and `E   `. Anything else falls back to the last
# line, which is wrong less often than printing nothing.
BLAME = ("MISSED", "NOT RUN", "FAILED", "E ", "ERROR")


def why(output: str) -> str:
    """The shortest line that says what went red, out of output that was being discarded."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    for line in lines:
        if line.startswith(BLAME):
            return line[:100]
    return lines[-1][:100] if lines else "no output"


def red(*command: str) -> str:
    """Empty when the command passed, and the line it failed on when it did not.

    `quiet()` was here and returned a bool over `capture_output=True`, so every byte that
    could say *why* was captured and thrown away. A mutant was then recorded as killed
    because something, somewhere, went red for thirteen seconds — a transient, an
    environment assertion, a ceiling — and no row could name the test that killed it. That
    is the same defect this file indicts in coverage: a number nobody can trace to a rule.
    """
    done = subprocess.run(list(command), cwd=ROOT, capture_output=True, text=True)
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
    """
    done = subprocess.run(
        ["git", "diff", "--", "hooks/", "src/"], cwd=ROOT, capture_output=True, text=True
    )
    return done.stdout


def select(only: str) -> list[tuple[str, str, str, str]]:
    """The rows this run is about, chosen before anything is counted.

    The filter used to live inside the loop as a `continue`, and the score underneath it
    counted `MUTANTS` — so `just guards nothing` skipped every row, appended no survivor,
    printed "16 of 16 killed" and exited 0. That is a green over zero mutants, which is
    the shape this repository exists to refuse, and it becomes load-bearing the moment a
    workflow passes a filter: one typo, or a rename of `hooks/`, and the gate measures
    nothing while reading exactly as it does now.
    """
    return [row for row in MUTANTS if not only or only in row[0] or only in row[3]]


def main(only: str = "") -> int:
    for kill in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(kill, unwind)
    rows = select(only)
    if not rows:
        sys.stderr.write(f"mutation: no row names {only!r}, so nothing would be measured.\n")
        return 1
    half, line = killer()
    if half:
        sys.stderr.write(f"mutation: {half} is red before any mutant ({line}). Fix that first.\n")
        return 1
    survivors, opening = [], touched()
    for name, old, new, what in rows:
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
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "-k" else ""))
