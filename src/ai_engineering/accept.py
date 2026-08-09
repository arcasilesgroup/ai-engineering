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
    out = []
    for spec in sorted((root / "specs").glob("*/spec.md")) if (root / "specs").exists() else []:
        for block in text.yaml_blocks(spec.read_text(errors="replace")):
            if "expires" in block and "finding" in block:
                out.append((spec, block))
    return out


def expired(root: Path) -> list[dict]:
    today = date.today().isoformat()
    return [block for _, block in blocks(root) if str(block.get("expires", "")) < today]


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
        stale = expired(root)
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
    existing = [b for _, b in blocks(root) if b.get("finding") == args.finding]
    renewals = max((int(b.get("renewals", 0)) for b in existing), default=-1) + 1
    if renewals > MAX_RENEWALS:
        print(
            f"  {args.finding} has already been renewed {MAX_RENEWALS} times. "
            f"That is the ceiling: fix it, or change the answer."
        )
        return 1
    number = len([b for _, b in blocks(root)]) + 1
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
