"""One scanner lane, and the five ways it can report nothing without having looked.

A missing engine, missing rules, a crash, a timeout and zero inputs all produce the same
thing on a terminal: no findings. Every one of them is a way for a green to mean the
opposite of what it says, so each one is INCOMPLETE here and each one has its own fixture.

PASS is reachable exactly one way: an engine that was there, with its rules, ran to
completion over inputs that existed, and found nothing.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering import outcome

MISSING_ENGINE = "LANE_ENGINE_MISSING"
MISSING_RULES = "LANE_RULES_MISSING"
TAMPERED_RULES = "LANE_RULES_TAMPERED"
CRASHED = "LANE_CRASHED"
TIMEOUT = "LANE_TIMEOUT"
NO_INPUTS = "LANE_NO_INPUTS"

DEFAULT_TIMEOUT = 120


@dataclass(frozen=True, slots=True)
class Lane:
    """One engine, its argument list, and the two things that decide how to read it: which
    exit code means "found something", and how long it may take."""

    id: str
    argv: tuple[str, ...]
    rules: Path | None = None
    rules_digest: str = ""
    findings_exit: int = 1
    timeout: int = DEFAULT_TIMEOUT
    extra: tuple[str, ...] = field(default=())


def _incomplete(lane: Lane, code: str, why: str, cure: str) -> outcome.Fact:
    return outcome.fact(
        f"lane-{lane.id}", "INCOMPLETE", f"The {lane.id} lane", f"{code}: {why}", cure=cure
    )


def run(lane: Lane, root: Path, inputs: list[str]) -> outcome.Fact:
    """Run one lane over one list of inputs and say what it observed.

    The order matters. Inputs are checked before the engine is started, because a lane with
    nothing to scan is not a lane that scanned; and the rules are checked before the exit
    code is read, because an engine with no rules exits zero having looked for nothing.
    """

    if not inputs:
        return _incomplete(
            lane,
            NO_INPUTS,
            "there was nothing to scan, so nothing was scanned",
            "point the lane at files that exist, or say why this stack has none",
        )
    if lane.rules is not None:
        where = Path(root) / lane.rules if not Path(lane.rules).is_absolute() else Path(lane.rules)
        if not where.is_file():
            return _incomplete(
                lane,
                MISSING_RULES,
                f"the rules at {Path(lane.rules).name} are not there",
                "restore the rules file; an engine with no rules looks for nothing",
            )
        # One byte is enough. A rule deleted from the middle of a file leaves an engine that
        # runs, exits zero, and no longer looks for the thing it was deleted for — which is
        # indistinguishable from a clean scan unless the bytes themselves are pinned.
        if lane.rules_digest:
            found = hashlib.sha256(where.read_bytes()).hexdigest()
            if found != lane.rules_digest:
                return _incomplete(
                    lane,
                    TAMPERED_RULES,
                    f"{Path(lane.rules).name} is not the file this lane was pinned to",
                    "review the change and move the pin deliberately, or restore the file",
                )

    try:
        done = subprocess.run(
            [*lane.argv, *lane.extra, *inputs],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=lane.timeout,
            check=False,
        )
    except FileNotFoundError:
        return _incomplete(
            lane,
            MISSING_ENGINE,
            f"{lane.argv[0]} is not installed here",
            "install the pinned engine, or record this lane as not applicable",
        )
    except subprocess.TimeoutExpired:
        return _incomplete(
            lane,
            TIMEOUT,
            f"it did not finish within {lane.timeout} seconds",
            "narrow the inputs or raise the bound deliberately",
        )
    except OSError as why:
        return _incomplete(
            lane, CRASHED, f"it could not be executed: {type(why).__name__}", "check the engine"
        )

    if done.returncode == lane.findings_exit:
        return outcome.fact(
            f"lane-{lane.id}",
            "FAIL",
            f"The {lane.id} lane",
            f"it ran over {len(inputs)} input(s) and found something",
            cure="read its output, fix what it found, and run it again",
        )
    if done.returncode != 0:
        return _incomplete(
            lane,
            CRASHED,
            f"it exited {done.returncode}, which has no meaning in this lane",
            "read its output; an exit code with no defined meaning is not a verdict",
        )
    return outcome.fact(
        f"lane-{lane.id}",
        "PASS",
        f"The {lane.id} lane",
        f"it ran over {len(inputs)} input(s) and found nothing",
    )


# The three lanes this repository's own baseline runs, in one place so the gate and any
# future reader of it see the same list. Each `findings_exit` is the engine's documented
# code for "I found something"; anything else it can exit is undefined and INCOMPLETE.
BASELINE = (
    Lane("secrets", ("gitleaks", "dir"), extra=("--redact", "--no-banner", "--exit-code", "1")),
    Lane(
        "semantic",
        ("semgrep", "scan"),
        rules=Path("policy/semgrep.yml"),
        # Moved deliberately when the rules change, and a test says so with the command that
        # prints the new value. A pin nobody has to update is a pin nobody notices missing.
        rules_digest="81adf3bdbd24ca883bbc75d659e9a44ba0967ef4c4445628bb78f63f85a26c2a",
        extra=("--config", "policy/semgrep.yml", "--error", "--quiet"),
    ),
    Lane(
        "dependencies",
        ("trivy", "fs"),
        extra=(
            "--scanners",
            "vuln,license,misconfig",
            "--exit-code",
            "1",
            "--severity",
            "CRITICAL,HIGH,MEDIUM",
        ),
    ),
)


# The two cross-checks the proposal names by product, and the reason they are here rather
# than in `BASELINE`. Neither is required: this repository's baseline is the three lanes
# above and it passes with neither installed, which is the whole point of a cross-check —
# a second opinion an organisation may want, never a dependency this framework acquires.
#
# What was missing is that the tree said nothing at all about them. `grep` for either name
# found spec prose and no code, so a reader could not tell "we decided not to require this"
# from "nobody thought about it", and the requirement asks for exactly that distinction:
# configured and unable to run is INCOMPLETE, absent is not applicable.
CROSS_CHECKS = (
    Lane("skillspector", ("skillspector", "scan")),
    Lane("claude-security", ("claude-security", "review")),
)


def cross_check(lane: Lane, root: Path, inputs: list[str]) -> outcome.Fact:
    """A second opinion, or the honest answer that nobody asked for one.

    Absent means not applicable and passes: an organisation that never installed this tool
    is not failing a check, it is declining one. Present means it runs under exactly the
    contract the baseline runs under — an engine that is there and cannot answer is
    INCOMPLETE, and INCOMPLETE is not a pass. The difference between those two sentences is
    the entire requirement.
    """

    if shutil.which(lane.argv[0]) is None:
        return outcome.fact(
            f"cross-{lane.id}",
            "SKIPPED",
            f"The {lane.id} cross-check",
            f"{lane.argv[0]} is not installed here, so there is no second opinion to read",
        )
    return run(lane, root, inputs)


def baseline(root: Path) -> int:
    """Run the three lanes and return the exit code the gate should take.

    INCOMPLETE fails the gate exactly as FAIL does. A lane that could not run is a lane
    whose answer nobody has, and the whole point of this module is that nobody's answer is
    not a clean one.
    """

    worst = 0
    for lane in BASELINE:
        fact = run(lane, root, ["."])
        print(f"  {fact.status:<11} {lane.id:<13} {fact.detail}")
        if fact.status != "PASS":
            worst = 1
    return worst
