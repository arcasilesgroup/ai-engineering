"""specs/NNN-slug/spec.md — the record, in the user's repository, in their diff.

Specs live at the root and not inside a hidden directory, deliberately: a governance
record hidden in a dot-directory is a record nobody reviews, because reviewers read the
file tree and do not expand hidden folders. There is no drafts/ either — a draft is a
spec with status: draft from the first keystroke, on a branch. That is not tidiness, it
is data loss: `git clean -ndx` eats a draft that sits inside a committed directory.
"""

from __future__ import annotations

import argparse
import contextlib
import re
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from ai_engineering import intent, outcome, paths, spec_transaction

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/#-]*$")
_NON_AUTHORITY = re.compile(r"(^|[^A-Za-z0-9])(agent|model|reviewer)([^A-Za-z0-9]|$)", re.I)
_CANONICAL_SPEC = re.compile(r"^([0-9]{3})-[a-z0-9]+(?:-[a-z0-9]+)*$")
_PENDING_SPEC = re.compile(r"^pending-([0-9]{3})-[a-z0-9]+(?:-[a-z0-9]+)*$")
_MAX_FILE_BYTES = 100_000
_MAX_GRAPH_FILES = 128
_MAX_SLUG = 80
_MAX_REF = 256
_document_relations = intent._document_relations
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


def _render(number: str, slug: str, ref: str) -> bytes:
    return TEMPLATE.format(
        number=number,
        slug=slug,
        today=date.today().isoformat(),
        ref=f'"{ref}"' if ref else '""',
        title=slug.replace("-", " ").capitalize(),
        boxes="\n".join(f"- [ ] {box}" for box in BOXES),
    ).encode()


def _number(inventory: spec_transaction.Inventory) -> str:
    used: set[int] = set()
    for name in inventory.names:
        if name == ".gitkeep":
            continue
        matched = _CANONICAL_SPEC.fullmatch(name) or _PENDING_SPEC.fullmatch(name)
        if matched is None:
            if name[:1].isdecimal() or name.lower().startswith("pending-"):
                raise spec_transaction.Unsafe("spec namespace contains an ambiguous identifier")
            continue
        identifier = int(matched.group(1))
        if identifier in used:
            raise spec_transaction.Unsafe("spec namespace contains a duplicate identifier")
        used.add(identifier)
    next_identifier = max(used, default=0) + 1
    if next_identifier > 999:
        raise spec_transaction.Unsafe("spec identifier range is exhausted")
    return f"{next_identifier:03d}"


def _canonical_specs(root: Path) -> list[Path]:
    home = specs_dir(root)
    try:
        home_value = home.lstat()
    except FileNotFoundError:
        return []
    if not stat.S_ISDIR(home_value.st_mode) or stat.S_ISLNK(home_value.st_mode):
        raise OSError("specs home is not one regular repository directory")
    found: list[Path] = []
    for folder in home.iterdir():
        if _CANONICAL_SPEC.fullmatch(folder.name) is None:
            continue
        folder_value = folder.lstat()
        if not stat.S_ISDIR(folder_value.st_mode) or stat.S_ISLNK(folder_value.st_mode):
            raise OSError("canonical spec entry is not one regular directory")
        candidate = folder / "spec.md"
        try:
            candidate_value = candidate.lstat()
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(candidate_value.st_mode) or stat.S_ISLNK(candidate_value.st_mode):
            raise OSError("canonical spec file is not one regular file")
        found.append(candidate)
    return sorted(found)


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
        matches = [path for path in _canonical_specs(root) if path.parent.name.startswith(named)]
        if not matches:
            raise LookupError(f"no spec matches {named!r}")
        if len(matches) > 1:
            raise LookupError(
                f"{named!r} matches {', '.join(m.parent.name for m in matches)}. Name one of them."
            )
        return matches[0]
    every = _canonical_specs(root)
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
    for spec in _canonical_specs(root):
        head = spec.read_text(errors="replace")[:600]
        status = (re.search(r"^status:\s*(\S+)", head, re.M) or [None, "?"])[1]
        if status == "superseded" and not everything:
            continue
        title = (re.search(r"^# (.+)$", head, re.M) or [None, spec.parent.name])[1]
        rows.append(f"  {spec.parent.name:<28} {status:<12} {title}")
    return rows


def _argument(
    pattern: re.Pattern[str],
    label: str,
    *,
    allow_empty: bool = False,
    maximum: int | None = None,
):
    def parse(value: str) -> str:
        if (maximum is not None and len(value) > maximum) or (
            not (allow_empty and value == "") and pattern.fullmatch(value) is None
        ):
            raise argparse.ArgumentTypeError(f"{label} is not canonical")
        return value

    return parse


@dataclass(frozen=True, slots=True)
class _Snapshot:
    record: Mapping[str, Any] | None
    validation: intent.Validation
    observations: tuple[spec_transaction.Observation, ...]


def _schema_invalid() -> intent.Validation:
    return intent.Validation("INCOMPLETE", *intent.SCHEMA_INVALID)


def _materialize(writer: Any) -> _Snapshot:
    observations: dict[str, spec_transaction.Observation] = {}
    try:
        authority = writer.read(".ai/intent.md", maximum=_MAX_FILE_BYTES)
        observations[authority.path] = authority
        record = intent._json(authority.body)
        if not isinstance(record, dict) or not isinstance(record.get("relations"), list):
            return _Snapshot(None, _schema_invalid(), tuple(observations.values()))
        pending: list[str] = []
        for relation in record["relations"]:
            if not isinstance(relation, dict) or not isinstance(relation.get("path"), str):
                return _Snapshot(record, _schema_invalid(), tuple(observations.values()))
            pending.append(relation["path"])
        while pending:
            relative = pending.pop()
            if relative == ".ai/intent.md" or relative in observations:
                continue
            if len(observations) >= _MAX_GRAPH_FILES:
                validation = intent.Validation(
                    "INCOMPLETE", "INTENT_RELATION_BROKEN", "relation graph exceeds its bound"
                )
                return _Snapshot(record, validation, tuple(observations.values()))
            observed = writer.read(relative, maximum=_MAX_FILE_BYTES)
            observations[relative] = observed
            try:
                linked = _document_relations(observed.body)
            except (RecursionError, TypeError, ValueError):
                break
            pending.extend(linked)
        materialized = {path: observed.body for path, observed in observations.items()}
        validation = intent.validate(record, materialized)
        return _Snapshot(record, validation, tuple(observations.values()))
    except (RecursionError, TypeError, ValueError):
        return _Snapshot(None, _schema_invalid(), tuple(observations.values()))


def _authority(snapshot: _Snapshot) -> intent.Validation:
    """Only an exact materialized Intent snapshot may grant this bounded mutation."""
    if snapshot.validation.outcome != "PASS" or snapshot.record is None:
        return snapshot.validation
    try:
        lifecycle = snapshot.record["lifecycle"]
        approval = lifecycle["approval"]
        transition = lifecycle["transitions"][-1]
        role = approval["authority_role"]
        owner = snapshot.record["ownership"]["accountable_role"]
    except (IndexError, KeyError, RecursionError, TypeError, ValueError):
        return _schema_invalid()
    if (
        lifecycle["status"] != "active"
        or role != owner
        or transition["authority_role"] != role
        or transition["approval_ref"] != approval["approval_ref"]
        or _NON_AUTHORITY.search(role)
    ):
        return _MISSING_AUTHORITY
    return intent.PASS


def _same_snapshot(
    before: _Snapshot,
    after: _Snapshot,
    pending: spec_transaction.Pending,
) -> bool:
    if before.validation != intent.PASS or after.validation != intent.PASS:
        return False
    left = {item.path: item for item in before.observations}
    right = {item.path: item for item in after.observations}
    if left.keys() != right.keys():
        return False
    for path, earlier in left.items():
        later = right[path]
        if (
            earlier.path != later.path
            or earlier.body != later.body
            or earlier.generation != later.generation
            or earlier.maximum != later.maximum
            or len(earlier.parents) != len(later.parents)
        ):
            return False
        for old_parent, new_parent in zip(earlier.parents, later.parents, strict=True):
            if old_parent.path != new_parent.path:
                return False
            if old_parent.path == "specs":
                if (
                    old_parent.identity != new_parent.identity
                    or new_parent != pending.home_generation
                ):
                    return False
            elif old_parent != new_parent:
                return False
    return True


@dataclass(frozen=True, slots=True)
class _Report:
    execution: outcome.Execution
    lines: tuple[str, ...]


def _incomplete_report(
    code: str,
    message: str,
    *,
    proven_pending: str | None = None,
    possible_pending: str | None = None,
    retryable: bool = True,
) -> _Report:
    if proven_pending is not None and possible_pending is not None:
        raise ValueError("pending state cannot be both proven and possible")
    changes = []
    checks = []
    remaining = ["No canonical spec was published"]
    next_actions = ["restore one stable approved Intent snapshot and run spec new again"]
    lines = [f"  INCOMPLETE  {message}"]
    if proven_pending is not None:
        relative = f"specs/{proven_pending}/spec.md"
        changes.append(
            outcome.fact(
                "spec-pending",
                "INCOMPLETE",
                "A noncanonical pending spec state requires inspection",
                relative,
            )
        )
        remaining.append(f"Inspect or remove {relative} before retrying")
        next_actions = [f"inspect {relative}; remove it only after proving it is this attempt"]
        lines.append(f"    pending: {relative}")
    elif possible_pending is not None:
        relative = f"specs/{possible_pending}/spec.md"
        remaining.append(f"If {relative} exists, inspect it before retrying")
        next_actions = [f"if {relative} exists, inspect it without assuming ownership"]
        checks.append(
            outcome.fact(
                "spec-pending-possible",
                "INCOMPLETE",
                "A stage failure left the pending path existence or ownership unproven",
                relative,
            )
        )
        lines.append(f"    possible pending: {relative}; inspect only if it exists")
    checks.append(outcome.fact("spec-publication", "INCOMPLETE", message))
    execution = outcome.execution(
        outcome.result("INCOMPLETE"),
        summary=message,
        changes=changes,
        checks=checks,
        remaining=remaining,
        next_actions=next_actions,
        execution_error=outcome.error(code, message, retryable, next_actions[0]),
    )
    return _Report(execution, tuple(lines))


def _finish(report: _Report) -> outcome.Execution:
    with contextlib.suppress(OSError, UnicodeError):
        for line in report.lines:
            print(line)
    return report.execution


def _transaction_kind(problem: spec_transaction.TransactionError) -> str:
    if isinstance(problem, spec_transaction.Busy):
        return "busy"
    if isinstance(problem, spec_transaction.Unsupported):
        return "unsupported"
    if isinstance(problem, spec_transaction.Collision):
        return "collision"
    return "unsafe"


def _transaction_incomplete(
    problem: spec_transaction.TransactionError,
    *,
    proven_pending: str | None = None,
    possible_pending: str | None = None,
) -> _Report:
    kind = _transaction_kind(problem)
    if kind == "busy":
        return _incomplete_report(
            "SPEC_TRANSACTION_BUSY",
            "another spec transaction holds the canonical Intent lock",
            proven_pending=proven_pending,
            possible_pending=possible_pending,
        )
    if kind == "unsupported":
        return _incomplete_report(
            "SPEC_TRANSACTION_UNSUPPORTED",
            "this filesystem cannot prove a safe spec publication",
            proven_pending=proven_pending,
            possible_pending=possible_pending,
            retryable=False,
        )
    if kind == "collision":
        return _incomplete_report(
            "SPEC_PUBLICATION_COLLISION",
            "the reserved spec destination is no longer exclusive",
            proven_pending=proven_pending,
            possible_pending=possible_pending,
        )
    return _incomplete_report(
        "SPEC_TRANSACTION_UNSAFE",
        "the spec transaction could not prove an unchanged safe filesystem state",
        proven_pending=proven_pending,
        possible_pending=possible_pending,
    )


def _publication_reports(pending: str) -> dict[str, _Report]:
    problems: dict[str, spec_transaction.TransactionError] = {
        "busy": spec_transaction.Busy(),
        "unsupported": spec_transaction.Unsupported(),
        "collision": spec_transaction.Collision(),
        "unsafe": spec_transaction.Unsafe(),
    }
    return {
        kind: _transaction_incomplete(problem, proven_pending=pending)
        for kind, problem in problems.items()
    }


def _new(root: Path, slug: str, ref: str) -> outcome.Execution:
    candidate_name: str | None = None
    pending: spec_transaction.Pending | None = None
    publication_reports: dict[str, _Report] | None = None
    try:
        with spec_transaction.writer(root, ".ai/intent.md", "specs") as transaction:
            inventory = transaction.inventory()
            number = _number(inventory)
            first = _materialize(transaction)
            authority = _authority(first)
            if authority.outcome != "PASS":
                return _finish(
                    _incomplete_report(
                        authority.code or "INTENT_AUTHORITY_MISSING",
                        f"Solution Intent authority is incomplete: {authority.reason}",
                    )
                )

            final_name = f"{number}-{slug}"
            candidate_name = f"pending-{final_name}"
            body = _render(number, slug, ref)
            pending = transaction.stage(inventory, candidate_name, "spec.md", body)

            relative = f"specs/{final_name}/spec.md"
            success_line = f"  ✓ {relative}"
            completed = outcome.execution(
                outcome.result("PASS"),
                summary=f"Created governed spec {final_name}",
                changes=[
                    outcome.fact("spec-created", "APPLIED", "Created governed spec", relative)
                ],
                checks=[
                    outcome.fact(
                        "intent-authority",
                        "PASS",
                        "Solution Intent is actively approved by its accountable role",
                    ),
                    outcome.fact(
                        "authority-snapshot",
                        "PASS",
                        "Authority files and parent generations remained unchanged",
                    ),
                    outcome.fact(
                        "spec-publication",
                        "PASS",
                        "Published the spec with native no-replace semantics",
                        relative,
                    ),
                ],
                remaining=[],
                next_actions=[f"edit and review {relative}"],
            )
            changed_report = _incomplete_report(
                "INTENT_SNAPSHOT_CHANGED",
                "Solution Intent authority changed before publication",
                proven_pending=pending.name,
            )
            publication_reports = _publication_reports(pending.name)

            second = _materialize(transaction)
            second_authority = _authority(second)
            same = _same_snapshot(first, second, pending)
            if second_authority.outcome != "PASS" or not same:
                return _finish(changed_report)
            transaction.publish(pending, final_name)
            with contextlib.suppress(OSError, UnicodeError):
                print(success_line)
            return completed
    except spec_transaction.TransactionError as problem:
        if publication_reports is not None:
            report = publication_reports[_transaction_kind(problem)]
        elif pending is not None:
            report = _transaction_incomplete(problem, proven_pending=pending.name)
        else:
            report = _transaction_incomplete(problem, possible_pending=candidate_name)
        return _finish(report)


def main(argv: list[str]) -> outcome.Result | outcome.Execution:
    parser = argparse.ArgumentParser("ai-eng spec")
    sub = parser.add_subparsers(dest="action", required=True)
    made = sub.add_parser("new")
    made.add_argument("slug", type=_argument(_SLUG, "slug", maximum=_MAX_SLUG))
    made.add_argument(
        "--ref",
        default="",
        type=_argument(_REF, "work item", allow_empty=True, maximum=_MAX_REF),
        help='a work item, e.g. "owner/repo#45"',
    )
    shown = sub.add_parser("show")
    shown.add_argument("id", type=_argument(re.compile(r"^[0-9]+$"), "spec id"))
    listed = sub.add_parser("list")
    listed.add_argument("--all", action="store_true", help="include superseded specs")
    # The one subcommand here that reaches a remote, and the reason `spec`'s declared scope
    # names one. A claim is a decision recorded where the other machine can also read it —
    # which is what this verb is for — and it is the only shape of that decision two agents
    # who cannot talk to each other can both act on.
    taken = sub.add_parser("claim")
    taken.add_argument("item", type=_argument(_REF, "work item", maximum=_MAX_REF))
    taken.add_argument("--base", required=True, help="the exact SHA this claim is taken against")
    taken.add_argument("--path", action="append", default=[], required=True)
    taken.add_argument("--role", required=True)
    taken.add_argument("--remote", default="origin")
    sub.add_parser("checkpoint")
    args = parser.parse_args(argv)

    root = paths.repo_root()
    if root is None:
        print("not inside a repository")
        return outcome.result("INCOMPLETE")
    if args.action == "checkpoint":
        from ai_engineering import checkpoint

        return checkpoint.verify(root)
    if args.action == "claim":
        from ai_engineering import claim

        return claim.take(root, args.item, args.base, args.path, args.role, args.remote)
    if args.action == "new":
        return _new(root, args.slug, args.ref)
    if args.action == "list":
        try:
            rows = listing(root, args.all)
        except OSError as why:
            print(f"  INCOMPLETE  specs could not be listed: {why}")
            return outcome.result("INCOMPLETE")
        print("\n".join(rows) if rows else "  no specs yet — `ai-eng spec new <slug>`")
        return outcome.result("PASS")
    try:
        matches = [path for path in _canonical_specs(root) if path.parent.name.startswith(args.id)]
    except OSError:
        print("  INCOMPLETE  specs could not be read safely")
        return outcome.result("INCOMPLETE")
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
