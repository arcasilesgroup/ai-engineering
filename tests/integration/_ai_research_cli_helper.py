"""Lockstep Python implementation of the CLI flag parser documented in the
``$ARGUMENTS`` contract of ``.claude/skills/ai-research/SKILL.md``.

The skill is a Markdown spec consumed by an LLM agent. To pin the contract
for the 5 supported flags (``--depth``, ``--reuse-notebook``, ``--persist``,
``--allowed-domains``, ``--blocked-domains``) this helper mirrors the
agent-side parsing logic 1:1. If the SKILL.md flag list changes, this
module must follow (and vice versa).

Public API:

* :class:`CLIArgs`        -- dataclass capturing parsed values.
* :func:`parse_cli_args`  -- consume the raw argv list and return CLIArgs.

The parser is intentionally minimal: ``argparse`` would import a stdlib
module per invocation; the flag set is small enough that an explicit
loop is clearer and faster.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

# Pinned vocabulary -- changes here MUST be reflected in SKILL.md.
_VALID_DEPTHS: frozenset[str] = frozenset({"quick", "standard", "deep"})
_DEFAULT_DEPTH = "standard"


@dataclass
class CLIArgs:
    """Parsed ``$ARGUMENTS`` for the ``/ai-research`` skill."""

    query: str = ""
    depth: str = _DEFAULT_DEPTH
    reuse_notebook: str | None = None
    persist: bool = False
    allowed_domains: list[str] = field(default_factory=list)
    blocked_domains: list[str] = field(default_factory=list)


def _split_csv(value: str) -> list[str]:
    """Split a comma-separated CLI value into trimmed, non-empty entries."""
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_cli_args(argv: Sequence[str]) -> CLIArgs:
    """Parse the agent-supplied ``argv`` into :class:`CLIArgs`.

    Recognized flags (must precede the positional query):

    * ``--depth=<quick|standard|deep>`` -- defaults to ``standard``.
    * ``--reuse-notebook=<id>``         -- opt-in for follow-ups.
    * ``--persist``                     -- opt-in flag (no value).
    * ``--allowed-domains=<csv>``       -- pass-through to WebSearch.
    * ``--blocked-domains=<csv>``       -- pass-through to WebSearch.

    Everything that is not a recognized flag is appended to the query
    (verbatim, separated by single spaces). An unknown flag raises
    ``ValueError`` so typos surface immediately.

    A flag-only invocation (no positional query) raises ``ValueError``.
    """
    args = CLIArgs()
    query_parts: list[str] = []

    for token in argv:
        if token == "--persist":
            args.persist = True
            continue
        if token.startswith("--depth="):
            value = token.split("=", 1)[1]
            if value not in _VALID_DEPTHS:
                raise ValueError(
                    f"invalid depth {value!r}; expected one of {sorted(_VALID_DEPTHS)}"
                )
            args.depth = value
            continue
        if token.startswith("--reuse-notebook="):
            args.reuse_notebook = token.split("=", 1)[1]
            continue
        if token.startswith("--allowed-domains="):
            args.allowed_domains = _split_csv(token.split("=", 1)[1])
            continue
        if token.startswith("--blocked-domains="):
            args.blocked_domains = _split_csv(token.split("=", 1)[1])
            continue
        if token.startswith("--"):
            raise ValueError(f"unknown flag: {token!r}")
        query_parts.append(token)

    if not query_parts:
        raise ValueError("query is required after the recognized flags")

    args.query = " ".join(query_parts)
    return args


__all__: Iterable[str] = (
    "CLIArgs",
    "parse_cli_args",
)
