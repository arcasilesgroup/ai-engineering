"""The cold-read verifier, spec 030 / B-030-1.

A reviewer that reads only the spec (or answer key) and the delivered files — never the
constructor's conversation, never the plan's rationale — and has no write tools. Its rules:
"an uncertain check is a fail"; it reports what it saw, not what the builder said. A
verifier with write access or the constructor's reasoning is refused by this contract.

The verifier walks the named files read-only and applies the answer key with `--recheck`
via `evidencing` (spec 029 B-029-3) — a claim that merely says it passed is not believed.
"""

from __future__ import annotations

import subprocess
import tomllib
from enum import StrEnum
from pathlib import Path


class Verdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


def _run(command: str, cwd: Path) -> bool:
    """Run a check command inside `cwd`; a non-zero exit is a fail, never a guess."""
    done = subprocess.run(command, shell=True, cwd=str(cwd), capture_output=True, text=True)
    return done.returncode == 0


def verify(
    tree: Path,
    key_file: Path,
    *,
    allow_write: bool = False,
    constructor_reasoning: str = "",
) -> Verdict:
    """Apply `key_file` to `tree` read-only, reporting what was observed.

    `allow_write` and `constructor_reasoning` exist only for the contract test that refuses
    them; a real cold-read call never sets either.
    """
    if allow_write:
        raise ValueError("cold-read verifier must be read-only")
    if constructor_reasoning:
        raise ValueError("cold-read verifier must not see the constructors reasoning")

    raw = tomllib.loads(key_file.read_text(encoding="utf-8"))
    checks = raw.get("checks", [])

    # A touched unknown blocks — the work hit a standard nobody decided.
    unknown = set(raw.get("unknowns", []))
    if unknown:
        return Verdict.BLOCKED

    # Every run-it check re-executes; nothing is believed on a claim.
    failed = [c["id"] for c in checks if not _run(c.get("command", ""), tree)]
    if failed:
        return Verdict.FAIL
    return Verdict.PASS
