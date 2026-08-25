"""Walking the chain, link by link.

Not the same job as doctor: doctor looks at the chain's head and whether it is writable
and takes a second, and runs every session. This walks the whole history, and runs in
CI and on the day somebody asks you for proof.

The anchor is what makes losing the laptop survivable. The commit-msg hook writes the
(repository, machine) pair, the sequence number and the head's first twelve characters
into every commit, so git history — immutable and replicated — carries a tamper-evident
checkpoint. Lose the machine and you lose the event bodies, not the proof of the head.

Solution Intent is current-state evidence, not chain metadata. When its canonical record
exists, audit validates that record and reads every relation target again; an event that
says those relations passed cannot make changed or missing bytes green.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from ai_engineering import accept, outcome, paths

INTENT_HOME = ".ai/intent.md"
INTENT_INCOMPLETE_PREFIX = f"Solution Intent at {INTENT_HOME} is INCOMPLETE: "
ROOT_INCOMPLETE = "Repository context is INCOMPLETE: no repository root can be proven"
CHAIN_INCOMPLETE_PREFIX = "Chain evidence is INCOMPLETE: "
# The event name an account carries. Not a new event class: the six are closed, and an
# account is a command a person ran, which is what `command` means.
ACCOUNT = "audit_account"


class _ChainRead(list[dict]):
    """One stable read of the chain plus why no trustworthy read was possible."""

    def __init__(self, events: list[dict], problem: str = "") -> None:
        super().__init__(events)
        self.problem = problem


class _AmbiguousJson(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    value = {}
    for key, item in pairs:
        if key in value:
            raise _AmbiguousJson("duplicate JSON key")
        value[key] = item
    return value


def _invalid_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value}")


@dataclass(frozen=True, slots=True)
class _Inspection:
    events: tuple[dict, ...]
    findings: tuple[tuple[str, str], ...]

    @property
    def result(self) -> outcome.Result:
        if any(kind == "BROKEN" for kind, _ in self.findings):
            return outcome.result("FAIL")
        # An accounted break is still printed — it is never erased — but it has been
        # answered by a human with authority, so it does not hold the chain open. Reading
        # it as INCOMPLETE would leave the anchor refused forever, which is the ratchet the
        # account exists to release.
        if any(kind not in ("ACCOUNTED", "WARN") for kind, _ in self.findings):
            return outcome.result("INCOMPLETE")
        if any(kind == "ACCOUNTED" for kind, _ in self.findings):
            return outcome.result("WARN")
        return outcome.result("PASS")


def _chain_bytes(path: Path) -> tuple[bytes, str]:
    descriptor = -1
    close_failed = False
    raw = b""
    problem = ""
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode):
            raise OSError("chain is not one regular file")
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_BINARY", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        identity = (opened.st_dev, opened.st_ino)
        if not stat.S_ISREG(opened.st_mode) or identity != (before.st_dev, before.st_ino):
            raise OSError("chain changed while opening")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 65_536):
            chunks.append(chunk)
        finished = os.fstat(descriptor)
        after = path.lstat()
        if (
            identity != (finished.st_dev, finished.st_ino)
            or identity != (after.st_dev, after.st_ino)
            or opened.st_size != finished.st_size
            or opened.st_mtime_ns != finished.st_mtime_ns
        ):
            raise OSError("chain changed while reading")
        raw = b"".join(chunks)
    except FileNotFoundError:
        problem = "CHAIN_MISSING — no chain exists for this repository and machine"
    except OSError:
        problem = "CHAIN_UNREADABLE — the chain cannot be read as one stable regular file"
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                close_failed = True
        if close_failed:
            problem = "CHAIN_UNREADABLE — the chain file could not be closed safely"
    return (b"", problem) if problem else (raw, "")


def read(root: Path | None) -> list[dict]:
    # Inside the `try`, and the `except` below has listed `ImportError` since it was written.
    # The load was one line above it, so an emitter that cannot be imported — a half-removed
    # install, a machine whose home moved — raised straight out of this function instead of
    # answering CHAIN_UNREADABLE. Every caller here treats a raise as a crash and a problem
    # string as an answer, so the one case the handler was written for was the one it missed.
    try:
        emit = paths.load("_emit")
        raw, problem = _chain_bytes(emit.chain_path(root))
    except (ImportError, OSError, RuntimeError, TypeError, ValueError):
        return _ChainRead([], "CHAIN_UNREADABLE — the chain location cannot be derived")
    if problem:
        return _ChainRead([], problem)
    if not raw.strip():
        return _ChainRead([], "CHAIN_EMPTY — the chain contains no evidence to audit")
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return _ChainRead([], "CHAIN_UNREADABLE — the chain is not UTF-8 JSON Lines")
    out: list[dict] = []
    last_line_invalid = False
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            event = json.loads(
                line,
                object_pairs_hook=_unique_object,
                parse_constant=_invalid_constant,
            )
            if not isinstance(event, dict):
                raise ValueError("chain link is not an object")
            out.append(event)
        except _AmbiguousJson:
            out.append(
                {
                    "ts": "?",
                    "cls": "unreadable",
                    "name": "?",
                    "hash": "",
                    "_audit_kind": "INCOMPLETE",
                    "_audit_problem": (
                        f"{CHAIN_INCOMPLETE_PREFIX}CHAIN_AMBIGUOUS — "
                        f"line {number} repeats one JSON key"
                    ),
                }
            )
            last_line_invalid = number == len(lines)
        except (RecursionError, ValueError):
            # A hook killed mid-append leaves half a line behind. Doctor may skip it; here
            # skipping is how a chain cut at the end walks clean and reports itself intact.
            out.append(
                {
                    "ts": "?",
                    "cls": "unreadable",
                    "name": "?",
                    "hash": "",
                    "_audit_problem": f"link {number}: the line is not one JSON object",
                }
            )
            last_line_invalid = number == len(lines)
    if raw and not raw.endswith(b"\n") and not last_line_invalid:
        out.append(
            {
                "ts": "?",
                "cls": "unreadable",
                "name": "?",
                "hash": "",
                "_audit_problem": (
                    f"link {len(lines)}: the line is not terminated — a write was cut here"
                ),
            }
        )
    return _ChainRead(out)


def verify_intent(root: Path) -> list[str]:
    """Recompute Intent health from its current home and relation target bytes."""
    from ai_engineering import intent

    source = root / INTENT_HOME
    if not source.is_file():
        return [
            INTENT_INCOMPLETE_PREFIX
            + f"INTENT_HOME_MISSING — Solution Intent is missing at {INTENT_HOME}"
        ]
    result = intent.validate(source, root)
    if result.outcome == "PASS":
        return []
    return [INTENT_INCOMPLETE_PREFIX + f"{result.code} — {result.reason}"]


def _accounted(events: list[dict]) -> dict[int, str]:
    """Every link a human with authority has already answered for, and what they said.

    An account is a link like any other, so it is covered by the digest of every link after
    it and by the head that git commits anchor. Adding one retroactively moves the head and
    the anchors stop matching, which is the case `_history_findings` already reports. That
    is what keeps this from being a way out from under a real edit."""

    answered: dict[int, str] = {}
    for event in events:
        data = event.get("data")
        if event.get("name") != ACCOUNT or not isinstance(data, dict):
            continue
        first, last = data.get("first"), data.get("last")
        if type(first) is not int or type(last) is not int:
            continue
        for seq in range(first, last + 1):
            answered[seq] = f"{data.get('why', '')} — {data.get('by', '')}".strip(" —")
    return answered


def _chain_findings(events: list[dict]) -> list[tuple[str, str]]:
    emit = paths.load("_emit")
    findings: list[tuple[str, str]] = []
    problem = getattr(events, "problem", "")
    if problem:
        findings.append(("INCOMPLETE", CHAIN_INCOMPLETE_PREFIX + problem))
    answered = _accounted(events)
    prev = ""
    for seq, event in enumerate(events, 1):
        if event.get("cls") == "unreadable":
            findings.append(
                (
                    event.get("_audit_kind", "BROKEN"),
                    event.get("_audit_problem")
                    or f"link {seq}: the line is not JSON — a write was cut here",
                )
            )
            continue
        data = event.get("data")
        if not isinstance(data, dict):
            findings.append(("BROKEN", f"link {seq}: data is not one JSON object"))
            data = {}
        if (data or {}).get("outcome") == "edited":
            # Sealed truthfully, so every hash below matches. Without this line the one
            # command README.md offers as the tamper detector exits 0 over a rewritten event.
            #
            # Unless a human with authority has already answered for it. The break is still
            # reported — it is never erased, because erasing is the act this file exists to
            # catch — but a break that has been accounted for does not go on blocking the
            # anchor forever. Without that, one poisoned link ends anchoring on a machine
            # permanently, which is what happened here at 22 links.
            if seq in answered:
                findings.append(("ACCOUNTED", f"link {seq}: accounted for — {answered[seq]}"))
            else:
                findings.append(("BROKEN", f"link {seq}: it arrived edited before it was sealed"))
        if type(event.get("seq")) is not int or event.get("seq") != seq:
            findings.append(("BROKEN", f"link {seq}: the sequence jumps to {event.get('seq')}"))
        if event.get("prev") != prev:
            findings.append(("BROKEN", f"link {seq}: it does not extend the link before it"))
        try:
            recomputed = emit.digest(event)
        except (RecursionError, TypeError, ValueError):
            recomputed = ""
        if recomputed != event.get("hash"):
            findings.append(
                ("BROKEN", f"link {seq}: the hash does not match its own body — it was edited")
            )
        stored = event.get("hash")
        prev = stored if isinstance(stored, str) else ""
    return findings


def _inspect(
    root: Path | None,
    *,
    require_root: bool,
    include_intent: bool,
) -> _Inspection:
    events = read(root)
    findings: list[tuple[str, str]] = []
    if require_root and root is None:
        findings.append(("INCOMPLETE", ROOT_INCOMPLETE))
    findings.extend(_chain_findings(events))
    if include_intent and root is not None:
        findings.extend(("INCOMPLETE", problem) for problem in verify_intent(root))
    return _Inspection(tuple(events), tuple(findings))


def verify(root: Path | None) -> list[str]:
    inspection = _inspect(
        root,
        require_root=False,
        include_intent=root is not None,
    )
    # Findings only. The cure is presentation and belongs in `_render`, where a person
    # reads it — appending it here made three fixtures that count findings go red, which is
    # the fixtures being right: an API that returns advice mixed with data is one nobody can
    # count.
    return [line for _, line in inspection.findings]


def _cure(findings: Sequence[tuple[str, str]]) -> list[str]:
    """The command that answers a broken link, printed beside the links themselves.

    A break holds this machine's anchor open until a person answers for it, and until now
    the report listed the links and stopped. Measured here: twenty-two of them from a single
    day held the anchor for five days while every commit printed "this commit is not
    anchored" — a warning with no reachable cure, which is the shape everybody learns to
    ignore. The whole point of the account is that it exists; a reader has to be able to
    find it.

    The ranges are printed because a person answering for twenty-two links should not have
    to derive five contiguous runs from a list by eye.
    """

    # A set, because one link can be reported broken for more than one reason and the runs
    # are about which links need answering, not how many complaints each one drew. Without
    # it, two findings on link 2 printed "2 broken link(s) in 2 run(s): 2 2" — which a
    # fixture caught on the first run.
    numbers = sorted(
        {
            int(found.group(1))
            for kind, line in findings
            if kind == "BROKEN"
            for found in [re.match(r"link (\d+):", line.strip())]
            if found
        }
    )
    if not numbers:
        return []
    runs: list[tuple[int, int]] = []
    start = previous = numbers[0]
    for seq in numbers[1:]:
        if seq != previous + 1:
            runs.append((start, previous))
            start = seq
        previous = seq
    runs.append((start, previous))
    spans = " ".join(f"{a}-{b}" if a != b else str(a) for a, b in runs)
    return [
        "",
        f"  {len(numbers)} broken link(s) in {len(runs)} run(s): {spans}",
        "  A break is never erased. Answering for one stops it holding the anchor open:",
        "    ai-eng audit account --range FIRST-LAST --why '<what happened>' --by '<person>'",
        "  A line a test wrote through the in-clone buffer under its own "
        "AI_ENGINEERING_HOME arrives here as `edited`, because the seal cannot tell that "
        "from a real edit — see the note in hooks/_emit.py before you decide which it was.",
    ]


def _replay(events: list[dict] | tuple[dict, ...], session: str) -> list[str]:
    rows = []
    for event in events:
        if session and event.get("session") != session:
            continue
        data = event.get("data")
        data = data if isinstance(data, dict) else {}
        detail = data.get("reason") or data.get("error") or data.get("verb") or ""
        rows.append(
            f"  {event.get('ts', '?')}  {event.get('cls', '?'):<9} "
            f"{event.get('name', '?'):<16} {detail}"
        )
    return rows


def replay(root: Path | None, session: str) -> list[str]:
    return _replay(read(root), session)


def account(root: Path | None, *, first: int, last: int, why: str, by: str) -> outcome.Result:
    """Answer for a named range of broken links, as a new link.

    The chain had no way back before this. One link sealed as edited and `verify` fails for
    good, `anchor_line` raises, and no commit on that machine can be anchored again — a
    ratchet, measured here at 22 links written by this repository's own test suite.

    Nothing is erased or rewritten. The links keep saying exactly what they said; this adds
    a record that a person with authority looked at them and said why they are there. A
    reader sees both, which is the honest shape: the break happened, and it was answered."""

    emit = paths.load("_emit")
    if first < 1 or last < first or not why.strip() or not by.strip():
        return outcome.result("INCOMPLETE")
    emit.emit(ACCOUNT, "command", first=first, last=last, why=why.strip(), by=by.strip())
    emit.flush(root)
    return outcome.result("PASS")


def _render(inspection: _Inspection, *, stream=None) -> None:
    destination = sys.stdout if stream is None else stream
    print("\n".join(f"  {kind}  {line}" for kind, line in inspection.findings), file=destination)
    # The cure, beside the thing it cures. Listing the links and stopping is what this did,
    # and it is why twenty-two of them held this machine's anchor for five days while every
    # commit printed a warning whose remedy was in no output anywhere.
    for line in _cure(inspection.findings):
        print(line, file=destination)


def main(argv: list[str]) -> outcome.Result:
    parser = argparse.ArgumentParser("ai-eng audit")
    parser.add_argument(
        "action", nargs="?", default="verify", choices=["verify", "replay", "account"]
    )
    parser.add_argument("--range", help="the broken links to answer for, as FIRST-LAST")
    parser.add_argument("--why", help="why those links are there")
    parser.add_argument("--by", help="the person answering for them")
    parser.add_argument("--session")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="bounded sample size; gates the lane behind the cost policy",
    )
    parser.add_argument(
        "--revalidate",
        type=str,
        default=None,
        metavar="FINDING_ID",
        help="revalidate one finding at finding granularity (spec 030 B-030-3)",
    )
    parser.add_argument("--file", default=None, help="the file the finding lives in")
    parser.add_argument("--trigger", default=None, help="the exact substring the finding flagged")
    args = parser.parse_args(argv)

    # Revalidation (spec 030 B-030-3): re-read the specific file's diff and mark the finding
    # fixed only when the change actually removed the trigger, without re-running the lane.
    if args.revalidate is not None:
        if not (args.file and args.trigger):
            parser.error("--revalidate requires --file and --trigger")
        from ai_engineering import revalidate

        path = paths.repo_root() / args.file
        before = subprocess.run(
            ["git", "-C", str(paths.repo_root()), "show", f"HEAD:{args.file}"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        after = path.read_text(encoding="utf-8") if path.is_file() else ""
        finding = {"id": args.revalidate, "trigger": args.trigger, "file": args.file}
        fixed = revalidate.apply(finding, before, after)
        print(
            f"  {'FIXED' if fixed else 'INCOMPLETE'} {args.revalidate} "
            f"in {args.file}: the trigger is {'gone' if fixed else 'still present'}"
        )
        return outcome.result("PASS" if fixed else "INCOMPLETE")

    # The cost gate (spec 029 B-029-4): a bounded sample before an expensive lane. Without
    # `--limit` the flow runs exactly as before; with it, the lane first checks its
    # prerequisites and refuses without consent above the declared threshold.
    if args.limit is not None:
        from ai_engineering import cost

        missing = cost.doctor_prereqs()
        if missing:
            for line in missing:
                print(f"  INCOMPLETE {line}")
            return outcome.result("INCOMPLETE")
        _total, projected, ok = cost.calibrate(args.limit, [(0.01, 35.0)], interactive=False)
        if not ok:
            print(
                f"  INCOMPLETE [COST_UNCONSENTED]: the lane would project ~$"
                f"{projected:.2f} over a {args.limit}-unit run; re-run with consent."
            )
            return outcome.result("INCOMPLETE")

    if args.action == "account" and not (args.range and args.why and args.by):
        parser.error("account requires --range FIRST-LAST, --why and --by")
    if args.action != "account" and (args.range or args.why or args.by):
        parser.error("--range, --why and --by apply only to account")
    if args.action != "replay" and args.session is not None:
        parser.error("--session applies only to replay")

    try:
        root = paths.repo_root()
    except (ImportError, OSError, RuntimeError, TypeError, ValueError):
        root_failure = _Inspection((), (("INCOMPLETE", ROOT_INCOMPLETE),))
        _render(root_failure, stream=None)
        return root_failure.result
    if args.action == "account":
        try:
            first, _, last = args.range.partition("-")
            bounds = (int(first), int(last or first))
        except ValueError:
            parser.error("--range must read FIRST-LAST, both whole numbers")
        # The same ceremony a risk acceptance asks for, and for the same reason: this is a
        # person taking responsibility for evidence a machine cannot judge. An agent that
        # can type into this process cannot answer a prompt on the controlling terminal.
        #
        # And the phrase is printed first, which it was not. The reader opened the terminal
        # and waited in silence, so the only way to learn what to type was to read this
        # source — and the operator who tried it typed ahead, the process read an empty line,
        # returned INCOMPLETE, and their shell got the phrase: `zsh: command not found:
        # ACCOUNT`. A control whose refusal a person cannot act on is the defect this
        # repository is named after, and it was sitting in the one command that clears a
        # chain nobody else can clear.
        phrase = f"ACCOUNT {args.range} AS {args.by}"
        print(f"\n  To answer for links {args.range}, type exactly this and press return:")
        print(f"    {phrase}")
        print("  Nothing is erased. This adds a record that a person looked and said why.")
        if not accept.controlling_terminal_response(phrase):
            print("  nothing was written: the phrase did not match, or there is no keyboard here.")
            return outcome.result("INCOMPLETE")
        return account(root, first=bounds[0], last=bounds[1], why=args.why, by=args.by)
    if args.action == "replay":
        inspection = _inspect(
            root,
            require_root=True,
            include_intent=False,
        )
        if inspection.result.outcome != "PASS":
            _render(inspection)
            return inspection.result
        rows = _replay(inspection.events, args.session or "")
        print("\n".join(rows) if rows else "  nothing recorded for that session")
        return outcome.result("PASS")
    inspection = _inspect(
        root,
        require_root=True,
        include_intent=True,
    )
    if inspection.findings:
        _render(inspection)
        return inspection.result
    print(f"  ✓ {len(inspection.events)} links, intact, and each one extends the one before it.")
    return outcome.result("PASS")
