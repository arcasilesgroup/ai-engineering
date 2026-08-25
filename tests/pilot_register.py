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

import json
import re
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

# Eighteen since `EP-056`: the thirteen this repository could already compute, plus the six
# it was commissioned to measure and had never listed. Five rows were added — conflicts was
# already tracked as `coordination_overlap` and a second row for it would be two homes for
# one number, which is the defect this file was written to stop.
INDICATORS = 19
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
        if not str(row.get("quote", "")).strip():
            found.append(f"{name} does not quote the sentence in the report it answers")

    # The place in the source list each row answers. Fourteen rows carried fourteen English
    # sentences and the report carries fourteen Spanish ones, and nothing said which was
    # which — so the audit graded fourteen requirements against a correspondence nobody had
    # written down, and got eleven of them proven against seven rows that have a check.
    # An ordering is checkable where a paraphrase is not: exactly 1..14, each once.
    places = [row.get("source_order") for row in prohibitions]
    if sorted(x for x in places if isinstance(x, int)) != list(range(1, PROHIBITIONS + 1)):
        found.append(
            f"the prohibitions place themselves at {places}, and the source list has "
            f"{PROHIBITIONS} entries numbered 1..{PROHIBITIONS} — each row answers one of "
            "them, exactly once"
        )
    return found


# The report the register is derived from. `.ai/` is ignored in its entirety, so a fresh
# clone and every CI runner has neither report — which is why this is a separate function
# that says it could not look, rather than a row in `problems()` that would fail the gate on
# every machine but this one.
REPORT = ROOT / ".ai" / "reports" / "001-evolution-proposal.html"


def against_report(register: dict) -> tuple[bool, list[str]]:
    """Is the register the report's own list, in the report's own order?

    Returns whether the question could be answered at all, and what was wrong if it could.
    The check is the quoted sentence and the offset it is found at: fourteen substrings, each
    present, each later in the document than the one before it. That is the whole claim —
    the register does not paraphrase the prohibitions, it indexes them.
    """

    try:
        document = REPORT.read_text(encoding="utf-8")
    except OSError:
        return False, []

    wrong, previous = [], -1
    for row in sorted(register.get("prohibition", []), key=lambda one: one.get("source_order", 0)):
        quote = str(row.get("quote", ""))
        where = document.find(quote)
        if where < 0:
            wrong.append(f"{row['id']} quotes a sentence the report does not contain: {quote[:60]}")
        elif where < previous:
            wrong.append(
                f"{row['id']} sits at place {row.get('source_order')} and its sentence comes "
                "earlier in the report than the one before it"
            )
        else:
            previous = where
    return True, wrong


def stale_claim(register: dict, missing: int) -> str:
    """Does the reason the claim gives quote a number the register no longer has?

    It did. The claim said "six indicators have no instrument" and five rows were added,
    four of them uninstrumented — so the sentence a reader takes the state from was one
    short and nothing noticed, because a sentence is data here and nothing read it as a
    number. Two homes for one count, which is the defect this whole file was written for,
    sitting in the file itself.

    Only digits are checked, and only against this one count. A `why` that argues without
    quoting a figure is fine; one that quotes the wrong figure is the failure.
    """

    said = re.findall(r"\d+", str(register.get("claim", {}).get("why", "")))
    if said and str(missing) not in said:
        return (
            f"the claim says {', '.join(said)} where {missing} indicators have no instrument. "
            "Write the number this run computed, or stop quoting one."
        )
    return ""


SURFACE_RECEIPTS = ROOT / ".ai" / "receipts" / "surface"
SURFACE_AGE = "surface_proof_age"


def looser_than_declared(register: dict) -> list[str]:
    """Does any receipt in this tree give itself longer than the register promises?

    `EP-283` asks that a surface's proof go red when its observed denial is older than a
    week. The register declares that week — `surface_proof_age`, 604,800 seconds — and
    `surface._standing` enforces `min(the receipt's own window, 31 days)`. It never reads the
    register. So a receipt is free to write `max_age_seconds` of thirty-one days and stay
    green at thirty, while this file publishes seven to anyone who asks.

    Two numbers for one promise and nothing comparing them, which is the defect this whole
    register was written to stop, sitting between the register and the product it describes.

    Checked here rather than in `surface.py` on purpose: making the product import a policy
    table would tie the code that decides to the document that describes it, and then the
    document could never be wrong. The point is that it can be, and that something says so.
    """

    row = next((one for one in register.get("indicator", []) if one.get("id") == SURFACE_AGE), None)
    bound = (row or {}).get("bound_seconds")
    if not isinstance(bound, int) or isinstance(bound, bool):
        return []  # already reported by problems(); one complaint per defect

    loose, compared = [], 0
    for receipt in sorted(SURFACE_RECEIPTS.glob("*.json")):
        compared += 1
        try:
            window = json.loads(receipt.read_text(encoding="utf-8")).get("max_age_seconds")
        except (OSError, ValueError):
            # Unreadable is `surface.py`'s answer to give, and it gives it. Saying so twice
            # in two vocabularies is how a reader learns to ignore one of them.
            continue
        if isinstance(window, int) and not isinstance(window, bool) and window > bound:
            loose.append(
                f"{receipt.stem} declares {window}s where {SURFACE_AGE} bounds at {bound}s: "
                f"it stays proven for {(window - bound) // 86_400} days past what this "
                "register publishes"
            )
    # How many were compared, because zero and none-too-loose print the same word otherwise.
    # `.ai/` is ignored whole, so a fresh clone and every CI runner has no receipts at all
    # and this check passes over nothing — which is a different answer from agreeing, and
    # the count is the only thing that tells them apart.
    print(f"  {compared} surface receipt(s) compared against the {bound}s {SURFACE_AGE} bound")
    return loose


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

    loose = looser_than_declared(register)
    if loose:
        for line in loose:
            print(f"  {line}", file=sys.stderr)
        return 1

    missing = uninstrumented(register)
    drifted = stale_claim(register, len(missing))
    if drifted:
        print(f"  {drifted}", file=sys.stderr)
        return 1
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
    looked, wrong = against_report(register)
    if wrong:
        for line in wrong:
            print(f"  {line}", file=sys.stderr)
        return 1
    if looked:
        print(f"  the {PROHIBITIONS} prohibitions are the report's own list, in its own order.")
    else:
        print(
            f"  the {PROHIBITIONS} prohibitions could not be checked against the report: "
            f"{REPORT.relative_to(ROOT)} is not in this tree, so their order is unverified here."
        )

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
