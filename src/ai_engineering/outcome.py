"""Canonical terminal outcomes derived from the approved v1 policy."""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from ai_engineering import intent, paths

SCHEMA_PATH = paths.policy("outcome-v1.schema.json")
_EXPECTED_SCHEMA_DIGEST = "2e42b949c5e43693b97caa08eb439448ef19f8577002a3077e0117c0e23d7cfd"
_SCHEMA = "urn:ai-engineering:outcome:1"
_VERSION = "1"
_FIELDS = ("schema", "schema_version", "outcome", "exit_code", "reason", "next_action")
_MAX_POLICY_BYTES = 100_000


class OutcomePolicyError(RuntimeError):
    """The canonical outcome policy cannot be trusted."""


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()


def _read_policy(path: Path) -> bytes:
    descriptor = -1
    close_failed = False
    try:
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise OSError("outcome policy is not a regular file")
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_BINARY", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        identity = (opened.st_dev, opened.st_ino)
        if not stat.S_ISREG(opened.st_mode) or identity != (before.st_dev, before.st_ino):
            raise OSError("outcome policy changed while opening")
        raw = os.read(descriptor, _MAX_POLICY_BYTES + 1)
        if os.read(descriptor, 1):
            raise OSError("outcome policy exceeds its bound")
        after = path.lstat()
        if identity != (after.st_dev, after.st_ino):
            raise OSError("outcome policy changed while reading")
    except OSError as error:
        raise OutcomePolicyError("outcome policy cannot be read") from error
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                close_failed = True
    if close_failed or len(raw) > _MAX_POLICY_BYTES:
        raise OutcomePolicyError("outcome policy cannot be read")
    return raw


def _mapping() -> tuple[dict[str, tuple[int, str, str]], dict[str, Any]]:
    try:
        schema = intent._json(_read_policy(SCHEMA_PATH))
        if not isinstance(schema, dict):
            raise ValueError("policy is not an object")
        digest = sha256(_canonical_json(schema)).hexdigest()
        if digest != _EXPECTED_SCHEMA_DIGEST:
            raise ValueError("outcome policy differs from its approved contract")
        policy = schema["x-outcome-policy"]
        ordered = policy["ordered_outcomes"]
        branches = {
            branch["properties"]["outcome"]["const"]: (
                branch["properties"]["exit_code"]["const"],
                branch["properties"]["reason"]["const"],
                branch["properties"]["next_action"]["const"],
            )
            for branch in schema["oneOf"]
        }
        if (
            schema["$id"] != _SCHEMA
            or schema["properties"]["schema_version"]["const"] != _VERSION
            or schema["additionalProperties"] is not False
            or tuple(schema["required"]) != _FIELDS
            or set(schema["properties"]) != set(_FIELDS)
            or list(branches) != ordered
            or len(branches) != 7
            or policy["phase_only"] != ["RUNNING"]
            or policy["invalid_cli_exit"] != 2
            or policy["unknown_normalizes_to"] != "INCOMPLETE"
            or policy["dry_run_undecidable"] != "INCOMPLETE"
        ):
            raise ValueError("outcome policy is inconsistent")
    except OutcomePolicyError:
        raise
    except (KeyError, RecursionError, TypeError, ValueError):
        raise OutcomePolicyError("outcome policy is unsupported") from None
    return branches, policy


@dataclass(frozen=True, slots=True)
class Result:
    schema: str
    schema_version: str
    outcome: str
    exit_code: int
    reason: str
    next_action: str

    def __post_init__(self) -> None:
        mapping, _ = _mapping()
        if self.schema != _SCHEMA or self.schema_version != _VERSION:
            raise ValueError("result version is not canonical")
        if mapping.get(self.outcome) != (self.exit_code, self.reason, self.next_action):
            raise ValueError("result fields do not match one canonical outcome")

    def as_dict(self) -> dict[str, str | int]:
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "outcome": self.outcome,
            "exit_code": self.exit_code,
            "reason": self.reason,
            "next_action": self.next_action,
        }


def result(status: object) -> Result:
    """Return one exact terminal result; unknown and phase labels normalize to INCOMPLETE."""

    mapping, policy = _mapping()
    normalized = (
        status if isinstance(status, str) and status in mapping else policy["unknown_normalizes_to"]
    )
    exit_code, reason, next_action = mapping[normalized]
    return Result(_SCHEMA, _VERSION, normalized, exit_code, reason, next_action)


def dry_run(*, exact_changes: object) -> Result:
    """A dry run is WOULD_CHANGE only when its exact proposed changes are complete."""

    _, policy = _mapping()
    status = "WOULD_CHANGE" if exact_changes is True else policy["dry_run_undecidable"]
    return result(status)


def invalid_cli_exit() -> int:
    """CLI misuse is parser exit 2, not a terminal operation outcome."""

    _, policy = _mapping()
    return policy["invalid_cli_exit"]
