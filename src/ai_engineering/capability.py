"""Fail-closed capability declarations and action preflight.

The shipped manifest declares scope; it does not prove enforcement. P0 has no executor
that owns the requested filesystem, process, network or secret operation, so preflight
never promotes metadata to READY. Unknown scope is denied and declared scope remains
INCOMPLETE until a later installed executor can bind the decision to the operation.
"""

from __future__ import annotations

import json
import os
import re
import stat
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

from ai_engineering import intent, paths

SCHEMA_UNSUPPORTED = ("CAPABILITY_SCHEMA_UNSUPPORTED", "capability schema is unsupported")
MANIFEST_UNREADABLE = ("CAPABILITY_MANIFEST_UNREADABLE", "capability manifest cannot be read")
MANIFEST_INVALID = ("CAPABILITY_MANIFEST_INVALID", "capability manifest is invalid")
CAPABILITY_UNDECLARED = ("CAPABILITY_UNDECLARED", "capability is not declared")
MODE_UNDECLARED = ("CAPABILITY_MODE_UNDECLARED", "capability mode is not declared")
ACTION_INVALID = ("CAPABILITY_ACTION_INVALID", "requested action is malformed")
ACTION_UNDECLARED = ("CAPABILITY_ACTION_UNDECLARED", "requested action is outside declared scope")
ENFORCEMENT_UNAVAILABLE = (
    "CAPABILITY_ENFORCEMENT_UNAVAILABLE",
    "declared enforcement did not execute",
)

PASS = intent.Validation("PASS")
SCHEMA_PATH = paths.policy("capability-manifest.schema.json")
MANIFEST_PATH = paths.policy("capabilities.toml")
# Moved deliberately when the manifest gained `phase`, and moved a second time when an
# independent review found the sentence explaining it counting the wrong things: it said
# twelve commands, where the catalogue is fifteen capabilities, the skill tree is twelve
# directories and the CLI has ten verbs. The pin is what makes a change here a decision
# somebody takes rather than a file that drifted, and a wrong number inside a governed file
# is exactly what it exists to make expensive.
_EXPECTED_SCHEMA_DIGEST = "1f1273266cc1f01a366aa5277082c6fe50976cee16f0adda045e62461f1df9e2"
_MAX_POLICY_BYTES = 1_000_000
# The `\.` alternative that stood here matched nothing the class after it did not:
# a dot is already in `[A-Za-z0-9._-]`. It read as though a lone `.` were special
# and handled apart, and it never was — `_DOT_SEGMENT` below is what refuses dot
# segments, in one place, on every root.
_ROOT = re.compile(r"^[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$")
_DOT_SEGMENT = re.compile(r"(^|/)\.{1,2}(/|$)")
_WILDCARD = re.compile(r"[*?\[\]{}]")
_DIMENSIONS = {
    "read_roots": "preflight.read",
    "write_roots": "preflight.write",
    "exec_allowlist": "preflight.exec",
    "network": "preflight.network",
    "secrets": "preflight.secrets",
}


class _Problem(ValueError):
    def __init__(self, result: tuple[str, str]) -> None:
        self.result = result
        super().__init__(result[1])


class _Schema(intent._Schema):
    _KEYWORDS = intent._Schema._KEYWORDS | {
        "anyOf",
        "x-capability-policy",
        "x-mode-policy",
    }
    _SCHEMA_LISTS = intent._Schema._SCHEMA_LISTS | {"anyOf"}
    _TYPES = intent._Schema._TYPES | {"boolean"}

    @staticmethod
    def _matches_type(instance: Any, expected: str) -> bool:
        if expected == "boolean":
            return isinstance(instance, bool)
        return intent._Schema._matches_type(instance, expected)

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


@dataclass(frozen=True, slots=True)
class Action:
    kind: str
    path: str = ""
    argv: tuple[str, ...] = ()
    protocol: str = ""
    host: str = ""
    purpose: str = ""
    secret: str = ""

    @classmethod
    def read(cls, path: str) -> Action:
        return cls("read", path=path)

    @classmethod
    def write(cls, path: str) -> Action:
        return cls("write", path=path)

    @classmethod
    def execute(cls, *argv: str) -> Action:
        return cls("exec", argv=tuple(argv))

    @classmethod
    def connect(cls, protocol: str, host: str, purpose: str) -> Action:
        return cls("network", protocol=protocol, host=host, purpose=purpose)

    @classmethod
    def use_secret(cls, secret: str) -> Action:
        return cls("secret", secret=secret)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()


def _read(path: Path, problem: tuple[str, str]) -> bytes:
    descriptor = -1
    close_failed = False
    try:
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise OSError("policy path is not a regular file")
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_BINARY", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        identity = (opened.st_dev, opened.st_ino)
        if not stat.S_ISREG(opened.st_mode) or identity != (before.st_dev, before.st_ino):
            raise OSError("policy identity changed while opening")
        chunks: list[bytes] = []
        remaining = _MAX_POLICY_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        after = path.lstat()
        if identity != (after.st_dev, after.st_ino):
            raise OSError("policy identity changed while reading")
        raw = b"".join(chunks)
    except OSError as error:
        raise _Problem(problem) from error
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                close_failed = True
    if close_failed or len(raw) > _MAX_POLICY_BYTES:
        raise _Problem(problem)
    return raw


def _load_schema() -> tuple[dict[str, Any], _Schema]:
    try:
        schema = intent._json(_read(SCHEMA_PATH, SCHEMA_UNSUPPORTED))
        if not isinstance(schema, dict):
            raise ValueError("schema is not an object")
        if sha256(_canonical_json(schema)).hexdigest() != _EXPECTED_SCHEMA_DIGEST:
            raise ValueError("capability policy differs from its approved contract")
        structural = _Schema(schema)
    except _Problem:
        raise
    except (RecursionError, TypeError, ValueError, re.error, intent._UnsupportedSchema):
        raise _Problem(SCHEMA_UNSUPPORTED) from None
    return schema, structural


def _load_manifest(source: Mapping[str, Any] | Path | None) -> dict[str, Any]:
    if isinstance(source, Mapping):
        try:
            materialized = intent._json(_canonical_json(dict(source)))
        except (RecursionError, TypeError, ValueError):
            raise _Problem(MANIFEST_INVALID) from None
        if not isinstance(materialized, dict):
            raise _Problem(MANIFEST_INVALID)
        return materialized
    path = MANIFEST_PATH if source is None else source
    if not isinstance(path, Path):
        raise _Problem(MANIFEST_INVALID)
    try:
        value = tomllib.loads(_read(path, MANIFEST_UNREADABLE).decode("utf-8"))
    except _Problem:
        raise
    except (UnicodeDecodeError, tomllib.TOMLDecodeError):
        raise _Problem(MANIFEST_UNREADABLE) from None
    if not isinstance(value, dict):
        raise _Problem(MANIFEST_INVALID)
    return value


def _semantic_valid(manifest: dict[str, Any], schema: dict[str, Any]) -> bool:
    capabilities = manifest["capabilities"]
    policy = schema["x-capability-policy"]
    identifiers = [entry[policy["id_field"]] for entry in capabilities]
    if len(identifiers) != len(set(identifiers)) or set(identifiers) != set(policy["allowed_ids"]):
        return False

    mode_policy = schema["x-mode-policy"]
    proof_ids: list[str] = []
    for capability in capabilities:
        modes = capability["modes"]
        mode_ids = [mode[mode_policy["id_field"]] for mode in modes]
        if len(mode_ids) != len(set(mode_ids)):
            return False
        permissions = [
            _canonical_json(
                {
                    field: (
                        sorted(mode[field], key=_canonical_json)
                        if field in _DIMENSIONS
                        else mode[field]
                    )
                    for field in mode_policy["permission_fields"]
                }
            )
            for mode in modes
        ]
        if len(permissions) != len(set(permissions)):
            return False
        for mode in modes:
            expected = {control for field, control in _DIMENSIONS.items() if mode[field]}
            if mode["human_gate"] != "never":
                expected.add("preflight.human-gate")
            if set(mode["enforcement"]) != expected:
                return False
            proof = mode["proof_requirements"]
            if set(proof["allow"]) & set(proof["deny"]):
                return False
            proof_ids.extend([*proof["allow"], *proof["deny"]])
    return len(proof_ids) == len(set(proof_ids))


def _validated(source: Mapping[str, Any] | Path | None) -> dict[str, Any]:
    schema, structural = _load_schema()
    manifest = _load_manifest(source)
    try:
        if not structural.valid(manifest) or not _semantic_valid(manifest, schema):
            raise _Problem(MANIFEST_INVALID)
    except _Problem:
        raise
    except (KeyError, RecursionError, TypeError, ValueError):
        raise _Problem(MANIFEST_INVALID) from None
    return manifest


def validate(source: Mapping[str, Any] | Path | None = None) -> intent.Validation:
    """Validate one manifest against the approved canonical schema and semantic policy."""

    try:
        _validated(source)
    except _Problem as problem:
        return intent.Validation("INCOMPLETE", *problem.result)
    return PASS


def _normal_path(raw: str) -> PurePosixPath | None:
    if (
        not isinstance(raw, str)
        or not _ROOT.fullmatch(raw)
        or _WILDCARD.search(raw)
        or (raw != "." and _DOT_SEGMENT.search(raw))
    ):
        return None
    path = PurePosixPath(raw)
    return path if path.as_posix() == raw and not path.is_absolute() else None


def _within(requested: str, roots: list[str]) -> bool:
    path = _normal_path(requested)
    if path is None:
        return False
    for raw_root in roots:
        root = _normal_path(raw_root)
        if root == PurePosixPath(".") or (
            root is not None and (path == root or root in path.parents)
        ):
            return True
    return False


def _secret_path(path: str) -> str:
    name = PurePosixPath(path).name.lower()
    if name == ".env" or name.startswith(".env."):
        return "repository.env"
    if name in {".git-credentials", ".npmrc", ".pypirc", "credentials"}:
        return "repository.credentials"
    if name in {"id_dsa", "id_ecdsa", "id_ed25519", "id_rsa"} or name.endswith(
        (".key", ".pem", ".p12", ".pfx")
    ):
        return "repository.private-key"
    return ""


def _declared_action(mode: dict[str, Any], action: Action) -> bool:
    if action.kind == "read":
        secret = _secret_path(action.path)
        return (
            action == Action.read(action.path)
            and _within(action.path, mode["read_roots"])
            and (not secret or secret in mode["secrets"])
        )
    if action.kind == "write":
        secret = _secret_path(action.path)
        return (
            action == Action.write(action.path)
            and _within(action.path, mode["write_roots"])
            and (not secret or secret in mode["secrets"])
        )
    if action.kind == "exec":
        return (
            action == Action.execute(*action.argv)
            and bool(action.argv)
            and all(isinstance(item, str) and item and "\x00" not in item for item in action.argv)
            and any(entry["executable"] == action.argv[0] for entry in mode["exec_allowlist"])
        )
    if action.kind == "network":
        expected = {
            "protocol": action.protocol,
            "host": action.host,
            "purpose": action.purpose,
        }
        return (
            action == Action.connect(action.protocol, action.host, action.purpose)
            and expected in mode["network"]
        )
    if action.kind == "secret":
        return action == Action.use_secret(action.secret) and action.secret in mode["secrets"]
    return False


_ACTION_CONTROLS = {
    "read": "preflight.read",
    "write": "preflight.write",
    "exec": "preflight.exec",
    "network": "preflight.network",
    "secret": "preflight.secrets",
}


def preflight(
    capability_id: str,
    mode_id: str,
    action: Action,
) -> intent.Validation:
    """Check canonical declaration and refuse until an installed executor proves enforcement."""

    try:
        manifest = _validated(None)
    except _Problem as problem:
        return intent.Validation("INCOMPLETE", *problem.result)
    capability = next(
        (entry for entry in manifest["capabilities"] if entry["id"] == capability_id), None
    )
    if capability is None:
        return intent.Validation("INCOMPLETE", *CAPABILITY_UNDECLARED)
    mode = next((entry for entry in capability["modes"] if entry["id"] == mode_id), None)
    if mode is None:
        return intent.Validation("INCOMPLETE", *MODE_UNDECLARED)
    if (
        not isinstance(action, Action)
        or not isinstance(action.kind, str)
        or action.kind not in _ACTION_CONTROLS
    ):
        return intent.Validation("INCOMPLETE", *ACTION_INVALID)
    control = _ACTION_CONTROLS[action.kind]
    try:
        declared = control in mode["enforcement"] and _declared_action(mode, action)
    except (KeyError, TypeError, ValueError):
        return intent.Validation("INCOMPLETE", *ENFORCEMENT_UNAVAILABLE)
    if not declared:
        return intent.Validation("INCOMPLETE", *ACTION_UNDECLARED)
    return intent.Validation("INCOMPLETE", *ENFORCEMENT_UNAVAILABLE)
