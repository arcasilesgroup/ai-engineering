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

INDICATORS = 13
PROHIBITIONS = 14


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
