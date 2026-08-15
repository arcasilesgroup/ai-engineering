"""The eight production-ready boxes, and the receipts that are allowed to tick them.

Nothing gets a URL until every box is ticked by observed evidence. The failure this
guards against is the checklist that ticks itself: a box marked done because somebody
wrote that it was done, or because a workflow file mentions the word. So a box is ticked
by exactly one thing — a check-evidence receipt that was executed, is fresh, and matches
a requirement the receipt did not get to write.

The eight boxes are fixed here rather than configured, because which boxes exist is a
decision that always comes out the same way. What each box *means* in one repository is
not: only the repository knows the command that proves it, the version of the tool that
ran it, and the digests of what went in and came out. That declaration is committed, and
a receipt is measured against it. A repository can say a box does not apply — traces with
one hop is the spec's own example — but it must say so in the declaration, with a reason,
before any receipt can claim the exemption.

Absent, stale, malformed and mismatched receipts are `INCOMPLETE`: unproven, not passed.
A receipt that ran and failed is `FAIL`, because that is decided, and reporting a decided
fault as undecidable is the same lie as a green nobody earned, told the other way round.
"""

from __future__ import annotations

import json
import stat
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ai_engineering import evidence, outcome

SCHEMA = "urn:ai-engineering:readiness:1"
VERSION = "1"
DECLARATION = ".ai/readiness.json"
RECEIPTS = ".ai/receipts"

DECLARATION_MISSING = "READINESS_DECLARATION_MISSING"
DECLARATION_MALFORMED = "READINESS_DECLARATION_MALFORMED"
DECLARATION_INVALID = "READINESS_DECLARATION_INVALID"
BOXES_MISMATCH = "READINESS_BOXES_MISMATCH"
RECEIPT_UNREADABLE = "READINESS_RECEIPT_UNREADABLE"
TIME_INVALID = "READINESS_TIME_INVALID"

_MAX_BYTES = 100_000
# A decided failure outranks an undecidable one: both block a URL, but only one of them
# is already answered, and the report has to say which.
_SEVERITY = {"PASS": 0, "WARN": 1, "INCOMPLETE": 2, "FAIL": 3}


@dataclass(frozen=True, slots=True)
class Box:
    """One production-ready box: its identifier, the spec's own words, and its kind."""

    id: str
    label: str
    kind: str


BOXES: tuple[Box, ...] = (
    Box("ci_cd", "CI/CD", "automated"),
    Box("logs", "Logs", "automated"),
    Box("traces", "Traces", "automated"),
    Box("errors", "Errors", "automated"),
    Box("health", "Health and data age", "automated"),
    # Outside the service by definition, so it carries the independent path it took and
    # the limits it states — the schema calls that kind `external` and requires both.
    Box("external_check", "External check", "external"),
    Box("second_path", "Second path", "automated"),
    Box("security", "Security", "automated"),
)


@dataclass(frozen=True, slots=True)
class BoxStatus:
    """What was proven about one box, and how old the proof is."""

    id: str
    label: str
    outcome: str
    code: str
    age_seconds: int | None

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "outcome": self.outcome,
            "code": self.code,
            "age_seconds": self.age_seconds,
        }


@dataclass(frozen=True, slots=True)
class Readiness:
    """The aggregate, and every box it was aggregated from."""

    result: outcome.Result
    code: str
    boxes: tuple[BoxStatus, ...]

    def age_of(self, box: str) -> int | None:
        for status in self.boxes:
            if status.id == box:
                return status.age_seconds
        return None

    def as_dict(self) -> dict[str, object]:
        return {
            "result": self.result.as_dict(),
            "code": self.code,
            "boxes": [status.as_dict() for status in self.boxes],
        }


class _Unreadable(Exception):
    """A file is there and this process cannot read what it holds."""


def _refused(code: str, status: str = "INCOMPLETE") -> Readiness:
    return Readiness(outcome.result(status), code, ())


def _read(path: Path) -> bytes | None:
    """The bytes at that exact path, nothing if there is no file, and a refusal if there
    is one this process cannot read as itself.

    A link is not followed and a directory is not read: a receipt that is really a
    redirection somewhere else is a receipt somebody else wrote. The content is proven
    afterwards by requirement and digest, so this stops short of the open-and-restat
    dance the policy schema needs — the schema decides what a receipt may say, while a
    receipt only says it."""

    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as error:
        raise _Unreadable from error
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_size > _MAX_BYTES:
        raise _Unreadable
    try:
        return path.read_bytes()
    except OSError as error:
        raise _Unreadable from error


def _object(raw: bytes) -> dict[str, Any]:
    record = json.loads(raw.decode("utf-8"))
    if not isinstance(record, dict) or not all(isinstance(key, str) for key in record):
        raise ValueError("not an object with string keys")
    return record


def _age(raw: bytes, now: datetime) -> int | None:
    """How long ago the receipt says its run finished, or nothing if it does not say."""

    try:
        finished = _object(raw)["finished_at"]
        parsed = datetime.fromisoformat(finished.removesuffix("Z") + "+00:00")
        return int((now - parsed).total_seconds())
    except (AttributeError, KeyError, OverflowError, TypeError, ValueError):
        return None


def _status(box: Box, declared: object, root: Path, now: datetime) -> BoxStatus:
    def answer(status: str, code: str, age: int | None = None) -> BoxStatus:
        return BoxStatus(box.id, box.label, status, code, age)

    if not isinstance(declared, dict) or not all(isinstance(key, str) for key in declared):
        return answer("INCOMPLETE", DECLARATION_INVALID)
    try:
        # Kind and identity are this module's to state. A declaration that tries to set
        # either collides with the argument already passed and is refused, rather than
        # letting a repository rename a box into one it finds easier to prove.
        expected = evidence.Expectation(kind=box.kind, id=box.id, **declared)
    except TypeError:
        return answer("INCOMPLETE", DECLARATION_INVALID)
    try:
        raw = _read(root / RECEIPTS / f"{box.id}.json")
    except _Unreadable:
        return answer("INCOMPLETE", RECEIPT_UNREADABLE)
    verified = evidence.verify(raw, expected=expected, now=now)
    return answer(verified.outcome, verified.code, None if raw is None else _age(raw, now))


def read(root: Path, *, now: datetime) -> Readiness:
    """Verify every production-ready box in the repository at `root` as of `now`."""

    if not isinstance(now, datetime) or now.utcoffset() != timedelta(0):
        return _refused(TIME_INVALID)
    now = now.astimezone(UTC)
    try:
        raw = _read(root / DECLARATION)
    except _Unreadable:
        return _refused(DECLARATION_MALFORMED)
    if raw is None:
        return _refused(DECLARATION_MISSING)
    try:
        declaration = _object(raw)
        if declaration["schema"] != SCHEMA or declaration["schema_version"] != VERSION:
            raise ValueError("declaration is of another contract")
        declared = declaration["boxes"]
    except (KeyError, RecursionError, UnicodeDecodeError, ValueError):
        return _refused(DECLARATION_MALFORMED)
    if not isinstance(declared, dict) or set(declared) != {box.id for box in BOXES}:
        # Not "the ones it named passed": a declaration that drops a box, or invents one,
        # is a checklist the repository wrote for itself.
        return _refused(BOXES_MISMATCH)

    boxes = tuple(_status(box, declared[box.id], root, now) for box in BOXES)
    worst = max(boxes, key=lambda box: _SEVERITY.get(box.outcome, _SEVERITY["INCOMPLETE"]))
    return Readiness(outcome.result(worst.outcome), worst.code, boxes)
