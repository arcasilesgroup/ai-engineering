"""Output routing layer: human vs JSON mode.

Decides whether to call human-facing Rich output or emit a JSON envelope
based on the global ``--json`` flag.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ai_engineering.cli_envelope import NextAction, emit_success

_json_mode: bool = False


def set_json_mode(enabled: bool) -> None:
    """Set the global JSON output mode."""
    global _json_mode
    _json_mode = enabled


def is_json_mode() -> bool:
    """Return whether JSON output mode is active."""
    return _json_mode


def output(
    *,
    command: str,
    result: dict[str, Any],
    next_actions: list[NextAction] | None = None,
    human_fn: Callable[[], None],
) -> None:
    """Route output to human or JSON mode.

    Args:
        command: The command name for the JSON envelope.
        result: Structured result data.
        next_actions: HATEOAS next actions for the JSON envelope.
        human_fn: Callable that produces human-readable output.
    """
    if _json_mode:
        emit_success(command, result, next_actions)
    else:
        human_fn()
