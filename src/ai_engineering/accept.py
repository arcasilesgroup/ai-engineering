"""An accountable role accepted this finding until date D, for reason R, against spec S.

That artifact is what an engineering lead hands an auditor, and it is the line between this
product and a bundle of prompts. It expires. Assertion 16 and the pre-push hook both read
it, so a repository with no CI still expires on push, and two renewals is the ceiling —
after that the finding gets fixed or the answer changes.

The record is published, never edited in. Earlier versions appended YAML by rewriting the
whole `spec.md`, and no supported system can rewrite a file conditionally on it still
holding what you read: Linux `renameat2` has no expected-destination predicate, Apple's
exclusive rename refuses an existing destination rather than comparing it, and Windows
`ReplaceFileW` replaces whatever is at the name. So every acceptance is one immutable
directory published by an exclusive no-replace rename, `spec.md` is never opened for write,
and a colliding writer loses the race without losing its bytes.

What this command proves and what it does not: it proves that the exact bytes displayed
were the bytes bound, and that the record became visible atomically at a name nothing
else held. It does not prove who answered, that the sources stayed current in the
unobservable window after the last read, that the record survives power loss, or that
anything stops a repository owner from editing the file afterwards. Git review remains the
durable history.
"""

from __future__ import annotations

import argparse
import os
import re
import stat
import unicodedata
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path, PurePosixPath

from ai_engineering import (
    acceptance,
    acceptance_privacy,
    outcome,
    paths,
    spec,
    spec_transaction,
)

MAX_RENEWALS = 2
_MAX_EVIDENCE_BYTES = 100_000
# A role, never a person. Every one of these is somebody nobody can be held to, and an
# acceptance whose owner cannot be held to anything is a note.
_DENIED_ROLE_TOKENS = frozenset(
    {
        "agent",
        "assistant",
        "ai",
        "bot",
        "model",
        "reviewer",
        "self",
        "myself",
        "unknown",
        "unassigned",
        "unspecified",
        "someone",
        "somebody",
        "tbd",
        "todo",
    }
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


def expired(root: Path) -> list[dict]:
    """The acceptances past their date, read through the one register there is.

    This used to hold its own YAML parser. Two parsers of the same bytes drift, and the
    thing they would eventually disagree about is which risks are live — which is what the
    push gate and assertion 16 block on. `acceptance` is now the only reader; this is the
    shape those two callers already speak, and the refusal they already handle.

    A renewal retires what it renews, so only the unique head of each chain is judged. An
    undecidable register raises rather than reporting nothing found, because nothing found
    is indistinguishable from nothing wrong.
    """

    register = acceptance.expired(root)
    if register.outcome != "PASS":
        raise ValueError(register.reason)
    return [
        {
            "id": entry.id or "?",
            "finding": entry.finding,
            "expires": entry.expires,
            "home": entry.home,
            "provenance": entry.provenance,
        }
        for entry in register.entries
    ]


def denied_role(role: str) -> bool:
    """Compare the way an attacker would spell it, not the way a policy wishes it were
    spelled. Compatibility-normalize, case-fold, split on everything that is not a letter or
    a digit, and reject if any token is one of the denied words."""

    folded = unicodedata.normalize("NFKC", role).casefold()
    tokens = {token for token in re.split(r"[^0-9a-z]+", folded) if token}
    return bool(tokens & _DENIED_ROLE_TOKENS)


def controlling_terminal_response(expected: str) -> bool:
    """Read one line from the OS controlling terminal and compare it to the exact challenge.

    `isatty`, a flag, an environment value and piped standard input are all things a script
    can supply, so none of them are read here. What this observes is that matching bytes
    arrived through the controlling-terminal boundary — not that a particular human was
    present, and not that they were entitled to the role they claimed. P0 has no proof of
    either, and no outcome this module returns says otherwise.
    """

    device = "CONIN$" if os.name == "nt" else "/dev/tty"
    try:
        with open(device, encoding="utf-8") as terminal:
            answer = terminal.readline()
    except OSError:
        # The device name is deliberately not reported: it names a machine.
        return False
    return answer.rstrip("\r\n") == expected


def _digest_of(root: Path, relative: str, maximum: int) -> str:
    """One bounded, anchored read of a repository-relative regular file."""

    target = root.joinpath(*PurePosixPath(relative).parts)
    try:
        component = root
        for part in PurePosixPath(relative).parts:
            component /= part
            if component.is_symlink():
                raise _EvidenceProblem("an anchored path component is a symbolic link")
        value = target.lstat()
        if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
            raise _EvidenceProblem("an anchored path is not one singly linked regular file")
        if value.st_dev != root.lstat().st_dev:
            raise _EvidenceProblem("an anchored path crosses a filesystem boundary")
        if not 0 < value.st_size <= maximum:
            raise _EvidenceProblem("an anchored file is empty or exceeds its bound")
        body = target.read_bytes()
    except OSError as error:
        # A path this command cannot even read is a refusal, never a traceback: an
        # unreadable source has to leave the tree untouched and say so.
        raise _EvidenceProblem("an anchored file could not be read") from error
    if len(body) != value.st_size:
        raise _EvidenceProblem("an anchored file changed while it was read")
    return "sha256:" + sha256(body).hexdigest()


def publish(root: Path, slug: str, record: dict) -> str:
    """Stage one canonical record and commit it with the native exclusive rename.

    The rename is the only commit point. Once it reports success the record exists and this
    is a `PASS`; there is no later check that can downgrade that, because a check that could
    would make a retry overwrite a published decision.
    """

    body = acceptance.canonical_bytes(record)
    # Validated against the schema before anything is staged. A record that only the reader
    # would refuse is worse than one that is never written: it is published, immutable, and
    # permanently unreadable.
    acceptance.validate_record(body, f"specs/{slug}/{record['id']}", acceptance.schema())
    final = "acceptance-" + record["id"].lower()
    # The lock is the repository's authority file, the same one `spec new` holds, and not
    # the spec being cited. An authority inside the transaction home would see its own
    # staging change the directory it lives in and refuse every publication.
    with spec_transaction.writer(root, ".ai/intent.md", f"specs/{slug}") as writer:
        inventory = writer.inventory()
        if final in inventory.names:
            raise spec_transaction.Collision("that acceptance name is already published")
        pending = writer.stage(inventory, f"pending-{record['id'].lower()}", "record.json", body)
        scanned = acceptance_privacy.gitleaks_v1(root / "specs" / slug / pending.name)
        if scanned.outcome != "PASS":
            # The refusal happens before the commit point, so the staged entry is removed
            # and the tree is left exactly as it was found.
            writer.discard(pending)
            raise _Refused(scanned.outcome, scanned.reason)
        writer.publish(pending, final)
    return f"specs/{slug}/{final}/record.json"


class _Refused(Exception):
    """A privacy check decided against the candidate before anything was published."""

    def __init__(self, verdict: str, reason: str) -> None:
        self.verdict, self.reason = verdict, reason
        super().__init__(reason)


def main(argv: list[str]) -> outcome.Result | outcome.Execution:
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
                f"  EXPIRED  {block['id']}  {block['finding']}  "
                f"expired {block['expires']}  recorded in {block['home']} ({block['provenance']})"
            )
        if stale:
            print(
                "  An acceptance that ran out is not an acceptance. Fix it or renew it "
                "with a reason, up to twice."
            )
        return outcome.result("FAIL" if stale else "PASS")

    if denied_role(args.by):
        print(
            "  INCOMPLETE  risk needs one accountable human role; agents, models, reviewers "
            "and placeholders cannot accept it."
        )
        return outcome.result("INCOMPLETE")
    if args.expires < _utc_today():
        print("  INCOMPLETE  an acceptance cannot already be expired. Use a current date.")
        return outcome.result("INCOMPLETE")
    try:
        where = spec.target(root, args.spec)
        slug = where.parent.name
        owner = acceptance.owner_of(slug)
    except (LookupError, OSError, acceptance.Refusal) as why:
        print(f"  {why}")
        print("  A risk with no context is a note, not a decision.")
        return outcome.result("INCOMPLETE")

    proposed = acceptance.plan(root, args.finding, owner)
    if proposed.outcome == "FAIL":
        print(f"  FAIL  {proposed.reason}. That is the ceiling: fix it, or change the answer.")
        return outcome.result("FAIL")
    if proposed.outcome != "PASS":
        print(f"  INCOMPLETE  {proposed.reason}. Nothing was written.")
        return outcome.result("INCOMPLETE")

    for candidate in (args.finding, args.by, args.justification, args.follow_up):
        for check in (
            acceptance_privacy.acceptance_pii_v1,
            acceptance_privacy.acceptance_machine_path_v1,
        ):
            verdict = check(candidate)
            if verdict.outcome != "PASS":
                print(f"  {verdict.outcome}  {verdict.reason}. Nothing was written.")
                return outcome.result(verdict.outcome)

    try:
        bindings = _bindings(root, slug, args.evidence)
    except _EvidenceProblem as why:
        print(f"  INCOMPLETE  {why}. Nothing was written.")
        return outcome.result("INCOMPLETE")

    register = acceptance.read(root)
    head = (
        acceptance.head_of(register.entries, args.finding) if register.outcome == "PASS" else None
    )
    _display(proposed, args, bindings, slug, head if proposed.renews else None)
    if not controlling_terminal_response(f"ACCEPT {proposed.id} AS {args.by}"):
        print("  INCOMPLETE  no exact confirmation arrived from the controlling terminal.")
        return outcome.result("INCOMPLETE")

    # Everything below re-establishes what was displayed. The date is taken again because a
    # prompt can be answered after midnight, and every source is read again because the
    # answer must bind the bytes the person actually saw.
    accepted = _utc_today()
    if args.expires < accepted:
        print("  INCOMPLETE  the expiry passed while this was being confirmed.")
        return outcome.result("INCOMPLETE")
    try:
        if _bindings(root, slug, args.evidence) != bindings:
            raise _EvidenceProblem("a displayed source changed before it could be bound")
    except _EvidenceProblem as why:
        print(f"  INCOMPLETE  {why}. Nothing was written.")
        return outcome.result("INCOMPLETE")
    if acceptance.plan(root, args.finding, owner) != proposed:
        print("  INCOMPLETE  the register changed while this was being confirmed.")
        return outcome.result("INCOMPLETE")

    record = {
        "schema": "urn:ai-engineering:risk-acceptance:1",
        "schema_version": "1",
        "id": proposed.id,
        "spec": owner,
        "spec_digest": bindings["spec"],
        "finding": args.finding,
        "severity": args.severity,
        "authority_role": args.by,
        "accepted": accepted,
        "expires": args.expires,
        "renewals": proposed.renewals,
        "renews": proposed.renews,
        "renews_digest": proposed.renews_digest,
        "justification": args.justification,
        "evidence": {"path": args.evidence, "content_digest": bindings["evidence"]},
        "follow_up": args.follow_up,
    }
    record["record_digest"] = acceptance.record_digest(record)
    try:
        published = publish(root, slug, record)
    except _Refused as refused:
        print(f"  {refused.verdict}  {refused.reason}. Nothing was published.")
        return outcome.result(refused.verdict)
    except (spec_transaction.TransactionError, acceptance.Refusal) as why:
        print(f"  INCOMPLETE  {why}. Nothing was published.")
        return outcome.result("INCOMPLETE")

    print(f"  ✓ published {published} — it expires {args.expires}, and the push gate reads it.")
    print("  This records the bytes you confirmed. It does not claim who confirmed them.")
    return outcome.execution(
        outcome.result("PASS"),
        summary=f"Published risk acceptance {proposed.id}",
        changes=[
            outcome.fact(
                "risk-acceptance", "APPLIED", f"Published risk acceptance {proposed.id}", published
            )
        ],
    )


def _utc_today() -> str:
    return datetime.now(UTC).date().isoformat()


def _predecessor_bytes(head) -> str:
    """What the person is being asked to renew.

    A canonical record is shown whole, because its bytes are short and exact. A legacy block
    is shown as its home and digest: it is displayed with derived provenance and never
    rewritten, so quoting it back would suggest an edit that is not going to happen.
    """

    if head.provenance != acceptance.CANONICAL_RECORD:
        return f"stored at {head.home}, digest {head.digest}"
    body = (paths.repo_root() or Path()).joinpath(*head.home.split("/"))
    try:
        return body.read_text(encoding="utf-8")
    except OSError:
        return f"unreadable at {head.home}, digest {head.digest}"


def _bindings(root: Path, slug: str, evidence: str) -> dict[str, str]:
    """One bounded anchored read of every source the record will bind."""

    return {
        "spec": _digest_of(root, f"specs/{slug}/spec.md", acceptance.MAX_SPEC_BYTES),
        "evidence": _digest_of(root, evidence, _MAX_EVIDENCE_BYTES),
    }


def _display(proposed, args, bindings: dict[str, str], slug: str, head=None) -> None:
    """The challenge. Everything the record will hold, shown before it is bound, so the
    exact response confirms bytes a person actually read.

    A renewal shows more, not less: the predecessor's complete stored bytes beside the newly
    observed spec and evidence. Renewing a record whose old contents were never displayed is
    signing for something nobody read.
    """

    print(f"  id            {proposed.id}")
    print(f"  finding       {args.finding}")
    print(f"  severity      {args.severity}")
    print(f"  role          {args.by}")
    print(f"  expires       {args.expires}")
    print(f"  justification {args.justification}")
    print(f"  follow-up     {args.follow_up or '(none)'}")
    print(f"  spec          specs/{slug}/spec.md {bindings['spec']}")
    print(f"  evidence      {args.evidence} {bindings['evidence']}")
    if proposed.renews:
        print(f"  renews        {proposed.renews} {proposed.renews_digest}")
        print(f"  renewal       {proposed.renewals} of {MAX_RENEWALS}")
        if head is not None:
            print(f"  predecessor   {head.home} ({head.provenance})")
            for line in _predecessor_bytes(head).splitlines():
                print(f"    {line}")
    print(f"  Type exactly: ACCEPT {proposed.id} AS {args.by}")
    print("  The controlling terminal is the only channel this reads.")
