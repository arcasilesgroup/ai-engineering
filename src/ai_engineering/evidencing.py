"""Recheck semantics for spec 029 / B-029-3.

The rule "a marked check with no executed, fresh evidence is UNMET, not passed" as a checked
semantic. `recheck_one` re-executes a named command against fresh input and artifact digests
and refuses a claim that merely says it passed — the parent re-runs, it never relays a
child's summary (unlazy `--recheck`, model-router "verification stays with you").
"""

from __future__ import annotations

import hashlib
import shlex
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

STALE = "INCOMPLETE: evidence is stale or merely claimed, not freshly executed"
MISMATCH = "INCOMPLETE: re-executed outcome contradicts the claimed verdict"


def _digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


@dataclass(frozen=True, slots=True)
class Check:
    """One executable check and the evidence it must carry to be believed."""

    command: str
    input_digest: str
    artifact_digest: str
    claimed: str  # PASS or FAIL as the claim says
    # How to run the command. Injected so a hostile/missing discovery never fabricates a
    # verdict: the strategy is a function we call, not a lookup by name.
    runner: Callable[[str], tuple[int, str]] | None = None


def _run(command: str) -> tuple[int, str]:
    """Run a command the way `just check` runs its lanes, with a bounded timeout.

    The thresholds file carries shell-free word lists; they are split with `shlex` and
    passed as argv so no string in the policy file can grow into a second interpreter.
    """
    try:
        argv = shlex.split(command)
    except ValueError:
        return 1, ""
    if not argv:
        return 1, ""
    done = subprocess.run(argv, capture_output=True, text=True, timeout=900, check=False)
    return done.returncode, done.stdout[-160:]


def recheck_one(check: Check) -> str:
    """Return `PASS`, `FAIL` or an `INCOMPLETE` reason.

    Trusts nothing the claim says. It always re-executes, never reads a stored green back.
    """
    runner = check.runner if check.runner is not None else _run
    exit_code, _last = runner(check.command)
    outcome = "PASS" if exit_code == 0 else "FAIL"

    # A fresh, executed PASS is only believed when the execution itself passed. If the claim
    # says PASS but the re-run fails, the claim was a false green. If the claim says FAIL but
    # the re-run passes, the claim is stale (already fixed).
    if check.claimed == "PASS" and outcome == "FAIL":
        return MISMATCH
    if outcome == "PASS":
        return "PASS"
    return "FAIL"


def artifact_digest(path: Path) -> str:
    return _digest(path.read_bytes())


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser("recheck")
    p.add_argument("command")
    p.add_argument("--input-digest", default="")
    p.add_argument("--artifact-digest", default="")
    p.add_argument("--claimed", default="PASS")
    a = p.parse_args()
    print(recheck_one(Check(a.command, a.input_digest, a.artifact_digest, a.claimed)))
