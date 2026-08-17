#!/usr/bin/env python3
"""The reader for `policy/pilot-register.toml`, and the only thing that can refuse a P5 claim.

Specification 015: each of the thirteen indicators is one row naming the indicator, the
command that computes it, its bound and the wave that owns it; a row nothing computes
carries `no_instrument` with a reason and no bound; each of the fourteen prohibitions is one
row naming what must not appear and either the check that would find it or the reason no
check can decide it.

The register is data and this is the reader. It fails closed: a register it cannot parse, a
row missing its parts, or a completion claim standing over an uninstrumented row all exit
non-zero. What it will not do is convert an absence into a pass — the whole point of writing
`no_instrument` down is that it stays visible until somebody builds the instrument.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "policy" / "pilot-register.toml"

# This runs as a command, not only under pytest: `just register` invokes it with a bare
# interpreter, and the mutation harness runs it from a copied tree. Neither has the package
# installed, so the threshold check below imported `ai_engineering` and died with
# `ModuleNotFoundError` — a runner that works only when something else happens to have put
# the product on the path. `uv run` provides it locally, which is exactly why the local gate
# was green and the mutation run was not.
sys.path.insert(0, str(ROOT / "src"))

INDICATORS = 13
PROHIBITIONS = 14


# Read from the module that enforces it rather than written down again. Two copies of a
# number are two numbers, and this file exists because of one that had drifted.
try:  # the package is on the path under `just check`; a bare run of this file need not be
    from ai_engineering.surface import MAX_AGE_CEILING as _CEILING
except ImportError:  # pragma: no cover - exercised only outside the suite's path
    _CEILING = 2_678_400


def problems(register: dict) -> list[str]:
    """Every way this register is not a register. One list, so the reader prints all of
    them rather than the first — a shape error found one run at a time is four runs."""

    found: list[str] = []
    indicators = register.get("indicator", [])
    prohibitions = register.get("prohibition", [])

    if len(indicators) != INDICATORS:
        found.append(f"the register holds {len(indicators)} indicators and there are {INDICATORS}")
    if len(prohibitions) != PROHIBITIONS:
        found.append(
            f"the register holds {len(prohibitions)} prohibitions and there are {PROHIBITIONS}"
        )

    seen: set[str] = set()
    for row in indicators:
        name = str(row.get("id", "<unnamed>"))
        if name in seen:
            found.append(f"{name} appears twice; an indicator has one row")
        seen.add(name)
        if not row.get("wave"):
            found.append(f"{name} names no wave that owns it")
        equipped = bool(row.get("command"))
        unequipped = bool(row.get("no_instrument"))
        if equipped == unequipped:
            found.append(
                f"{name} is both instrumented and not, or neither: "
                "a row carries a command or a reason it has none"
            )
        if unequipped and row.get("bound"):
            found.append(f"{name} carries a bound and no instrument; that pair is an error")
        if equipped and not row.get("bound"):
            found.append(f"{name} names a command and no bound, so nothing can go red")
        # A bound stated twice has to agree with itself. `surface_proof_age` said seven days
        # in a sentence while `surface.MAX_AGE_CEILING` caps a receipt's own window at
        # thirty-one, and nothing said which number governed or compared them — the same
        # shape as the manifest that declared a capability the gate forbade. A numeric bound
        # is optional; a numeric bound looser than the ceiling it sits under is an error,
        # because an indicator that goes red only after the reader has already refused the
        # receipt is an indicator that never goes red.
        seconds = row.get("bound_seconds")
        if seconds is not None and (not isinstance(seconds, int) or seconds <= 0):
            found.append(f"{name} carries a bound_seconds that is not a positive number")
        elif seconds is not None and seconds > _CEILING:
            found.append(
                f"{name} bounds at {seconds}s, past the {_CEILING}s ceiling the reader "
                f"enforces: it could never go red first"
            )

    # A requirement this framework will not gate owes four things, and the fourth is the one
    # worth enforcing: `reopen_when` is what would change the decision. Without it a row is a
    # permanent no, and a permanent no about somebody else's requirement is not a decision
    # this framework is entitled to take. The reasons used to live in three specifications,
    # two ceiling comments and a test docstring, so a reader asking whether anybody had
    # decided at all had to find six places before they could tell.
    for row in register.get("ungated", []):
        name = str(row.get("id", "<unnamed>"))
        for field, why in (
            ("asks", "does not say what the requirement asks for"),
            ("reason", "does not say why no gate can hold it"),
            ("reopen_when", "refuses forever, which is not this framework's to decide"),
        ):
            if not str(row.get(field, "")).strip():
                found.append(f"{name} {why}")

    for row in prohibitions:
        name = str(row.get("id", "<unnamed>"))
        if not row.get("never"):
            found.append(f"{name} does not say what must not appear")
        if bool(row.get("check")) == bool(row.get("reason")):
            found.append(
                f"{name} names both a check and a reason, or neither: "
                "one row says how it would be found, or why it cannot be"
            )
    return found


def uninstrumented(register: dict) -> list[str]:
    return [str(row["id"]) for row in register.get("indicator", []) if row.get("no_instrument")]


def main() -> int:
    try:
        register = tomllib.loads(REGISTER.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as why:
        print(f"  the register could not be read: {type(why).__name__}", file=sys.stderr)
        return 1

    broken = problems(register)
    if broken:
        for line in broken:
            print(f"  {line}", file=sys.stderr)
        return 1

    missing = uninstrumented(register)
    equipped = INDICATORS - len(missing)
    print(f"  {equipped} of {INDICATORS} indicators have a command; {len(missing)} have none:")
    for name in missing:
        print(f"    no_instrument  {name}")

    # The prohibitions split the same way and nothing printed it, so the only statement of
    # how many can fail closed was a sentence in a specification — and that sentence said
    # eleven while the register shipped seven. Rule 12 keeps a judgement no script can
    # decide as a prompt with its reason written down, which is what those rows are; what
    # was missing is anybody being able to see how many there are without counting by hand.
    # The number is read from the register on every run now, so it cannot go stale again.
    argued = [str(row["id"]) for row in register.get("prohibition", []) if not row.get("check")]
    decided = PROHIBITIONS - len(argued)
    print(f"  {decided} of {PROHIBITIONS} prohibitions fail closed; {len(argued)} are argued:")
    for name in argued:
        print(f"    reason_only    {name}")

    # `EP-057`: a stated prohibition and a numeric threshold for the same rule. Fourteen
    # prohibitions carry no number, which was the finding; these are the two rules that do,
    # and the number is checked against the code that enforces it rather than printed on
    # trust — a declared threshold nothing binds is a number in a document.
    try:
        from ai_engineering import report as report_module
    except ImportError as why:
        # Undecidable, not clean. The thresholds are declared and this run could not read the
        # code that enforces them, which is a different answer from "they agree".
        print(f"  the declared thresholds could not be checked against the code: {why}")
        return 1

    for row in register.get("threshold", []):
        constant = str(row["enforced_by"]).split(",")[0].rsplit(".", 1)[-1]
        actual = getattr(report_module, constant, None)
        if actual != row["threshold"]:
            print(
                f"  {row['id']} declares {row['threshold']} and {constant} is {actual}: a "
                "prohibition and its number have drifted apart",
                file=sys.stderr,
            )
            return 1
        print(f"    threshold      {row['id']} = {row['threshold']} {row['unit']}")

    ungated = [str(row["id"]) for row in register.get("ungated", [])]
    if ungated:
        print(f"  {len(ungated)} requirements are held by a written reason and no gate:")
        for name in ungated:
            print(f"    ungated        {name}")

    claimed = bool(register.get("claim", {}).get("p5_complete"))
    if claimed and missing:
        print("\n  P5 is claimed complete while these have no instrument:", file=sys.stderr)
        for name in missing:
            print(f"    {name}", file=sys.stderr)
        print("  A wave does not close on the rows nobody equipped.", file=sys.stderr)
        return 1
    if claimed:
        print("  P5 is claimed complete and every indicator carries a command.")
    else:
        why = register.get("claim", {}).get("why", "")
        print(f"  P5 is not claimed complete: {why}")
    print(f"RAN register={INDICATORS + PROHIBITIONS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
