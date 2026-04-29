"""RED-phase tests for spec-111 T-4.11 -- /ai-research CLI flag parsing.

Spec acceptance:
    The skill SKILL.md is a Markdown spec consumed by an LLM agent. To
    pin the contract for the 5 CLI flags (``--depth``, ``--reuse-notebook``,
    ``--persist``, ``--allowed-domains``, ``--blocked-domains``) we ship
    a deterministic parser helper at
    ``tests/integration/_ai_research_cli_helper.py`` that the agent
    consumes (and tests exercise directly).

The 8 scenarios required:
  1. default depth=standard
  2. --depth=quick
  3. --depth=deep
  4. --reuse-notebook=ID
  5. --persist with quick
  6. --allowed-domains a,b
  7. --blocked-domains x,y
  8. combination (--depth=deep + --persist + --allowed-domains)

Status: RED until T-4.12 lands the parser helper.
"""

from __future__ import annotations

import pytest

from tests.integration._ai_research_cli_helper import (
    CLIArgs,
    parse_cli_args,
)

# ---------------------------------------------------------------------------
# Scenario 1: default depth=standard
# ---------------------------------------------------------------------------


def test_default_depth_is_standard() -> None:
    """No flags -> depth=standard, all opt-ins false/empty."""
    args = parse_cli_args(["how do projects retry"])

    assert isinstance(args, CLIArgs)
    assert args.depth == "standard", f"Default depth must be 'standard'; got {args.depth!r}"
    assert args.reuse_notebook is None
    assert args.persist is False
    assert args.allowed_domains == []
    assert args.blocked_domains == []
    assert args.query == "how do projects retry"


# ---------------------------------------------------------------------------
# Scenario 2: --depth=quick
# ---------------------------------------------------------------------------


def test_depth_quick() -> None:
    args = parse_cli_args(["--depth=quick", "Pyramid testing"])

    assert args.depth == "quick"
    assert args.query == "Pyramid testing"


# ---------------------------------------------------------------------------
# Scenario 3: --depth=deep
# ---------------------------------------------------------------------------


def test_depth_deep() -> None:
    args = parse_cli_args(["--depth=deep", "compare hexagonal vs onion architecture"])

    assert args.depth == "deep"
    assert args.query == "compare hexagonal vs onion architecture"


# ---------------------------------------------------------------------------
# Scenario 4: --reuse-notebook=ID
# ---------------------------------------------------------------------------


def test_reuse_notebook_flag() -> None:
    args = parse_cli_args(
        ["--reuse-notebook=nb-existing-abc123", "follow-up question"],
    )

    assert args.reuse_notebook == "nb-existing-abc123"
    assert args.query == "follow-up question"


# ---------------------------------------------------------------------------
# Scenario 5: --persist with quick
# ---------------------------------------------------------------------------


def test_persist_with_quick() -> None:
    args = parse_cli_args(["--depth=quick", "--persist", "research worth saving"])

    assert args.depth == "quick"
    assert args.persist is True
    assert args.query == "research worth saving"


# ---------------------------------------------------------------------------
# Scenario 6: --allowed-domains a,b
# ---------------------------------------------------------------------------


def test_allowed_domains() -> None:
    args = parse_cli_args(
        ["--allowed-domains=docs.python.org,realpython.com", "Python asyncio patterns"],
    )

    assert args.allowed_domains == ["docs.python.org", "realpython.com"]
    assert args.blocked_domains == []
    assert args.query == "Python asyncio patterns"


# ---------------------------------------------------------------------------
# Scenario 7: --blocked-domains x,y
# ---------------------------------------------------------------------------


def test_blocked_domains() -> None:
    args = parse_cli_args(
        ["--blocked-domains=stackoverflow.com,reddit.com", "TypeScript narrowing"],
    )

    assert args.blocked_domains == ["stackoverflow.com", "reddit.com"]
    assert args.allowed_domains == []
    assert args.query == "TypeScript narrowing"


# ---------------------------------------------------------------------------
# Scenario 8: combination (--depth=deep + --persist + --allowed-domains)
# ---------------------------------------------------------------------------


def test_flag_combination() -> None:
    args = parse_cli_args(
        [
            "--depth=deep",
            "--persist",
            "--allowed-domains=docs.example.com,api.example.com",
            "compare option A vs option B",
        ],
    )

    assert args.depth == "deep"
    assert args.persist is True
    assert args.allowed_domains == ["docs.example.com", "api.example.com"]
    assert args.blocked_domains == []
    assert args.reuse_notebook is None
    assert args.query == "compare option A vs option B"


# ---------------------------------------------------------------------------
# Edge cases pinning the contract
# ---------------------------------------------------------------------------


def test_unknown_flag_raises() -> None:
    """An unknown flag must raise so typos surface immediately."""
    with pytest.raises(ValueError, match="unknown flag"):
        parse_cli_args(["--bogus-flag=foo", "query"])


def test_missing_query_raises() -> None:
    """A flag-only invocation with no positional query is an error."""
    with pytest.raises(ValueError, match="query"):
        parse_cli_args(["--depth=standard"])


@pytest.mark.parametrize(
    "depth",
    ["quick", "standard", "deep"],
)
def test_valid_depth_values(depth: str) -> None:
    args = parse_cli_args([f"--depth={depth}", "x"])
    assert args.depth == depth


def test_invalid_depth_value_raises() -> None:
    with pytest.raises(ValueError, match="depth"):
        parse_cli_args(["--depth=hyper", "x"])
