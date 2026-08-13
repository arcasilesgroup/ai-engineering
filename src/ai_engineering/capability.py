"""Fail-closed capability declarations and action preflight.

The shipped manifest declares scope; it does not prove enforcement. A preflight reaches
READY only after this installed module executes the exact enforcer for the requested
action. Unknown capabilities, modes, actions, policy shapes and unavailable enforcement
remain INCOMPLETE.
"""

from __future__ import annotations

import json
import os
import re
import stat
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from types import MappingProxyType
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
HUMAN_GATE_REQUIRED = ("CAPABILITY_HUMAN_GATE_REQUIRED", "declared human gate is not proven")

PASS = intent.Validation("PASS")
SCHEMA_PATH = paths.policy("capability-manifest.schema.json")
MANIFEST_PATH = paths.policy("capabilities.toml")
_EXPECTED_SCHEMA_DIGEST = "2af5f4e200bcd1c19ed8577249c2fe2b0dbb41a22cc1924226f76b9b39c16620"
_MAX_POLICY_BYTES = 1_000_000
_ROOT = re.compile(r"^(?:\.|[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*)$")
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


@dataclass(frozen=True, slots=True)
class Authorization:
    """An installed preflight decision bound to one immutable action payload."""

    capability_id: str
    mode_id: str
    action: Action
    action_digest: str


@dataclass(frozen=True, slots=True)
class Preflight:
    outcome: str
    code: str = ""
    reason: str = ""
    authorization: Authorization | None = None

    def as_dict(self) -> dict[str, str]:
        result = {"outcome": self.outcome}
        if self.outcome != "READY":
            result.update(code=self.code, reason=self.reason)
        return result


@dataclass(frozen=True, slots=True)
class Effects:
    write_paths: tuple[str, ...] = ()
    network: tuple[tuple[str, str, str], ...] = ()
    secrets: tuple[str, ...] = ()


_CommandMatcher = Callable[[tuple[str, ...]], Effects | None]


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
            _canonical_json({field: mode[field] for field in mode_policy["permission_fields"]})
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


def _read_allowed(mode: dict[str, Any], action: Action) -> bool:
    secret = _secret_path(action.path)
    return (
        action == Action.read(action.path)
        and _within(action.path, mode["read_roots"])
        and (not secret or secret in mode["secrets"])
    )


def _write_allowed(mode: dict[str, Any], action: Action) -> bool:
    secret = _secret_path(action.path)
    return (
        action == Action.write(action.path)
        and _within(action.path, mode["write_roots"])
        and (not secret or secret in mode["secrets"])
    )


def _prefix(argv: tuple[str, ...], prefix: tuple[str, ...]) -> bool:
    return len(argv) >= len(prefix) and argv[: len(prefix)] == prefix


def _git_subcommand(argv: tuple[str, ...]) -> tuple[str, tuple[str, ...]] | None:
    if len(argv) < 2 or argv[1].startswith("-"):
        return None
    return argv[1], argv[2:]


def _git_read(argv: tuple[str, ...]) -> Effects | None:
    parsed = _git_subcommand(argv)
    if parsed is None:
        return None
    command, arguments = parsed
    if command not in {
        "diff",
        "log",
        "ls-files",
        "rev-parse",
        "show",
        "status",
    }:
        return None
    forbidden = {
        "--exec-path",
        "--ext-diff",
        "--no-index",
        "--no-pager",
        "--paginate",
        "--path-format=absolute",
        "--textconv",
    }
    if any(
        item in forbidden
        or item.startswith(("--exec-path=", "--output=", "--path-format="))
        or item in {"-o", "--output"}
        for item in arguments
    ):
        return None
    return Effects()


def _git_change(argv: tuple[str, ...]) -> Effects | None:
    parsed = _git_subcommand(argv)
    if parsed is None:
        return None
    command, arguments = parsed
    if command not in {"add", "restore", "rm"} or "--" not in arguments:
        return None
    separator = arguments.index("--")
    targets = arguments[separator + 1 :]
    if not targets or any(_normal_path(target) is None for target in targets):
        return None
    allowed_options = {
        "add": {"-A", "--all", "-u", "--update"},
        "restore": {"--staged", "--worktree"},
        "rm": {"-r", "--recursive"},
    }[command]
    if any(option not in allowed_options for option in arguments[:separator]):
        return None
    return Effects(write_paths=targets)


def _git_commit(argv: tuple[str, ...]) -> Effects | None:
    forbidden = {"--all", "--amend", "--include", "--no-verify", "-a", "-i"}
    parsed = _git_subcommand(argv)
    if parsed is None or parsed[0] != "commit":
        return None
    arguments = parsed[1]
    if any(
        item in forbidden
        or (item.startswith("-") and "a" in item[1:] and not item.startswith("--"))
        or item.startswith("--fixup=")
        for item in arguments
    ):
        return None
    return Effects(write_paths=(".",))


def _git_push(argv: tuple[str, ...]) -> Effects | None:
    forbidden = {"-f", "--force", "--force-with-lease"}
    parsed = _git_subcommand(argv)
    if parsed is None or parsed[0] != "push" or not forbidden.isdisjoint(parsed[1]):
        return None
    return Effects(
        network=(("https", "api.github.com", "pull-request.publish"),),
        secrets=("github.token",),
    )


def _ai_eng_spec(argv: tuple[str, ...]) -> Effects | None:
    if len(argv) != 4 or argv[:3] != ("ai-eng", "spec", "new"):
        return None
    return Effects(write_paths=("specs",))


def _github_issue(argv: tuple[str, ...]) -> Effects | None:
    if not _prefix(argv, ("gh", "issue", "create")):
        return None
    return Effects(
        network=(("https", "api.github.com", "issue.publish"),),
        secrets=("github.token",),
    )


def _github_pr(argv: tuple[str, ...]) -> Effects | None:
    if not _prefix(argv, ("gh", "pr", "create")):
        return None
    return Effects(
        network=(("https", "api.github.com", "pull-request.publish"),),
        secrets=("github.token",),
    )


def _uv_unproven(argv: tuple[str, ...]) -> Effects | None:
    if not _prefix(argv, ("uv", "run")):
        return None
    allowed = {"coverage", "pytest", "ruff"}
    index = 2
    value_options = {"--directory", "--project", "--python", "--with"}
    while index < len(argv):
        item = argv[index]
        if item in value_options:
            index += 2
            continue
        if item.startswith("--with=") or item in {"--no-project", "--offline"}:
            index += 1
            continue
        if item not in allowed:
            return None
        raise LookupError("uv command effects are not proven by an installed matcher")
    return None


def _unproven_command(argv: tuple[str, ...]) -> Effects | None:
    del argv
    raise LookupError("command effects are not proven by an installed matcher")


_ARGUMENT_MATCHERS: Mapping[tuple[str, str], _CommandMatcher] = MappingProxyType(
    {
        ("ai-eng", "spec.new"): _ai_eng_spec,
        ("gh", "issue.create"): _github_issue,
        ("gh", "pr.create"): _github_pr,
        ("git", "commit"): _git_commit,
        ("git", "push"): _git_push,
        ("git", "read-only"): _git_read,
        ("git", "scoped.change"): _git_change,
        ("gitleaks", "repository.scan"): _unproven_command,
        ("just", "check"): _unproven_command,
        ("just", "declared.recipe"): _unproven_command,
        ("npm", "declared.check"): _unproven_command,
        ("npm", "run.dev"): _unproven_command,
        ("semgrep", "repository.scan"): _unproven_command,
        ("trivy", "repository.scan"): _unproven_command,
        ("uv", "declared.check"): _uv_unproven,
    }
)


def _effects_allowed(mode: dict[str, Any], effects: Effects) -> bool:
    if any(not _within(path, mode["write_roots"]) for path in effects.write_paths):
        return False
    if any(
        {"protocol": protocol, "host": host, "purpose": purpose} not in mode["network"]
        for protocol, host, purpose in effects.network
    ):
        return False
    return not (set(effects.secrets) - set(mode["secrets"]))


def _exec_allowed(mode: dict[str, Any], action: Action) -> tuple[bool, Effects]:
    if (
        action != Action.execute(*action.argv)
        or not action.argv
        or not all(isinstance(item, str) and item and "\x00" not in item for item in action.argv)
    ):
        return False, Effects()
    executable = action.argv[0]
    declared = [entry for entry in mode["exec_allowlist"] if entry["executable"] == executable]
    for entry in declared:
        matcher = _ARGUMENT_MATCHERS.get((executable, entry["argument_pattern"]))
        if matcher is None:
            raise LookupError("declared argument matcher is not installed")
        effects = matcher(action.argv)
        if effects is not None:
            return _effects_allowed(mode, effects), effects
    return False, Effects()


def _network_allowed(mode: dict[str, Any], action: Action) -> bool:
    expected = {"protocol": action.protocol, "host": action.host, "purpose": action.purpose}
    exact_action = action == Action.connect(action.protocol, action.host, action.purpose)
    return exact_action and expected in mode["network"]


def _secret_allowed(mode: dict[str, Any], action: Action) -> bool:
    return action == Action.use_secret(action.secret) and action.secret in mode["secrets"]


_Enforcer = Callable[[dict[str, Any], Action], bool | tuple[bool, Effects]]
_ACTION_CONTROLS = {
    "read": "preflight.read",
    "write": "preflight.write",
    "exec": "preflight.exec",
    "network": "preflight.network",
    "secret": "preflight.secrets",
}
_ENFORCERS: Mapping[str, tuple[str, _Enforcer, bool]] = MappingProxyType(
    {
        "read": ("preflight.read", _read_allowed, False),
        "write": ("preflight.write", _write_allowed, False),
        "exec": ("preflight.exec", _exec_allowed, True),
        "network": ("preflight.network", _network_allowed, True),
        "secret": ("preflight.secrets", _secret_allowed, True),
    }
)


def _gate_applies(gate: str, action: Action) -> bool:
    return (
        action.kind
        in {
            "never": set(),
            "before_write": {"write"},
            "before_exec": {"exec"},
            "before_network": {"network"},
            "before_publish": {"exec", "network", "secret"},
        }[gate]
    )


def _effects_need_gate(gate: str, effects: Effects) -> bool:
    return {
        "never": False,
        "before_write": bool(effects.write_paths),
        "before_exec": False,
        "before_network": bool(effects.network),
        "before_publish": bool(effects.network or effects.secrets),
    }[gate]


def _incomplete(problem: tuple[str, str]) -> Preflight:
    return Preflight("INCOMPLETE", *problem)


def preflight(
    capability_id: str,
    mode_id: str,
    action: Action,
) -> Preflight:
    """Execute installed enforcement for one exact requested action without performing it."""

    try:
        manifest = _validated(None)
    except _Problem as problem:
        return _incomplete(problem.result)
    capability = next(
        (entry for entry in manifest["capabilities"] if entry["id"] == capability_id), None
    )
    if capability is None:
        return _incomplete(CAPABILITY_UNDECLARED)
    mode = next((entry for entry in capability["modes"] if entry["id"] == mode_id), None)
    if mode is None:
        return _incomplete(MODE_UNDECLARED)
    if not isinstance(action, Action) or action.kind not in _ACTION_CONTROLS:
        return _incomplete(ACTION_INVALID)
    installed = _ENFORCERS.get(action.kind)
    if installed is None or installed[0] != _ACTION_CONTROLS[action.kind]:
        return _incomplete(ENFORCEMENT_UNAVAILABLE)
    control, enforce, binds_operation = installed
    if control not in mode["enforcement"]:
        return _incomplete(ACTION_UNDECLARED)
    try:
        decision = enforce(mode, action)
    except (KeyError, LookupError, TypeError, ValueError):
        return _incomplete(ENFORCEMENT_UNAVAILABLE)
    effects = Effects()
    if isinstance(decision, tuple):
        allowed, effects = decision
    else:
        allowed = decision
    if not allowed:
        return _incomplete(ACTION_UNDECLARED)
    if _gate_applies(mode["human_gate"], action) or _effects_need_gate(mode["human_gate"], effects):
        return _incomplete(HUMAN_GATE_REQUIRED)
    if not binds_operation:
        return _incomplete(ENFORCEMENT_UNAVAILABLE)
    payload = {
        "capability_id": capability_id,
        "mode_id": mode_id,
        "action": {
            "kind": action.kind,
            "path": action.path,
            "argv": list(action.argv),
            "protocol": action.protocol,
            "host": action.host,
            "purpose": action.purpose,
            "secret": action.secret,
        },
        "effects": {
            "write_paths": list(effects.write_paths),
            "network": [list(destination) for destination in effects.network],
            "secrets": list(effects.secrets),
        },
    }
    authorization = Authorization(
        capability_id,
        mode_id,
        action,
        "sha256:" + sha256(_canonical_json(payload)).hexdigest(),
    )
    return Preflight("READY", authorization=authorization)
