"""Fail-closed verification of one check-evidence v1 receipt.

The canonical schema decides receipt shape.  Callers supply the versioned requirement
that the receipt must satisfy; a receipt cannot choose its own identity, applicability,
freshness window or digests.  Labels are considered only after those facts are proven.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any

from ai_engineering import intent, outcome, paths

SCHEMA_PATH = paths.policy("check-evidence-v1.schema.json")
_EXPECTED_SCHEMA_DIGEST = "692aa60b1acc55c9ff790184bc59066fdc5832fe94608c70a31f02b2845ed60c"
_SCHEMA = "urn:ai-engineering:check-evidence:1"
_VERSION = "1"
_MAX_POLICY_BYTES = 100_000
_MAX_EVIDENCE_BYTES = 100_000
_RFC3339_UTC = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z$")

POLICY_UNSUPPORTED = "EVIDENCE_POLICY_UNSUPPORTED"
REQUIREMENT_INVALID = "EVIDENCE_REQUIREMENT_INVALID"
MISSING = "EVIDENCE_MISSING"
MALFORMED = "EVIDENCE_MALFORMED"
STALE = "EVIDENCE_STALE"
DIGEST_MISMATCH = "EVIDENCE_DIGEST_MISMATCH"
APPLICABILITY_MISMATCH = "EVIDENCE_APPLICABILITY_MISMATCH"
REQUIREMENT_MISMATCH = "EVIDENCE_REQUIREMENT_MISMATCH"
EXECUTED_FAIL = "EVIDENCE_EXECUTED_FAIL"
VERIFIED = "EVIDENCE_VERIFIED"
VERIFIED_WITH_WARNING = "EVIDENCE_VERIFIED_WITH_WARNING"
NOT_APPLICABLE = "EVIDENCE_NOT_APPLICABLE"

_HUMAN_FIELDS = (
    "test_id",
    "owner_role",
    "protocol_id",
    "protocol_version",
    "environment_id",
    "environment_version",
    "receipt_digest",
)
_EXTERNAL_FIELDS = ("independent_path", "limits")


class _Problem(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class _SchemaValidator(intent._Schema):
    _KEYWORDS = intent._Schema._KEYWORDS | {
        "anyOf",
        "format",
        "minimum",
        "x-evidence-policy",
    }
    _SCHEMA_LISTS = intent._Schema._SCHEMA_LISTS | {"anyOf"}

    def _check_scalars(self, schema: dict[str, Any]) -> None:
        super()._check_scalars(schema)
        if "format" in schema and schema["format"] not in {"date", "date-time"}:
            raise intent._UnsupportedSchema("unsupported string format")
        if "minimum" in schema and (
            not isinstance(schema["minimum"], int) or isinstance(schema["minimum"], bool)
        ):
            raise intent._UnsupportedSchema("invalid minimum")

    def valid(
        self,
        instance: Any,
        schema: dict[str, Any] | None = None,
        references: tuple[str, ...] = (),
    ) -> bool:
        active = self.root if schema is None else schema
        if not super().valid(instance, active, references):
            return False
        if "anyOf" in active and not any(
            self.valid(instance, child, references) for child in active["anyOf"]
        ):
            return False
        if "minimum" in active and isinstance(instance, int) and instance < active["minimum"]:
            return False
        return "format" not in active or _valid_format(instance, active["format"])


@dataclass(frozen=True, slots=True)
class Expectation:
    """The versioned requirement a receipt must match exactly."""

    kind: str
    id: str
    applicability: str
    command: str
    tool_version: str
    input_digest: str
    artifact_digest: str
    max_age_seconds: int
    reason: str = ""
    test_id: str = ""
    owner_role: str = ""
    protocol_id: str = ""
    protocol_version: str = ""
    environment_id: str = ""
    environment_version: str = ""
    receipt_digest: str = ""
    independent_path: str = ""
    limits: str = ""


@dataclass(frozen=True, slots=True)
class Verification:
    """A canonical terminal result plus one stable evidence-specific classification."""

    result: outcome.Result
    code: str

    @property
    def outcome(self) -> str:
        return self.result.outcome

    def as_dict(self) -> dict[str, object]:
        return {"result": self.result.as_dict(), "code": self.code}


def _verification(status: str, code: str) -> Verification:
    return Verification(outcome.result(status), code)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()


def _read_policy(path: Path) -> bytes:
    descriptor = -1
    close_failed = False
    raw = b""
    try:
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise OSError("evidence policy is not a regular file")
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_BINARY", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        identity = (opened.st_dev, opened.st_ino)
        if not stat.S_ISREG(opened.st_mode) or identity != (before.st_dev, before.st_ino):
            raise OSError("evidence policy changed while opening")
        raw = os.read(descriptor, _MAX_POLICY_BYTES + 1)
        if os.read(descriptor, 1):
            raise OSError("evidence policy exceeds its bound")
        after = path.lstat()
        if identity != (after.st_dev, after.st_ino):
            raise OSError("evidence policy changed while reading")
    except OSError as error:
        raise _Problem(POLICY_UNSUPPORTED) from error
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                close_failed = True
    if close_failed or len(raw) > _MAX_POLICY_BYTES:
        raise _Problem(POLICY_UNSUPPORTED)
    return raw


def _load_schema() -> tuple[dict[str, Any], _SchemaValidator, dict[str, Any]]:
    try:
        schema = intent._json(_read_policy(SCHEMA_PATH))
        if not isinstance(schema, dict):
            raise ValueError("schema is not an object")
        if sha256(_canonical_json(schema)).hexdigest() != _EXPECTED_SCHEMA_DIGEST:
            raise ValueError("evidence policy differs from its approved contract")
        structural = _SchemaValidator(schema)
        policy = schema["x-evidence-policy"]
        if (
            schema["$id"] != _SCHEMA
            or schema["properties"]["schema_version"]["const"] != _VERSION
            or policy
            != {
                "freshness_field": "max_age_seconds",
                "missing": "INCOMPLETE",
                "stale": "INCOMPLETE",
                "malformed": "INCOMPLETE",
                "digest_mismatch": "INCOMPLETE",
                "executed_fail": "FAIL",
                "metadata_is_proof": False,
                "not_applicable_covers_applicable": False,
                "independent_kind": "external",
            }
        ):
            raise ValueError("evidence policy is inconsistent")
    except _Problem:
        raise
    except (KeyError, RecursionError, TypeError, ValueError, re.error, intent._UnsupportedSchema):
        raise _Problem(POLICY_UNSUPPORTED) from None
    return schema, structural, policy


def _valid_format(value: Any, name: str) -> bool:
    if not isinstance(value, str):
        return False
    try:
        if name == "date":
            return date.fromisoformat(value).isoformat() == value
        if _RFC3339_UTC.fullmatch(value) is None:
            return False
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
        return parsed.utcoffset() == timedelta(0)
    except (OverflowError, ValueError):
        return False


def _parse(source: object) -> dict[str, Any]:
    try:
        if isinstance(source, Mapping):
            materialized = dict(source)
            if not all(isinstance(key, str) for key in materialized):
                raise ValueError("evidence keys must be strings")
            raw = _canonical_json(materialized)
        elif isinstance(source, str):
            raw = source.encode("utf-8")
        elif isinstance(source, bytes):
            raw = source
        else:
            raise TypeError("evidence is not JSON")
        if len(raw) > _MAX_EVIDENCE_BYTES:
            raise ValueError("evidence exceeds its bound")
        record = intent._json(raw)
        if not isinstance(record, dict):
            raise ValueError("evidence is not an object")
        return record
    except (Exception, RecursionError):
        raise _Problem(MALFORMED) from None


def _expectation_record(expected: Expectation) -> dict[str, Any]:
    candidate: dict[str, Any] = {
        "schema": _SCHEMA,
        "schema_version": _VERSION,
        "kind": expected.kind,
        "id": expected.id,
        "applicability": expected.applicability,
        "command": expected.command,
        "tool_version": expected.tool_version,
        "input_digest": expected.input_digest,
        "artifact_digest": expected.artifact_digest,
        "started_at": "2000-01-01T00:00:00Z",
        "finished_at": "2000-01-01T00:00:00Z",
        "max_age_seconds": expected.max_age_seconds,
        "outcome": "PASS",
    }
    for field in ("reason", *_HUMAN_FIELDS, *_EXTERNAL_FIELDS):
        value = getattr(expected, field)
        if value != "":
            candidate[field] = value
    if expected.kind in {"human", "external"}:
        candidate["observation_date"] = "2000-01-01"
    return candidate


def _requirement_fields(expected: dict[str, Any]) -> dict[str, Any]:
    fields = {
        "kind": expected["kind"],
        "id": expected["id"],
        "command": expected["command"],
        "tool_version": expected["tool_version"],
        "max_age_seconds": expected["max_age_seconds"],
    }
    if expected["applicability"] == "not_applicable":
        fields["reason"] = expected["reason"]
    if expected["kind"] in {"human", "external"}:
        fields.update({field: expected[field] for field in _HUMAN_FIELDS[:-1]})
    if expected["kind"] == "external":
        fields.update({field: expected[field] for field in _EXTERNAL_FIELDS})
    return fields


def _timestamps(record: dict[str, Any], now: datetime) -> tuple[datetime, datetime] | None:
    try:
        started = datetime.fromisoformat(record["started_at"].removesuffix("Z") + "+00:00")
        finished = datetime.fromisoformat(record["finished_at"].removesuffix("Z") + "+00:00")
        if started > finished or finished > now:
            return None
        if record["kind"] in {"human", "external"}:
            observed = date.fromisoformat(record["observation_date"])
            if observed != finished.astimezone(UTC).date():
                return None
    except (AttributeError, KeyError, OverflowError, TypeError, ValueError):
        return None
    return started, finished


def verify(
    source: object,
    *,
    expected: Expectation,
    now: datetime,
) -> Verification:
    """Verify one receipt against an exact requirement and explicit observation time."""

    if source is None:
        return _verification("INCOMPLETE", MISSING)
    try:
        _, structural, policy = _load_schema()
    except _Problem as problem:
        return _verification("INCOMPLETE", problem.code)
    try:
        if (
            not isinstance(expected, Expectation)
            or not isinstance(now, datetime)
            or now.utcoffset() != timedelta(0)
        ):
            return _verification("INCOMPLETE", REQUIREMENT_INVALID)
        now = now.astimezone(UTC)
        requirement = intent._json(_canonical_json(_expectation_record(expected)))
        if not isinstance(requirement, dict) or not structural.valid(requirement):
            return _verification("INCOMPLETE", REQUIREMENT_INVALID)
    except Exception:
        return _verification("INCOMPLETE", REQUIREMENT_INVALID)
    try:
        record = _parse(source)
        if not structural.valid(record):
            return _verification(policy["malformed"], MALFORMED)
    except Exception:
        return _verification(policy["malformed"], MALFORMED)

    times = _timestamps(record, now)
    if times is None:
        return _verification(policy["malformed"], MALFORMED)
    _, finished = times
    if record["applicability"] != requirement["applicability"]:
        return _verification("INCOMPLETE", APPLICABILITY_MISMATCH)
    absent = object()
    if any(
        record.get(field, absent) != value
        for field, value in _requirement_fields(requirement).items()
    ):
        return _verification("INCOMPLETE", REQUIREMENT_MISMATCH)

    expected_digests = {
        "input_digest": requirement["input_digest"],
        "artifact_digest": requirement["artifact_digest"],
    }
    if requirement["kind"] in {"human", "external"}:
        expected_digests["receipt_digest"] = requirement["receipt_digest"]
    if any(record.get(field, absent) != value for field, value in expected_digests.items()):
        return _verification(policy["digest_mismatch"], DIGEST_MISMATCH)
    if (now - finished).total_seconds() > requirement["max_age_seconds"]:
        return _verification(policy["stale"], STALE)

    if record["outcome"] == "FAIL":
        return _verification(policy["executed_fail"], EXECUTED_FAIL)
    if record["outcome"] == "WARN":
        return _verification("WARN", VERIFIED_WITH_WARNING)
    if requirement["applicability"] == "not_applicable":
        return _verification("PASS", NOT_APPLICABLE)
    return _verification("PASS", VERIFIED)


# ── what a check ran over ───────────────────────────────────────────────────────────────

RECEIPT_PARTS = (".ai", "receipts", "ran.json")

# Ignored files are excluded, so a build directory or a virtualenv cannot move the digest.
# `--others` is what makes the set stable across `git add`: a file being added for the first
# time is "other" before the add and "cached" after it, and it has to be in both readings or
# every commit that adds a file would silently lose its trailer.
LISTING = ("git", "ls-files", "--cached", "--others", "--exclude-standard", "-z")


def toplevel(root: Path | None = None) -> Path:
    """The repository this is being asked about, from where it is being asked.

    Not the parent of this file. `commit-msg` invokes its caller by absolute path, and a
    checkout that vendors it — or a test that builds a repository in a temporary directory —
    would otherwise get a digest over *this* tree while committing to another one. A receipt
    that answers about the wrong repository is worse than no receipt.
    """

    found = subprocess.run(
        ("git", "rev-parse", "--show-toplevel"),
        capture_output=True,
        text=True,
        check=True,
        cwd=None if root is None else str(root),
    )
    return Path(found.stdout.strip())


def content_digest(root: Path | None = None) -> str:
    """One digest over the name and bytes of every file this commit could carry.

    Read from disk rather than from the index on purpose. The index answers "what is staged",
    and the question here is "what did the suite actually run over" — which is the working
    tree. Editing a file after the gate and before the commit has to break this, and reading
    the index would not notice.

    It lives here rather than beside the script that writes the receipt because a second
    reader needs it: `checkpoint` decides whether the executed-checks receipt is about this
    code, and the only receipt in the tree bound to content is this one. Nothing under `src/`
    can import a file in `tests/`, so the choice was one home or two copies of a hash.
    """

    where = toplevel(root)
    listed = subprocess.run(LISTING, capture_output=True, cwd=str(where), check=True).stdout
    running = sha256()
    # The receipt is never part of what the receipt measures. `.ai/` is ignored in this
    # repository so it fell out anyway, and that is exactly the accident worth removing: in a
    # tree where it is not ignored, writing the receipt changes the digest the receipt just
    # recorded, and the trailer can never appear. A tool that cannot tell what it is looking
    # at from what it is looking through — the same defect, one level down.
    mine = "/".join(RECEIPT_PARTS).encode()
    for name in sorted(one for one in listed.split(b"\0") if one and one != mine):
        path = where / name.decode("utf-8", "surrogateescape")
        running.update(name)
        try:
            running.update(sha256(path.read_bytes()).digest())
        except (OSError, ValueError):
            # A symlink to nowhere, a directory left by a removed submodule, an unreadable
            # file. Recorded as its own state rather than skipped: skipping would make two
            # different trees digest the same.
            running.update(b"\0unreadable")
    return running.hexdigest()
