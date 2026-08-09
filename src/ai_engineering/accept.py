"""A named person accepted this finding until date D, for reason R, against spec S.

That artifact is what an engineering lead hands an auditor, and it is the line between
this product and a bundle of prompts. It expires. Assertion 16 and the pre-push hook
both read it, so a repository with no CI still expires on push, and two renewals is the
ceiling — after that the finding gets fixed or the answer changes.
"""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path

from ai_engineering import paths, text

MAX_RENEWALS = 2
SECTION = "## Accepted risks"


def blocks(root: Path) -> list[tuple[Path, dict]]:
    """Raises ValueError naming the file when a block cannot be read. Every caller either
    handles that or lets it become could-not-evaluate — none of them may treat it as
    nothing found, which is what made a malformed acceptance invisible to the expiry
    check while the gate reported green over it."""
    out = []
    for spec in sorted((root / "specs").glob("*/spec.md")) if (root / "specs").exists() else []:
        name = str(spec.relative_to(root)) if spec.is_relative_to(root) else str(spec)
        for block in text.yaml_blocks(spec.read_text(errors="replace"), name):
            if "expires" in block and "finding" in block:
                out.append((spec, block))
    return out


def renewals_of(block: dict) -> int:
    """Hand-written blocks are allowed, so the counter can be missing or not a number."""
    try:
        return int(block.get("renewals", 0))
    except (TypeError, ValueError):
        return 0


def expired(root: Path) -> list[dict]:
    """A renewal retires what it renews. Without this, renewing a finding in a later spec
    left the expired original in the record as an independent result, so the push gate and
    assertion 16 both stayed red on it and no renewal ever recorded had retired anything.
    The highest renewal per finding is the live one; the blocks it replaced are history."""
    today = date.today().isoformat()
    live: dict[str, dict] = {}
    for _, block in blocks(root):
        seen = live.get(block["finding"])
        if seen is None or renewals_of(block) >= renewals_of(seen):
            live[block["finding"]] = block
    return [block for block in live.values() if str(block.get("expires", "")) < today]


def add(spec: Path, fields: dict) -> None:
    body = spec.read_text(encoding="utf-8")
    if SECTION not in body:
        body += f"\n{SECTION}\n"
    head, tail = body.split(SECTION, 1)
    spec.write_text(f"{head}{SECTION}\n\n{text.render(fields)}{tail.lstrip()}", encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser("ai-eng accept")
    parser.add_argument("--finding", help="the finding id being accepted")
    parser.add_argument("--severity", default="medium")
    parser.add_argument("--expires", help="ISO date. After it, pre-push and doctor fail.")
    parser.add_argument("--by", default="", help="the person accepting it, by name or address")
    parser.add_argument("--justification", default="", help="why this is acceptable, in one line")
    parser.add_argument("--follow-up", default="")
    parser.add_argument(
        "--spec", default="", help="which spec it belongs to; default is the newest"
    )
    parser.add_argument("--expired", action="store_true", help="list acceptances past their date")
    args = parser.parse_args(argv)

    root = paths.repo_root()
    if root is None:
        print("not inside a repository")
        return 1

    if args.expired:
        try:
            stale = expired(root)
        except ValueError as why:
            print(f"  UNDECIDABLE  {why}")
            print("  A record block nobody can read is not a record, and it is not a pass.")
            return 1
        for block in stale:
            print(
                f"  EXPIRED  {block.get('id', '?')}  {block['finding']}  "
                f"expired {block['expires']}  accepted by {block.get('accepted_by', '?')}"
            )
        if stale:
            print(
                "  An acceptance that ran out is not an acceptance. Fix it or renew it "
                "with a reason, up to twice."
            )
        return 1 if stale else 0

    if not (args.finding and args.expires and args.by and args.justification):
        print(
            "  --finding, --expires, --by and --justification are all required: an "
            "acceptance with no end date, no name against it and no reason is not one."
        )
        return 2
    specs = (
        sorted((root / "specs").glob(f"{args.spec}*/spec.md"))
        if args.spec
        else sorted((root / "specs").glob("*/spec.md"))
    )
    if not specs:
        print(
            "  no spec to attach this to. `ai-eng spec new <slug>` first: a risk with no "
            "context is a note, not a decision."
        )
        return 1
    spec = specs[-1]
    try:
        recorded = blocks(root)
    except ValueError as why:
        # Without this the verb tracebacks on a neighbour somebody typed wrong, and the
        # answer to "the record is unreadable" is not "so is this command".
        print(f"  {why}")
        print(
            "  Nothing was written: a new acceptance cannot be numbered against a "
            "record that cannot be read. Fix that block first."
        )
        return 1
    existing = [b for _, b in recorded if b.get("finding") == args.finding]
    renewals = max((renewals_of(b) for b in existing), default=-1) + 1
    if renewals > MAX_RENEWALS:
        print(
            f"  {args.finding} has already been renewed {MAX_RENEWALS} times. "
            f"That is the ceiling: fix it, or change the answer."
        )
        return 1
    # The nth risk of this spec, which is what the number is supposed to read as. Counting
    # every block in the repository made the first risk recorded against a spec number eight.
    number = sum(1 for where, _ in recorded if where == spec) + 1
    add(
        spec,
        {
            "id": f"R-{re.sub(r'[^0-9]', '', spec.parent.name)[:3]}-{number:02d}",
            "finding": args.finding,
            "severity": args.severity,
            "accepted_by": args.by,
            "accepted": date.today().isoformat(),
            "expires": args.expires,
            "renewals": renewals,
            "justification": args.justification,
            "follow_up": args.follow_up,
        },
    )
    print(
        f"  ✓ recorded in {spec.relative_to(root)} — it expires {args.expires}, and both "
        f"pre-push and doctor read that date."
    )
    return 0
