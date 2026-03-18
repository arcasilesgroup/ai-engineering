"""Agent-facing JSON envelope for ``--json`` mode.

Emits structured JSON to stdout with HATEOAS ``next_actions`` for
agent consumption. Human output is suppressed when this mode is active.
"""

from __future__ import annotations

import sys
from typing import Any, Literal

from pydantic import BaseModel


class NextAction(BaseModel):
    """A suggested follow-up command for agent consumption."""

    command: str
    description: str
    params: dict[str, Any] | None = None


class SuccessEnvelope(BaseModel):
    """JSON envelope for successful command results."""

    ok: Literal[True] = True
    command: str
    result: dict[str, Any]
    next_actions: list[NextAction] = []


class ErrorEnvelope(BaseModel):
    """JSON envelope for command failures."""

    ok: Literal[False] = False
    command: str
    error: dict[str, str]
    fix: str
    next_actions: list[NextAction] = []


def emit_success(
    command: str,
    result: dict[str, Any],
    next_actions: list[NextAction] | None = None,
) -> None:
    """Write a success JSON envelope to stdout."""
    envelope = SuccessEnvelope(
        command=command,
        result=result,
        next_actions=next_actions or [],
    )
    sys.stdout.write(envelope.model_dump_json(indent=2) + "\n")
    sys.stdout.flush()


def emit_error(
    command: str,
    message: str,
    code: str,
    fix: str,
    next_actions: list[NextAction] | None = None,
) -> None:
    """Write an error JSON envelope to stdout."""
    envelope = ErrorEnvelope(
        command=command,
        error={"message": message, "code": code},
        fix=fix,
        next_actions=next_actions or [],
    )
    sys.stdout.write(envelope.model_dump_json(indent=2) + "\n")
    sys.stdout.flush()


def truncate_list(items: list[Any], max_items: int = 20) -> dict[str, Any]:
    """Truncate a list for context-protecting JSON output.

    Returns a dict with 'items' (truncated) and 'total' (original count).
    """
    return {
        "items": items[:max_items],
        "total": len(items),
        "truncated": len(items) > max_items,
    }
