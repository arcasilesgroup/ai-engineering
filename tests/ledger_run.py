"""Run the answer key.

`docs/requirements.toml` names a command beside every requirement it calls PROVEN. Until
now nothing ran them. `tests/test_requirements_ledger.py` checks that each row *names* a
command of at least eight characters, which is a check on the shape of a sentence, not on
whether the sentence is true — so a row could name a test that was renamed, deleted or
never existed and the ledger would keep reporting it as proof.

That is the defect this repository exists to remove, sitting in the document that measures
this repository. A ledger nobody executes is a checklist a model reads back to itself.

This runner executes every command in every PROVEN row and reports what actually passed.
A row whose command fails is not a failing test — it is a *false verdict*, and the two
deserve different words, so the output says `FALSE PROVEN` rather than `FAIL`.

It is a runner rather than a pytest case for the same reason `tests/surface_receipt.py`
is: a receipt is evidence about a machine, produced by something that ran on it. It is
also far too slow for `just check` — two hundred subprocesses, most of them pytest — so it
belongs beside the mutation lane rather than in front of a commit.

It runs shell strings from a committed, reviewed file, deliberately. There is no way to
execute an answer key without executing what the answer key says, and the alternative —
parsing the commands into something safer — would be a second language nobody writes the
ledger in. What it will not do is run against an untracked file: the ledger is read
through `git show HEAD:` unless `--worktree` is passed, so an edit nobody committed cannot
quietly turn a red row green.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import shlex
import subprocess
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = "docs/requirements.toml"
RECEIPTS = ROOT / ".ai" / "receipts"
SCHEMA = "urn:ai-engineering:check-evidence:1"

# A week. The ledger changes when requirements close, not on every commit, so a run from
# this morning says as much as a run from ten minutes ago — but one from last month was
# measuring a different tree.
MAX_AGE = 604_800

# Long enough for the slowest single row (a full `just check` appears in two of them) and
# short enough that a command waiting on a terminal fails instead of hanging the run.
TIMEOUT = 900

WORKERS = 8

# The ledger's commands say `pytest`, which is the name they have inside the environment
# the gate builds — and `.venv` does not contain one, because `justfile` pins the engine
# with `uv run --with pytest==9.1.1` rather than installing it. The first version of this
# runner put `.venv/bin` on PATH, found somebody else's pytest, and reported a hundred and
# sixty rows as false verdicts when what had actually happened was `No module named 'rich'`.
#
# That is worth leaving written down: a runner that reports the wrong environment as a
# wrong answer is the same defect as a control that reads stronger than it is, pointed at
# the audit instead of at the product. So the commands run where the gate runs them.
ENGINE = "pytest==9.1.1"


def inside(command: str) -> str:
    """Put a ledger command in the environment `just check` would give it."""

    return f"uv run --with {ENGINE} sh -c {shlex.quote(command)}"


def stamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def ledger(worktree: bool) -> bytes:
    """Read the ledger from the commit unless asked for the working copy.

    Reading it from `HEAD` is what stops this from being self-certifying. An answer key
    somebody edited and did not commit is a claim about a file that exists on one machine.
    """

    if worktree:
        return (ROOT / LEDGER).read_bytes()
    done = subprocess.run(
        ["git", "show", f"HEAD:{LEDGER}"],
        capture_output=True,
        cwd=str(ROOT),
        check=False,
    )
    if done.returncode != 0:
        raise SystemExit(f"  REFUSED: {LEDGER} is not in HEAD: {done.stderr.decode()[:200]}")
    return done.stdout


def tree() -> str:
    """What git thinks is in the working tree, as one string.

    Running an answer key must not change the thing it is answering about. One row already
    does — `PO-17` writes a file and stages it to prove that whitespace is caught — so this
    is compared before and after and the difference is reported rather than cleaned up.
    Cleaning it up silently would be this runner deciding which of the operator's files it
    is allowed to delete.
    """

    done = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    return done.stdout


NOTHING_TO_RUN = "none — the requirement text could not be located"


def rows(payload: bytes, unproven: bool = False) -> list[dict[str, str]]:
    parsed = tomllib.loads(payload.decode("utf-8"))
    every = [*parsed.get("requirement", []), *parsed.get("commitment", [])]
    if not unproven:
        return [row for row in every if row.get("verdict") == "PROVEN"]
    # The other direction, and the one nothing had ever taken. A row graded not-proven still
    # names a command, and nobody had asked those commands what they say today — so a row
    # whose gap closed as a side effect of other work stayed not-proven until somebody
    # happened to re-read it. Three have already been found that way by hand, each after its
    # own note had gone stale without anybody noticing.
    #
    # A pass here is a candidate and never a verdict. These commands were written to check
    # the half that existed, so one passing means the half it checks still holds, not that
    # the requirement is met. Promoting a row is a reading; this only says which rows are
    # worth re-reading.
    return [
        row
        for row in every
        if row.get("verdict") != "PROVEN"
        and row.get("evidence", "").strip() not in ("", NOTHING_TO_RUN)
    ]


def run_one(row: dict[str, str]) -> tuple[str, bool, str]:
    command = row["evidence"].strip()
    try:
        done = subprocess.run(  # noqa: S602 — the ledger is a list of commands; see the docstring
            inside(command),
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return row["id"], False, f"no answer in {TIMEOUT}s"
    if done.returncode == 0:
        return row["id"], True, ""
    tail = (done.stderr or done.stdout).strip().splitlines()
    return row["id"], False, (tail[-1] if tail else f"exit {done.returncode}")[:160]


def main(argv: list[str]) -> int:
    ask = argparse.ArgumentParser(description="Run every command the ledger calls proof.")
    ask.add_argument("--worktree", action="store_true", help="read the ledger from disk, not HEAD")
    ask.add_argument("--only", default="", help="run one id, for checking a single row")
    ask.add_argument(
        "--unproven",
        action="store_true",
        help="run the rows graded not-proven and list the ones whose command passes today",
    )
    args = ask.parse_args(argv)

    payload = ledger(args.worktree)
    todo = rows(payload, unproven=args.unproven)
    if args.only:
        todo = [row for row in todo if row["id"] == args.only]
        if not todo:
            print(f"  REFUSED: {args.only} is not a PROVEN row in {LEDGER}.")
            return 1

    before = tree()
    started = stamp()
    answers: list[tuple[str, bool, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for answer in pool.map(run_one, todo):
            answers.append(answer)
            mark = "." if answer[1] else "x"
            print(mark, end="", flush=True)
    print()
    finished = stamp()

    if args.unproven:
        # Inverted on purpose: here a pass is the interesting answer, because it means a row
        # graded not-proven names a command that holds today. It exits zero either way. This
        # is a question, not a gate, and a question that fails a build teaches people to stop
        # asking it.
        moved = sorted(rid for rid, passed, _ in answers if passed)
        print(f"  RAN unproven={len(answers)}  command holds={len(moved)}")
        for rid in moved:
            print(f"    RE-READ  {rid}")
        print("  A command that passes proves the half it checks, not the requirement.")
        return 0

    false_proven = [(rid, why) for rid, passed, why in answers if not passed]
    for rid, why in sorted(false_proven):
        print(f"  FALSE PROVEN  {rid}  {why}")

    passed = len(answers) - len(false_proven)
    print(f"  RAN rows={len(answers)}  held={passed}  false={len(false_proven)}")

    after = tree()
    if after != before:
        print("  LEFT BEHIND: running the answer key changed the working tree.")
        for line in sorted(set(after.splitlines()) - set(before.splitlines())):
            print(f"    {line}")
        print("  Nothing was cleaned up. Decide what to do with these before believing the run.")

    if false_proven:
        print("  No receipt written. A receipt over an answer key that did not answer is the")
        print("  artefact this product exists to prevent.")
        return 1

    RECEIPTS.mkdir(parents=True, exist_ok=True)
    where = RECEIPTS / "ledger-run.json"
    where.write_text(
        json.dumps(
            {
                "schema": SCHEMA,
                "schema_version": "1",
                "kind": "automated",
                "id": "ledger-run",
                "applicability": "applicable",
                "command": "python tests/ledger_run.py",
                "tool_version": f"ledger rows={len(answers)}",
                # The ledger's own bytes. A receipt that survived an edit to the answer key
                # would be a receipt about a question nobody is asking any more.
                "input_digest": digest(payload),
                "artifact_digest": digest(f"held={passed}".encode()),
                "started_at": started,
                "finished_at": finished,
                "max_age_seconds": MAX_AGE,
                "outcome": "PASS",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"  receipt: {where.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":  # pragma: no cover — the entry point, exercised by the lane
    sys.exit(main(sys.argv[1:]))
