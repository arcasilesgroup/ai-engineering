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
from collections.abc import Iterator, Mapping
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
    _assert_private(path, 0o600, directory=False)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write_json(path: Path, document: Mapping[str, object]) -> None:
    """Durably replace an already-validated private JSON document."""
    _assert_private(path.parent, 0o700, directory=True)
    payload = _json_payload(document)
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


def validate_manifest(document: Mapping[str, object]) -> dict[str, object]:
    """Validate the minimal values-free manifest schema used before discovery."""
    expected = {"schema", "records", "receipt_index"}
    if set(document) != expected:
        raise PrivateStoreError("manifest fields differ from the pre-discovery allowlist")
    schema = document["schema"]
    records = document["records"]
    receipt_index = document["receipt_index"]
    if not isinstance(schema, str) or not schema:
        raise PrivateStoreError("manifest schema must be a non-empty string")
    if not isinstance(records, list) or not isinstance(receipt_index, list):
        raise PrivateStoreError("manifest collections must be lists")
    validate_values_free(schema)
    validate_values_free(records)
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
    return {"schema": schema, "records": list(records), "receipt_index": validated_index}


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
        return new_digest

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
        return ReceiptCommit(
            manifest=manifest,
            manifest_digest=manifest_digest,
            receipt_sha256=receipt_sha256,
        )


@contextmanager
def private_store_session(root: Path) -> Iterator[PrivateStoreSession]:
    """Yield the sole writer capability while the owner-only lock is held."""
    paths = ensure_private_store(root)
    descriptor, _ = _open_private_file(paths.lock, os.O_CREAT | os.O_RDWR)
    session = PrivateStoreSession(paths)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield session
    finally:
        session.close()
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


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
