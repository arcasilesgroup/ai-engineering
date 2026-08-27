"""One reader for every acceptance this repository has ever recorded.

There are two shapes on disk and there will only ever be two: the YAML blocks earlier
versions embedded in `spec.md`, frozen and never written again, and the immutable records
this version publishes at `specs/NNN-slug/acceptance-r-NNN-NN/record.json`. One reader
validates both, because two readers of the same bytes drift and then disagree about which
risks are live — and the answer to that question is what a push gate blocks on.

Two states, evaluated in this order and never merged. **Integrity** asks whether a record is
what it says it is: canonical bytes, closed schema, self digest, agreeing identities.
**Freshness** asks whether the spec and evidence it was bound to still hash the same.
An integrity failure is unrepairable and unrenewable. A stale binding is neither: the record
stays exactly as published, stays renewable, and blocks green until a human decides again.
Collapsing those two into one answer is how a corrupt record gets "renewed" into a clean one.

Nothing here rewrites, copies or canonicalizes a legacy block, and no result this module
returns can change any other check's status. An acceptance says a known problem may stay; it
has never been able to turn a red check green, and this reader is not where that starts.
"""

from __future__ import annotations

import json
import re
import stat
from dataclasses import dataclass, field, replace
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

from ai_engineering import paths

# Every bound the specification states. Reaching one is `INCOMPLETE`; a reader that stops at
# a bound and reports what it managed to see has invented a clean register.
MAX_SPEC_DIRECTORIES = 1_000
MAX_RECORDS_PER_SPEC = 99
MAX_SPEC_BYTES = 1024 * 1024
MAX_RECORD_BYTES = 64 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_EVIDENCE_BYTES = 100_000

STORED_LEGACY = "stored legacy"
DERIVED_LEGACY = "derived legacy"
CANONICAL_RECORD = "canonical record"

_ID = re.compile(r"^R-([0-9]{3})-([0-9]{2})$")
# The carriage return is optional and the opening fence is captured, because the span
# below is measured off what actually matched. A spec file written on Windows holds
# CRLF, the fence read as unclosed, and this reader answered PASS over zero acceptances
# in a file that held one — the quietest way a register can be wrong.
_LEGACY_BLOCK = re.compile(rb"^(```yaml\r?\n).*?^```", re.S | re.M)
_KEY = re.compile(r"^([a-zA-Z][\w.-]*):\s*(.*)$")
_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


# The seven expressions the contract states, written out here as source. Compiling the
# string a file happens to hold is how a regular expression stops being ours: the schema is
# digest-pinned above and that is a good control, but a pin is a promise about bytes and
# this is the code that would run if the promise were ever wrong. Written here, the set is
# closed by the language rather than by a check — nothing constructs an expression at all —
# and `_pattern` refuses a pattern it does not already hold, which is the same refusal the
# digest makes, one layer in, where the compiling actually happens.
_EVIDENCE_PATH = r"^(?:(?!\.\.?(?:/|$))[^/\\\u0000-\u001f]+/)*(?!\.\.?$)[^/\\\u0000-\u001f]+$"
_PATTERNS: dict[str, re.Pattern[str]] = {
    "^R-[0-9]{3}-[0-9]{2}$": re.compile(r"^R-[0-9]{3}-[0-9]{2}$"),
    "^[0-9]{3}$": re.compile(r"^[0-9]{3}$"),
    "^(|R-[0-9]{3}-[0-9]{2})$": re.compile(r"^(|R-[0-9]{3}-[0-9]{2})$"),
    "^(|sha256:[0-9a-f]{64})$": re.compile(r"^(|sha256:[0-9a-f]{64})$"),
    "^sha256:[0-9a-f]{64}$": re.compile(r"^sha256:[0-9a-f]{64}$"),
    "^[0-9]{4}-[0-9]{2}-[0-9]{2}$": re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"),
    _EVIDENCE_PATH: re.compile(_EVIDENCE_PATH),
}


def _pattern(source: str) -> re.Pattern[str]:
    """The compiled expression this contract states, or a refusal."""

    found = _PATTERNS.get(source)
    if found is None:
        raise Refusal(
            "ACCEPTANCE_CONTRACT_UNRECOGNISED",
            "the contract states an expression this release does not hold",
        )
    return found


_NOT_A_STRING = frozenset({"true", "false", "yes", "no", "on", "off", "null", "~"})
_LEAF = re.compile(r"^acceptance-(r-[0-9]{3}-[0-9]{2})$")
# The frozen legacy evidence syntax: one normalized repository-relative path, then the
# digest of what it held. It is historical syntax and is never copied into a new record.
_LEGACY_EVIDENCE = re.compile(
    r"(?:(?!\.\.?(?:/|$))[^/\\\x00-\x1f]+/)*(?!\.\.?@)[^/\\\x00-\x1f]+@sha256:[0-9a-f]{64}"
)

# The frozen legacy recognizer. These fields and no others; anything else is malformed
# rather than ignored, because ignoring an unknown key is how a typo hides an expiry.
_LEGACY_FIELDS = (
    "id",
    "finding",
    "severity",
    "accepted_by",
    "accepted",
    "expires",
    "renewals",
    "justification",
    "evidence",
    "follow_up",
)
_LEGACY_LIMITS = {
    "id": 16,
    "finding": 256,
    "severity": 16,
    "accepted_by": 256,
    "accepted": 10,
    "expires": 10,
    "justification": 8192,
    "evidence": 2048,
    "follow_up": 4096,
}
_LEGACY_DEFAULTS: dict[str, Any] = {
    "id": "",
    "severity": "medium",
    "accepted_by": "?",
    "accepted": "",
    "justification": "",
    "evidence": "",
    "follow_up": "",
}
_SEVERITIES = ("low", "medium", "high", "critical")


class Refusal(Exception):
    """One reason the register could not be decided. Never a partial result."""

    def __init__(self, code: str, reason: str) -> None:
        self.code, self.reason = code, reason
        super().__init__(reason)


@dataclass(frozen=True, slots=True)
class Entry:
    """One acceptance, normalized in memory only. `home` is repository-relative."""

    id: str
    provenance: str
    home: str
    owner: str
    ordinal: str
    finding: str
    severity: str
    accepted: str
    expires: str
    renewals: int
    renews: str
    renews_digest: str
    digest: str
    spec_digest: str = ""
    evidence_path: str = ""
    evidence_digest: str = ""


@dataclass(frozen=True, slots=True)
class Register:
    """The decided state of every acceptance, or the exact reason there is none."""

    outcome: str
    code: str = ""
    reason: str = ""
    entries: tuple[Entry, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"outcome": self.outcome, "count": len(self.entries)}
        if self.outcome != "PASS":
            result.update(code=self.code, reason=self.reason)
        return result


@dataclass(slots=True)
class _Budget:
    """The whole-register byte ceiling, carried so one huge tree cannot be read in pieces
    that each look small."""

    # Read at construction, not at class definition, so the ceiling a test lowers is the
    # ceiling the reader actually enforces. A bound nothing can exercise is a bound nobody
    # has evidence for.
    remaining: int = field(default_factory=lambda: MAX_TOTAL_BYTES)

    def spend(self, amount: int) -> None:
        self.remaining -= amount
        if self.remaining < 0:
            raise Refusal(
                "ACCEPTANCE_OVER_BOUND", "the acceptance register exceeds its total read bound"
            )


# The bytes this reader is allowed to treat as its contract. Every `pattern` in that file
# is compiled and run against text a person wrote, so the file is the only thing standing
# between "our expression" and "an expression somebody supplied" — and until this line it
# stood on nothing but its path. `capability` pins its schema exactly this way; this is the
# same control on the other policy file, and the same one-line refusal when it moves.
_EXPECTED_SCHEMA_DIGEST = "727523b570d737c527c51e92934dd1c516eab4231b72c57a7c496beaac34cec2"


def schema() -> dict[str, Any]:
    """The one canonical contract, read from its file so this code cannot drift from it,
    and refused when its bytes are not the bytes this release was built against."""

    from ai_engineering import intent

    loaded = json.loads(paths.policy("risk-acceptance-v1.schema.json").read_text(encoding="utf-8"))
    if sha256(intent.canonical_json(loaded)).hexdigest() != _EXPECTED_SCHEMA_DIGEST:
        raise Refusal(
            "ACCEPTANCE_CONTRACT_UNRECOGNISED",
            "the risk-acceptance contract is not the one this release was built against",
        )
    return loaded


def _device(root: Path) -> int:
    """The volume every acceptance path must be on. A root this process cannot even stat is
    a refusal, not an empty register."""

    try:
        return root.lstat().st_dev
    except OSError as error:
        raise Refusal("ACCEPTANCE_UNREADABLE", "the repository root could not be read") from error


def _resolve(node: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    reference = node.get("$ref")
    return root["$defs"][reference.removeprefix("#/$defs/")] if reference else node


def _safe_stat(path: Path, device: int, *, directory: bool) -> None:
    """Refuse anything that is not exactly one entry on the repository's own volume."""

    try:
        value = path.lstat()
    except OSError as error:
        raise Refusal(
            "ACCEPTANCE_UNREADABLE", f"an acceptance path could not be read: {path.name}"
        ) from error
    if stat.S_ISLNK(value.st_mode):
        raise Refusal("ACCEPTANCE_UNSAFE_PATH", "an acceptance path component is a symbolic link")
    if getattr(value, "st_reparse_tag", False):
        raise Refusal("ACCEPTANCE_UNSAFE_PATH", "an acceptance path component is a reparse point")
    if value.st_dev != device:
        raise Refusal("ACCEPTANCE_UNSAFE_PATH", "an acceptance path crosses a filesystem boundary")
    if directory:
        if not stat.S_ISDIR(value.st_mode):
            raise Refusal("ACCEPTANCE_UNSAFE_PATH", "an acceptance directory is not a directory")
        return
    if not stat.S_ISREG(value.st_mode):
        raise Refusal("ACCEPTANCE_UNSAFE_PATH", "an acceptance file is not a regular file")
    if value.st_nlink != 1:
        raise Refusal("ACCEPTANCE_UNSAFE_PATH", "an acceptance file has more than one link")


def _read(path: Path, maximum: int, device: int, budget: _Budget) -> bytes:
    _safe_stat(path, device, directory=False)
    size = path.lstat().st_size
    if size > maximum:
        raise Refusal("ACCEPTANCE_OVER_BOUND", f"{path.name} exceeds its {maximum}-byte bound")
    budget.spend(size)
    try:
        body = path.read_bytes()
    except OSError as error:
        raise Refusal("ACCEPTANCE_UNREADABLE", f"{path.name} could not be read") from error
    if len(body) != size:
        raise Refusal("ACCEPTANCE_UNREADABLE", f"{path.name} changed while it was read")
    return body


def _text(body: bytes, where: str) -> str:
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError as error:
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} is not valid UTF-8") from error


def owner_of(leaf: str) -> str:
    """The three-digit spec a directory leaf owns.

    A canonical `NNN-slug` states it. A preserved pre-canonical name does not, so the ASCII
    digits in the leaf are concatenated and the first three taken. Fewer than three digits
    is undecidable, and undecidable is refused rather than guessed into a namespace.
    """

    digits = "".join(character for character in leaf if character.isascii() and character.isdigit())
    if len(digits) < 3:
        raise Refusal(
            "ACCEPTANCE_UNDECIDABLE_OWNER", f"the spec directory {leaf} names no three-digit owner"
        )
    return digits[:3]


def legacy_spans(body: bytes) -> list[tuple[int, int, str]]:
    """Every fenced YAML block with its exact byte span.

    The span runs from the first backtick of the opening delimiter through the third
    backtick of the closing one and excludes everything after it. A renewal binds that span,
    so it is taken from the stored bytes and never from a re-rendering.
    """

    spans: list[tuple[int, int, str]] = []
    for match in _LEGACY_BLOCK.finditer(body):
        start, end = match.span()
        inner = body[start + len(match.group(1)) : end - len(b"```")]
        spans.append((start, end, _text(inner, "a legacy acceptance block")))
    return spans


def _identity(stored: str, where: str) -> re.Match[str]:
    """The two halves of an acceptance id, or a refusal.

    `fullmatch` can answer None, and four call sites read `.group()` off it as though it
    could not. A malformed id would have raised an AttributeError from inside the parser
    whose whole job is to refuse malformed input — the one place a crash reads as a bug in
    the reader rather than as a fault in what was read.
    """

    named = _ID.fullmatch(stored)
    if named is None:
        raise Refusal("ACCEPTANCE_ID_MALFORMED", f"{where} carries an id that is not one")
    return named


def _parse_legacy(block: str, where: str) -> dict[str, str] | None:
    """The frozen recognizer. A block is an acceptance only when `finding` and `expires` are
    both present; anything else in the file is somebody else's YAML and is left alone."""

    fields: dict[str, str] = {}
    key: str | None = None
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")):
            if key is None:
                raise Refusal("ACCEPTANCE_MALFORMED", f"{where} indents a line with no key above")
            if line.lstrip().startswith(("-", "?")):
                raise Refusal("ACCEPTANCE_MALFORMED", f"{where} holds a container where a value")
            fields[key] = f"{fields[key]} {line.strip()}".strip()
            continue
        found = _KEY.match(line)
        if not found:
            raise Refusal("ACCEPTANCE_MALFORMED", f"{where} holds a line that is not a key")
        key, value = found.group(1), found.group(2).strip()
        if key in fields:
            raise Refusal("ACCEPTANCE_MALFORMED", f"{where} repeats the key {key}")
        if value.startswith(("[", "{")):
            raise Refusal("ACCEPTANCE_MALFORMED", f"{where} holds a container where a value")
        fields[key] = "" if value in (">", ">-", "|", "|-") else value.strip("\"'")
    if "finding" not in fields or "expires" not in fields:
        return None
    return fields


def _valid_date(value: str) -> bool:
    try:
        return _DATE.fullmatch(value) is not None and date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _legacy_renewals(value: str | None, where: str) -> int:
    """Absence and a non-decimal string holding no ASCII digit are zero, which preserves the
    shipped `once` behaviour exactly. Everything else must be a number in range."""

    if value is not None and value.lower() in _NOT_A_STRING:
        # `renewals: true` is a boolean, and the recognizer's own rule is that a boolean is
        # malformed. Reading it as zero turns a block that claims a renewal into an original
        # and lets the same finding be renewed twice more past the ceiling of two.
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} has a renewal counter that is not a value")
    if not value:
        return 0
    if not any(character.isdigit() for character in value):
        return 0
    if not value.isdigit():
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} has a renewal counter that is not a number")
    count = int(value, 10)
    if not 0 <= count <= 2:
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} has a renewal counter outside zero to two")
    return count


def _normalized_legacy(fields: dict[str, str], where: str) -> dict[str, Any]:
    if set(fields) - set(_LEGACY_FIELDS):
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} holds a key the recognizer never defined")
    for name, value in fields.items():
        if _CONTROL.search(value) is not None:
            raise Refusal("ACCEPTANCE_MALFORMED", f"{where} holds a control character in {name}")
        if name != "renewals" and value.lower() in _NOT_A_STRING:
            raise Refusal("ACCEPTANCE_MALFORMED", f"{where} holds a non-string value in {name}")
        limit = _LEGACY_LIMITS.get(name)
        if limit is not None and len(value.encode("utf-8")) > limit:
            raise Refusal("ACCEPTANCE_MALFORMED", f"{where} exceeds the legacy bound on {name}")

    record: dict[str, Any] = dict(_LEGACY_DEFAULTS)
    record.update({name: value for name, value in fields.items() if name != "renewals"})
    record["renewals"] = _legacy_renewals(fields.get("renewals"), where)
    if not record["finding"]:
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} has an empty finding")
    if record["severity"] not in _SEVERITIES:
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} names a severity that was never defined")
    if not _valid_date(record["expires"]):
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} has an expiry that is not one exact date")
    if record["accepted"] and not _valid_date(record["accepted"]):
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} has an accepted date that is not one date")
    if record["id"] and _ID.fullmatch(record["id"]) is None:
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} has an identity that is not R-NNN-NN")
    if record["evidence"] and _LEGACY_EVIDENCE.fullmatch(record["evidence"]) is None:
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} has evidence in no readable syntax")
    return record


def canonical_bytes(record: dict[str, Any]) -> bytes:
    """The exact encoding the schema declares, so a digest is taken over bytes and not over
    a Python dictionary that happened to print the same way."""

    return (
        json.dumps(record, allow_nan=False, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def record_digest(record: dict[str, Any]) -> str:
    """The self digest, over the canonical projection of every field except itself. It
    catches corruption; it is not a signature and proves nothing against somebody who can
    rewrite the value and the checksum together."""

    without = {name: value for name, value in record.items() if name != "record_digest"}
    return "sha256:" + sha256(canonical_bytes(without)).hexdigest()


def _validate_field(
    name: str, value: Any, node: dict[str, Any], root: dict[str, Any], where: str
) -> None:
    node = _resolve(node, root)
    if node.get("type") == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise Refusal("ACCEPTANCE_MALFORMED", f"{where} holds a non-integer {name}")
        if not node.get("minimum", value) <= value <= node.get("maximum", value):
            raise Refusal("ACCEPTANCE_MALFORMED", f"{where} holds {name} outside its range")
        return
    if node.get("type") == "object":
        if not isinstance(value, dict) or set(value) != set(node["required"]):
            raise Refusal("ACCEPTANCE_MALFORMED", f"{where} holds a malformed {name}")
        for child, item in value.items():
            _validate_field(f"{name}.{child}", item, node["properties"][child], root, where)
        return
    if not isinstance(value, str):
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} holds a non-string {name}")
    if _CONTROL.search(value) is not None:
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} holds a control character in {name}")
    if "const" in node and value != node["const"]:
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} holds an unexpected {name}")
    if "enum" in node and value not in node["enum"]:
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} holds an undefined {name}")
    if "pattern" in node and _pattern(node["pattern"]).fullmatch(value) is None:
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} holds a malformed {name}")
    if len(value) < node.get("minLength", 0):
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} holds an empty {name}")
    if "format" in node and node["format"] == "date" and not _valid_date(value):
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} holds a {name} that is not one exact date")


def validate_record(body: bytes, where: str, contract: dict[str, Any]) -> dict[str, Any]:
    """Check one canonical record against the schema document itself.

    The schema is the contract, so its `required`, patterns, enumerations and byte limits
    are read from it rather than restated here. Restating them is how a policy file and the
    code enforcing it start to disagree while both look right.
    """

    text = _text(body, where)
    try:
        record = json.loads(text)
    except ValueError as error:
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} is not JSON") from error
    if not isinstance(record, dict):
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} is not one JSON object")
    if canonical_bytes(record) != body:
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} is not canonical JSON")
    if set(record) != set(contract["required"]):
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} does not carry exactly the closed fields")
    for name, value in record.items():
        _validate_field(name, value, contract["properties"][name], contract, where)
    for name, limit in contract["x-utf8-byte-limits"].items():
        held: Any = record
        for part in name.split("."):
            held = held[part]
        if len(str(held).encode("utf-8")) > limit:
            raise Refusal("ACCEPTANCE_MALFORMED", f"{where} exceeds the byte bound on {name}")
    if record["record_digest"] != record_digest(record):
        raise Refusal("ACCEPTANCE_CHECKSUM", f"{where} does not match its own record digest")
    _validate_relation(record, where)
    if not _valid_date(record["expires"]) or record["expires"] < record["accepted"]:
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} expires before it was accepted")
    return record


def _validate_relation(record: dict[str, Any], where: str) -> None:
    """An original names no predecessor and has renewed nothing. A renewal names exactly one
    predecessor, binds its exact bytes, and counts one higher."""

    original = record["renews"] == ""
    if original and (record["renewals"] != 0 or record["renews_digest"] != ""):
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} renews nothing but counts a renewal")
    if not original and (record["renewals"] < 1 or not record["renews_digest"]):
        raise Refusal("ACCEPTANCE_MALFORMED", f"{where} renews a record without binding it")


def _present(path: Path) -> bool:
    """Whether an entry exists at this exact name, without following anything.

    `Path.exists()` follows symlinks, so a link pointing nowhere reads as absent — and a
    spec.md replaced by a dangling link would silently take its whole acceptance history
    out of the register. Absent is absent; anything else is somebody else's problem to
    prove, which is what `_safe_stat` is for.
    """

    try:
        path.lstat()
    except FileNotFoundError:
        return False
    except OSError as error:
        raise Refusal("ACCEPTANCE_UNREADABLE", f"{path.name} could not be read") from error
    return True


def _spec_directories(root: Path, device: int) -> list[Path]:
    home = root / "specs"
    if not _present(home):
        return []
    _safe_stat(home, device, directory=True)
    try:
        found = sorted(entry for entry in home.iterdir() if not entry.name.startswith("."))
    except OSError as error:
        raise Refusal("ACCEPTANCE_UNREADABLE", "the specs home could not be listed") from error
    if len(found) > MAX_SPEC_DIRECTORIES:
        raise Refusal("ACCEPTANCE_OVER_BOUND", "the repository holds more spec directories")
    directories: list[Path] = []
    for entry in found:
        try:
            value = entry.lstat()
        except OSError as error:
            raise Refusal("ACCEPTANCE_UNREADABLE", f"{entry.name} could not be read") from error
        # A link is refused rather than skipped: skipping one takes whatever it points at
        # out of the register without saying so. A plain file cannot hold records at all,
        # so it is not a spec directory and it hides nothing.
        if stat.S_ISLNK(value.st_mode) or getattr(value, "st_reparse_tag", False):
            raise Refusal("ACCEPTANCE_UNSAFE_PATH", f"the spec entry {entry.name} is a link")
        if not stat.S_ISDIR(value.st_mode):
            continue
        _safe_stat(entry, device, directory=True)
        directories.append(entry)
    return directories


def _legacy_entries(directory: Path, device: int, budget: _Budget) -> list[tuple[Entry, int]]:
    """Every embedded acceptance in one spec, with the byte offset that orders it."""

    spec = directory / "spec.md"
    if not _present(spec):
        return []
    body = _read(spec, MAX_SPEC_BYTES, device, budget)
    owner = owner_of(directory.name)
    home = f"specs/{directory.name}/spec.md"
    found: list[tuple[Entry, int]] = []
    for start, end, block in legacy_spans(body):
        # The shape `<file> cannot be read: …` is the message assertion 16 and the push gate
        # already speak. Changing the reader is not a reason to change what they print.
        where = f"{home} cannot be read: the block at byte {start}"
        fields = _parse_legacy(block, where)
        if fields is None:
            continue
        record = _normalized_legacy(fields, where)
        stored = record["id"]
        if stored and _identity(stored, where).group(1) != owner:
            raise Refusal("ACCEPTANCE_OWNER_MISMATCH", f"{where} names another spec's namespace")
        found.append(
            (
                Entry(
                    id=stored,
                    provenance=STORED_LEGACY if stored else DERIVED_LEGACY,
                    home=home,
                    owner=owner,
                    ordinal=_identity(stored, where).group(2) if stored else "",
                    finding=record["finding"],
                    severity=record["severity"],
                    accepted=record["accepted"],
                    expires=record["expires"],
                    renewals=record["renewals"],
                    renews="",
                    renews_digest="",
                    digest="sha256:" + sha256(body[start:end]).hexdigest(),
                ),
                start,
            )
        )
    return found


def _record_entries(
    directory: Path, device: int, budget: _Budget, contract: dict[str, Any]
) -> list[Entry]:
    owner = owner_of(directory.name)
    leaves = sorted(entry for entry in directory.iterdir() if _LEAF.fullmatch(entry.name))
    if len(leaves) > MAX_RECORDS_PER_SPEC:
        raise Refusal("ACCEPTANCE_OVER_BOUND", "one spec holds more records than the bound")
    found: list[Entry] = []
    for leaf in leaves:
        _safe_stat(leaf, device, directory=True)
        home = f"specs/{directory.name}/{leaf.name}/record.json"
        body = _read(leaf / "record.json", MAX_RECORD_BYTES, device, budget)
        record = validate_record(body, home, contract)
        expected = "acceptance-" + record["id"].lower()
        if leaf.name != expected:
            raise Refusal("ACCEPTANCE_PATH_MISMATCH", f"{home} does not live at its own identity")
        if record["spec"] != owner or _identity(record["id"], str(home)).group(1) != owner:
            raise Refusal("ACCEPTANCE_OWNER_MISMATCH", f"{home} names another spec's namespace")
        found.append(
            Entry(
                id=record["id"],
                provenance=CANONICAL_RECORD,
                home=home,
                owner=owner,
                ordinal=_identity(record["id"], str(home)).group(2),
                finding=record["finding"],
                severity=record["severity"],
                accepted=record["accepted"],
                expires=record["expires"],
                renewals=record["renewals"],
                renews=record["renews"],
                renews_digest=record["renews_digest"],
                digest="sha256:" + sha256(body).hexdigest(),
                spec_digest=record["spec_digest"],
                evidence_path=record["evidence"]["path"],
                evidence_digest=record["evidence"]["content_digest"],
            )
        )
    return found


def read(root: Path) -> Register:
    """Integrity only: what is on disk, whether it is what it claims, and nothing about
    whether the world it was bound to has moved since."""

    try:
        return Register("PASS", entries=_entries(root))
    except Refusal as refusal:
        return Register("INCOMPLETE", refusal.code, refusal.reason)
    except OSError as error:
        # A reader that raises kills every other check in the same run. Whatever the
        # filesystem refused, the answer this register owes its callers is one word.
        return Register(
            "INCOMPLETE",
            "ACCEPTANCE_UNREADABLE",
            f"the acceptance register could not be read: native error {error.errno}",
        )


def _entries(root: Path) -> tuple[Entry, ...]:
    contract = schema()
    device = _device(root)
    budget = _Budget()
    collected: list[Entry] = []
    nameless: list[tuple[int, int]] = []
    for directory in _spec_directories(root, device):
        _safe_stat(directory, device, directory=True)
        for entry, offset in _legacy_entries(directory, device, budget):
            if not entry.id:
                nameless.append((len(collected), offset))
            collected.append(entry)
        collected.extend(_record_entries(directory, device, budget, contract))
    _require_unique_ids(collected)
    entries = _with_derived_ids(collected, nameless)
    _require_chains(entries)
    return entries


def _require_unique_ids(entries: list[Entry]) -> None:
    seen: set[str] = set()
    for entry in entries:
        if not entry.id:
            continue
        if entry.id in seen:
            raise Refusal("ACCEPTANCE_DUPLICATE_ID", f"{entry.id} is published more than once")
        seen.add(entry.id)


def taken_ordinals(entries: list[Entry] | tuple[Entry, ...], owner: str) -> set[str]:
    """Every ordinal already spoken for in one numeric namespace.

    Every home whose leaf extracts the same three digits participates, canonical or
    preserved. Two directories that both mean spec 042 share one sequence, or the same name
    is published twice under two spellings.
    """

    return {entry.ordinal for entry in entries if entry.owner == owner and entry.ordinal}


def next_ordinal(entries: list[Entry] | tuple[Entry, ...], owner: str) -> str:
    """The lowest ordinal nobody holds. Historical gaps are filled rather than treated as
    corruption, because a gap is what a deleted draft or a renumbered spec leaves behind."""

    taken = taken_ordinals(entries, owner)
    for number in range(1, MAX_RECORDS_PER_SPEC + 1):
        candidate = f"{number:02d}"
        if candidate not in taken:
            return candidate
    raise Refusal(
        "ACCEPTANCE_ORDINAL_EXHAUSTED", f"spec {owner} has no acceptance ordinal left to allocate"
    )


def _with_derived_ids(collected: list[Entry], nameless: list[tuple[int, int]]) -> tuple[Entry, ...]:
    """Give every ID-less legacy block a deterministic in-memory identity.

    Stored identities reserve their ordinals first. What is left is handed out in stable
    `(home byte spelling, block byte offset)` order, so two runs on the same bytes always
    agree. The derived name exists to be displayed and to be named by a renewal; it is never
    written back into the historical block, which stays exactly as its author left it.
    """

    entries = list(collected)
    for index, _offset in sorted(
        nameless, key=lambda item: (entries[item[0]].home.encode(), item[1])
    ):
        entry = entries[index]
        ordinal = next_ordinal(entries, entry.owner)
        entries[index] = replace(
            entry, id=f"R-{entry.owner}-{ordinal}", ordinal=ordinal, provenance=DERIVED_LEGACY
        )
    return tuple(entries)


def _require_chains(entries: tuple[Entry, ...]) -> None:
    """Every renewal chain, resolved to exactly one head or refused.

    Chains are repository-wide and keyed by exact `finding`, which is what lets a later spec
    renew a predecessor recorded in an earlier one. A canonical record states its relation
    and binds its predecessor's exact bytes. Legacy blocks state nothing, so their order is
    reconstructed from the counters — and only when each counter from zero to the head names
    exactly one record. Anything else has no unique head, and inventing one is how the wrong
    record ends up deciding whether a risk is live.
    """

    for finding, group in _by_finding(entries).items():
        renewed: dict[str, Entry] = {}
        for entry in group:
            if not entry.renews:
                continue
            predecessor = next((other for other in group if other.id == entry.renews), None)
            if predecessor is None:
                raise Refusal(
                    "ACCEPTANCE_CHAIN_MISSING", f"{entry.id} renews a record that is not here"
                )
            if predecessor.id == entry.id:
                raise Refusal("ACCEPTANCE_CHAIN_CYCLE", f"{entry.id} renews itself")
            if predecessor.renewals != entry.renewals - 1:
                raise Refusal(
                    "ACCEPTANCE_CHAIN_COUNTER", f"{entry.id} does not count one past what it renews"
                )
            if predecessor.digest != entry.renews_digest:
                raise Refusal(
                    "ACCEPTANCE_CHAIN_DIGEST", f"{entry.id} does not bind its predecessor's bytes"
                )
            if entry.renews in renewed:
                raise Refusal("ACCEPTANCE_CHAIN_FORK", f"{entry.renews} is renewed more than once")
            renewed[entry.renews] = entry
        head = _reconstructed_head(group, finding)
        if head.id in renewed:
            raise Refusal("ACCEPTANCE_CHAIN_FORK", f"{head.id} is both the head and renewed")


def _reconstructed_head(group: list[Entry], finding: str) -> Entry:
    """The one record a renewal must point at.

    Legacy blocks state no relation at all, so their counters are the only thing there is:
    each counter from zero to the head has to name exactly one record. That rule settles the
    canonical case too, and it is what makes a fork or a gap undecidable rather than resolved
    by whichever record happened to be read last.
    """

    counters = sorted(entry.renewals for entry in group)
    if counters != list(range(len(group))):
        raise Refusal(
            "ACCEPTANCE_CHAIN_AMBIGUOUS",
            f"the finding {finding[:48]!r} has counters that describe no single chain",
        )
    return max(group, key=lambda entry: entry.renewals)


def _by_finding(entries: tuple[Entry, ...]) -> dict[str, list[Entry]]:
    groups: dict[str, list[Entry]] = {}
    for entry in entries:
        groups.setdefault(entry.finding, []).append(entry)
    return groups


def head_of(entries: tuple[Entry, ...], finding: str) -> Entry | None:
    """The one entry a renewal must point at, or nothing when the finding is new."""

    group = _by_finding(entries).get(finding)
    return max(group, key=lambda entry: entry.renewals) if group else None


def current(root: Path) -> Register:
    """Integrity first, then the binding. A stale record is still a record: it keeps its
    place, keeps its bytes and stays renewable, and it blocks green until a human decides
    again. Only integrity failures make a record unusable."""

    integrity = read(root)
    if integrity.outcome != "PASS":
        return integrity
    try:
        device = _device(root)
        budget = _Budget()
        # Only the head of each chain is bound to the current world. A record that has been
        # renewed is history: it is exactly what somebody signed, and holding the repository
        # red forever because the spec moved on after it would make renewal pointless.
        heads = {
            head.id
            for finding in _by_finding(integrity.entries)
            if (head := head_of(integrity.entries, finding)) is not None
        }
        for entry in integrity.entries:
            if entry.provenance != CANONICAL_RECORD or entry.id not in heads:
                continue
            _require_binding(root, entry, device, budget)
    except Refusal as refusal:
        return Register("INCOMPLETE", refusal.code, refusal.reason, integrity.entries)
    return integrity


def _anchored(root: Path, relative: str, device: int) -> Path:
    """Resolve a repository-relative path one exact component at a time under the root.

    The schema already refuses an absolute, dot, parent or backslash spelling, but a
    spelling check is not a filesystem check: a legal-looking `proof/receipt.txt` can still
    be a symlink out of the tree. Every component is proved here, so a record can only ever
    bind a file this repository holds.
    """

    if not relative or relative.startswith("/") or "\\" in relative:
        raise Refusal("ACCEPTANCE_UNSAFE_PATH", "an evidence path is not repository-relative")
    parts = relative.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise Refusal("ACCEPTANCE_UNSAFE_PATH", "an evidence path is not normalized")
    walked = root
    for part in parts[:-1]:
        walked = walked / part
        _safe_stat(walked, device, directory=True)
    # The leaf is proved by the bounded read that follows, which also requires it to be one
    # singly linked regular file on this volume.
    return walked / parts[-1]


def _require_binding(root: Path, entry: Entry, device: int, budget: _Budget) -> None:
    spec = root / "specs" / entry.home.split("/")[1] / "spec.md"
    body = _read(spec, MAX_SPEC_BYTES, device, budget)
    if "sha256:" + sha256(body).hexdigest() != entry.spec_digest:
        raise Refusal(
            "ACCEPTANCE_BINDING_STALE", f"{entry.id} no longer matches the spec it was bound to"
        )
    held = _read(_anchored(root, entry.evidence_path, device), MAX_EVIDENCE_BYTES, device, budget)
    if "sha256:" + sha256(held).hexdigest() != entry.evidence_digest:
        raise Refusal(
            "ACCEPTANCE_BINDING_STALE", f"{entry.id} no longer matches the evidence it was bound to"
        )


def expired(root: Path, today: str | None = None) -> Register:
    """The acceptances whose expiry has passed, and nothing else.

    This returns state; it does not change any. A live acceptance has never made a `FAIL` or
    an `INCOMPLETE` into a `PASS`, and a caller that treats one as permission to downgrade a
    check has stopped reading a record and started reading a bypass.
    """

    decided = current(root)
    if decided.outcome != "PASS":
        return decided
    day = today or date.today().isoformat()
    # Only the head of each chain decides. A renewal retires what it renews, so counting a
    # superseded record as independently expired reports a risk that was already renewed.
    heads = (head_of(decided.entries, finding) for finding in _by_finding(decided.entries))
    return Register("PASS", entries=tuple(e for e in heads if e is not None and e.expires < day))


@dataclass(frozen=True, slots=True)
class Plan:
    """What a renewal or first acceptance would be named and bound to, or why it is refused.

    `FAIL` here is a policy answer and not a defect: two renewals are the limit, and the
    third request is conclusively refused rather than published and flagged later.
    """

    outcome: str
    code: str = ""
    reason: str = ""
    id: str = ""
    renews: str = ""
    renews_digest: str = ""
    renewals: int = 0

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"outcome": self.outcome}
        if self.outcome == "PASS":
            result.update(
                id=self.id,
                renews=self.renews,
                renews_digest=self.renews_digest,
                renewals=self.renewals,
            )
        else:
            result.update(code=self.code, reason=self.reason)
        return result


MAX_RENEWALS = 2


def plan(root: Path, finding: str, owner: str) -> Plan:
    """Name the next record for one finding in one canonical namespace.

    The namespace is named explicitly and is not inferred from the predecessor, so a valid
    record under a preserved pre-canonical directory can be renewed only into the canonical
    target a person asked for. Nothing is written here.
    """

    if _ID.fullmatch(f"R-{owner}-01") is None:
        return Plan(
            "INCOMPLETE", "ACCEPTANCE_UNDECIDABLE_OWNER", "the target spec is not three digits"
        )
    register = read(root)
    if register.outcome != "PASS":
        return Plan("INCOMPLETE", register.code, register.reason)
    head = head_of(register.entries, finding)
    if head is not None and head.renewals >= MAX_RENEWALS:
        return Plan(
            "FAIL",
            "ACCEPTANCE_RENEWAL_EXHAUSTED",
            f"{head.id} has already been renewed {MAX_RENEWALS} times",
        )
    try:
        ordinal = next_ordinal(register.entries, owner)
    except Refusal as refusal:
        return Plan("INCOMPLETE", refusal.code, refusal.reason)
    return Plan(
        "PASS",
        id=f"R-{owner}-{ordinal}",
        renews="" if head is None else head.id,
        renews_digest="" if head is None else head.digest,
        renewals=0 if head is None else head.renewals + 1,
    )
