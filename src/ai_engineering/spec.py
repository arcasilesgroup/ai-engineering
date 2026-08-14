"""specs/NNN-slug/spec.md — the record, in the user's repository, in their diff.

Specs live at the root and not inside a hidden directory, deliberately: a governance
record hidden in a dot-directory is a record nobody reviews, because reviewers read the
file tree and do not expand hidden folders. There is no drafts/ either — a draft is a
spec with status: draft from the first keystroke, on a branch. That is not tidiness, it
is data loss: `git clean -ndx` eats a draft that sits inside a committed directory.
"""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path

from ai_engineering import intent, outcome, paths

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/#-]*$")
_NON_AUTHORITY = re.compile(r"(^|[^A-Za-z0-9])(agent|model|reviewer)([^A-Za-z0-9]|$)", re.I)
_MISSING_AUTHORITY = intent.Validation(
    "INCOMPLETE",
    "INTENT_AUTHORITY_MISSING",
    "canonical Solution Intent is not actively approved by an accountable role",
)

BOXES = [
    "CI/CD — build, lint, test and security analysis on every push; deploy from the default branch",
    "Logs — structured JSON, one line per event, with level and service, to stdout",
    "Traces — only if this is our code and has more than one hop; no hop, no trace",
    "Errors — every uncaught exception leaves as a log with severity 17 and marks its span",
    "Health and data age — alive, age of the newest datum, and an independent recomputation",
    "External check — something outside the service verifies it and says what it could not check",
    "Second path — every published number recomputed by an independent route and compared",
    "Security — secrets sealed, no credential in a plain variable, SAST and dependency audit in CI",
]

TEMPLATE = """---
id: "{number}"
slug: {slug}
status: draft
date: {today}
ref: {ref}
supersedes: ""
---

# {title}

## Context and problem

TODO: what is true today, and what about it is a problem. Written so somebody who does
not code can follow.

## Options considered

1. TODO: the first real option, and what it costs.
2. TODO: the second. At least two, and the losers are killed in writing here.

## Decision

TODO: the one chosen, and why the others were not. If this decision constrains specs
that do not exist yet, promote it: `ai-eng decide --madr "<title>"`.

## Decisions

<!-- ai-eng decide writes yaml blocks here -->

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command.

{boxes}
"""


def specs_dir(root: Path) -> Path:
    return root / "specs"


def next_number(root: Path) -> str:
    heads = [p.name.split("-")[0] for p in specs_dir(root).glob("[0-9]*-*") if p.is_dir()]
    used = [int(head) for head in heads if head.isdecimal()]
    return f"{max(used, default=0) + 1:03d}"


def create(root: Path, slug: str, ref: str) -> Path:
    specs_dir(root).mkdir(exist_ok=True)
    number = next_number(root)
    folder = specs_dir(root) / f"{number}-{slug}"
    folder.mkdir()
    text = TEMPLATE.format(
        number=number,
        slug=slug,
        today=date.today().isoformat(),
        ref=f'"{ref}"' if ref else '""',
        title=slug.replace("-", " ").capitalize(),
        boxes="\n".join(f"- [ ] {box}" for box in BOXES),
    )
    spec = folder / "spec.md"
    spec.write_text(text, encoding="utf-8")
    return spec


def status_of(path: Path) -> str:
    head = path.read_text(errors="replace")[:600]
    found = re.search(r"^status:\s*(\S+)", head, re.M)
    return found.group(1) if found else "?"


def target(root: Path, named: str = "") -> Path:
    """The spec a record verb writes to. It used to be whichever directory sorted last,
    and that is not a guess anybody can check: writing spec 003, two decisions landed in
    another session's spec because a fourth directory appeared between two commands.
    Named, it is the one you named. Unnamed, it is the only candidate there is — the
    drafts if there are any, everything otherwise — and where there is more than one
    there is no answer to guess at, so it refuses and says which ones it saw."""
    if named:
        matches = sorted(specs_dir(root).glob(f"{named}*/spec.md"))
        if not matches:
            raise LookupError(f"no spec matches {named!r}")
        if len(matches) > 1:
            raise LookupError(
                f"{named!r} matches {', '.join(m.parent.name for m in matches)}. Name one of them."
            )
        return matches[0]
    every = sorted(specs_dir(root).glob("*/spec.md"))
    candidates = [path for path in every if status_of(path) == "draft"] or every
    if not candidates:
        raise LookupError("no spec to record this against. `ai-eng spec new <slug>` first")
    if len(candidates) > 1:
        raise LookupError(
            f"{len(candidates)} specs are open — {', '.join(p.parent.name for p in candidates)}. "
            f"Name the one this belongs to with --spec."
        )
    return candidates[0]


def listing(root: Path, everything: bool) -> list[str]:
    """Derived, never hand-maintained: a hand-maintained index rots, and ours did — 198
    rows whose own third line said the details were in the git history."""
    rows = []
    for spec in sorted(specs_dir(root).glob("*/spec.md")):
        head = spec.read_text(errors="replace")[:600]
        status = (re.search(r"^status:\s*(\S+)", head, re.M) or [None, "?"])[1]
        if status == "superseded" and not everything:
            continue
        title = (re.search(r"^# (.+)$", head, re.M) or [None, spec.parent.name])[1]
        rows.append(f"  {spec.parent.name:<28} {status:<12} {title}")
    return rows


def _argument(pattern: re.Pattern[str], label: str, *, allow_empty: bool = False):
    def parse(value: str) -> str:
        if not (allow_empty and value == "") and pattern.fullmatch(value) is None:
            raise argparse.ArgumentTypeError(f"{label} is not canonical")
        return value

    return parse


def _authority(root: Path) -> intent.Validation:
    """The active canonical Intent is the existing local authority record; CLI metadata is not."""
    home = root / ".ai" / "intent.md"
    try:
        before = home.read_bytes()
    except OSError:
        return intent.Validation("INCOMPLETE", "INTENT_SCHEMA_INVALID", "schema validation failed")
    validation = intent.validate(home, root)
    if validation.outcome != "PASS":
        return validation
    try:
        after = home.read_bytes()
        if after != before:
            return _MISSING_AUTHORITY
        record = intent._json(after)
        validation = intent.validate(record, root)
        if validation.outcome != "PASS":
            return validation
        lifecycle = record["lifecycle"]
        approval = lifecycle["approval"]
        transition = lifecycle["transitions"][-1]
        role = approval["authority_role"]
        owner = record["ownership"]["accountable_role"]
    except (IndexError, KeyError, OSError, RecursionError, TypeError, ValueError):
        return intent.Validation("INCOMPLETE", "INTENT_SCHEMA_INVALID", "schema validation failed")
    if (
        lifecycle["status"] != "active"
        or role != owner
        or transition["authority_role"] != role
        or transition["approval_ref"] != approval["approval_ref"]
        or _NON_AUTHORITY.search(role)
    ):
        return _MISSING_AUTHORITY
    return intent.PASS


def main(argv: list[str]) -> outcome.Result:
    parser = argparse.ArgumentParser("ai-eng spec")
    sub = parser.add_subparsers(dest="action", required=True)
    made = sub.add_parser("new")
    made.add_argument("slug", type=_argument(_SLUG, "slug"))
    made.add_argument(
        "--ref",
        default="",
        type=_argument(_REF, "work item", allow_empty=True),
        help='a work item, e.g. "owner/repo#45"',
    )
    shown = sub.add_parser("show")
    shown.add_argument("id", type=_argument(re.compile(r"^[0-9]+$"), "spec id"))
    listed = sub.add_parser("list")
    listed.add_argument("--all", action="store_true", help="include superseded specs")
    args = parser.parse_args(argv)

    root = paths.repo_root()
    if root is None:
        print("not inside a repository")
        return outcome.result("INCOMPLETE")
    if args.action == "new":
        authority = _authority(root)
        if authority.outcome != "PASS":
            print(f"  INCOMPLETE  Solution Intent authority: {authority.code} — {authority.reason}")
            return outcome.result("INCOMPLETE")
        home = specs_dir(root)
        if home.is_symlink() or (home.exists() and not home.is_dir()):
            print("  INCOMPLETE  specs/ is not one regular repository directory")
            return outcome.result("INCOMPLETE")
        try:
            created = create(root, args.slug, args.ref)
        except OSError as why:
            print(f"  INCOMPLETE  the draft could not be created: {why}")
            return outcome.result("INCOMPLETE")
        print(f"  ✓ {created.relative_to(root)}")
        return outcome.result("PASS")
    if args.action == "list":
        try:
            rows = listing(root, args.all)
        except OSError as why:
            print(f"  INCOMPLETE  specs could not be listed: {why}")
            return outcome.result("INCOMPLETE")
        print("\n".join(rows) if rows else "  no specs yet — `ai-eng spec new <slug>`")
        return outcome.result("PASS")
    matches = sorted(specs_dir(root).glob(f"{args.id}*/spec.md"))
    if not matches:
        print(f"  no spec matches {args.id!r}")
        return outcome.result("INCOMPLETE")
    # All of them, named. Printing the first and saying nothing about the rest is how
    # somebody reads one spec and acts as though it were the only one that matched.
    for match in matches:
        if len(matches) > 1:
            print(f"── {match.parent.name} ── {matches.index(match) + 1} of {len(matches)}")
        try:
            print(match.read_text())
        except OSError as why:
            print(f"  INCOMPLETE  {match.parent.name} could not be read: {why}")
            return outcome.result("INCOMPLETE")
    return outcome.result("PASS")
