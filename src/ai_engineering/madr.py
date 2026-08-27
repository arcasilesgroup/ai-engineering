"""Fail-closed validation for Structured MADR v1.

The canonical schema decides frontmatter structure. This module checks the facts JSON
Schema cannot see: one filesystem home, local graph edges, real Markdown body sections and
every parent-to-child transition in Git. Validation is read-only and metadata proves
nothing about filesystem or history state.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from ai_engineering import intent, paths

ADR_HOME = "docs/adr"
SPEC_MD = "spec.md"

SCHEMA_INVALID = ("MADR_SCHEMA_INVALID", "frontmatter does not match MADR v1")
SCHEMA_UNSUPPORTED = ("MADR_SCHEMA_UNSUPPORTED", "MADR schema is unsupported")
BODY_INVALID = ("MADR_BODY_INVALID", "required MADR body content is missing or ambiguous")
UNREADABLE = ("MADR_UNREADABLE", "MADR content cannot be read")
AMBIGUOUS = ("MADR_AMBIGUOUS", "MADR identity or target is ambiguous")
GRAPH_INVALID = ("MADR_GRAPH_INVALID", "MADR graph has a broken local edge")
HOME_INVALID = ("MADR_HOME_INVALID", "MADR exists outside docs/adr")
TRANSITION_INVALID = ("MADR_TRANSITION_INVALID", "MADR status has no valid committed history")
HISTORY_UNAVAILABLE = ("MADR_HISTORY_UNAVAILABLE", "Git history cannot prove MADR transitions")

PASS = intent.Validation("PASS")
SCHEMA_PATH = paths.policy("madr-v1.schema.json")
_EXPECTED_SCHEMA_DIGEST = "e4f0e2034075b77550d3b5f192112f4f2223754b4e4bcbd7025338304ad89c83"
_V1 = "urn:ai-engineering:madr:1"
_MADR_NAME = re.compile(r"^([0-9]{4})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
_SPEC_NAME = re.compile(r"^[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*$")
_KEY = re.compile(r"^[a-z][a-z0-9_]*$")
_BARE_STRING = re.compile(r"[A-Za-z0-9][A-Za-z0-9 .,_:/-]*")
_IMPLICIT = re.compile(
    r"(?:null|~|true|false|[-+]?(?:[0-9][0-9_]*)(?:\.[0-9_]+)?|"
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}(?:[Tt ].*)?)",
    re.I,
)
_DISCOVERY_LIMIT = 65_536


class _Problem(ValueError):
    def __init__(self, result: tuple[str, str]) -> None:
        self.result = result
        super().__init__(result[1])


@dataclass(frozen=True, slots=True)
class _Parsed:
    fields: dict[str, Any]
    raw_fields: dict[str, str]
    body: str
    declares_v1: bool
    ambiguous_candidate: bool
    problem: tuple[str, str] | None = None


@dataclass(frozen=True, slots=True)
class _Implicit:
    value: str


@dataclass(frozen=True, slots=True)
class _UnsupportedScalar:
    value: str


@dataclass(frozen=True, slots=True)
class _Document:
    path: str
    identifier: str
    record: dict[str, Any]


@dataclass(frozen=True, slots=True)
class _Snapshot:
    states: dict[str, str]
    paths: dict[str, str]
    approvals: dict[str, tuple[str, str, str] | None]


def _incomplete(problem: tuple[str, str]) -> intent.Validation:
    return intent.Validation("INCOMPLETE", *problem)


class _Schema(intent._Schema):
    _KEYWORDS = intent._Schema._KEYWORDS | {
        "anyOf",
        "format",
        "x-body-sections",
        "x-decision-graph",
        "x-owner-field",
        "x-status-transitions",
    }
    _SCHEMA_LISTS = intent._Schema._SCHEMA_LISTS | {"anyOf"}

    def _check_scalars(self, schema: dict[str, Any]) -> None:
        super()._check_scalars(schema)
        if "format" in schema and schema["format"] not in {"date", "date-time"}:
            raise intent._UnsupportedSchema("unsupported string format")

    def valid(
        self,
        instance: Any,
        schema: dict[str, Any] | None = None,
        references: tuple[str, ...] = (),
    ) -> bool:
        active = self.root if schema is None else schema
        if not super().valid(instance, active, references):
            return False
        return "anyOf" not in active or any(
            self.valid(instance, child, references) for child in active["anyOf"]
        )


def _load_schema() -> tuple[dict[str, Any], _Schema]:
    try:
        schema = intent.pinned_policy(SCHEMA_PATH, _EXPECTED_SCHEMA_DIGEST)
        structural = _Schema(schema)
    except (OSError, RecursionError, TypeError, ValueError, re.error, intent._UnsupportedSchema):
        raise _Problem(SCHEMA_UNSUPPORTED) from None
    return schema, structural


def _decode(raw: bytes) -> str:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise _Problem(UNREADABLE) from error
    if "\r" in text.replace("\r\n", "") or any(
        value in text for value in ("\u0085", "\u2028", "\u2029")
    ):
        raise _Problem(UNREADABLE)
    return text.replace("\r\n", "\n")


def _scalar(value: str) -> Any:
    if value == "":
        raise _Problem(SCHEMA_INVALID)
    if value[0] in {'"', "'"}:
        if len(value) < 2 or value[-1] != value[0]:
            raise _Problem(UNREADABLE)
        if value[0] == "'":
            return value[1:-1]
        try:
            decoded = json.loads(value)
        except (json.JSONDecodeError, TypeError) as error:
            raise _Problem(UNREADABLE) from error
        if not isinstance(decoded, str):
            raise _Problem(SCHEMA_INVALID)
        return decoded
    if _IMPLICIT.fullmatch(value):
        return _Implicit(value)
    if _BARE_STRING.fullmatch(value) is None:
        return _UnsupportedScalar(value)
    return value


def _parse(raw: bytes) -> _Parsed:
    beginning = raw.removeprefix(b"\xef\xbb\xbf")
    if not beginning.startswith((b"---\n", b"---\r\n")):
        return _Parsed({}, {}, "", False, False)
    text = _decode(raw)
    closing = text.find("\n---\n", 4)
    if closing == -1:
        header = text[4:]
        body = ""
        problem = UNREADABLE
    else:
        header = text[4:closing]
        body = text[closing + 5 :]
        problem = None
    fields: dict[str, Any] = {}
    raw_fields: dict[str, str] = {}
    for line in header.split("\n"):
        if ":" not in line or line.startswith((" ", "\t", "#")):
            problem = problem or UNREADABLE
            continue
        key, raw_value = line.split(":", 1)
        if (
            _KEY.fullmatch(key) is None
            or key in raw_fields
            or (raw_value and not raw_value.startswith(" "))
        ):
            problem = AMBIGUOUS if key in raw_fields else (problem or UNREADABLE)
            continue
        scalar = raw_value[1:] if raw_value else ""
        raw_fields[key] = scalar
        try:
            fields[key] = _scalar(scalar)
        except _Problem as scalar_problem:
            problem = problem or scalar_problem.result
    madr_shape = fields.get("type") == "adr" and "id" in raw_fields
    declares = fields.get("schema") == _V1 or (fields.get("schema_version") == "1" and madr_shape)
    if problem is not None and not declares:
        raw_schema = raw_fields.get("schema")
        raw_version = raw_fields.get("schema_version")
        raw_shape = raw_fields.get("type") in {'"adr"', "adr"} and "id" in raw_fields
        declares = raw_schema in {'"urn:ai-engineering:madr:1"', _V1} or (
            raw_version in {'"1"', "1"} and raw_shape
        )
    # Ambiguity is a file that smells like a record without declaring one. A file that
    # declares a *different* schema by URN is not ambiguous — it says what it is, and
    # that thing is not a MADR (`specs/*/approval.md` carries
    # `urn:ai-engineering:spec-approval:1`). Ambiguous instead: a version number with no
    # schema name, the bare MADR shape with no schema line, or a schema line the parse
    # could not read a value from.
    declared_foreign_schema = fields.get("schema") not in (None, _V1)
    parsed_schema_unreadable = fields.get("schema") is None and "schema" in raw_fields
    ambiguous = not declares and (
        (("schema_version" in raw_fields) and not declared_foreign_schema)
        or (madr_shape and "schema" not in raw_fields)
        or parsed_schema_unreadable
    )
    return _Parsed(fields, raw_fields, body, declares, ambiguous, problem)


def _v1_fields(parsed: _Parsed) -> dict[str, str]:
    if parsed.problem is not None:
        raise _Problem(parsed.problem)
    fields: dict[str, str] = {}
    for key, raw in parsed.raw_fields.items():
        if not raw.startswith('"'):
            raise _Problem(SCHEMA_INVALID)
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as error:
            raise _Problem(SCHEMA_INVALID) from error
        if not isinstance(value, str):
            raise _Problem(SCHEMA_INVALID)
        fields[key] = value
    return fields


def _strip_fences(body: str) -> str:
    output: list[str] = []
    marker = ""
    length = 0
    for line in body.splitlines():
        if marker:
            closing = re.fullmatch(rf"[ ]{{0,3}}{re.escape(marker)}{{{length},}}[ \t]*", line)
            if closing:
                marker = ""
            output.append("")
        else:
            backtick = re.fullmatch(r"[ ]{0,3}(`{3,})([^`]*)", line)
            tilde = re.fullmatch(r"[ ]{0,3}(~{3,})(.*)", line)
            opening = backtick or tilde
            if opening:
                marker = opening.group(1)[0]
                length = len(opening.group(1))
                output.append("")
            else:
                output.append(line)
    return "\n".join(output)


def _body_valid(body: str, record: dict[str, Any], schema: dict[str, Any]) -> bool:
    clean = _strip_fences(body)
    policy = schema["x-body-sections"]
    headings = list(re.finditer(r"^## ([^\r\n]+)\s*$", clean, re.M))
    names = [heading.group(1) for heading in headings]
    if any(names.count(required) != 1 for required in policy["required"]):
        return False
    sections: dict[str, str] = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(clean)
        sections[heading.group(1)] = clean[heading.end() : end].strip()
    if any(not sections.get(required) for required in policy["required"]):
        return False
    alternatives = re.findall(
        r"(?m)^\s*(?:[0-9]+[.)]|[-*+])\s+\S.*$", sections[policy["alternatives"]]
    )
    return len(alternatives) >= 2 and (
        record["status"] != "rejected" or bool(sections[policy["rejection_reason"]])
    )


def _valid_format(record: dict[str, Any]) -> bool:
    try:
        if date.fromisoformat(record["date"]).isoformat() != record["date"]:
            return False
        if "approved_at" in record:
            timestamp = record["approved_at"]
            datetime.fromisoformat(timestamp.removesuffix("Z") + "+00:00")
            if not timestamp.endswith("Z"):
                return False
    except (AttributeError, TypeError, ValueError):
        return False
    return True


def _v1_document(
    path: str,
    parsed: _Parsed,
    schema: dict[str, Any],
    structural: _Schema,
    *,
    force: bool = False,
) -> _Document | None:
    if not parsed.declares_v1 and not force:
        return None
    fields = _v1_fields(parsed)
    name = PurePosixPath(path).name
    match = _MADR_NAME.fullmatch(name)
    if match is None:
        raise _Problem(HOME_INVALID)
    if not structural.valid(fields) or not _valid_format(fields):
        raise _Problem(SCHEMA_INVALID)
    if match.group(1) != fields["id"]:
        raise _Problem(GRAPH_INVALID)
    if not _body_valid(parsed.body, fields, schema):
        raise _Problem(BODY_INVALID)
    return _Document(path, fields["id"], fields)


def _git(root: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            input=input_bytes,
            check=False,
            capture_output=True,
            env=environment,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise _Problem(HISTORY_UNAVAILABLE) from error
    if result.returncode != 0:
        raise _Problem(HISTORY_UNAVAILABLE)
    return result.stdout


def _root(repository: Path) -> Path:
    try:
        root = repository.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise _Problem(UNREADABLE) from error
    if not root.is_dir():
        raise _Problem(UNREADABLE)
    try:
        top = Path(_git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve(strict=True)
        _git(root, "rev-parse", "--verify", "HEAD^{commit}")
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise _Problem(HISTORY_UNAVAILABLE) from error
    if top != root:
        raise _Problem(HISTORY_UNAVAILABLE)
    if _git(root, "rev-parse", "--is-shallow-repository").strip() != b"false":
        raise _Problem(HISTORY_UNAVAILABLE)
    if _git(root, "for-each-ref", "--format=%(refname)", "refs/replace").strip():
        raise _Problem(HISTORY_UNAVAILABLE)
    try:
        common = Path(_git(root, "rev-parse", "--git-common-dir").decode().strip())
        if not common.is_absolute():
            common = root / common
        grafts = common.resolve(strict=True) / "info" / "grafts"
    except (OSError, RuntimeError, UnicodeDecodeError) as error:
        raise _Problem(HISTORY_UNAVAILABLE) from error
    if grafts.exists():
        raise _Problem(HISTORY_UNAVAILABLE)
    return root


def _worktree_files(root: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    try:
        visible = _git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
        ignored = _git(root, "ls-files", "--others", "--ignored", "--exclude-standard", "-z")
        visible_paths = set(visible.rstrip(b"\0").split(b"\0")) if visible else set()
        ignored_paths = set(ignored.rstrip(b"\0").split(b"\0")) if ignored else set()
        for raw_path in sorted(visible_paths | ignored_paths):
            try:
                relative = raw_path.decode("utf-8")
            except UnicodeDecodeError as error:
                raise _Problem(UNREADABLE) from error
            pure = PurePosixPath(relative)
            if pure.is_absolute() or ".." in pure.parts or pure.as_posix() != relative:
                raise _Problem(UNREADABLE)
            path = root.joinpath(*pure.parts)
            if path.is_symlink():
                if (
                    pure.parent.as_posix() == ADR_HOME
                    or pure.name == SPEC_MD
                    or _MADR_NAME.fullmatch(pure.name) is not None
                ):
                    raise _Problem(UNREADABLE)
                continue
            if not path.exists():
                continue
            resolved = path.resolve(strict=True)
            if not resolved.is_relative_to(root):
                raise _Problem(UNREADABLE)
            try:
                exact_candidate = pure.parent.as_posix() == ADR_HOME or (
                    len(pure.parts) == 3 and pure.parts[0] == "specs" and pure.name == SPEC_MD
                )
                if raw_path in ignored_paths and not exact_candidate:
                    with path.open("rb") as stream:
                        prefix = stream.read(_DISCOVERY_LIMIT + 1)
                    beginning = prefix.removeprefix(b"\xef\xbb\xbf")
                    if not beginning.startswith((b"---\n", b"---\r\n")):
                        continue
                    normalized = beginning[:_DISCOVERY_LIMIT].replace(b"\r\n", b"\n")
                    closing = normalized.find(b"\n---\n", 4)
                    if closing == -1 and len(prefix) > _DISCOVERY_LIMIT:
                        raise _Problem(UNREADABLE)
                    header = normalized[4:] if closing == -1 else normalized[4:closing]
                    if b"schema" not in header and b"schema_version" not in header:
                        continue
                files[relative] = path.read_bytes()
            except OSError as error:
                raise _Problem(UNREADABLE) from error
    except OSError as error:
        raise _Problem(UNREADABLE) from error
    return files


def _legacy_identity(path: str, parsed: _Parsed) -> str | None:
    name = _MADR_NAME.fullmatch(PurePosixPath(path).name)
    if name is None:
        return None
    if parsed.declares_v1:
        return None
    if parsed.problem is not None:
        return None
    fields = parsed.fields
    if set(fields) != {"status", "date", "spec", "supersedes"}:
        return None
    raw_date = fields["date"]
    date_value = raw_date.value if isinstance(raw_date, _Implicit) else raw_date
    try:
        valid_date = (
            isinstance(date_value, str) and date.fromisoformat(date_value).isoformat() == date_value
        )
    except ValueError:
        valid_date = False
    if (
        not parsed.body.strip()
        or not valid_date
        or not isinstance(fields["status"], str)
        or re.fullmatch(r"(?:proposed|superseded by [0-9]{4})", fields["status"]) is None
        or not isinstance(fields["spec"], str)
        or re.fullmatch(r"[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*", fields["spec"]) is None
        or not isinstance(fields["supersedes"], str)
        or re.fullmatch(r"(?:|[0-9]{4})", fields["supersedes"]) is None
    ):
        return None
    headings = re.findall(r"(?m)^# ([0-9]{4})\.\s+\S.*$", _strip_fences(parsed.body))
    if len(headings) != 1:
        return None
    return headings[0]


def _specs(files: dict[str, bytes]) -> dict[str, str]:
    identities: defaultdict[str, list[str]] = defaultdict(list)
    valid: dict[str, str] = {}
    allowed = {"date", "id", "ref", "relations", "slug", "status", "supersedes", "type"}
    for path in sorted(files):
        raw = files[path]
        pure = PurePosixPath(path)
        if len(pure.parts) != 3 or pure.parts[0] != "specs" or pure.name != SPEC_MD:
            continue
        try:
            parsed = _parse(raw)
        except _Problem:
            raise _Problem(GRAPH_INVALID) from None
        identifier = parsed.fields.get("id")
        if isinstance(identifier, str) and re.fullmatch(r"[0-9]{3}", identifier):
            identities[identifier].append(path)
            if (
                _SPEC_NAME.fullmatch(pure.parent.name)
                and pure.parent.name[:3] == identifier
                and not set(parsed.fields) - allowed
                and parsed.fields.get("status") in {"draft", "shipped", "superseded"}
                and parsed.fields.get("type", "spec") == "spec"
            ):
                valid[identifier] = path
    if any(len(paths) != 1 for paths in identities.values()):
        raise _Problem(AMBIGUOUS)
    return valid


def _acyclic(edges: dict[str, str]) -> bool:
    color: dict[str, int] = {}
    for origin in edges:
        if color.get(origin, 0):
            continue
        chain: list[str] = []
        positions: dict[str, int] = {}
        node = origin
        while node in edges and color.get(node, 0) == 0:
            if node in positions:
                return False
            positions[node] = len(chain)
            chain.append(node)
            node = edges[node]
        for visited in chain:
            color[visited] = 2
    return True


def _snapshot(
    files: dict[str, bytes], schema: dict[str, Any], structural: _Schema, graph: bool
) -> _Snapshot:
    current: dict[str, _Document] = {}
    identities: defaultdict[str, list[str]] = defaultdict(list)
    targets: dict[str, str] = {}
    candidates: list[tuple[str, _Parsed, bool]] = []
    legacy_mismatches: list[str] = []
    for path in sorted(files):
        raw = files[path]
        try:
            parsed = _parse(raw)
        except _Problem as problem:
            if path.startswith("docs/adr/"):
                raise
            if problem.result == UNREADABLE:
                continue
            raise
        pure = PurePosixPath(path)
        in_home = pure.parent.as_posix() == ADR_HOME
        canonical_home = in_home and _MADR_NAME.fullmatch(pure.name) is not None
        if parsed.declares_v1 or parsed.ambiguous_candidate:
            if not in_home:
                raise _Problem(HOME_INVALID)
            declared = parsed.fields.get("id")
            if isinstance(declared, str) and re.fullmatch(r"[0-9]{4}", declared):
                identities[declared].append(path)
            candidates.append((path, parsed, parsed.ambiguous_candidate))
        elif in_home:
            legacy = _legacy_identity(path, parsed)
            if legacy is not None:
                identities[legacy].append(path)
                targets[legacy] = path
                filename = _MADR_NAME.fullmatch(pure.name)
                if filename is None or filename.group(1) != legacy:
                    legacy_mismatches.append(path)
            elif canonical_home:
                raise _Problem(parsed.problem or SCHEMA_INVALID)
    if any(len(paths) != 1 for paths in identities.values()):
        raise _Problem(AMBIGUOUS)
    if legacy_mismatches:
        raise _Problem(GRAPH_INVALID)
    for path, parsed, force in candidates:
        document = _v1_document(path, parsed, schema, structural, force=force)
        assert document is not None
        current[document.identifier] = document
    targets.update({identifier: document.path for identifier, document in current.items()})
    if graph:
        specs = _specs(files)
        edges: dict[str, str] = {}
        for identifier, document in current.items():
            if document.record["spec"] not in specs:
                raise _Problem(GRAPH_INVALID)
            target = document.record["supersedes"]
            if target:
                if target == identifier or target not in targets:
                    raise _Problem(GRAPH_INVALID)
                edges[identifier] = target
        if not _acyclic(edges):
            raise _Problem(GRAPH_INVALID)
    return _Snapshot(
        {identifier: document.record["status"] for identifier, document in current.items()},
        {identifier: document.path for identifier, document in current.items()},
        {
            identifier: (
                (
                    document.record["authority_role"],
                    document.record["approval_ref"],
                    document.record["approved_at"],
                )
                if document.record["status"] != "proposed"
                else None
            )
            for identifier, document in current.items()
        },
    )


def _objects(root: Path, names: list[str]) -> dict[str, bytes]:
    if not names:
        return {}
    request = b"".join(name.encode("ascii") + b"\n" for name in names)
    response = _git(root, "cat-file", "--batch", input_bytes=request)
    objects: dict[str, bytes] = {}
    cursor = 0
    for name in names:
        newline = response.find(b"\n", cursor)
        if newline == -1:
            raise _Problem(HISTORY_UNAVAILABLE)
        header = response[cursor:newline].split()
        if len(header) != 3 or header[1] not in {b"commit", b"tree", b"blob"}:
            raise _Problem(HISTORY_UNAVAILABLE)
        try:
            size = int(header[2])
        except ValueError as error:
            raise _Problem(HISTORY_UNAVAILABLE) from error
        start = newline + 1
        end = start + size
        if end >= len(response) or response[end : end + 1] != b"\n":
            raise _Problem(HISTORY_UNAVAILABLE)
        objects[name] = response[start:end]
        cursor = end + 1
    return objects


def _tree(raw: bytes, identifier_bytes: int) -> dict[str, tuple[str, str]]:
    entries: dict[str, tuple[str, str]] = {}
    cursor = 0
    while cursor < len(raw):
        space = raw.find(b" ", cursor)
        nul = raw.find(b"\0", space + 1)
        end = nul + 1 + identifier_bytes
        if space == -1 or nul == -1 or end > len(raw):
            raise _Problem(HISTORY_UNAVAILABLE)
        try:
            mode = raw[cursor:space].decode("ascii")
            name = raw[space + 1 : nul].decode("utf-8")
        except UnicodeDecodeError as error:
            raise _Problem(HISTORY_UNAVAILABLE) from error
        if not name or "/" in name or name in entries:
            raise _Problem(HISTORY_UNAVAILABLE)
        entries[name] = (mode, raw[nul + 1 : end].hex())
        cursor = end
    return entries


def _history(
    root: Path,
) -> tuple[list[str], dict[str, tuple[str, ...]], dict[str, dict[str, bytes]]]:
    lines = (
        _git(root, "rev-list", "--topo-order", "--reverse", "--parents", "HEAD")
        .decode()
        .splitlines()
    )
    if not lines:
        raise _Problem(HISTORY_UNAVAILABLE)
    revisions: list[str] = []
    parents: dict[str, tuple[str, ...]] = {}
    for line in lines:
        words = line.split()
        revisions.append(words[0])
        parents[words[0]] = tuple(words[1:])
    identifier_bytes = len(revisions[0]) // 2
    commits = _objects(root, revisions)
    roots: dict[str, str] = {}
    for revision in revisions:
        found = re.match(rb"tree ([0-9a-f]+)\n", commits[revision])
        if found is None:
            raise _Problem(HISTORY_UNAVAILABLE)
        roots[revision] = found.group(1).decode("ascii")

    root_objects = _objects(root, sorted(set(roots.values())))
    root_trees = {name: _tree(raw, identifier_bytes) for name, raw in root_objects.items()}
    second_ids = {
        identifier
        for entries in root_trees.values()
        for name, (mode, identifier) in entries.items()
        if name in {"docs", "specs"} and mode == "40000"
    }
    second_objects = _objects(root, sorted(second_ids))
    second_trees = {name: _tree(raw, identifier_bytes) for name, raw in second_objects.items()}
    third_ids: set[str] = set()
    for revision in revisions:
        root_entries = root_trees[roots[revision]]
        docs = root_entries.get("docs")
        specs = root_entries.get("specs")
        if docs and docs[0] == "40000":
            adr = second_trees[docs[1]].get("adr")
            if adr and adr[0] == "40000":
                third_ids.add(adr[1])
        if specs and specs[0] == "40000":
            third_ids.update(
                identifier
                for mode, identifier in second_trees[specs[1]].values()
                if mode == "40000"
            )
    third_objects = _objects(root, sorted(third_ids))
    third_trees = {name: _tree(raw, identifier_bytes) for name, raw in third_objects.items()}

    listings: dict[str, dict[str, str]] = {}
    blobs: set[str] = set()
    for revision in revisions:
        listing: dict[str, str] = {}
        root_entries = root_trees[roots[revision]]
        docs = root_entries.get("docs")
        if docs and docs[0] == "40000":
            adr = second_trees[docs[1]].get("adr")
            if adr and adr[0] == "40000":
                for filename, (mode, identifier) in third_trees[adr[1]].items():
                    if mode != "40000":
                        listing[f"docs/adr/{filename}"] = identifier
                        blobs.add(identifier)
        specs = root_entries.get("specs")
        if specs and specs[0] == "40000":
            for directory, (mode, identifier) in second_trees[specs[1]].items():
                if mode != "40000":
                    continue
                spec = third_trees[identifier].get(SPEC_MD)
                if spec and spec[0] != "40000":
                    listing[f"specs/{directory}/spec.md"] = spec[1]
                    blobs.add(spec[1])
        listings[revision] = listing
    contents = _objects(root, sorted(blobs))
    snapshots = {
        revision: {path: contents[blob] for path, blob in listing.items()}
        for revision, listing in listings.items()
    }
    return revisions, parents, snapshots


def _edge_valid(
    parent: _Snapshot,
    child: _Snapshot,
    allowed: set[tuple[str, str]],
    *,
    committed: bool,
) -> bool:
    if set(parent.states) - set(child.states):
        return False
    for identifier, status in child.states.items():
        before = parent.states.get(identifier)
        if (
            before is None
            and status != "proposed"
            and not (
                # A record born approved: its first committed appearance already carries the
                # approval triple (authority, reference, timestamp), so there is no earlier
                # state the leap could have skipped. Records 0024+ use this convention; every
                # record before 0023 walked proposed -> accepted in two commits. Judged only
                # where history is being replayed — the uncommitted edge (worktree against
                # HEAD) keeps the strict rule, because the worktree is where a record could
                # still appear from nothing without a person having seen it.
                committed and child.approvals.get(identifier)
            )
        ):
            return False
        if (
            before is not None
            and before != status
            and (not committed or (before, status) not in allowed)
        ):
            return False
        if (
            not committed
            and before is not None
            and parent.approvals[identifier] != child.approvals[identifier]
        ):
            return False
    return True


def _historic_snapshot(
    files: dict[str, bytes], schema: dict[str, Any], structural: _Schema
) -> _Snapshot:
    """A revision's states, best-effort where the bytes predate a schema repair.

    A full `_snapshot` refuses any revision carrying a record the current schema rejects,
    which makes one malformed historical ADR poison the verdict forever: the gate could
    never go green again without rewriting pushed history. The repair is judged at HEAD,
    where it lives; history keeps owing only what it can still answer for — the states it
    declares and the edges between them.
    """
    try:
        return _snapshot(files, schema, structural, graph=False)
    except _Problem:
        states: dict[str, str] = {}
        approvals: dict[str, tuple[str, str, str] | None] = {}
        for path in sorted(files):
            pure = PurePosixPath(path)
            if pure.parent.as_posix() != ADR_HOME:
                continue
            try:
                parsed = _parse(files[path])
            except _Problem:
                continue
            identifier = parsed.fields.get("id")
            status = parsed.fields.get("status")
            role = parsed.fields.get("authority_role")
            ref = parsed.fields.get("approval_ref")
            stamp = parsed.fields.get("approved_at")
            if not isinstance(identifier, str) or not re.fullmatch(r"[0-9]{4}", identifier):
                continue
            if not isinstance(status, str) or not status:
                continue
            states[identifier] = status
            # The stored approval triple is typed `tuple[str, str, str]`; a record born
            # before the timestamp field existed is still approved by role and reference,
            # so the missing stamp stores as the empty string. None is the proposed state's
            # no-approval, and conflating the two would let a proposed record look
            # born-approved.
            approved: tuple[str, str, str] | None = None
            if (
                status != "proposed"
                and isinstance(role, str)
                and role
                and isinstance(ref, str)
                and ref
                and (isinstance(stamp, str) or "approved_at" not in parsed.raw_fields)
            ):
                approved = (role, ref, stamp if isinstance(stamp, str) else "")
            approvals[identifier] = approved
        return _Snapshot(states, {i: f"docs/adr/{i}" for i in states}, approvals)


def _transitions(
    root: Path,
    current: _Snapshot,
    schema: dict[str, Any],
    structural: _Schema,
) -> bool:
    revisions, parents, raw_snapshots = _history(root)
    # HEAD's snapshot is fully schema-gated by `validate` before this runs; history is
    # replayed to prove every *transition*, and a revision whose content predates a repair
    # (four ADRs were born before their `supersedes`/`approved_at` fields were stamped)
    # still carries readable states. Judging that revision by today's schema would make the
    # verdict permanently un-cure-able: the bytes are pushed, the branch is protected, and
    # the record's own repair is the HEAD commit this run already gates. So a historic
    # snapshot that fails the schema falls back to the statuses its frontmatter still
    # declares, and the edges those states form are judged as strictly as ever — a record
    # that went `accepted` -> `proposed` in the broken years still fails here.
    snapshots = {
        revision: _historic_snapshot(raw_snapshots[revision], schema, structural)
        for revision in revisions
    }
    allowed = {(edge["from"], edge["to"]) for edge in schema["x-status-transitions"]["allowed"]}
    empty = _Snapshot({}, {}, {})
    for revision in revisions:
        sources = parents[revision] or ("",)
        # A merge whose decisions are one parent's decisions introduced none of its own, and
        # the edge from the other parent is a leap over states that were each validated where
        # they were made. Judging that leap as a transition fails every merge whose second
        # parent is more than one decision behind — which is every pull request, and which is
        # why this was invisible until a branch first reached CI: locally nothing ever
        # validates a merge commit.
        #
        # A merge that resolved to a set neither parent holds is new work that no line has
        # reviewed, and every one of its edges still has to be a legal transition.
        if len(sources) > 1 and any(
            parent and snapshots[parent] == snapshots[revision] for parent in sources
        ):
            continue
        for parent in sources:
            if not _edge_valid(
                empty if not parent else snapshots[parent],
                snapshots[revision],
                allowed,
                committed=True,
            ):
                return False
    head = revisions[-1]
    return _edge_valid(snapshots[head], current, allowed, committed=False)


def validate(repository: Path) -> intent.Validation:
    """Validate every Structured MADR v1 in one concrete local Git repository."""

    try:
        schema, structural = _load_schema()
        root = _root(repository)
        current = _snapshot(_worktree_files(root), schema, structural, graph=True)
    except _Problem as problem:
        return _incomplete(problem.result)
    except (KeyError, RecursionError, TypeError, ValueError, re.error, OSError):
        return _incomplete(SCHEMA_UNSUPPORTED)
    try:
        if not _transitions(root, current, schema, structural):
            return _incomplete(TRANSITION_INVALID)
    except _Problem as problem:
        return _incomplete(problem.result)
    except (KeyError, RecursionError, TypeError, ValueError, UnicodeError, OSError):
        return _incomplete(HISTORY_UNAVAILABLE)
    return PASS
