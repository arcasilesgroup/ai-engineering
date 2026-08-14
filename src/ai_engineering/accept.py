"""A named person accepted this finding until date D, for reason R, against spec S.

That artifact is what an engineering lead hands an auditor, and it is the line between
this product and a bundle of prompts. It expires. Assertion 16 and the pre-push hook
both read it, so a repository with no CI still expires on push, and two renewals is the
ceiling — after that the finding gets fixed or the answer changes.
"""

from __future__ import annotations

import argparse
import os
import re
import stat
from datetime import date
from hashlib import sha256
from pathlib import Path, PurePosixPath

from ai_engineering import outcome, paths, spec, text

MAX_RENEWALS = 2
SECTION = "## Accepted risks"
_MAX_EVIDENCE_BYTES = 100_000
_INVALID_OWNER = re.compile(
    r"(^|[^A-Za-z0-9])"
    r"(agent|model|reviewer|self|myself|unknown|unassigned|unspecified|someone|somebody|tbd|todo)"
    r"([^A-Za-z0-9]|$)",
    re.I,
)


class _EvidenceProblem(ValueError):
    pass


def _required(label: str):
    def parse(value: str) -> str:
        if not value.strip() or value != value.strip() or any(ord(char) < 0x20 for char in value):
            raise argparse.ArgumentTypeError(f"{label} must be one explicit value")
        return value

    return parse


def _date(value: str) -> str:
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except (OverflowError, ValueError):
        raise argparse.ArgumentTypeError("expiry must be one ISO date") from None
    return value


def _evidence_path(value: str) -> str:
    parts = value.split("/")
    if (
        not value
        or "\\" in value
        or value.startswith("/")
        or any(ord(char) < 0x20 for char in value)
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise argparse.ArgumentTypeError("evidence must be one repository-relative path")
    return value


def _evidence_reference(root: Path, relative: str, target: Path) -> str:
    """Bind one real local regular file to the acceptance without calling metadata proof."""
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    if candidate == target:
        raise _EvidenceProblem("an acceptance cannot cite the record it is about to change")
    component = root
    try:
        for part in PurePosixPath(relative).parts:
            component /= part
            if component.is_symlink():
                raise _EvidenceProblem("evidence path is not one local regular file")
        before = candidate.lstat()
        if not stat.S_ISREG(before.st_mode):
            raise _EvidenceProblem("evidence path is not one local regular file")
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_BINARY", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(candidate, flags)
        try:
            opened = os.fstat(descriptor)
            identity = (opened.st_dev, opened.st_ino)
            if not stat.S_ISREG(opened.st_mode) or identity != (before.st_dev, before.st_ino):
                raise _EvidenceProblem("evidence changed while opening")
            if opened.st_size < 1 or opened.st_size > _MAX_EVIDENCE_BYTES:
                raise _EvidenceProblem("evidence is empty or exceeds its size bound")
            chunks = []
            remaining = opened.st_size
            while remaining:
                chunk = os.read(descriptor, min(remaining, 65_536))
                if not chunk:
                    raise _EvidenceProblem("evidence changed while reading")
                chunks.append(chunk)
                remaining -= len(chunk)
            if os.read(descriptor, 1):
                raise _EvidenceProblem("evidence changed while reading")
            content = b"".join(chunks)
        finally:
            os.close(descriptor)
        after = candidate.lstat()
        if identity != (after.st_dev, after.st_ino):
            raise _EvidenceProblem("evidence changed while reading")
    except OSError as error:
        raise _EvidenceProblem("evidence cannot be read") from error
    if not content or len(content) > _MAX_EVIDENCE_BYTES:
        raise _EvidenceProblem("evidence is empty or exceeds its size bound")
    return f"{relative}@sha256:{sha256(content).hexdigest()}"


def blocks(root: Path) -> list[tuple[Path, dict]]:
    """Raises ValueError naming the file when a block cannot be read. Every caller either
    handles that or lets it become could-not-evaluate — none of them may treat it as
    nothing found, which is what made a malformed acceptance invisible to the expiry
    check while the gate reported green over it."""
    out = []
    for where in sorted((root / "specs").glob("*/spec.md")) if (root / "specs").exists() else []:
        name = str(where.relative_to(root)) if where.is_relative_to(root) else str(where)
        for block in text.yaml_blocks(where.read_text(errors="replace"), name):
            if "expires" in block and "finding" in block:
                out.append((where, block))
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


def add(where: Path, fields: dict) -> None:
    body = where.read_text(encoding="utf-8")
    if SECTION not in body:
        body += f"\n{SECTION}\n"
    head, tail = body.split(SECTION, 1)
    with where.open("w", encoding="utf-8") as stream:
        stream.write(f"{head}{SECTION}\n\n{text.render(fields)}{tail.lstrip()}")


def main(argv: list[str]) -> outcome.Result:
    parser = argparse.ArgumentParser("ai-eng accept")
    parser.add_argument(
        "--finding", type=_required("finding"), help="the finding id being accepted"
    )
    parser.add_argument("--severity", default="medium")
    parser.add_argument(
        "--expires", type=_date, help="ISO date. After it, pre-push and doctor fail."
    )
    parser.add_argument("--by", type=_required("owner"), help="the accountable person or role")
    parser.add_argument(
        "--justification",
        type=_required("reason"),
        help="why this is acceptable, in one line",
    )
    parser.add_argument(
        "--evidence",
        type=_evidence_path,
        help="repository-relative evidence file; its content digest is recorded",
    )
    parser.add_argument("--follow-up", default="")
    parser.add_argument(
        "--spec", default="", help="which spec it belongs to; needed when more than one is open"
    )
    parser.add_argument("--expired", action="store_true", help="list acceptances past their date")
    args = parser.parse_args(argv)

    if not args.expired and not (
        args.finding and args.expires and args.by and args.justification and args.evidence
    ):
        parser.error(
            "--finding, --expires, --by, --justification and --evidence are all required; "
            "a risk acceptance needs an owner, expiry, reason and actual local evidence"
        )

    root = paths.repo_root()
    if root is None:
        print("not inside a repository")
        return outcome.result("INCOMPLETE")

    if args.expired:
        try:
            stale = expired(root)
        except (OSError, ValueError) as why:
            print(f"  UNDECIDABLE  {why}")
            print("  A record block nobody can read is not a record, and it is not a pass.")
            return outcome.result("INCOMPLETE")
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
        return outcome.result("FAIL" if stale else "PASS")

    if _INVALID_OWNER.search(args.by):
        print(
            "  INCOMPLETE  risk needs one named accountable person or role; agents, models, "
            "reviewers and placeholders cannot accept it."
        )
        return outcome.result("INCOMPLETE")
    if args.expires < date.today().isoformat():
        print("  INCOMPLETE  an acceptance cannot already be expired. Use a current date.")
        return outcome.result("INCOMPLETE")
    try:
        where = spec.target(root, args.spec)
    except (LookupError, OSError) as why:
        print(f"  {why}")
        print("  A risk with no context is a note, not a decision.")
        return outcome.result("INCOMPLETE")
    try:
        evidence = _evidence_reference(root, args.evidence, where)
    except _EvidenceProblem:
        print(
            "  INCOMPLETE  evidence must be a readable, non-empty, repository-local regular "
            "file. Nothing was written."
        )
        return outcome.result("INCOMPLETE")
    try:
        recorded = blocks(root)
    except (OSError, ValueError) as why:
        # Without this the verb tracebacks on a neighbour somebody typed wrong, and the
        # answer to "the record is unreadable" is not "so is this command".
        print(f"  {why}")
        print(
            "  Nothing was written: a new acceptance cannot be numbered against a "
            "record that cannot be read. Fix that block first."
        )
        return outcome.result("INCOMPLETE")
    existing = [b for _, b in recorded if b.get("finding") == args.finding]
    renewals = max((renewals_of(b) for b in existing), default=-1) + 1
    if renewals > MAX_RENEWALS:
        print(
            f"  {args.finding} has already been renewed {MAX_RENEWALS} times. "
            f"That is the ceiling: fix it, or change the answer."
        )
        return outcome.result("FAIL")
    # The nth risk of this spec, which is what the number is supposed to read as. Counting
    # every block in the repository made the first risk recorded against a spec number eight.
    number = sum(1 for at, _ in recorded if at == where) + 1
    fields = {
        "id": f"R-{re.sub(r'[^0-9]', '', where.parent.name)[:3]}-{number:02d}",
        "finding": args.finding,
        "severity": args.severity,
        "accepted_by": args.by,
        "accepted": date.today().isoformat(),
        "expires": args.expires,
        "renewals": renewals,
        "justification": args.justification,
        "evidence": evidence,
        "follow_up": args.follow_up,
    }
    try:
        add(where, fields)
        after = blocks(root)
        expected = {**fields, "renewals": str(renewals)}
        if len(after) != len(recorded) + 1 or (where, expected) not in after:
            raise OSError("risk acceptance postcondition did not hold")
        if _evidence_reference(root, args.evidence, where) != evidence:
            raise OSError("evidence changed before the acceptance completed")
    except (OSError, ValueError):
        print(
            "  INCOMPLETE  the exact acceptance could not be proven after writing. Inspect "
            "the target spec before retrying."
        )
        return outcome.result("INCOMPLETE")
    print(
        f"  ✓ recorded in {where.relative_to(root)} — it expires {args.expires}, and both "
        f"pre-push and doctor read that date."
    )
    return outcome.result("PASS")
