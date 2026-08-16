"""A decision is born inside its spec, and is promoted only when it earns it.

The single question that decides promotion: does this decision constrain specs that do
not exist yet? If the answer is no it stays a block inside its spec, which is where it
has its context and where it is reviewed in the same diff. If it is yes, --madr writes a
proposed Structured MADR in docs/adr/NNNN-title.md. It does not edit the spec or grant the
proposal authority: the file becomes the one reviewable home.

Numbers collide between concurrent branches. That is the classic failure of every ADR
tool and it is not hidden behind a numbering service: it collides, doctor names it, and
a file is renamed in review like any other conflict.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import stat
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from ai_engineering import intent as intents
from ai_engineering import madr, outcome, paths, text
from ai_engineering import spec as specs
from ai_engineering.intent import Validation

MADR_BODY = """# {number}. {title}

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

_DIR_FD_REQUIRED = (os.open, os.mkdir, os.unlink, os.rmdir, os.stat)
_FD_REQUIRED = (os.listdir,)
_NOFOLLOW_REQUIRED = (os.stat,)


def adr_dir(root: Path) -> Path:
    return root / "docs" / "adr"


def next_number(root: Path) -> str:
    used = [int(p.name[:4]) for p in adr_dir(root).glob("[0-9][0-9][0-9][0-9]-*.md")]
    return f"{max(used, default=0) + 1:04d}"


@dataclass(frozen=True, slots=True)
class _Promotion:
    path: Path
    filename: str
    home: _Home


@dataclass(slots=True)
class _Home:
    root_fd: int = -1
    docs_fd: int = -1
    adr_fd: int = -1
    docs_created: bool = False
    adr_created: bool = False
    docs_identity: tuple[int, int] | None = None
    adr_identity: tuple[int, int] | None = None


class _WriteFailure(OSError):
    def __init__(self, residue: bool) -> None:
        self.residue = residue
        super().__init__("MADR could not be created")


def _title(value: str) -> str:
    title = value.strip()
    if not title:
        raise ValueError("a decision needs a title")
    return title


def _slug(title: str, number: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60].strip("-")
    return slug or f"decision-{number}"


def _render_proposal(number: str, title: str, supersedes: str, spec: Path) -> str:
    record = {
        "schema": "urn:ai-engineering:madr:1",
        "schema_version": "1",
        "type": "adr",
        "id": number,
        "title": title,
        "date": date.today().isoformat(),
        "spec": spec.parent.name[:3],
        "status": "proposed",
        "supersedes": supersedes,
    }
    header = "\n".join(
        f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in record.items()
    )
    return f"---\n{header}\n---\n\n{MADR_BODY.format(number=number, title=title)}"


def _require_anchored_io() -> tuple[int, int]:
    if not all(hasattr(os, name) for name in ("O_DIRECTORY", "O_NOFOLLOW")):
        raise OSError("descriptor-relative writes are unsupported")
    if (
        not all(function in os.supports_dir_fd for function in _DIR_FD_REQUIRED)
        or not all(function in os.supports_fd for function in _FD_REQUIRED)
        or not all(function in os.supports_follow_symlinks for function in _NOFOLLOW_REQUIRED)
    ):
        raise OSError("descriptor-relative writes are unsupported")
    directory = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    exclusive = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    return directory, exclusive


def _identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


def _at(parent_fd: int, name: str) -> os.stat_result:
    return os.stat(name, dir_fd=parent_fd, follow_symlinks=False)


def _same_entry(parent_fd: int, name: str, identity: tuple[int, int] | None) -> bool:
    if parent_fd < 0 or identity is None:
        return False
    try:
        return _identity(_at(parent_fd, name)) == identity
    except OSError:
        return False


def _exists_at(parent_fd: int, name: str) -> bool:
    try:
        _at(parent_fd, name)
    except OSError:
        return False
    return True


def _close_home(home: _Home) -> None:
    for descriptor in (home.adr_fd, home.docs_fd, home.root_fd):
        if descriptor >= 0:
            with contextlib.suppress(OSError):
                os.close(descriptor)


def _directory_linked(descriptor: int) -> bool:
    if descriptor < 0:
        return False
    try:
        return os.fstat(descriptor).st_nlink != 0
    except OSError:
        return True


def _cleanup(home: _Home, filename: str, created_file: bool) -> bool:
    docs_changed = home.docs_fd >= 0 and not _same_entry(home.root_fd, "docs", home.docs_identity)
    adr_changed = home.adr_fd >= 0 and not _same_entry(home.docs_fd, "adr", home.adr_identity)
    if created_file and home.adr_fd >= 0:
        with contextlib.suppress(OSError):
            os.unlink(filename, dir_fd=home.adr_fd)
    file_remains = bool(filename) and (home.adr_fd < 0 or _exists_at(home.adr_fd, filename))
    if home.adr_created and _same_entry(home.docs_fd, "adr", home.adr_identity):
        with contextlib.suppress(OSError):
            os.rmdir("adr", dir_fd=home.docs_fd)
    if home.docs_created and _same_entry(home.root_fd, "docs", home.docs_identity):
        with contextlib.suppress(OSError):
            os.rmdir("docs", dir_fd=home.root_fd)
    return (
        docs_changed
        or adr_changed
        or file_remains
        or (home.adr_created and _directory_linked(home.adr_fd))
        or (home.docs_created and _directory_linked(home.docs_fd))
    )


def _mkdir_at(parent_fd: int, name: str) -> bool:
    try:
        os.mkdir(name, dir_fd=parent_fd)
    except FileExistsError:
        return False
    return True


def _open_home(root: Path) -> _Home:
    home = _Home()
    try:
        directory_flags, _ = _require_anchored_io()
        home.root_fd = os.open(os.fspath(root), directory_flags)
        home.docs_created = _mkdir_at(home.root_fd, "docs")
        docs_info = _at(home.root_fd, "docs")
        home.docs_identity = _identity(docs_info)
        if not stat.S_ISDIR(docs_info.st_mode):
            raise OSError("docs is not a directory")
        home.docs_fd = os.open("docs", directory_flags, dir_fd=home.root_fd)
        if _identity(os.fstat(home.docs_fd)) != home.docs_identity:
            raise OSError("docs changed while opening")
        home.adr_created = _mkdir_at(home.docs_fd, "adr")
        adr_info = _at(home.docs_fd, "adr")
        home.adr_identity = _identity(adr_info)
        if not stat.S_ISDIR(adr_info.st_mode):
            raise OSError("adr is not a directory")
        home.adr_fd = os.open("adr", directory_flags, dir_fd=home.docs_fd)
        if _identity(os.fstat(home.adr_fd)) != home.adr_identity:
            raise OSError("adr changed while opening")
    except OSError as error:
        residue = _cleanup(home, "", False)
        _close_home(home)
        raise _WriteFailure(residue) from error
    return home


def _next_number_at(adr_fd: int) -> str:
    used = [int(name[:4]) for name in os.listdir(adr_fd) if re.fullmatch(r"[0-9]{4}-.*\.md", name)]
    return f"{max(used, default=0) + 1:04d}"


def _create(root: Path, title: str, supersedes: str, spec: Path | None) -> _Promotion:
    if spec is None:
        raise LookupError("a MADR needs exactly one local spec")
    title = _title(title)
    home = _open_home(root)
    filename = ""
    created_file = False
    file_fd = -1
    try:
        _, exclusive_flags = _require_anchored_io()
        number = _next_number_at(home.adr_fd)
        filename = f"{number}-{_slug(title, number)}.md"
        file_fd = os.open(filename, exclusive_flags, 0o666, dir_fd=home.adr_fd)
        created_file = True
        stream = os.fdopen(file_fd, "w", encoding="utf-8", newline="\n")
        file_fd = -1
        with stream:
            proposal = _render_proposal(number, title, supersedes, spec)
            if stream.write(proposal) != len(proposal):
                raise OSError("MADR write was incomplete")
    except OSError as error:
        if file_fd >= 0:
            with contextlib.suppress(OSError):
                os.close(file_fd)
        residue = _cleanup(home, filename, created_file)
        _close_home(home)
        raise _WriteFailure(residue) from error
    return _Promotion(adr_dir(root) / filename, filename, home)


def promote(root: Path, title: str, supersedes: str, spec: Path | None) -> Path:
    promotion = _create(root, title, supersedes, spec)
    _close_home(promotion.home)
    return promotion.path


def _refuse_invalid(result: Validation, state: str = "Nothing was written.") -> outcome.Result:
    print(f"  INCOMPLETE [{result.code}]: {result.reason}. {state}")
    return outcome.result(result.outcome)


def _refuse_write(failure: _WriteFailure) -> outcome.Result:
    if failure.residue:
        state = "Repository state remains under docs/adr/; inspect it before retrying."
    else:
        state = "No change remains."
    print(f"  INCOMPLETE [MADR_WRITE_FAILED]: MADR could not be created. {state}")
    return outcome.result("INCOMPLETE")


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
        match = re.search(r"^status:\s*(.+)$", head, re.M)
        raw_status = match.group(1).strip() if match else ""
        try:
            status = json.loads(raw_status) if raw_status.startswith('"') else raw_status
        except (json.JSONDecodeError, TypeError):
            status = "?"
        if not isinstance(status, str) or not (
            status in {"proposed", "accepted", "rejected", "superseded"}
            or re.fullmatch(r"superseded by [0-9]{4}", status)
        ):
            status = "?"
        rows.append(f"  {path.stem:<44} {status}")
    return rows


def granted(root: Path) -> tuple[str, str] | str:
    """The authority this repository already recorded, or why there is none.

    Not asked for again, and never invented. The Solution Intent is committed, validated
    and carries the human who approved it; a record transition is that same authority
    applied to a smaller thing. An Intent that does not validate grants nothing, and one
    still in draft grants nothing either, because a draft has no approval block to read —
    which is the whole point of the draft state.

    This is the specification's own second path: "an authorized human **or preapproved
    policy**". The policy is the approved Intent, and it is one a person committed."""

    home = root / ".ai" / "intent.md"
    verdict = intents.validate(home, root)
    if verdict.outcome != "PASS":
        why = verdict.code or "unknown"
        return f"the Solution Intent does not validate ({why}), so it grants nothing"
    try:
        lifecycle = json.loads(home.read_text(encoding="utf-8"))["lifecycle"]
        approval = lifecycle["approval"]
        role, reference = approval["authority_role"], approval["approval_ref"]
    except (KeyError, OSError, ValueError):
        return "the Solution Intent is a draft, so it carries no approval to act on"
    if re.search(r"agent|reviewer", role, re.IGNORECASE):
        return (
            f"the recorded role is {role!r}, and a record is never accepted by an "
            "agent or a reviewer"
        )
    return role, reference


def accept(root: Path, number: str) -> outcome.Result:
    """Move one MADR out of `proposed`, with the three fields the schema wants together.

    Every one of them is read or measured, never typed at a person: the role and the
    reference come from the approved Intent, and the timestamp is now. The transition still
    has to be its own commit, because that is what the validator checks and it is what
    makes the change reviewable — so this writes the record and names the commit rather
    than making it."""

    # Four digits and nothing else, and then the directory is read rather than searched.
    # `--accept` takes text off the command line and this built a glob pattern out of it:
    # `..` is a legal glob segment, so `--accept ../../../../etc/rc` matched a file outside
    # `docs/adr` and the rewrite below would have edited it. A framework whose subject is
    # filesystem authority does not get to make that mistake in its own record verb.
    #
    # Both halves, and the second is the one that holds. A validated number is a promise
    # about this call; listing the directory and comparing names is a property of the code —
    # every path here comes from `adr_dir(root)` and the argument never touches path
    # construction at all, so there is no spelling of it that reaches outside.
    if re.fullmatch(r"[0-9]{4}", number) is None:
        print(f"  INCOMPLETE: {number!r} is not a four-digit MADR number")
        return outcome.result("INCOMPLETE")
    try:
        entries = sorted(adr_dir(root).iterdir())
    except OSError:
        print("  INCOMPLETE: docs/adr could not be read")
        return outcome.result("INCOMPLETE")
    found = [
        entry
        for entry in entries
        if entry.is_file() and entry.suffix == ".md" and entry.name.startswith(f"{number}-")
    ]
    if len(found) != 1:
        print(f"  INCOMPLETE: {len(found)} MADRs are numbered {number}")
        return outcome.result("INCOMPLETE")
    decision = found[0]
    raw = decision.read_bytes()
    if madr._parse(raw).raw_fields.get("status") != '"proposed"':
        print(f"  INCOMPLETE: {number} has already left `proposed`; accepting is not repeatable")
        return outcome.result("INCOMPLETE")

    authority = granted(root)
    if isinstance(authority, str):
        print(f"  INCOMPLETE: {authority}")
        return outcome.result("INCOMPLETE")
    role, reference = authority
    stamped = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    decision.write_text(
        raw.decode("utf-8").replace(
            'status: "proposed"',
            f'status: "accepted"\nauthority_role: "{role}"\n'
            f'approval_ref: "{reference}"\napproved_at: "{stamped}"',
            1,
        ),
        encoding="utf-8",
    )
    print(f"  {decision.relative_to(root)} accepted as {role}, on the authority of {reference}")
    print(f"  commit it on its own: git add {decision.relative_to(root)} && git commit")
    return outcome.result("PASS")


def main(argv: list[str]) -> outcome.Result:
    parser = argparse.ArgumentParser("ai-eng decide", allow_abbrev=False)
    parser.add_argument("title", nargs="?", default="")
    parser.add_argument("--madr", action="store_true", help="propose it in docs/adr/")
    parser.add_argument("--supersede", default="", metavar="NNNN")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--accept", default="", metavar="NNNN", help="accept a proposed MADR")
    parser.add_argument("--why", default="", help="the rationale, when it stays inside the spec")
    parser.add_argument(
        "--spec", default="", help="which spec it belongs to; needed when more than one is open"
    )
    args = parser.parse_args(argv)

    if not args.list and not args.accept:
        try:
            title = _title(args.title)
        except ValueError as why:
            parser.error(str(why))

    root = paths.repo_root()
    if root is None:
        print("not inside a repository")
        return outcome.result("INCOMPLETE")
    if args.accept:
        return accept(root, args.accept)
    if args.list:
        try:
            rows = listing(root)
        except OSError as why:
            print(f"  INCOMPLETE [MADR_UNREADABLE]: MADRs could not be listed: {why}")
            return outcome.result("INCOMPLETE")
        print("\n".join(rows) if rows else "  no MADRs yet — most decisions never need one")
        return outcome.result("PASS")
    # Named, or the only one open. It used to resolve to whichever directory sorted last,
    # and that is how two decisions written for spec 003 landed in another session's spec,
    # because a fourth directory appeared between two commands.
    if args.madr:
        existing = madr.validate(root)
        if existing.outcome != "PASS":
            return _refuse_invalid(existing)
        try:
            target = specs.target(root, args.spec)
        except LookupError as why:
            print(f"  INCOMPLETE [MADR_GRAPH_INVALID]: {why}. Nothing was written.")
            return outcome.result("INCOMPLETE")
        try:
            promoted = _create(root, title, args.supersede, target)
        except _WriteFailure as failure:
            return _refuse_write(failure)
        try:
            result = madr.validate(root)
            if result.outcome != "PASS":
                residue = _cleanup(promoted.home, promoted.filename, True)
                state = (
                    "Repository state remains under docs/adr/; inspect it before retrying."
                    if residue
                    else "No change remains."
                )
                return _refuse_invalid(result, state)
        finally:
            _close_home(promoted.home)
        print(f"  ✓ {promoted.path.relative_to(root)}")
        print("    outcome: PASS. status: proposed; this record grants no authority.")
        return outcome.result("PASS")
    try:
        spec = specs.target(root, args.spec)
    except (LookupError, OSError) as why:
        print(f"  {why}")
        return outcome.result("INCOMPLETE")
    try:
        append(
            spec,
            {
                "decision": title,
                "date": date.today().isoformat(),
                "rationale": args.why or "TODO: why, in one sentence",
            },
        )
    except OSError as why:
        print(f"  INCOMPLETE [DECISION_WRITE_FAILED]: decision could not be recorded: {why}")
        return outcome.result("INCOMPLETE")
    print(
        f"  ✓ recorded in {spec.relative_to(root)}. If it constrains specs that do not exist "
        f"yet, promote it with --madr."
    )
    return outcome.result("PASS")
