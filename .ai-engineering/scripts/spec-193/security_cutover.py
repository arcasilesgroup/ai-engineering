"""Values-free foundation for the one-shot spec-193 security cutover.

This module deliberately has no CLI entry point, no package registration, and
no host/provider discovery.  It is loaded only by the explicit migration
runner and its synthetic tests.  Callers supply every path; this module never
reads home configuration, credentials, environment values, or process output.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from threading import Lock
from typing import Final, cast

RECEIPT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "credential_alias",
        "provider",
        "cli_version",
        "probe_id",
        "exit_code",
        "timestamp",
        "redacted_field_count",
        "invalidation_evidence_ref",
    }
)
_FORBIDDEN_FIELD_NAMES: Final[frozenset[str]] = frozenset(
    {
        "account",
        "account_id",
        "argv",
        "chain_pointer",
        "endpoint",
        "manifest_reference",
        "operation",
        "raw_output",
        "raw_stderr",
        "raw_stdout",
        "raw_stream",
        "result",
        "secret",
        "secret_derived_hash",
        "token",
        "workspace",
        "workspace_id",
    }
)
_HASH_LIKE: Final[re.Pattern[str]] = re.compile(r"(?:sha256:)?[0-9a-fA-F]{64}\Z")
_SECRET_MARKER: Final[re.Pattern[str]] = re.compile(
    r"(?:canary|secret|api[_-]?key|password)", re.IGNORECASE
)
_SENSITIVE_ASSIGNMENT: Final[re.Pattern[str]] = re.compile(
    r"(?:api[_-]?key|password|secret|token)\s*(?:=|:)\s*\S+", re.IGNORECASE
)


@dataclass(frozen=True)
class PrivateStorePaths:
    """All private files owned by one external spec-193 state root."""

    root: Path
    manifest: Path
    receipts: Path
    runbook: Path
    lock: Path


class PrivateStoreError(ValueError):
    """A path, schema, or privacy invariant failed closed."""


class DiscoveryInputTooLargeError(PrivateStoreError):
    """A declared read-only loader exceeded its fixed discovery byte limit."""


def validate_values_free(value: object) -> None:
    """Reject metadata which could preserve identity, paths, streams, or secrets.

    The check is intentionally conservative.  It operates on synthetic
    structures before durable write, never converts rejected data to text, and
    therefore does not echo a potentially sensitive value.
    """
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise PrivateStoreError("values-free mappings require string keys")
            if key.lower() in _FORBIDDEN_FIELD_NAMES:
                raise PrivateStoreError("values-free mapping contains a forbidden field")
            validate_values_free(nested)
        return
    if isinstance(value, (list, tuple)):
        for nested in value:
            validate_values_free(nested)
        return
    if isinstance(value, str):
        if Path(value).is_absolute():
            raise PrivateStoreError("values-free metadata cannot contain absolute paths")
        if _HASH_LIKE.fullmatch(value) or _SECRET_MARKER.search(value):
            raise PrivateStoreError("values-free metadata resembles a secret or derived hash")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise PrivateStoreError("values-free metadata must be JSON-compatible")


def validate_receipt(receipt: Mapping[str, object]) -> dict[str, object]:
    """Return a copy only when a D-193-08 receipt has the exact field set."""
    actual_fields = set(receipt)
    if actual_fields != RECEIPT_FIELDS:
        raise PrivateStoreError("receipt fields differ from the D-193-08 allowlist")

    result = dict(receipt)
    for name in (
        "credential_alias",
        "provider",
        "cli_version",
        "probe_id",
        "timestamp",
        "invalidation_evidence_ref",
    ):
        if not isinstance(result[name], str) or not result[name]:
            raise PrivateStoreError("receipt text fields must be non-empty strings")
    for name in ("exit_code", "redacted_field_count"):
        if isinstance(result[name], bool) or not isinstance(result[name], int):
            raise PrivateStoreError("receipt numeric fields must be integers")
    if result["redacted_field_count"] < 0:
        raise PrivateStoreError("redacted_field_count must be non-negative")

    validate_values_free(result)
    return result


def normalize_home_path(path: Path, *, home: Path) -> str:
    """Normalize only a supplied home-relative path; redact every external path."""
    try:
        relative = path.resolve(strict=False).relative_to(home.resolve(strict=False))
    except ValueError:
        return "<external-path>"
    return "$HOME" if not relative.parts else f"$HOME/{relative.as_posix()}"


def _no_follow_flag() -> int:
    """Require a no-follow primitive; silent platform fallback is unsafe here."""
    flag = getattr(os, "O_NOFOLLOW", None)
    if not isinstance(flag, int) or flag == 0:
        raise PrivateStoreError("safe no-follow open is unavailable on this platform")
    return flag


def _write_all(descriptor: int, payload: bytes) -> None:
    """Write a complete record even when the kernel accepts a partial write."""
    view = memoryview(payload)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise OSError("private-store write made no progress")
        view = view[written:]


def _exists_without_following(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    return True


def private_store_paths(root: Path) -> PrivateStorePaths:
    """Derive the private bundle paths without creating or inspecting them."""
    return PrivateStorePaths(
        root=root,
        manifest=root / "manifest.json",
        receipts=root / "receipts.ndjson",
        runbook=root / "runbook.md",
        lock=root / ".lock",
    )


def _assert_private(path: Path, expected_mode: int, *, directory: bool) -> None:
    """Fail closed unless ``path`` is owner-only, regular, and non-symlinked."""
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise PrivateStoreError("private store path is missing") from error
    if stat.S_ISLNK(metadata.st_mode):
        raise PrivateStoreError("private store paths cannot be symlinks")
    expected_type = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected_type(metadata.st_mode):
        raise PrivateStoreError("private store path has an unexpected file type")
    if metadata.st_uid != os.getuid():
        raise PrivateStoreError("private store path has an unexpected owner")
    if stat.S_IMODE(metadata.st_mode) != expected_mode:
        raise PrivateStoreError("private store path has an unsafe mode")


def _assert_private_ancestor_chain(root: Path) -> None:
    """Reject user-controlled symlink or writable-parent traversal before writes."""
    if not root.is_absolute() or root.resolve(strict=False) != root:
        raise PrivateStoreError("private store root must be a canonical absolute path")
    current = root
    while True:
        metadata = current.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise PrivateStoreError("private store traversal contains an unsafe component")
        if current == root:
            _assert_private(current, 0o700, directory=True)
        elif metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise PrivateStoreError("private store traversal has a writable ancestor")
        if current.parent == current:
            return
        current = current.parent


def ensure_private_store(root: Path) -> PrivateStorePaths:
    """Create and validate an owner-only external state root and its traversal."""
    if not root.is_absolute() or root.resolve(strict=False) != root:
        raise PrivateStoreError("private store root must be a canonical absolute path")
    old_umask = os.umask(0o077)
    try:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
    finally:
        os.umask(old_umask)
    _assert_private_ancestor_chain(root)
    return private_store_paths(root)


def _open_private_file(path: Path, flags: int) -> tuple[int, bool]:
    """Open a private file without following a pre-existing symlink."""
    existed = _exists_without_following(path)
    if existed:
        _assert_private(path, 0o600, directory=False)
    try:
        descriptor = os.open(path, flags | _no_follow_flag(), 0o600)
    except OSError as error:
        raise PrivateStoreError("private store file could not be opened safely") from error
    if not existed:
        os.fchmod(descriptor, 0o600)
    _assert_private(path, 0o600, directory=False)
    return descriptor, existed


def _fsync_directory(directory: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | _no_follow_flag()
    try:
        descriptor = os.open(directory, flags)
    except OSError as error:
        raise PrivateStoreError("private store directory could not be fsynced safely") from error
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _json_payload(document: Mapping[str, object]) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def _manifest_digest(path: Path) -> str | None:
    if not _exists_without_following(path):
        return None
    return hashlib.sha256(_read_private_bytes(path)).hexdigest()


def _read_private_bytes(path: Path) -> bytes:
    """Read one existing private regular file through a no-follow descriptor."""
    descriptor, existed = _open_private_file(path, os.O_RDONLY)
    if not existed:
        os.close(descriptor)
        raise PrivateStoreError("private store file is missing")
    try:
        with os.fdopen(descriptor, "rb") as handle:
            return handle.read()
    except OSError as error:
        raise PrivateStoreError("private store file could not be read safely") from error


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    """Durably replace an already-validated owner-only private file."""
    _assert_private(path.parent, 0o700, directory=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if _exists_without_following(path):
            _assert_private(path, 0o600, directory=False)
        os.replace(temporary, path)
        _assert_private(path, 0o600, directory=False)
        _fsync_directory(path.parent)
    finally:
        if _exists_without_following(temporary):
            temporary.unlink()


def _atomic_write_json(path: Path, document: Mapping[str, object]) -> None:
    """Durably replace an already-validated private JSON document."""
    _atomic_write_bytes(path, _json_payload(document))


def _ensure_private_file(path: Path, payload: bytes) -> None:
    """Create a private auxiliary file exactly once under the held store lock."""
    _assert_private(path.parent, 0o700, directory=True)
    if _exists_without_following(path):
        _assert_private(path, 0o600, directory=False)
        return
    try:
        descriptor = os.open(
            path,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY | _no_follow_flag(),
            0o600,
        )
    except FileExistsError:
        _assert_private(path, 0o600, directory=False)
        return
    except OSError as error:
        raise PrivateStoreError("private auxiliary file could not be created safely") from error
    try:
        os.fchmod(descriptor, 0o600)
        _write_all(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _assert_private(path, 0o600, directory=False)
    _fsync_directory(path.parent)


def assert_private_bundle(paths: PrivateStorePaths) -> None:
    """Prove every present bundle member has private traversal, mode, owner, and ACLs."""
    _assert_private_ancestor_chain(paths.root)
    validate_private_acl(paths.root)
    for path in (paths.manifest, paths.receipts, paths.runbook, paths.lock):
        if not _exists_without_following(path):
            continue
        _assert_private(path, 0o600, directory=False)
        validate_private_acl(path)


def _append_receipt(receipts_path: Path, receipt: Mapping[str, object]) -> tuple[int, str]:
    """Append and fsync one exact receipt before its manifest index update."""
    serialized = _json_payload(validate_receipt(receipt))
    _assert_private(receipts_path.parent, 0o700, directory=True)
    descriptor, _ = _open_private_file(
        receipts_path, os.O_APPEND | os.O_CREAT | os.O_WRONLY
    )
    try:
        offset = os.lseek(descriptor, 0, os.SEEK_END)
        _write_all(descriptor, serialized)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return offset, hashlib.sha256(serialized).hexdigest()


def _validate_receipt_index(receipt_index: object) -> list[dict[str, object]]:
    """Validate the only permitted manifest-owned receipt reference format."""
    if not isinstance(receipt_index, list):
        raise PrivateStoreError("receipt index must be a list")
    validated_index: list[dict[str, object]] = []
    for entry in receipt_index:
        if not isinstance(entry, Mapping) or set(entry) != {"offset", "sha256"}:
            raise PrivateStoreError("receipt index entries have an invalid schema")
        entry_values = cast(Mapping[str, object], entry)
        offset = entry_values["offset"]
        digest = entry_values["sha256"]
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise PrivateStoreError("receipt index offset is invalid")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise PrivateStoreError("receipt index digest is invalid")
        validated_index.append({"offset": offset, "sha256": digest})
    return validated_index


def _validate_preflight_baseline(document: Mapping[str, object]) -> dict[str, object]:
    """Validate the immutable T0.0 baseline without treating structural hashes as values."""
    expected = {
        "schema",
        "created_at",
        "entries",
        "entry_count",
        "head_commit",
        "notes",
        "repo_token",
    }
    if set(document) != expected:
        raise PrivateStoreError("preflight baseline fields differ from the T0.0 allowlist")
    schema = document["schema"]
    created_at = document["created_at"]
    entries = document["entries"]
    entry_count = document["entry_count"]
    head_commit = document["head_commit"]
    notes = document["notes"]
    repo_token = document["repo_token"]
    if schema != "spec-193-preflight-baseline-v1":
        raise PrivateStoreError("preflight baseline schema is invalid")
    if not isinstance(created_at, str) or not isinstance(repo_token, str):
        raise PrivateStoreError("preflight baseline text fields are invalid")
    if not isinstance(entries, list) or not isinstance(notes, list):
        raise PrivateStoreError("preflight baseline collections are invalid")
    if isinstance(entry_count, bool) or not isinstance(entry_count, int):
        raise PrivateStoreError("preflight baseline entry count is invalid")
    if entry_count != len(entries):
        raise PrivateStoreError("preflight baseline entry count does not match entries")
    if not isinstance(head_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", head_commit):
        raise PrivateStoreError("preflight baseline head commit is invalid")
    validate_values_free(created_at)
    validate_values_free(repo_token)
    _validate_preflight_notes(cast(list[object], notes))
    validated_entries: list[dict[str, object]] = []
    for entry in entries:
        if not isinstance(entry, Mapping) or set(entry) != {
            "kind",
            "index_status",
            "worktree_status",
            "path_fingerprint",
            "size",
            "mtime_ns",
        }:
            raise PrivateStoreError("preflight baseline entry fields are invalid")
        entry_values = cast(Mapping[str, object], entry)
        fingerprint = entry_values["path_fingerprint"]
        if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise PrivateStoreError("preflight baseline path fingerprint is invalid")
        for name in ("kind", "index_status", "worktree_status"):
            value = entry_values[name]
            if not isinstance(value, str):
                raise PrivateStoreError("preflight baseline entry text is invalid")
            validate_values_free(value)
        size = entry_values["size"]
        modified_at = entry_values["mtime_ns"]
        if (size is None) != (modified_at is None):
            raise PrivateStoreError("preflight baseline file metadata must be jointly present")
        for name in ("size", "mtime_ns"):
            value = entry_values[name]
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise PrivateStoreError("preflight baseline entry numeric field is invalid")
        validated_entries.append(
            {
                "kind": entry_values["kind"],
                "index_status": entry_values["index_status"],
                "worktree_status": entry_values["worktree_status"],
                "path_fingerprint": fingerprint,
                "size": entry_values["size"],
                "mtime_ns": entry_values["mtime_ns"],
            }
        )
    return {
        "schema": schema,
        "created_at": created_at,
        "entries": validated_entries,
        "entry_count": entry_count,
        "head_commit": head_commit,
        "notes": list(notes),
        "repo_token": repo_token,
    }


def _validate_preflight_notes(notes: list[object]) -> None:
    """Permit short policy labels while rejecting values in the immutable T0.0 notes."""
    for note in notes:
        if not isinstance(note, str) or not note or len(note) > 256:
            raise PrivateStoreError("preflight baseline note is invalid")
        if Path(note).is_absolute() or "\x00" in note or "\n" in note:
            raise PrivateStoreError("preflight baseline note is unsafe")
        if _SENSITIVE_ASSIGNMENT.search(note):
            raise PrivateStoreError("preflight baseline note resembles a sensitive assignment")


_SURFACE_RECORD_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "surface",
        "scope",
        "loader_kind",
        "path_token",
        "owner_class",
        "mode_class",
        "acl_state",
        "structure_sha256",
        "component",
        "component_version",
        "discovery_state",
        "reachability",
        "proposed_action",
    }
)
_T12_SURFACES: Final[frozenset[str]] = frozenset({"claude", "codex", "opencode", "pi"})
_T12_SCOPES: Final[frozenset[str]] = frozenset(
    {"user", "project", "shared", "generated"}
)
_T12_LOADER_KINDS: Final[frozenset[str]] = frozenset(
    {"settings-json", "config-toml", "mcp-json", "auth-json", "metadata-tree"}
)
_T12_OWNER_CLASSES: Final[frozenset[str]] = frozenset(
    {"current-user", "unexpected-owner", "absent", "unsafe"}
)
_T12_MODE_CLASSES: Final[frozenset[str]] = frozenset(
    {"owner-only", "group-accessible", "other-accessible", "absent", "unsafe"}
)
_T12_ACL_STATES: Final[frozenset[str]] = frozenset(
    {"none-observed", "extended", "deferred", "absent", "unsafe"}
)
_T12_COMPONENTS: Final[frozenset[str]] = frozenset(
    {"mcp-configured", "mcp-not-observed", "unknown"}
)
_T12_DISCOVERY_STATES: Final[frozenset[str]] = frozenset(
    {"parsed", "absent", "unsafe", "unparseable", "oversized"}
)
_T12_REACHABILITY: Final[frozenset[str]] = frozenset(
    {"potential", "not-observed", "unknown", "none"}
)
_T12_ACTIONS: Final[frozenset[str]] = frozenset(
    {"preserve", "preview-disable", "block"}
)
MAX_DISCOVERY_FILE_BYTES: Final[int] = 64 * 1024
MAX_DISCOVERY_TREE_NODES: Final[int] = 128
MAX_DISCOVERY_TREE_DEPTH: Final[int] = 3


@dataclass(frozen=True)
class SurfaceCandidate:
    """One explicit T1.2 loader; roots are supplied by the caller, never inferred."""

    surface: str
    scope: str
    loader_kind: str
    root: str
    relative_path: str
    path_token: str
    parser: str


T12_SURFACE_CANDIDATES: Final[tuple[SurfaceCandidate, ...]] = (
    SurfaceCandidate(
        "claude",
        "user",
        "settings-json",
        "home",
        ".claude/settings.json",
        "$HOME/.claude/settings.json",
        "json",
    ),
    SurfaceCandidate(
        "claude",
        "project",
        "settings-json",
        "repo",
        ".claude/settings.json",
        "$REPO/.claude/settings.json",
        "json",
    ),
    SurfaceCandidate(
        "claude",
        "project",
        "mcp-json",
        "repo",
        ".mcp.json",
        "$REPO/.mcp.json",
        "json",
    ),
    SurfaceCandidate(
        "codex",
        "user",
        "config-toml",
        "home",
        ".codex/config.toml",
        "$HOME/.codex/config.toml",
        "toml",
    ),
    SurfaceCandidate(
        "opencode",
        "user",
        "settings-json",
        "home",
        ".config/opencode/opencode.json",
        "$HOME/.config/opencode/opencode.json",
        "json",
    ),
    SurfaceCandidate(
        "opencode",
        "shared",
        "auth-json",
        "home",
        ".local/share/opencode/auth.json",
        "$HOME/.local/share/opencode/auth.json",
        "json",
    ),
    SurfaceCandidate(
        "pi",
        "user",
        "settings-json",
        "home",
        ".pi/agent/settings.json",
        "$HOME/.pi/agent/settings.json",
        "json",
    ),
    SurfaceCandidate(
        "claude",
        "generated",
        "metadata-tree",
        "home",
        ".claude",
        "$HOME/.claude/**",
        "metadata-tree",
    ),
    SurfaceCandidate(
        "codex",
        "generated",
        "metadata-tree",
        "home",
        ".codex",
        "$HOME/.codex/**",
        "metadata-tree",
    ),
    SurfaceCandidate(
        "opencode",
        "generated",
        "metadata-tree",
        "home",
        ".config/opencode",
        "$HOME/.config/opencode/**",
        "metadata-tree",
    ),
    SurfaceCandidate(
        "pi",
        "generated",
        "metadata-tree",
        "home",
        ".pi",
        "$HOME/.pi/**",
        "metadata-tree",
    ),
)


def _validated_t12_token(
    path_token: str, *, root: str, relative_path: str, metadata_tree: bool
) -> str:
    expected_prefix = "$HOME/" if root == "home" else "$REPO/"
    if root not in {"home", "repo"} or not path_token.startswith(expected_prefix):
        raise PrivateStoreError("surface candidate root token is invalid")
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise PrivateStoreError("surface candidate relative path is invalid")
    expected_token = expected_prefix + relative.as_posix() + ("/**" if metadata_tree else "")
    if path_token != expected_token:
        raise PrivateStoreError("surface candidate path token is not canonical")
    return path_token


def _validate_surface_record(record: Mapping[str, object]) -> dict[str, object]:
    """Validate one values-free loader record before it enters the private manifest."""
    if set(record) != _SURFACE_RECORD_FIELDS:
        raise PrivateStoreError("surface record fields differ from the T1.2 allowlist")
    result = dict(record)
    enumerations: tuple[tuple[str, frozenset[str]], ...] = (
        ("surface", _T12_SURFACES),
        ("scope", _T12_SCOPES),
        ("loader_kind", _T12_LOADER_KINDS),
        ("owner_class", _T12_OWNER_CLASSES),
        ("mode_class", _T12_MODE_CLASSES),
        ("acl_state", _T12_ACL_STATES),
        ("component", _T12_COMPONENTS),
        ("discovery_state", _T12_DISCOVERY_STATES),
        ("reachability", _T12_REACHABILITY),
        ("proposed_action", _T12_ACTIONS),
    )
    for name, allowed in enumerations:
        value = result[name]
        if not isinstance(value, str) or value not in allowed:
            raise PrivateStoreError("surface record enumeration is invalid")
    path_token = result["path_token"]
    if not isinstance(path_token, str) or not re.fullmatch(
        r"\$(?:HOME|REPO)/(?:[A-Za-z0-9._-]+/)*[A-Za-z0-9._-]+(?:/\*\*)?",
        path_token,
    ):
        raise PrivateStoreError("surface record path token is invalid")
    version = result["component_version"]
    if not isinstance(version, str) or version not in {"not-declared", "redacted"}:
        raise PrivateStoreError("surface record component version is invalid")
    digest = result["structure_sha256"]
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise PrivateStoreError("surface record structure digest is invalid")
    return result


def _validate_surface_records(records: object) -> list[dict[str, object]]:
    if not isinstance(records, list):
        raise PrivateStoreError("surface records must be a list")
    validated: list[dict[str, object]] = []
    identifiers: set[tuple[str, str, str, str]] = set()
    for record in records:
        if not isinstance(record, Mapping):
            raise PrivateStoreError("surface record must be a mapping")
        copied = _validate_surface_record(cast(Mapping[str, object], record))
        identifier = cast(
            tuple[str, str, str, str],
            tuple(
                cast(str, copied[name])
                for name in ("surface", "scope", "loader_kind", "path_token")
            ),
        )
        if identifier in identifiers:
            raise PrivateStoreError("surface records must not duplicate a loader")
        identifiers.add(identifier)
        validated.append(copied)
    return validated


def _safe_candidate_lstat(
    root: Path, relative_path: str
) -> tuple[Path | None, os.stat_result | None, str]:
    """Traverse an explicit root without following symlinks or parent escapes."""
    relative = Path(relative_path)
    if not root.is_absolute() or relative.is_absolute() or ".." in relative.parts:
        raise PrivateStoreError("surface discovery path is not rooted safely")
    try:
        root_metadata = root.lstat()
    except FileNotFoundError:
        return None, None, "absent"
    if stat.S_ISLNK(root_metadata.st_mode) or not stat.S_ISDIR(root_metadata.st_mode):
        return None, None, "unsafe"
    current = root
    for index, part in enumerate(relative.parts):
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            return None, None, "absent"
        if stat.S_ISLNK(metadata.st_mode):
            return None, None, "unsafe"
        if index < len(relative.parts) - 1 and not stat.S_ISDIR(metadata.st_mode):
            return None, None, "unsafe"
    return current, metadata, "present"


def _mode_class(metadata: os.stat_result) -> str:
    mode = stat.S_IMODE(metadata.st_mode)
    if mode & 0o007:
        return "other-accessible"
    if mode & 0o070:
        return "group-accessible"
    return "owner-only"


def _surface_acl_state(path: Path) -> str:
    """Collect a best-effort ACL signal without spawning a host command during discovery."""
    listxattr = getattr(os, "listxattr", None)
    if not callable(listxattr):
        return "deferred"
    try:
        attributes = listxattr(path, follow_symlinks=False)
    except (OSError, TypeError):
        return "deferred"
    unsafe = {
        "com.apple.acl.text",
        "system.posix_acl_access",
        "system.posix_acl_default",
    }
    return "extended" if any(attribute in unsafe for attribute in attributes) else "none-observed"


def _read_bounded_surface_file(path: Path) -> bytes:
    """Read one regular loader file through a no-follow descriptor and a hard cap."""
    try:
        descriptor = os.open(path, os.O_RDONLY | _no_follow_flag())
    except OSError as error:
        raise PrivateStoreError("surface loader could not be opened safely") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise PrivateStoreError("surface loader is not a regular file")
        payload = os.read(descriptor, MAX_DISCOVERY_FILE_BYTES + 1)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    if any(getattr(metadata, field) != getattr(after, field) for field in stable_fields):
        raise PrivateStoreError("surface loader changed during bounded read")
    if len(payload) > MAX_DISCOVERY_FILE_BYTES:
        raise DiscoveryInputTooLargeError("surface loader exceeds the discovery output cap")
    return payload


def _redacted_shape(value: object) -> object:
    """Return a deterministic schema-only representation without preserving values."""
    if isinstance(value, Mapping):
        return {
            "object": {
                str(key): _redacted_shape(nested)
                for key, nested in sorted(value.items(), key=lambda item: str(item[0]))
            }
        }
    if isinstance(value, list):
        return {"array": [_redacted_shape(nested) for nested in value]}
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    return f"unsupported:{type(value).__name__}"


def _contains_mcp_shape(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key).lower() in {"mcp", "mcpservers", "mcp_servers"}
            or _contains_mcp_shape(nested)
            for key, nested in value.items()
        )
    if isinstance(value, list):
        return any(_contains_mcp_shape(nested) for nested in value)
    return False


def _t12_structure_digest(value: object) -> str:
    shape = {"shape": _redacted_shape(value)}
    return hashlib.sha256(_json_payload(shape)).hexdigest()


def _metadata_name_class(name: str) -> str:
    lowered = name.lower()
    if "mcp" in lowered:
        return "mcp-named"
    if "plugin" in lowered:
        return "plugin-named"
    if "hook" in lowered:
        return "hook-named"
    return "other"


def _bounded_metadata_tree_shape(root: Path) -> tuple[dict[str, object], bool, bool]:
    """Summarize an explicit generated tree without persisting any file names or contents."""
    node_count = 0
    mcp_named = False
    truncated = False

    def visit(directory: Path, depth: int) -> list[dict[str, object]]:
        nonlocal node_count, mcp_named, truncated
        if depth >= MAX_DISCOVERY_TREE_DEPTH or node_count >= MAX_DISCOVERY_TREE_NODES:
            truncated = True
            return []
        try:
            with os.scandir(directory) as entries:
                ordered = sorted(entries, key=lambda entry: entry.name)
        except OSError as error:
            raise PrivateStoreError("generated metadata tree could not be inspected") from error
        shape: list[dict[str, object]] = []
        for entry in ordered:
            if node_count >= MAX_DISCOVERY_TREE_NODES:
                truncated = True
                break
            node_count += 1
            try:
                metadata = entry.stat(follow_symlinks=False)
            except OSError as error:
                raise PrivateStoreError(
                    "generated metadata entry could not be inspected"
                ) from error
            name_class = _metadata_name_class(entry.name)
            mcp_named = mcp_named or name_class == "mcp-named"
            if stat.S_ISLNK(metadata.st_mode):
                kind = "symlink"
            elif stat.S_ISDIR(metadata.st_mode):
                kind = "directory"
            elif stat.S_ISREG(metadata.st_mode):
                kind = "file"
            else:
                kind = "other"
            node: dict[str, object] = {"kind": kind, "name_class": name_class}
            if kind == "directory":
                node["children"] = visit(Path(entry.path), depth + 1)
            shape.append(node)
        return shape

    return {"entries": visit(root, 0)}, mcp_named, truncated


def _generated_tree_record(
    candidate: SurfaceCandidate, path: Path, metadata: os.stat_result, path_token: str
) -> dict[str, object]:
    """Return one bounded values-free record for a generated host subtree."""
    try:
        shape, mcp_named, truncated = _bounded_metadata_tree_shape(path)
    except PrivateStoreError:
        shape, mcp_named, truncated = {"state": "unparseable"}, False, False
    if shape == {"state": "unparseable"} or truncated or mcp_named:
        component = "unknown"
        reachability = "unknown"
        action = "block"
    else:
        component = "mcp-not-observed"
        reachability = "none"
        action = "preserve"
    return {
        "surface": candidate.surface,
        "scope": candidate.scope,
        "loader_kind": candidate.loader_kind,
        "path_token": path_token,
        "owner_class": "current-user" if metadata.st_uid == os.getuid() else "unexpected-owner",
        "mode_class": _mode_class(metadata),
        "acl_state": _surface_acl_state(path),
        "structure_sha256": _t12_structure_digest(shape),
        "component": component,
        "component_version": "not-declared",
        "discovery_state": "unparseable" if shape == {"state": "unparseable"} else "parsed",
        "reachability": reachability,
        "proposed_action": action,
    }


def _surface_record_for_candidate(
    candidate: SurfaceCandidate, *, home_root: Path, repo_root: Path
) -> dict[str, object]:
    """Inspect one declared loader and emit values-free metadata only."""
    path_token = _validated_t12_token(
        candidate.path_token,
        root=candidate.root,
        relative_path=candidate.relative_path,
        metadata_tree=candidate.parser == "metadata-tree",
    )
    if candidate.surface not in _T12_SURFACES or candidate.scope not in _T12_SCOPES:
        raise PrivateStoreError("surface candidate identity is invalid")
    if candidate.loader_kind not in _T12_LOADER_KINDS or candidate.parser not in {
        "json",
        "toml",
        "metadata-tree",
    }:
        raise PrivateStoreError("surface candidate loader definition is invalid")
    root = home_root if candidate.root == "home" else repo_root
    path, metadata, status = _safe_candidate_lstat(root, candidate.relative_path)
    absent = status == "absent"
    if absent or status == "unsafe" or path is None or metadata is None:
        state = "absent" if absent else "unsafe"
        return {
            "surface": candidate.surface,
            "scope": candidate.scope,
            "loader_kind": candidate.loader_kind,
            "path_token": path_token,
            "owner_class": "absent" if absent else "unsafe",
            "mode_class": "absent" if absent else "unsafe",
            "acl_state": "absent" if absent else "unsafe",
            "structure_sha256": _t12_structure_digest({"state": state}),
            "component": "unknown" if status == "unsafe" else "mcp-not-observed",
            "component_version": "not-declared",
            "discovery_state": state,
            "reachability": "unknown" if status == "unsafe" else "none",
            "proposed_action": "block" if status == "unsafe" else "preserve",
        }
    if candidate.parser == "metadata-tree":
        if not stat.S_ISDIR(metadata.st_mode):
            return {
                "surface": candidate.surface,
                "scope": candidate.scope,
                "loader_kind": candidate.loader_kind,
                "path_token": path_token,
                "owner_class": (
                    "current-user" if metadata.st_uid == os.getuid() else "unexpected-owner"
                ),
                "mode_class": _mode_class(metadata),
                "acl_state": _surface_acl_state(path),
                "structure_sha256": _t12_structure_digest({"state": "unsafe"}),
                "component": "unknown",
                "component_version": "not-declared",
                "discovery_state": "unsafe",
                "reachability": "unknown",
                "proposed_action": "block",
            }
        return _generated_tree_record(candidate, path, metadata, path_token)
    if not stat.S_ISREG(metadata.st_mode):
        return {
            "surface": candidate.surface,
            "scope": candidate.scope,
            "loader_kind": candidate.loader_kind,
            "path_token": path_token,
            "owner_class": "current-user" if metadata.st_uid == os.getuid() else "unexpected-owner",
            "mode_class": _mode_class(metadata),
            "acl_state": _surface_acl_state(path),
            "structure_sha256": _t12_structure_digest({"state": "unsafe"}),
            "component": "unknown",
            "component_version": "not-declared",
            "discovery_state": "unsafe",
            "reachability": "unknown",
            "proposed_action": "block",
        }
    try:
        payload = _read_bounded_surface_file(path)
        decoded = payload.decode("utf-8")
        parsed: object = (
            json.loads(decoded) if candidate.parser == "json" else tomllib.loads(decoded)
        )
        if not isinstance(parsed, Mapping):
            raise PrivateStoreError("surface loader root is not a mapping")
    except DiscoveryInputTooLargeError:
        state = "oversized"
    except (PrivateStoreError, UnicodeDecodeError, json.JSONDecodeError, tomllib.TOMLDecodeError):
        state = "unparseable"
    else:
        has_mcp = _contains_mcp_shape(parsed)
        return {
            "surface": candidate.surface,
            "scope": candidate.scope,
            "loader_kind": candidate.loader_kind,
            "path_token": path_token,
            "owner_class": "current-user" if metadata.st_uid == os.getuid() else "unexpected-owner",
            "mode_class": _mode_class(metadata),
            "acl_state": _surface_acl_state(path),
            "structure_sha256": _t12_structure_digest(parsed),
            "component": "mcp-configured" if has_mcp else "mcp-not-observed",
            "component_version": "redacted" if has_mcp else "not-declared",
            "discovery_state": "parsed",
            "reachability": "potential" if has_mcp else "not-observed",
            "proposed_action": "preview-disable" if has_mcp else "preserve",
        }
    return {
        "surface": candidate.surface,
        "scope": candidate.scope,
        "loader_kind": candidate.loader_kind,
        "path_token": path_token,
        "owner_class": "current-user" if metadata.st_uid == os.getuid() else "unexpected-owner",
        "mode_class": _mode_class(metadata),
        "acl_state": _surface_acl_state(path),
        "structure_sha256": _t12_structure_digest({"state": state}),
        "component": "unknown",
        "component_version": "not-declared",
        "discovery_state": state,
        "reachability": "unknown",
        "proposed_action": "block",
    }


def discover_surface_records(
    candidates: Sequence[SurfaceCandidate], *, home_root: Path, repo_root: Path
) -> list[dict[str, object]]:
    """Read explicit T1.2 candidates only; never infer home, environment, or commands."""
    records = [
        _surface_record_for_candidate(candidate, home_root=home_root, repo_root=repo_root)
        for candidate in candidates
    ]
    return _validate_surface_records(records)


def _canonical_baseline_digest(baseline: Mapping[str, object]) -> str:
    """Bind the preserved baseline structure without replacing its original raw digest."""
    validated = _validate_preflight_baseline(baseline)
    return hashlib.sha256(_json_payload(validated)).hexdigest()


def validate_manifest(document: Mapping[str, object]) -> dict[str, object]:
    """Validate the T0.0 or canonical upgraded values-free manifest schema."""
    schema = document.get("schema")
    if schema in {"spec-193-manifest-v1", "spec-193-manifest-v2"}:
        expected = {
            "schema",
            "baseline",
            "baseline_sha256",
            "surfaces",
            "credentials",
            "deletions",
            "cli_ownership",
            "checkpoints",
            "receipt_index",
            "runner_sha256",
        }
        if schema == "spec-193-manifest-v2":
            expected |= {"baseline_canonical_sha256", "runner_version"}
        if set(document) != expected:
            raise PrivateStoreError("canonical manifest fields differ from the schema allowlist")
        baseline = document["baseline"]
        baseline_digest = document["baseline_sha256"]
        runner_digest = document["runner_sha256"]
        if not isinstance(baseline, Mapping):
            raise PrivateStoreError("canonical manifest baseline is invalid")
        if not isinstance(baseline_digest, str) or not re.fullmatch(
            r"[0-9a-f]{64}", baseline_digest
        ):
            raise PrivateStoreError("canonical manifest baseline digest is invalid")
        if not isinstance(runner_digest, str) or not re.fullmatch(
            r"[0-9a-f]{64}", runner_digest
        ):
            raise PrivateStoreError("canonical manifest runner digest is invalid")
        validated_baseline = _validate_preflight_baseline(cast(Mapping[str, object], baseline))
        if schema == "spec-193-manifest-v2":
            canonical_digest = document["baseline_canonical_sha256"]
            runner_version = document["runner_version"]
            if not isinstance(canonical_digest, str) or not re.fullmatch(
                r"[0-9a-f]{64}", canonical_digest
            ):
                raise PrivateStoreError("canonical baseline digest is invalid")
            if canonical_digest != _canonical_baseline_digest(validated_baseline):
                raise PrivateStoreError("canonical baseline contents no longer match its digest")
            if not isinstance(runner_version, str) or not re.fullmatch(
                r"spec-193-t1\.\d+", runner_version
            ):
                raise PrivateStoreError("canonical manifest runner version is invalid")
        else:
            canonical_digest = None
            runner_version = None
        if any(
            document[name] != []
            for name in ("credentials", "deletions", "cli_ownership")
        ):
            raise PrivateStoreError("canonical manifest non-surface discovery rows must be empty")
        if document["checkpoints"] != {}:
            raise PrivateStoreError(
                "canonical manifest checkpoints must be empty before containment"
            )
        result: dict[str, object] = {
            "schema": schema,
            "baseline": validated_baseline,
            "baseline_sha256": baseline_digest,
            "surfaces": []
            if schema == "spec-193-manifest-v1"
            else _validate_surface_records(document["surfaces"]),
            "credentials": [],
            "deletions": [],
            "cli_ownership": [],
            "checkpoints": {},
            "receipt_index": _validate_receipt_index(document["receipt_index"]),
            "runner_sha256": runner_digest,
        }
        if schema == "spec-193-manifest-v1":
            if document["surfaces"] != []:
                raise PrivateStoreError("T1.1 manifest surface rows must be empty")
        else:
            result["baseline_canonical_sha256"] = canonical_digest
            result["runner_version"] = runner_version
        return result

    expected = {"schema", "records", "receipt_index"}
    if set(document) != expected:
        raise PrivateStoreError("manifest fields differ from the pre-discovery allowlist")
    records = document["records"]
    receipt_index = document["receipt_index"]
    if not isinstance(schema, str) or not schema:
        raise PrivateStoreError("manifest schema must be a non-empty string")
    if not isinstance(records, list) or not isinstance(receipt_index, list):
        raise PrivateStoreError("manifest collections must be lists")
    validate_values_free(schema)
    validate_values_free(records)
    return {
        "schema": schema,
        "records": list(records),
        "receipt_index": _validate_receipt_index(receipt_index),
    }


@dataclass(frozen=True)
class ReceiptCommit:
    """The manifest result of a receipt-first, lock-held durable transition."""

    manifest: dict[str, object]
    manifest_digest: str
    receipt_sha256: str


class PrivateStoreSession:
    """A non-forgeable-in-practice writer capability, valid only while locked."""

    def __init__(self, paths: PrivateStorePaths) -> None:
        self.paths = paths
        self._active = True

    def _require_active(self) -> None:
        if not self._active:
            raise PrivateStoreError("private store session is no longer active")

    def close(self) -> None:
        self._active = False

    def write_manifest(
        self, document: Mapping[str, object], *, expected_digest: str | None
    ) -> str:
        """CAS-replace a validated manifest under the session's held file lock."""
        self._require_active()
        manifest = validate_manifest(document)
        actual_digest = _manifest_digest(self.paths.manifest)
        if actual_digest != expected_digest:
            raise PrivateStoreError("manifest changed before compare-and-swap")
        _atomic_write_json(self.paths.manifest, manifest)
        new_digest = _manifest_digest(self.paths.manifest)
        if new_digest is None:
            raise PrivateStoreError("manifest write did not persist")
        assert_private_bundle(self.paths)
        return new_digest

    def ensure_auxiliary_file(self, path: Path, payload: bytes) -> None:
        """Create only the fixed values-free bundle scaffolding under the held lock."""
        self._require_active()
        approved_payloads = {
            self.paths.receipts: b"",
            self.paths.runbook: b"# Spec-193 migration runbook\n\nValues-free transition record.\n",
        }
        if path not in approved_payloads or payload != approved_payloads[path]:
            raise PrivateStoreError(
                "private auxiliary file is not an approved values-free scaffold"
            )
        _ensure_private_file(path, payload)
        assert_private_bundle(self.paths)

    def append_receipt_and_index(
        self, receipt: Mapping[str, object], *, expected_manifest_digest: str
    ) -> ReceiptCommit:
        """Commit receipt fsync → exact offset/hash → manifest CAS in that order."""
        self._require_active()
        actual_digest = _manifest_digest(self.paths.manifest)
        if actual_digest != expected_manifest_digest:
            raise PrivateStoreError("manifest changed before receipt transition")
        try:
            existing = json.loads(self.paths.manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise PrivateStoreError("existing manifest cannot be read safely") from error
        if not isinstance(existing, Mapping):
            raise PrivateStoreError("existing manifest is not a mapping")
        manifest = validate_manifest(existing)
        offset, receipt_sha256 = _append_receipt(self.paths.receipts, receipt)
        receipt_index = cast(list[dict[str, object]], manifest["receipt_index"])
        manifest["receipt_index"] = [
            *receipt_index,
            {"offset": offset, "sha256": receipt_sha256},
        ]
        manifest_digest = self.write_manifest(
            manifest, expected_digest=expected_manifest_digest
        )
        assert_private_bundle(self.paths)
        return ReceiptCommit(
            manifest=manifest,
            manifest_digest=manifest_digest,
            receipt_sha256=receipt_sha256,
        )


@contextmanager
def private_store_session(root: Path) -> Iterator[PrivateStoreSession]:
    """Yield the sole writer capability while the owner-only lock is held."""
    paths = ensure_private_store(root)
    assert_private_bundle(paths)
    descriptor, _ = _open_private_file(paths.lock, os.O_CREAT | os.O_RDWR)
    session = PrivateStoreSession(paths)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        assert_private_bundle(paths)
        yield session
    finally:
        session.close()
        try:
            assert_private_bundle(paths)
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _runner_digest(runner_path: Path) -> str:
    """Hash a stable, non-symlinked runner after checking its writable ancestry."""
    try:
        canonical_path = runner_path.resolve(strict=True)
    except OSError as error:
        raise PrivateStoreError("runner path could not be resolved safely") from error
    if not runner_path.is_absolute() or canonical_path != runner_path:
        raise PrivateStoreError("runner path must be a canonical absolute path")
    metadata = runner_path.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise PrivateStoreError("runner path must be a regular non-symlinked file")
    if metadata.st_uid != os.getuid():
        raise PrivateStoreError("runner path has an unexpected owner")
    if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise PrivateStoreError("runner path is writable by group or other")
    current = runner_path.parent
    while True:
        ancestor = current.lstat()
        if stat.S_ISLNK(ancestor.st_mode) or not stat.S_ISDIR(ancestor.st_mode):
            raise PrivateStoreError("runner traversal contains an unsafe component")
        if ancestor.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise PrivateStoreError("runner traversal has a writable ancestor")
        if current.parent == current:
            break
        current = current.parent
    try:
        validate_private_acl(runner_path)
        descriptor = os.open(runner_path, os.O_RDONLY | _no_follow_flag())
    except OSError as error:
        raise PrivateStoreError("runner file could not be read safely") from error
    try:
        before = os.fstat(descriptor)
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, 64 * 1024):
            digest.update(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    if any(getattr(before, field) != getattr(after, field) for field in stable_fields):
        raise PrivateStoreError("runner file changed during hashing")
    return digest.hexdigest()


def upgrade_external_bundle(
    root: Path, *, expected_baseline_sha256: str, runner_path: Path
) -> str:
    """Atomically promote the immutable T0.0 bundle to the canonical T1.1 shape.

    The caller supplies a previously recorded baseline digest.  No baseline is
    ever recaptured: a mismatch stops the migration before any durable write.
    """
    if not re.fullmatch(r"[0-9a-f]{64}", expected_baseline_sha256):
        raise PrivateStoreError("expected preflight baseline digest is invalid")
    runner_sha256 = _runner_digest(runner_path)
    with private_store_session(root) as session:
        paths = session.paths
        raw_manifest = _read_private_bytes(paths.manifest)
        manifest_digest = hashlib.sha256(raw_manifest).hexdigest()
        try:
            loaded = json.loads(raw_manifest)
        except json.JSONDecodeError as error:
            raise PrivateStoreError("private bundle manifest is not valid JSON") from error
        if not isinstance(loaded, Mapping):
            raise PrivateStoreError("private bundle manifest is not a mapping")

        schema = loaded.get("schema")
        if schema == "spec-193-preflight-baseline-v1":
            if manifest_digest != expected_baseline_sha256:
                raise PrivateStoreError("preflight baseline was replaced or is stale")
            baseline = _validate_preflight_baseline(cast(Mapping[str, object], loaded))
            upgraded: dict[str, object] = {
                "schema": "spec-193-manifest-v1",
                "baseline": baseline,
                "baseline_sha256": expected_baseline_sha256,
                "surfaces": [],
                "credentials": [],
                "deletions": [],
                "cli_ownership": [],
                "checkpoints": {},
                "receipt_index": [],
                "runner_sha256": runner_sha256,
            }
            session.ensure_auxiliary_file(paths.receipts, b"")
            session.ensure_auxiliary_file(
                paths.runbook,
                b"# Spec-193 migration runbook\n\nValues-free transition record.\n",
            )
            return session.write_manifest(upgraded, expected_digest=manifest_digest)

        manifest = validate_manifest(cast(Mapping[str, object], loaded))
        if manifest["schema"] != "spec-193-manifest-v1":
            raise PrivateStoreError("private bundle schema is not eligible for T1.1")
        if manifest["baseline_sha256"] != expected_baseline_sha256:
            raise PrivateStoreError("preflight baseline digest does not match the approved record")
        if manifest["runner_sha256"] != runner_sha256:
            raise PrivateStoreError("runner changed after the approved bundle upgrade")
        session.ensure_auxiliary_file(paths.receipts, b"")
        session.ensure_auxiliary_file(
            paths.runbook,
            b"# Spec-193 migration runbook\n\nValues-free transition record.\n",
        )
        return manifest_digest


def _load_private_manifest(paths: PrivateStorePaths) -> tuple[dict[str, object], str]:
    raw_manifest = _read_private_bytes(paths.manifest)
    digest = hashlib.sha256(raw_manifest).hexdigest()
    try:
        loaded = json.loads(raw_manifest)
    except json.JSONDecodeError as error:
        raise PrivateStoreError("private bundle manifest is not valid JSON") from error
    if not isinstance(loaded, Mapping):
        raise PrivateStoreError("private bundle manifest is not a mapping")
    return validate_manifest(cast(Mapping[str, object], loaded)), digest


def prepare_surface_discovery_bundle(
    root: Path,
    *,
    expected_manifest_sha256: str,
    expected_previous_runner_sha256: str,
    expected_current_runner_sha256: str,
    runner_path: Path,
    runner_version: str,
) -> str:
    """Atomically authorize T1.2 after an explicit, values-free runner identity update."""
    for digest in (
        expected_manifest_sha256,
        expected_previous_runner_sha256,
        expected_current_runner_sha256,
    ):
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise PrivateStoreError("surface discovery digest input is invalid")
    if not re.fullmatch(r"spec-193-t1\.\d+", runner_version):
        raise PrivateStoreError("surface discovery runner version is invalid")
    actual_runner_sha256 = _runner_digest(runner_path)
    if actual_runner_sha256 != expected_current_runner_sha256:
        raise PrivateStoreError("current runner does not match the explicitly approved identity")
    with private_store_session(root) as session:
        manifest, actual_digest = _load_private_manifest(session.paths)
        if actual_digest != expected_manifest_sha256:
            raise PrivateStoreError("private bundle changed before surface discovery preparation")
        if manifest["schema"] == "spec-193-manifest-v2":
            if manifest["runner_sha256"] != expected_previous_runner_sha256:
                raise PrivateStoreError(
                    "previous runner identity does not match the v2 bundle"
                )
            if (
                manifest["runner_sha256"] == actual_runner_sha256
                and manifest["runner_version"] == runner_version
            ):
                return actual_digest
            updated = dict(manifest)
            updated["runner_sha256"] = actual_runner_sha256
            updated["runner_version"] = runner_version
            return session.write_manifest(updated, expected_digest=actual_digest)
        if manifest["schema"] != "spec-193-manifest-v1":
            raise PrivateStoreError("private bundle schema is not eligible for surface discovery")
        if manifest["runner_sha256"] != expected_previous_runner_sha256:
            raise PrivateStoreError("previous runner identity does not match the bundle")
        upgraded = dict(manifest)
        upgraded["schema"] = "spec-193-manifest-v2"
        upgraded["baseline_canonical_sha256"] = _canonical_baseline_digest(
            cast(Mapping[str, object], manifest["baseline"])
        )
        upgraded["runner_sha256"] = actual_runner_sha256
        upgraded["runner_version"] = runner_version
        return session.write_manifest(upgraded, expected_digest=actual_digest)


def verify_surface_discovery_bundle(
    root: Path, *, runner_path: Path, runner_version: str
) -> str:
    """Authorize one host-discovery pass only when bundle ACLs and runner identity match."""
    actual_runner_sha256 = _runner_digest(runner_path)
    with private_store_session(root) as session:
        manifest, digest = _load_private_manifest(session.paths)
        if (
            manifest["schema"] != "spec-193-manifest-v2"
            or manifest["runner_sha256"] != actual_runner_sha256
            or manifest["runner_version"] != runner_version
        ):
            raise PrivateStoreError("host discovery is not authorized by the private bundle")
        assert_private_bundle(session.paths)
        return digest


def _surface_identifier(record: Mapping[str, object]) -> tuple[str, str, str, str]:
    return cast(
        tuple[str, str, str, str],
        tuple(
            cast(str, record[name])
            for name in ("surface", "scope", "loader_kind", "path_token")
        ),
    )


def merge_surface_records(
    root: Path,
    records: Sequence[Mapping[str, object]],
    *,
    expected_manifest_sha256: str,
    runner_path: Path,
    runner_version: str,
) -> str:
    """CAS-merge stable T1.2 loader rows; conflicting rediscovery fails closed."""
    if not re.fullmatch(r"[0-9a-f]{64}", expected_manifest_sha256):
        raise PrivateStoreError("expected surface manifest digest is invalid")
    validated_records = _validate_surface_records(list(records))
    actual_runner_sha256 = _runner_digest(runner_path)
    with private_store_session(root) as session:
        manifest, actual_digest = _load_private_manifest(session.paths)
        if actual_digest != expected_manifest_sha256:
            raise PrivateStoreError("private bundle changed before surface record merge")
        if (
            manifest["schema"] != "spec-193-manifest-v2"
            or manifest["runner_sha256"] != actual_runner_sha256
            or manifest["runner_version"] != runner_version
        ):
            raise PrivateStoreError("surface record merge lacks verified runner authorization")
        existing = _validate_surface_records(manifest["surfaces"])
        by_identifier = {_surface_identifier(record): record for record in existing}
        for record in validated_records:
            identifier = _surface_identifier(record)
            previous = by_identifier.get(identifier)
            if previous is not None and previous != record:
                raise PrivateStoreError("surface rediscovery changed an existing record")
            by_identifier[identifier] = record
        merged = [by_identifier[identifier] for identifier in sorted(by_identifier)]
        if merged == existing:
            return actual_digest
        updated = dict(manifest)
        updated["surfaces"] = merged
        return session.write_manifest(updated, expected_digest=actual_digest)


class CredentialState(StrEnum):
    """The only durable states allowed for an audited credential lane."""

    DISCOVERED = "DISCOVERED"
    SOURCE_CONTAINED = "SOURCE_CONTAINED"
    TARGET_READY = "TARGET_READY"
    NEW_AUTH_OK = "NEW_AUTH_OK"
    CONFIG_CUTOVER = "CONFIG_CUTOVER"
    OLD_INVALID = "OLD_INVALID"
    POSTCHECK = "POSTCHECK"
    BLOCKED = "BLOCKED"


class CredentialDisposition(StrEnum):
    """Approved credential lifecycle categories; no implicit retention exists."""

    REPLACE_REVOKE = "replace+revoke"
    RELOGIN_INVALIDATE = "re-login+invalidate"
    REVOKE_DELETE = "revoke+delete"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class CredentialRow:
    """Values-free state for one provider lane; secret material never belongs here."""

    credential_alias: str
    provider: str
    state: CredentialState
    disposition: CredentialDisposition
    future_consumer: str | None
    config_hash: str


@dataclass(frozen=True)
class QuarantineTransfer:
    """Recoverable source-to-private-store transfer state without the source value."""

    source_present: bool
    pending_item_present: bool
    active_item_present: bool = False


class OneShotWitness:
    """Best-effort zeroizing witness buffer that permits exactly one consumption."""

    def __init__(self, value: bytes) -> None:
        self._buffer = bytearray(value)
        self._consumed = False

    def consume(self) -> bytes:
        """Return once, then overwrite the only retained mutable source buffer."""
        if self._consumed:
            raise PrivateStoreError("old witness has already been released")
        self._consumed = True
        result = bytes(self._buffer)
        self._buffer[:] = b"\x00" * len(self._buffer)
        return result


_LEGAL_SUCCESSORS: Final[dict[CredentialState, frozenset[CredentialState]]] = {
    CredentialState.DISCOVERED: frozenset({CredentialState.SOURCE_CONTAINED}),
    CredentialState.SOURCE_CONTAINED: frozenset({CredentialState.TARGET_READY}),
    CredentialState.TARGET_READY: frozenset({CredentialState.NEW_AUTH_OK}),
    CredentialState.NEW_AUTH_OK: frozenset({CredentialState.CONFIG_CUTOVER}),
    CredentialState.CONFIG_CUTOVER: frozenset({CredentialState.OLD_INVALID}),
    CredentialState.OLD_INVALID: frozenset({CredentialState.POSTCHECK}),
    CredentialState.POSTCHECK: frozenset(),
    CredentialState.BLOCKED: frozenset(),
}
_CHECKPOINT_TARGETS: Final[frozenset[CredentialState]] = frozenset(
    {CredentialState.TARGET_READY, CredentialState.OLD_INVALID}
)
_PROVIDER_MUTATION_GUARD = Lock()


def _legal_successors(row: CredentialRow) -> frozenset[CredentialState]:
    """Permit the sole no-consumer disposal shortcut, otherwise use the closed FSM."""
    if (
        row.state is CredentialState.SOURCE_CONTAINED
        and row.disposition is CredentialDisposition.REVOKE_DELETE
        and row.future_consumer is None
    ):
        return frozenset({CredentialState.OLD_INVALID})
    return _LEGAL_SUCCESSORS[row.state]


def advance_credential(
    row: CredentialRow,
    target: CredentialState,
    *,
    observed_config_hash: str,
    checkpoint_id: str | None,
) -> CredentialRow:
    """Advance one credential state only when every fail-stop precondition holds."""
    if row.state is CredentialState.BLOCKED or row.disposition is CredentialDisposition.BLOCKED:
        raise PrivateStoreError("blocked credentials cannot advance")
    if observed_config_hash != row.config_hash:
        raise PrivateStoreError("credential configuration changed since discovery")
    if target is row.state:
        return row
    if target not in _legal_successors(row):
        raise PrivateStoreError("credential transition is not legal from its current state")
    if target in _CHECKPOINT_TARGETS and not checkpoint_id:
        raise PrivateStoreError("irreversible credential transition requires a checkpoint")
    return replace(row, state=target)


@contextmanager
def provider_mutation_lock(provider: str) -> Iterator[None]:
    """Refuse concurrent provider mutations in this process.

    Real provider actions must also run inside ``private_store_session``;
    its owner-only file lock provides the cross-process part of the invariant.
    """
    if not provider or not _PROVIDER_MUTATION_GUARD.acquire(blocking=False):
        raise PrivateStoreError("another provider mutation is already active")
    try:
        yield
    finally:
        _PROVIDER_MUTATION_GUARD.release()


def select_next_credential(rows: list[CredentialRow]) -> CredentialRow | None:
    """Select a lane only when no previously failed lane requires human action."""
    if any(
        row.state is CredentialState.BLOCKED
        or row.disposition is CredentialDisposition.BLOCKED
        for row in rows
    ):
        raise PrivateStoreError("a blocked credential prevents selecting another provider")
    return next((row for row in rows if row.state is not CredentialState.POSTCHECK), None)


def reconcile_receipt_first_orphan(
    manifest: Mapping[str, object],
    orphan_receipt: Mapping[str, object],
    *,
    postcondition_satisfied: bool,
) -> dict[str, object]:
    """Index an fsynced orphan only after independently proving its postcondition."""
    if not postcondition_satisfied:
        raise PrivateStoreError("orphan receipt cannot be indexed before postcondition proof")
    receipt_id = orphan_receipt.get("receipt_id")
    if not isinstance(receipt_id, str) or not receipt_id:
        raise PrivateStoreError("orphan receipt needs a values-free identifier")
    indexed = manifest.get("indexed_receipt_ids", [])
    if not isinstance(indexed, list) or not all(isinstance(item, str) for item in indexed):
        raise PrivateStoreError("manifest orphan index is malformed")
    updated = dict(manifest)
    updated["indexed_receipt_ids"] = indexed if receipt_id in indexed else [*indexed, receipt_id]
    return updated


def resume_quarantine_transfer(transfer: QuarantineTransfer) -> QuarantineTransfer:
    """Finish a pending transfer while ensuring no two durable source copies survive."""
    if transfer.active_item_present and not transfer.source_present:
        return transfer
    if transfer.source_present and transfer.pending_item_present:
        return QuarantineTransfer(
            source_present=False,
            pending_item_present=False,
            active_item_present=True,
        )
    raise PrivateStoreError("quarantine transfer is not resumable from its observed state")


def accepts_invalidation_evidence(evidence: Mapping[str, object]) -> bool:
    """Accept only a values-free semantic issuer-revocation witness."""
    validate_values_free(evidence)
    return (
        evidence.get("kind") == "issuer-revocation"
        and isinstance(evidence.get("reference"), str)
        and bool(evidence["reference"])
    )


MAX_PROBE_OUTPUT_BYTES: Final[int] = 64 * 1024
_MINIMAL_PROBE_ENV: Final[dict[str, str]] = {"LC_ALL": "C", "PATH": "/usr/bin:/bin"}
_DENIED_EXECUTABLES: Final[frozenset[str]] = frozenset(
    {"bash", "cmd", "env", "fish", "printenv", "pwsh", "powershell", "sh", "zsh"}
)
_SECRET_ARGUMENT: Final[re.Pattern[str]] = re.compile(
    r"(?:^--?(?:api[_-]?key|password|secret|token)(?:=|$)|(?:^|_)(?:API[_-]?KEY|PASSWORD|SECRET|TOKEN)=)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ProbeResult:
    """A values-free bounded probe result; streams and argv are never retained."""

    exit_code: int | None
    timed_out: bool
    output_discarded: bool
    launched: bool


def validate_probe_command(command: object) -> tuple[str, ...]:
    """Allow only a safe direct argument array for a read-only bounded probe."""
    if isinstance(command, (str, bytes)) or not isinstance(command, (tuple, list)):
        raise PrivateStoreError("probe commands must be explicit argument arrays")
    if not command or not all(isinstance(argument, str) and argument for argument in command):
        raise PrivateStoreError("probe command arguments must be non-empty strings")
    arguments = tuple(cast(str, argument) for argument in command)
    normalized = tuple(argument.lower() for argument in arguments)
    executable = Path(arguments[0]).name.lower()
    if executable in _DENIED_EXECUTABLES:
        raise PrivateStoreError("shell and environment-dump executables are forbidden")
    if "mcp" in normalized:
        raise PrivateStoreError("MCP command paths are forbidden")
    if executable == "ctx7" and len(normalized) > 1 and normalized[1] == "setup":
        raise PrivateStoreError("ctx7 setup is forbidden")
    if any(
        normalized[index : index + 2] == ("setup", "agent")
        for index in range(len(normalized) - 1)
    ):
        raise PrivateStoreError("agent setup command paths are forbidden")
    if any(_SECRET_ARGUMENT.search(argument) for argument in arguments):
        raise PrivateStoreError("credential values are forbidden in probe argv")
    if any("\x00" in argument or "\n" in argument or "\r" in argument for argument in arguments):
        raise PrivateStoreError("probe arguments contain an unsafe control character")
    return arguments



def _validate_allowed_executable(
    arguments: tuple[str, ...], allowed_executables: object
) -> None:
    """Require the executed realpath to match an explicit caller-provided allowlist."""
    if isinstance(allowed_executables, (str, bytes)) or not isinstance(
        allowed_executables, (tuple, list)
    ):
        raise PrivateStoreError("probe executable allowlist is required")
    try:
        executable = Path(arguments[0])
        if not executable.is_absolute():
            raise PrivateStoreError("probe executable must be an absolute reviewed path")
        actual = executable.resolve(strict=True)
    except OSError as error:
        raise PrivateStoreError("probe executable cannot be resolved") from error
    approved: set[Path] = set()
    for candidate in allowed_executables:
        if not isinstance(candidate, str):
            raise PrivateStoreError("probe executable allowlist is malformed")
        candidate_path = Path(candidate)
        if not candidate_path.is_absolute():
            raise PrivateStoreError("probe executable allowlist requires absolute paths")
        try:
            approved.add(candidate_path.resolve(strict=True))
        except OSError as error:
            raise PrivateStoreError("probe executable allowlist cannot be resolved") from error
    if actual not in approved:
        raise PrivateStoreError("probe executable is not explicitly approved")

def _kill_probe_group(process: subprocess.Popen[bytes]) -> None:
    """Terminate the isolated process group so timed-out children cannot survive."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (AttributeError, ProcessLookupError):
        process.kill()
    process.wait()


def run_bounded_probe(
    command: object,
    *,
    timeout_seconds: float = 5.0,
    max_output_bytes: int = MAX_PROBE_OUTPUT_BYTES,
    allowed_executables: object = None,
) -> ProbeResult:
    """Run an allowlisted direct command with no shell, output retention, or env leak."""
    arguments = validate_probe_command(command)
    if isinstance(timeout_seconds, bool) or timeout_seconds <= 0:
        raise PrivateStoreError("probe timeout must be positive")
    if isinstance(max_output_bytes, bool) or not 0 < max_output_bytes <= MAX_PROBE_OUTPUT_BYTES:
        raise PrivateStoreError("probe output cap must be between one byte and 64 KiB")
    _validate_allowed_executable(arguments, allowed_executables)
    try:
        process = subprocess.Popen(
            arguments,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            env=_MINIMAL_PROBE_ENV,
            start_new_session=True,
        )
    except OSError:
        return ProbeResult(
            exit_code=None,
            timed_out=False,
            output_discarded=True,
            launched=False,
        )
    try:
        exit_code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        _kill_probe_group(process)
        return ProbeResult(
            exit_code=None,
            timed_out=True,
            output_discarded=True,
            launched=True,
        )
    return ProbeResult(
        exit_code=exit_code,
        timed_out=False,
        output_discarded=True,
        launched=True,
    )


MAX_ACL_OUTPUT_BYTES: Final[int] = 8 * 1024


def _macos_acl_output(path: Path) -> bytes:
    """Read a bounded native ACL listing without persisting or printing it."""
    if sys.platform != "darwin":
        raise PrivateStoreError("extended ACL inspection is unavailable")
    try:
        process = subprocess.Popen(
            ("/bin/ls", "-lde", str(path)),
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            env=_MINIMAL_PROBE_ENV,
            start_new_session=True,
        )
        if process.stdout is None:
            raise PrivateStoreError("native ACL inspection has no bounded output stream")
        output = process.stdout.read(MAX_ACL_OUTPUT_BYTES + 1)
        if len(output) > MAX_ACL_OUTPUT_BYTES:
            _kill_probe_group(process)
            raise PrivateStoreError("native ACL inspection exceeded its output cap")
        if process.wait(timeout=2.0) != 0:
            raise PrivateStoreError("native ACL inspection failed")
        return output
    except subprocess.TimeoutExpired as error:
        _kill_probe_group(process)
        raise PrivateStoreError("native ACL inspection timed out") from error
    except OSError as error:
        raise PrivateStoreError("native ACL inspection could not start") from error


def validate_private_acl(path: Path) -> None:
    """Fail closed on extended access ACLs using a native macOS fallback if needed."""
    if stat.S_ISLNK(path.lstat().st_mode):
        raise PrivateStoreError("ACL validation refuses symlink paths")
    listxattr = getattr(os, "listxattr", None)
    if callable(listxattr):
        try:
            attributes = listxattr(path, follow_symlinks=False)
        except (OSError, TypeError) as error:
            raise PrivateStoreError("extended ACL inspection failed") from error
        unsafe = {
            "com.apple.acl.text",
            "system.posix_acl_access",
            "system.posix_acl_default",
        }
        if any(attribute in unsafe for attribute in attributes):
            raise PrivateStoreError("private-state path has an extended access ACL")
        return
    output = _macos_acl_output(path)
    try:
        lines = output.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise PrivateStoreError("native ACL inspection returned non-text output") from error
    if any(re.match(r"^\s*\d+:", line) for line in lines[1:]):
        raise PrivateStoreError("private-state path has an extended access ACL")


_DISCOVERY_STATES: Final[frozenset[str]] = frozenset(
    {"installed+runnable", "installed+broken", "residual-only", "shared-root"}
)
_ALLOWED_CODEX_IDENTITIES: Final[frozenset[tuple[str, str, str]]] = frozenset(
    {
        ("node_repl", "openai", "vendor"),
        ("sites-design-picker", "openai", "bundled"),
        ("github", "openai", "curated"),
    }
)
_HANDOFF_CLI_FIELDS: Final[frozenset[str]] = frozenset(
    {"alias", "version", "origin", "auth_class", "smoke", "risk_class", "mcp_status"}
)


@dataclass(frozen=True)
class SurfaceComponent:
    """A sanitized fixture component; it intentionally contains no raw config body."""

    host: str
    relative_path: str
    component_id: str
    publisher: str
    channel: str
    version: str
    allowed: bool


@dataclass(frozen=True)
class SurfaceRecord:
    """One discovered host loader from a controlled fixture tree."""

    host: str
    state: str
    relative_path: str
    components: tuple[SurfaceComponent, ...]


@dataclass(frozen=True)
class DiscoveryReport:
    """Read-only discovery output with explicit blockers instead of assumptions."""

    surfaces: tuple[SurfaceRecord, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class DeletionPreview:
    """Preview-only removal plan; it never edits the fixture tree."""

    removals: tuple[SurfaceComponent, ...]
    survivors: tuple[str, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class RestartEvidence:
    """A values-free post-restart verdict for the discovery closure."""

    clean: bool
    blockers: tuple[str, ...]


def _fixture_component(
    host: str, relative_path: str, raw_component: object
) -> SurfaceComponent:
    if not isinstance(raw_component, Mapping):
        raise PrivateStoreError("fixture component must be a mapping")
    values = cast(Mapping[str, object], raw_component)
    fields = ("component_id", "publisher", "channel", "version")
    if not all(isinstance(values.get(field), str) and values[field] for field in fields):
        raise PrivateStoreError("fixture component fields are malformed")
    component_id = cast(str, values["component_id"])
    publisher = cast(str, values["publisher"])
    channel = cast(str, values["channel"])
    version = cast(str, values["version"])
    identity = (component_id, publisher, channel)
    is_codex = host.startswith("codex")
    allowed = is_codex and identity in _ALLOWED_CODEX_IDENTITIES
    return SurfaceComponent(
        host=host,
        relative_path=relative_path,
        component_id=component_id,
        publisher=publisher,
        channel=channel,
        version=version,
        allowed=allowed,
    )


def scan_fixture_discovery(root: Path) -> DiscoveryReport:
    """Read a bounded synthetic host tree without reading real personal surfaces."""
    if root.is_symlink() or not root.is_dir():
        raise PrivateStoreError("fixture discovery root must be a real directory")
    surfaces: list[SurfaceRecord] = []
    blockers: list[str] = []
    for child in sorted(root.iterdir(), key=lambda item: item.name):
        if child.is_symlink():
            blockers.append("symlink-surface")
            continue
        if not child.is_dir():
            blockers.append("unknown-surface-entry")
            continue
        fixture_path = child / "surface.json"
        if fixture_path.is_symlink():
            blockers.append("symlink-surface")
            continue
        try:
            if fixture_path.stat().st_size > MAX_PROBE_OUTPUT_BYTES:
                raise PrivateStoreError("fixture surface exceeds bounded discovery size")
            raw_document = json.loads(fixture_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise PrivateStoreError("fixture surface cannot be read safely") from error
        if not isinstance(raw_document, Mapping):
            raise PrivateStoreError("fixture surface must be a mapping")
        document = cast(Mapping[str, object], raw_document)
        host = document.get("host")
        state = document.get("state")
        raw_components = document.get("components")
        if (
            not isinstance(host, str)
            or not isinstance(state, str)
            or not isinstance(raw_components, list)
        ):
            raise PrivateStoreError("fixture surface schema is malformed")
        if state not in _DISCOVERY_STATES:
            blockers.append("unknown-surface-state")
        relative_path = f"{child.name}/surface.json"
        components = tuple(
            _fixture_component(host, relative_path, component) for component in raw_components
        )
        if host.startswith("codex") and any(not component.allowed for component in components):
            blockers.append("codex-identity-mismatch")
        surfaces.append(
            SurfaceRecord(
                host=host,
                state=state,
                relative_path=relative_path,
                components=components,
            )
        )
    return DiscoveryReport(surfaces=tuple(surfaces), blockers=tuple(sorted(set(blockers))))


def build_deletion_preview(
    report: DiscoveryReport,
    *,
    dirty_relpaths: frozenset[str],
    expected_survivors: frozenset[str],
) -> DeletionPreview:
    """Build a no-write removal preview and stop on every dirty-path overlap."""
    blockers = list(report.blockers)
    removals: list[SurfaceComponent] = []
    for surface in report.surfaces:
        for component in surface.components:
            if component.allowed:
                continue
            if component.relative_path in dirty_relpaths:
                blockers.append("dirty-overlap")
                continue
            removals.append(component)
    return DeletionPreview(
        removals=tuple(removals),
        survivors=tuple(sorted(expected_survivors)),
        blockers=tuple(sorted(set(blockers))),
    )


def verify_restart_epoch(before: DiscoveryReport, after: DiscoveryReport) -> RestartEvidence:
    """Require a restart result with no residual or regenerated non-allowlisted MCP."""
    del before  # The report is retained by the caller as immutable pre-restart evidence.
    blockers = list(after.blockers)
    if any(
        not component.allowed
        for surface in after.surfaces
        for component in surface.components
    ):
        blockers.append("regenerated-third-party-mcp")
    return RestartEvidence(clean=not blockers, blockers=tuple(sorted(set(blockers))))


def export_handoff(
    report: DiscoveryReport,
    *,
    credential_states: Mapping[str, str],
    cli_rows: list[Mapping[str, object]],
) -> dict[str, object]:
    """Export a values-free handoff only after every closure and lane is terminal."""
    if report.blockers or any(
        not component.allowed
        for surface in report.surfaces
        for component in surface.components
    ):
        raise PrivateStoreError("handoff is blocked by incomplete MCP closure")
    if not credential_states or any(state != "POSTCHECK" for state in credential_states.values()):
        raise PrivateStoreError("handoff requires terminal credential postchecks")
    handoff_rows: list[dict[str, object]] = []
    for row in cli_rows:
        if set(row) != _HANDOFF_CLI_FIELDS:
            raise PrivateStoreError("handoff CLI row fields differ from the allowlist")
        copied = dict(row)
        validate_values_free(copied)
        handoff_rows.append(copied)
    states = dict(credential_states)
    validate_values_free(states)
    return {"credential_states": states, "cli": handoff_rows}
