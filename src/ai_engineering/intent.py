"""Fail-closed validation for the user-owned Solution Intent.

The JSON Schema is the one structural authority. This module implements only the schema
features that authority uses, then checks facts a schema cannot prove: target bytes,
repository containment, relation cycles and lifecycle history. Validation never writes.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

from ai_engineering import paths

DEFS_KEY = "$defs"
NON_CANONICAL = "Intent path is not canonical"

SCHEMA_INVALID = ("INTENT_SCHEMA_INVALID", "schema validation failed")
# Absent is not malformed. A repository where nobody has written an Intent yet and one
# holding an Intent that does not parse are two different states, and they were the same
# answer here — which is the reading `claim_scope_guard` refuses one directory over, and
# which made a stranger's first install report a schema failure over a file that was never
# there.
MISSING = ("INTENT_MISSING", "no Intent has been written here yet")
RELATION_STALE = ("INTENT_RELATION_STALE", "relation digest does not match target")
RELATION_MISSING = ("INTENT_RELATION_BROKEN", "relation target does not exist")
RELATION_AMBIGUOUS = ("INTENT_RELATION_BROKEN", "relation target is ambiguous")
RELATION_OUTSIDE = ("INTENT_RELATION_BROKEN", "relation target is outside repository")
RELATION_UNREADABLE = ("INTENT_RELATION_BROKEN", "relation target cannot be read")
RELATION_IDENTITY = (
    "INTENT_RELATION_BROKEN",
    "relation target identity does not match relation",
)
RELATION_CYCLE = ("INTENT_RELATION_CYCLE", "relation graph contains a cycle")
LIFECYCLE_INVALID = (
    "INTENT_LIFECYCLE_INVALID",
    "lifecycle history does not reach declared status",
)


@dataclass(frozen=True, slots=True)
class Validation:
    """One stable machine result for an Intent validation."""

    outcome: str
    code: str = ""
    reason: str = ""

    def as_dict(self) -> dict[str, str]:
        result = {"outcome": self.outcome}
        if self.outcome != "PASS":
            result.update(code=self.code, reason=self.reason)
        return result


PASS = Validation("PASS")


def _incomplete(problem: tuple[str, str]) -> Validation:
    return Validation("INCOMPLETE", *problem)


class _UnsupportedSchema(ValueError):
    pass


class _RepositoryProblem(ValueError):
    def __init__(self, result: tuple[str, str]) -> None:
        self.result = result
        super().__init__(result[1])


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-JSON number: {value}")


def _json(payload: str | bytes) -> Any:
    return json.loads(
        payload,
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )


def canonical_json(value: Any) -> bytes:
    """The digest input every pinned policy agrees on. Four modules carried byte-identical
    copies of this under private names; the pin only means something if every reader
    hashes the same bytes, so the helper lives where the JSON vocabulary lives."""
    return json.dumps(
        value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()


def pinned_policy(path: Path, digest: str, *, bounded: int | None = None) -> dict[str, Any]:
    """Read a policy file, parse it strictly, and refuse unless its canonical digest is
    the one this release was built against. Five modules carried the same five-step
    reader (read, parse, object-check, canonical digest, one-line refusal) differing
    only in the error each raises; the error stays the caller's, so this raises
    ValueError on every refusal and the caller translates. Spec 044 / D-044-03."""
    raw = paths.read_bounded(path, bounded, "policy") if bounded is not None else path.read_bytes()
    loaded = _json(raw)
    if not isinstance(loaded, dict):
        raise ValueError("policy is not an object")
    if sha256(canonical_json(loaded)).hexdigest() != digest:
        raise ValueError("policy differs from its approved contract")
    return loaded


_RFC3339_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


def _iso_value(instance: Any, fmt: str) -> bool:
    """RFC3339 shape for "date" / UTC-only "date-time". Three validators carried private
    copies of this; one is enough. The date half is the fromisoformat round-trip, which
    refuses everything a `YYYY-MM-DD` can be misspelled as."""
    if not isinstance(instance, str):
        return False
    try:
        if fmt == "date":
            return date.fromisoformat(instance).isoformat() == instance
        if _RFC3339_UTC.fullmatch(instance) is None:
            return False
        return datetime.fromisoformat(
            instance.removesuffix("Z") + "+00:00"
        ).utcoffset() == timedelta(0)
    except (OverflowError, ValueError):
        return False


class _Schema:
    _KEYWORDS = {
        DEFS_KEY,
        "$id",
        "$ref",
        "$schema",
        "additionalProperties",
        "allOf",
        "anyOf",
        "const",
        "description",
        "else",
        "enum",
        "format",
        "if",
        "items",
        "maxItems",
        "maxLength",
        "minimum",
        "minItems",
        "minLength",
        "not",
        "oneOf",
        "pattern",
        "properties",
        "required",
        "then",
        "title",
        "type",
        "uniqueItems",
        "x-canonical-home",
    }
    _SCHEMA_MAPS = {DEFS_KEY, "properties"}
    _SCHEMA_LISTS = {"allOf", "oneOf", "anyOf"}
    _SCHEMAS = {"else", "if", "items", "not", "then"}
    _TYPES = {"array", "integer", "object", "string"}

    def __init__(self, root: dict[str, Any]) -> None:
        self.root = root
        self._check(root)

    def _check(self, schema: Any) -> None:
        if not isinstance(schema, dict) or set(schema) - self._KEYWORDS:
            raise _UnsupportedSchema("unsupported schema shape or keyword")
        if "$ref" in schema:
            self._reference(schema["$ref"])
        if "type" in schema and schema["type"] not in self._TYPES:
            raise _UnsupportedSchema("unsupported schema type")
        if "pattern" in schema:
            if not isinstance(schema["pattern"], str):
                raise _UnsupportedSchema("non-string pattern")
            re.compile(schema["pattern"])
        for key in self._SCHEMA_MAPS:
            if key in schema:
                if not isinstance(schema[key], dict):
                    raise _UnsupportedSchema(f"{key} is not an object")
                for child in schema[key].values():
                    self._check(child)
        for key in self._SCHEMA_LISTS:
            if key in schema:
                if not isinstance(schema[key], list):
                    raise _UnsupportedSchema(f"{key} is not an array")
                for child in schema[key]:
                    self._check(child)
        for key in self._SCHEMAS:
            if key in schema:
                self._check(schema[key])
        self._check_scalars(schema)

    def _check_scalars(self, schema: dict[str, Any]) -> None:
        for key in ("minItems", "maxItems", "minLength", "maxLength"):
            if key in schema and (
                not isinstance(schema[key], int) or isinstance(schema[key], bool) or schema[key] < 0
            ):
                raise _UnsupportedSchema(f"invalid {key}")
        if "required" in schema and (
            not isinstance(schema["required"], list)
            or not all(isinstance(key, str) for key in schema["required"])
            or len(schema["required"]) != len(set(schema["required"]))
        ):
            raise _UnsupportedSchema("invalid required")
        if "enum" in schema and not isinstance(schema["enum"], list):
            raise _UnsupportedSchema("invalid enum")
        if "uniqueItems" in schema and not isinstance(schema["uniqueItems"], bool):
            raise _UnsupportedSchema("invalid uniqueItems")
        if "additionalProperties" in schema and not isinstance(
            schema["additionalProperties"], bool
        ):
            raise _UnsupportedSchema("unsupported additionalProperties")
        if "minimum" in schema and (
            not isinstance(schema["minimum"], int) or isinstance(schema["minimum"], bool)
        ):
            raise _UnsupportedSchema("invalid minimum")
        if "format" in schema and schema["format"] not in {"date", "date-time"}:
            raise _UnsupportedSchema("unsupported string format")

    def _reference(self, reference: Any) -> dict[str, Any]:
        if not isinstance(reference, str) or not reference.startswith("#/$defs/"):
            raise _UnsupportedSchema("only local definition references are supported")
        name = reference.removeprefix("#/$defs/")
        if not name or "/" in name:
            raise _UnsupportedSchema("unsupported definition reference")
        definitions = self.root.get(DEFS_KEY)
        if not isinstance(definitions, dict) or not isinstance(definitions.get(name), dict):
            raise _UnsupportedSchema("unknown definition reference")
        return definitions[name]

    def valid(
        self,
        instance: Any,
        schema: dict[str, Any] | None = None,
        references: tuple[str, ...] = (),
    ) -> bool:
        schema = self.root if schema is None else schema
        reference = schema.get("$ref")
        if reference is not None:
            if reference in references:
                raise _UnsupportedSchema("recursive references are unsupported")
            if not self.valid(instance, self._reference(reference), (*references, reference)):
                return False

        if "const" in schema and instance != schema["const"]:
            return False
        if "enum" in schema and instance not in schema["enum"]:
            return False
        if "type" in schema and not self._matches_type(instance, schema["type"]):
            return False

        if isinstance(instance, str):
            if len(instance) < schema.get("minLength", 0):
                return False
            if "maxLength" in schema and len(instance) > schema["maxLength"]:
                return False
            if "pattern" in schema and re.search(schema["pattern"], instance) is None:
                return False
        if isinstance(instance, list):
            if len(instance) < schema.get("minItems", 0):
                return False
            if "maxItems" in schema and len(instance) > schema["maxItems"]:
                return False
            if schema.get("uniqueItems") and not self._unique(instance):
                return False
            if "items" in schema and not all(
                self.valid(value, schema["items"], references) for value in instance
            ):
                return False
        if isinstance(instance, dict):
            required = schema.get("required", [])
            if any(key not in instance for key in required):
                return False
            properties = schema.get("properties", {})
            if schema.get("additionalProperties") is False and set(instance) - set(properties):
                return False
            if any(
                key in instance and not self.valid(instance[key], child, references)
                for key, child in properties.items()
            ):
                return False

        if "anyOf" in schema and not any(
            self.valid(instance, child, references) for child in schema["anyOf"]
        ):
            return False
        if isinstance(instance, int) and (instance < schema.get("minimum", instance)):
            # bool is an int in Python; evidence's original check counted it, so a
            # bool against `minimum` fails here exactly as it did before the merge.
            return False
        if "format" in schema and not _iso_value(instance, schema["format"]):
            return False
        if "allOf" in schema and not all(
            self.valid(instance, child, references) for child in schema["allOf"]
        ):
            return False
        if (
            "oneOf" in schema
            and sum(self.valid(instance, child, references) for child in schema["oneOf"]) != 1
        ):
            return False
        if "not" in schema and self.valid(instance, schema["not"], references):
            return False
        if "if" in schema:
            branch = "then" if self.valid(instance, schema["if"], references) else "else"
            if branch in schema and not self.valid(instance, schema[branch], references):
                return False
        return True

    @staticmethod
    def _matches_type(instance: Any, expected: str) -> bool:
        return {
            "array": isinstance(instance, list),
            "integer": isinstance(instance, int) and not isinstance(instance, bool),
            "object": isinstance(instance, dict),
            "string": isinstance(instance, str),
        }[expected]

    @staticmethod
    def _unique(items: list[Any]) -> bool:
        try:
            encoded = [
                json.dumps(item, allow_nan=False, separators=(",", ":"), sort_keys=True)
                for item in items
            ]
        except (TypeError, ValueError):
            return False
        return len(encoded) == len(set(encoded))


def _normal_path(raw: Any) -> str:
    if not isinstance(raw, str) or not raw or "\\" in raw or "\x00" in raw:
        raise _RepositoryProblem(RELATION_OUTSIDE)
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != raw:
        raise _RepositoryProblem(RELATION_OUTSIDE)
    return raw


class _Files:
    def read(self, relative: str) -> bytes:
        raise NotImplementedError


class _RootFiles(_Files):
    def __init__(self, root: Path) -> None:
        try:
            self.root = root.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise _RepositoryProblem(RELATION_UNREADABLE) from error
        if not self.root.is_dir():
            raise _RepositoryProblem(RELATION_UNREADABLE)

    def read(self, relative: str) -> bytes:
        relative = _normal_path(relative)
        candidate = self.root.joinpath(*PurePosixPath(relative).parts)
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError as error:
            raise _RepositoryProblem(RELATION_MISSING) from error
        except (OSError, RuntimeError) as error:
            raise _RepositoryProblem(RELATION_UNREADABLE) from error
        if not resolved.is_relative_to(self.root):
            raise _RepositoryProblem(RELATION_OUTSIDE)
        if not resolved.is_file():
            raise _RepositoryProblem(RELATION_UNREADABLE)
        try:
            return resolved.read_bytes()
        except OSError as error:
            raise _RepositoryProblem(RELATION_UNREADABLE) from error


class _MaterializedFiles(_Files):
    def __init__(
        self,
        values: Mapping[str, str | bytes] | Iterable[tuple[str, str | bytes]],
    ) -> None:
        entries = values.items() if isinstance(values, Mapping) else values
        self.values: dict[str, bytes] = {}
        try:
            for raw_path, raw_content in entries:
                path = _normal_path(raw_path)
                if path in self.values:
                    raise _RepositoryProblem(RELATION_AMBIGUOUS)
                if not isinstance(raw_content, (str, bytes)):
                    raise _RepositoryProblem(RELATION_UNREADABLE)
                self.values[path] = (
                    raw_content.encode("utf-8") if isinstance(raw_content, str) else raw_content
                )
        except _RepositoryProblem:
            raise
        except (TypeError, ValueError) as error:
            raise _RepositoryProblem(RELATION_UNREADABLE) from error

    def read(self, relative: str) -> bytes:
        relative = _normal_path(relative)
        try:
            return self.values[relative]
        except KeyError as error:
            raise _RepositoryProblem(RELATION_MISSING) from error


def _load_schema() -> tuple[dict[str, Any], _Schema]:
    schema = _json(paths.policy("intent-v1.schema.json").read_bytes())
    if not isinstance(schema, dict):
        raise _UnsupportedSchema("schema is not an object")
    return schema, _Schema(schema)


def _load_source(source: Mapping[str, Any] | Path, files: _Files, home: str) -> Any:
    if isinstance(source, Mapping):
        return dict(source)
    if not isinstance(source, Path) or not isinstance(files, _RootFiles):
        raise ValueError("an Intent path requires a repository root")
    if ".." in source.parts:
        raise ValueError(NON_CANONICAL)
    expected = files.root.joinpath(*PurePosixPath(home).parts)
    raw = source if source.is_absolute() else files.root / source
    try:
        lexical = Path(os.path.abspath(raw))
        relative = expected.relative_to(files.root)
    except (OSError, RuntimeError, ValueError) as error:
        raise ValueError("Intent cannot be read") from error
    if lexical != expected:
        raise ValueError(NON_CANONICAL)
    component = files.root
    for part in relative.parts:
        component /= part
        if component.is_symlink():
            raise ValueError(NON_CANONICAL)
    if not expected.is_file():
        # Absent, and said so. `ValueError` here becomes `INTENT_SCHEMA_INVALID` above, which
        # sends a reader looking for a mistake in a document nobody has written.
        raise FileNotFoundError(f"no Intent at {home}")
    return _json(expected.read_bytes())


def _relation_patterns(schema: dict[str, Any]) -> tuple[re.Pattern[str], ...]:
    relation = schema[DEFS_KEY]["relation"]
    patterns: list[str] = []

    def collect(node: Any) -> None:
        if isinstance(node, dict):
            path_schema = node.get("properties", {}).get("path")
            if isinstance(path_schema, dict) and isinstance(path_schema.get("pattern"), str):
                patterns.append(path_schema["pattern"])
            for value in node.values():
                collect(value)
        elif isinstance(node, list):
            for value in node:
                collect(value)

    collect(relation)
    if not patterns:
        raise _UnsupportedSchema("relation paths have no schema patterns")
    return tuple(re.compile(pattern) for pattern in patterns)


def _scalar(raw: str) -> str:
    if not raw.startswith(" ") or raw.startswith("  "):
        raise _RepositoryProblem(RELATION_UNREADABLE)
    value = raw[1:]
    if not value or value != value.rstrip():
        raise _RepositoryProblem(RELATION_UNREADABLE)
    if any(
        ord(character) < 0x20
        or 0x7F <= ord(character) <= 0x9F
        or (character != " " and unicodedata.category(character)[0] in {"C", "Z"})
        for character in value
    ):
        raise _RepositoryProblem(RELATION_UNREADABLE)
    quotes = {'"', "'"}
    if value[0] in quotes:
        delimiter = value[0]
        if len(value) < 2 or value[-1] != delimiter:
            raise _RepositoryProblem(RELATION_UNREADABLE)
        return value[1:-1]
    if value == "[]":
        return value
    if (
        any(quote in value for quote in quotes)
        or re.fullmatch(r"[A-Za-z0-9.][A-Za-z0-9 .,_:/-]*", value) is None
    ):
        raise _RepositoryProblem(RELATION_UNREADABLE)
    return value


def _frontmatter(content: bytes) -> dict[str, str]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise _RepositoryProblem(RELATION_UNREADABLE) from error
    if any(separator in text for separator in ("\u0085", "\u2028", "\u2029")) or re.search(
        r"\r(?!\n)", text
    ):
        raise _RepositoryProblem(RELATION_UNREADABLE)
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0] != "---":
        raise _RepositoryProblem(RELATION_IDENTITY)
    try:
        closing = lines.index("---", 1)
    except ValueError as error:
        raise _RepositoryProblem(RELATION_UNREADABLE) from error
    fields: dict[str, str] = {}
    for line in lines[1:closing]:
        if ":" not in line or line.startswith((" ", "\t", "#")):
            raise _RepositoryProblem(RELATION_UNREADABLE)
        key, raw = line.split(":", 1)
        if re.fullmatch(r"[a-z][a-z0-9_]*", key) is None:
            raise _RepositoryProblem(RELATION_UNREADABLE)
        if key in fields:
            raise _RepositoryProblem(RELATION_AMBIGUOUS)
        fields[key] = _scalar(raw)
    return fields


def _document_relations(content: bytes) -> list[str]:
    fields = _frontmatter(content)
    if "relations" not in fields or fields["relations"] in {"[]", ""}:
        return []
    declaration = fields["relations"]
    relations = declaration.split(",")
    if not all(relations) or len(relations) != len(set(relations)):
        raise _RepositoryProblem(RELATION_AMBIGUOUS)
    return relations


def _path_identity(path: str) -> tuple[str, str] | None:
    spec = re.fullmatch(r"specs/([0-9]{3})-[a-z0-9]+(?:-[a-z0-9]+)*/spec\.md", path)
    if spec:
        return "spec", spec.group(1)
    decision = re.fullmatch(r"docs/adr/([0-9]{4})-[a-z0-9]+(?:-[a-z0-9]+)*\.md", path)
    if decision:
        return "decision", decision.group(1)
    return None


def _target_valid(path: str, content: bytes, relation: dict[str, Any] | None = None) -> bool:
    expected = _path_identity(path)
    if expected is None:
        return False
    if relation is not None and expected != (relation["kind"], relation["id"]):
        return False
    fields = _frontmatter(content)
    kind, identifier = expected
    if fields.get("id") != identifier:
        return False
    if kind == "spec":
        if set(fields) - {
            "date",
            "id",
            "ref",
            "relations",
            "slug",
            "status",
            "supersedes",
            "type",
        }:
            return False
        return (
            fields.get("status") in {"draft", "shipped", "superseded"}
            and fields.get("type", "spec") == "spec"
        )
    if set(fields) - {
        "approval_ref",
        "approved_at",
        "authority_role",
        "date",
        "id",
        "relations",
        "schema",
        "schema_version",
        "spec",
        "status",
        "supersedes",
        "title",
        "type",
    }:
        return False
    return fields.get("type") == "adr" and fields.get("status") in {
        "proposed",
        "accepted",
        "rejected",
        "superseded",
    }


def _register_identity(path: str, identities: dict[tuple[str, str], str]) -> None:
    identity = _path_identity(path)
    if identity is None:
        raise _RepositoryProblem(RELATION_IDENTITY)
    existing = identities.get(identity)
    if existing is not None and existing != path:
        raise _RepositoryProblem(RELATION_AMBIGUOUS)
    identities[identity] = path


def _has_cycle(graph: dict[str, list[str]]) -> bool:
    colors: dict[str, int] = {}
    for start in graph:
        if colors.get(start, 0):
            continue
        colors[start] = 1
        stack: list[tuple[str, Any]] = [(start, iter(graph.get(start, [])))]
        while stack:
            node, targets = stack[-1]
            try:
                target = next(targets)
            except StopIteration:
                colors[node] = 2
                stack.pop()
                continue
            color = colors.get(target, 0)
            if color == 1:
                return True
            if color == 0:
                colors[target] = 1
                stack.append((target, iter(graph.get(target, []))))
    return False


def _relations_valid(
    value: dict[str, Any],
    files: _Files,
    schema: dict[str, Any],
) -> Validation:
    home = schema["x-canonical-home"]
    relations = value["relations"]
    targets = [relation["path"] for relation in relations]
    if len(targets) != len(set(targets)):
        return _incomplete(RELATION_AMBIGUOUS)

    contents: dict[str, bytes] = {}
    identities: dict[tuple[str, str], str] = {}
    try:
        for relation in relations:
            target = _normal_path(relation["path"])
            _register_identity(target, identities)
            content = files.read(target)
            contents[target] = content
            if "sha256:" + sha256(content).hexdigest() != relation["target_digest"]:
                return _incomplete(RELATION_STALE)
            if not _target_valid(target, content, relation):
                return _incomplete(RELATION_IDENTITY)

        patterns = _relation_patterns(schema)
        graph = {home: targets}
        pending = list(targets)
        while pending:
            target = pending.pop()
            if target in graph:
                continue
            cached = contents.get(target)
            if cached is None:
                cached = files.read(target)
                contents[target] = cached
            content = cached
            _register_identity(target, identities)
            if not _target_valid(target, content):
                raise _RepositoryProblem(RELATION_IDENTITY)
            linked = _document_relations(content)
            for path in linked:
                path = _normal_path(path)
                if path != home and not any(pattern.fullmatch(path) for pattern in patterns):
                    raise _RepositoryProblem(RELATION_OUTSIDE)
                if path != home and path not in contents:
                    contents[path] = files.read(path)
                    pending.append(path)
            graph[target] = linked
    except _RepositoryProblem as problem:
        return _incomplete(problem.result)
    except (KeyError, TypeError, ValueError, re.error):
        return _incomplete(SCHEMA_INVALID)
    return _incomplete(RELATION_CYCLE) if _has_cycle(graph) else PASS


def _lifecycle_valid(value: dict[str, Any]) -> bool:
    state = "draft"
    for transition in value["lifecycle"]["transitions"]:
        if transition["from"] != state:
            return False
        state = transition["to"]
    return state == value["lifecycle"]["status"]


def validate(
    source: Mapping[str, Any] | Path,
    repository: Path | Mapping[str, str | bytes] | Iterable[tuple[str, str | bytes]],
) -> Validation:
    """Validate an Intent object or its canonical path against real or materialized files.

    Repository materializations are path/content pairs. They exist for deterministic tests
    and callers that already hold target bytes; neither form grants permission to write.
    """
    try:
        schema, structural = _load_schema()
        home = _normal_path(schema["x-canonical-home"])
        files: _Files = (
            _RootFiles(repository)
            if isinstance(repository, Path)
            else _MaterializedFiles(repository)
        )
        value = _load_source(source, files, home)
        if not structural.valid(value):
            return _incomplete(SCHEMA_INVALID)
    except _RepositoryProblem as problem:
        return _incomplete(problem.result)
    except FileNotFoundError:
        # Before the OSError clause below, which would otherwise call an absent file a
        # schema failure — the one answer that sends somebody looking for a mistake in a
        # document that does not exist.
        return _incomplete(MISSING)
    except (KeyError, OSError, TypeError, ValueError, re.error, _UnsupportedSchema):
        return _incomplete(SCHEMA_INVALID)

    if not _lifecycle_valid(value):
        return _incomplete(LIFECYCLE_INVALID)
    return _relations_valid(value, files, schema)
