"""A decision is born inside its spec, and is promoted only when it earns it.

The single question that decides promotion: does this decision constrain specs that do
not exist yet? If the answer is no it stays a block inside its spec, which is where it
has its context and where it is reviewed in the same diff. If it is yes, --adr writes
docs/adr/NNNN-title.md with MADR's minimal shape and leaves only a pointer behind. No
duplicate: the file becomes the good place.

Numbers collide between concurrent branches. That is the classic failure of every ADR
tool and it is not hidden behind a numbering service: it collides, doctor names it, and
a file is renamed in review like any other conflict.
"""

from __future__ import annotations

import argparse
import contextlib
import re
from datetime import date
from pathlib import Path

from ai_engineering import paths, text
from ai_engineering import spec as specs

MADR = """---
status: proposed
date: {today}
spec: {spec}
supersedes: {supersedes}
---

# {number}. {title}

## Context and problem statement

TODO: what forces this decision, in one paragraph.

## Considered options

1. TODO
2. TODO

## Decision outcome

TODO: the chosen option, and why.

## Consequences

TODO: what gets better, and what gets worse. Both, or it is not a decision.
"""


def adr_dir(root: Path) -> Path:
    return root / "docs" / "adr"


def next_number(root: Path) -> str:
    used = [int(p.name[:4]) for p in adr_dir(root).glob("[0-9][0-9][0-9][0-9]-*.md")]
    return f"{max(used, default=0) + 1:04d}"


def promote(root: Path, title: str, supersedes: str, spec: Path | None) -> Path:
    adr_dir(root).mkdir(parents=True, exist_ok=True)
    number = next_number(root)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
    path = adr_dir(root) / f"{number}-{slug}.md"
    path.write_text(
        MADR.format(
            today=date.today().isoformat(),
            number=number,
            title=title,
            spec=spec.parent.name if spec else '""',
            supersedes=supersedes or '""',
        ),
        encoding="utf-8",
    )
    if supersedes:
        for old in adr_dir(root).glob(f"{supersedes}-*.md"):
            body = old.read_text(encoding="utf-8")
            old.write_text(
                re.sub(
                    r"^status:.*$", f"status: superseded by {number}", body, count=1, flags=re.M
                ),
                encoding="utf-8",
            )
    if spec:
        append(spec, {"adr": number, "title": title})
    return path


def append(spec: Path, fields: dict) -> None:
    body = spec.read_text(encoding="utf-8")
    marker = "## Decisions"
    if marker not in body:
        body += f"\n{marker}\n"
    head, tail = body.split(marker, 1)
    with spec.open("w", encoding="utf-8") as stream:
        stream.write(f"{head}{marker}\n\n{text.render(fields)}{tail.lstrip()}")


def listing(root: Path) -> list[str]:
    """A grep over headers. There is no index file to maintain by hand, because a
    hand-maintained index rots."""
    rows = []
    for path in sorted(adr_dir(root).glob("*.md")):
        head = path.read_text(errors="replace")[:400]
        status = (re.search(r"^status:\s*(.+)$", head, re.M) or [None, "?"])[1]
        rows.append(f"  {path.stem:<44} {status}")
    return rows


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser("ai-eng decide")
    parser.add_argument("title", nargs="?", default="")
    parser.add_argument("--adr", action="store_true", help="promote it to docs/adr/")
    parser.add_argument("--supersede", default="", metavar="NNNN")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--why", default="", help="the rationale, when it stays inside the spec")
    parser.add_argument(
        "--spec", default="", help="which spec it belongs to; needed when more than one is open"
    )
    args = parser.parse_args(argv)

    root = paths.repo_root()
    if root is None:
        print("not inside a repository")
        return 1
    if args.list:
        rows = listing(root)
        print("\n".join(rows) if rows else "  no ADRs yet — most decisions never need one")
        return 0
    if not args.title:
        print("  a decision needs a title.")
        return 2
    # Named, or the only one open. It used to resolve to whichever directory sorted last,
    # and that is how two decisions written for spec 003 landed in another session's spec,
    # because a fourth directory appeared between two commands.
    if args.adr:
        # An ADR outlives every spec, so it may be written without one — which is why this
        # branch reads the spec separately: the other one cannot proceed without a spec, and
        # fusing the two made the difference between them a flag read three lines later.
        promoted: Path | None = None
        with contextlib.suppress(LookupError):
            promoted = specs.target(root, args.spec)
        print(f"  ✓ {promote(root, args.title, args.supersede, promoted).relative_to(root)}")
        print("    status: proposed. Accept or reject it by changing one line in a pull request.")
        return 0
    try:
        spec = specs.target(root, args.spec)
    except LookupError as why:
        print(f"  {why}")
        return 1
    append(
        spec,
        {
            "decision": args.title,
            "date": date.today().isoformat(),
            "rationale": args.why or "TODO: why, in one sentence",
        },
    )
    print(
        f"  ✓ recorded in {spec.relative_to(root)}. If it constrains specs that do not exist "
        f"yet, promote it with --adr."
    )
    return 0
