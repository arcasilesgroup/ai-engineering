"""Canonical terminal outcomes derived from the approved v1 policy."""

from __future__ import annotations

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
_MAX_FACTS = 128
_MAX_SUMMARY = 512
_MAX_DETAIL = 1_024
_FACT_STATUSES = frozenset(
    {"APPLIED", "FAIL", "INCOMPLETE", "OBSERVED", "PASS", "SKIPPED", "WARN", "WOULD_CHANGE"}
)


class OutcomePolicyError(RuntimeError):
    """The canonical outcome policy cannot be trusted."""


def _read_policy(path: Path) -> bytes:
    try:
        return paths.read_bounded(path, _MAX_POLICY_BYTES, "outcome policy")
    except OSError as error:
        raise OutcomePolicyError("outcome policy cannot be read") from error


def _mapping() -> tuple[dict[str, tuple[int, str, str]], dict[str, Any]]:
    try:
        schema = intent._json(_read_policy(SCHEMA_PATH))
        if not isinstance(schema, dict):
            raise ValueError("policy is not an object")
        digest = sha256(intent.canonical_json(schema)).hexdigest()
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


class Unreadable(Exception):
    """A file that is there and cannot be read. Absent is an answer; unreadable is not.

    One base for a condition five modules had each named for themselves. `cli` has a handler
    for exactly this — stop, name the file, write nothing — and reaching it meant importing
    every module that could raise, which put `solution_intent` and `blocked` on the cold start
    of every verb and cost twenty milliseconds a `--version` call. A caller that wants to know
    "could this be read" should not have to know who was reading.
    """


@dataclass(frozen=True, slots=True)
class Fact:
    """One bounded execution fact, separate from the closed terminal-outcome schema."""

    id: str
    status: str
    summary: str
    detail: str | None
    # `detail` is the evidence — what was observed. `cure` is what to do about it, and the
    # JSON envelope used to drop it: a check object was `{id, status, summary, detail}`,
    # so the machine-readable half told a consumer something failed and withheld the one
    # field that says what to do, while the human half had it on screen. Optional, because
    # most facts have no cure and inventing one is worse than omitting it.
    cure: str | None = None

    def __post_init__(self) -> None:
        if (
            not self.id
            or len(self.id) > 64
            or any(
                character not in "abcdefghijklmnopqrstuvwxyz0123456789-_." for character in self.id
            )
            or self.status not in _FACT_STATUSES
            or not self.summary
            or len(self.summary) > _MAX_SUMMARY
            or (self.detail is not None and len(self.detail) > _MAX_DETAIL)
            or (self.cure is not None and len(self.cure) > _MAX_DETAIL)
        ):
            raise ValueError("execution fact is not bounded and canonical")

    def as_dict(self) -> dict[str, str | None]:
        return {
            "id": self.id,
            "status": self.status,
            "summary": self.summary,
            "detail": self.detail,
            "cure": self.cure,
        }


@dataclass(frozen=True, slots=True)
class Error:
    """The JSON error object known at the same boundary as its failure."""

    code: str
    message: str
    retryable: bool
    cure: str | None

    def __post_init__(self) -> None:
        if (
            not self.code
            or len(self.code) > 64
            or any(
                character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for character in self.code
            )
            or not self.message
            or len(self.message) > _MAX_SUMMARY
            or type(self.retryable) is not bool
            or (self.cure is not None and len(self.cure) > _MAX_DETAIL)
        ):
            raise ValueError("execution error is not bounded and canonical")

    def as_dict(self) -> dict[str, str | bool | None]:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "cure": self.cure,
        }


@dataclass(frozen=True, slots=True)
class Execution:
    """A terminal Result plus bounded facts; Result itself stays policy-schema exact."""

    result: Result
    summary: str
    changes: tuple[Fact, ...]
    checks: tuple[Fact, ...]
    remaining: tuple[str, ...]
    next_actions: tuple[str, ...]
    error: Error | None

    def __post_init__(self) -> None:
        if type(self.result) is not Result or not self.summary or len(self.summary) > _MAX_SUMMARY:
            raise ValueError("execution does not carry one canonical terminal result")
        if (
            len(self.changes) > _MAX_FACTS
            or len(self.checks) > _MAX_FACTS
            or len(self.remaining) > _MAX_FACTS
            or len(self.next_actions) > _MAX_FACTS
            or any(type(item) is not Fact for item in (*self.changes, *self.checks))
            or any(
                not item or len(item) > _MAX_DETAIL
                for item in (*self.remaining, *self.next_actions)
            )
            or (self.error is not None and type(self.error) is not Error)
            or (self.result.exit_code == 0) != (self.error is None)
        ):
            raise ValueError("execution facts do not match their terminal result")

    @property
    def outcome(self) -> str:
        return self.result.outcome

    @property
    def exit_code(self) -> int:
        return self.result.exit_code


def _text(value: object, limit: int) -> str:
    if not isinstance(value, str):
        raise TypeError("execution text must be a string")
    bounded = value[: limit * 4]
    safe = "".join(character if character.isprintable() else " " for character in bounded)
    safe = " ".join(safe.split())
    if not safe:
        raise ValueError("execution text cannot be empty")
    return safe if len(safe) <= limit else safe[: limit - 1].rstrip() + "…"


def fact(
    id: str,
    status: str,
    summary: str,
    detail: str | None = None,
    cure: str | None = None,
) -> Fact:
    """Build one bounded fact without retaining terminal prose buffers."""

    return Fact(
        id=id,
        status=status,
        summary=_text(summary, _MAX_SUMMARY),
        detail=None if detail is None else _text(detail, _MAX_DETAIL),
        # An empty cure is no cure. `doctor.resolve` returns one for an assertion whose
        # repair is a person rather than a command, and "" is not a shorter answer than
        # absent — it is the same answer spelled so that a consumer has to special-case it.
        cure=_text(cure, _MAX_DETAIL) if cure else None,
    )


def error(code: str, message: str, retryable: bool, cure: str | None = None) -> Error:
    """Build one bounded machine error without exposing an exception representation."""

    return Error(
        code=code,
        message=_text(message, _MAX_SUMMARY),
        retryable=retryable,
        cure=None if cure is None else _text(cure, _MAX_DETAIL),
    )


def execution(
    terminal: Result,
    *,
    summary: str | None = None,
    changes: tuple[Fact, ...] | list[Fact] = (),
    checks: tuple[Fact, ...] | list[Fact] = (),
    remaining: tuple[str, ...] | list[str] = (),
    next_actions: tuple[str, ...] | list[str] | None = None,
    execution_error: Error | None = None,
) -> Execution:
    """Attach facts without changing or widening the closed Result schema."""

    if type(terminal) is not Result:
        raise TypeError("execution requires one canonical Result")
    if execution_error is None and terminal.exit_code:
        execution_error = error(
            terminal.outcome,
            terminal.reason,
            terminal.outcome in {"FAIL", "INCOMPLETE"},
            terminal.next_action,
        )
    actions = [terminal.next_action] if next_actions is None else next_actions
    return Execution(
        result=terminal,
        summary=_text(summary or terminal.reason, _MAX_SUMMARY),
        changes=tuple(changes),
        checks=tuple(checks),
        remaining=tuple(_text(item, _MAX_DETAIL) for item in remaining),
        next_actions=tuple(_text(item, _MAX_DETAIL) for item in actions),
        error=execution_error,
    )


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
