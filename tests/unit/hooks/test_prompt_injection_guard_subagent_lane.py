"""Tests for the sub-agent positive allow-list lane in ``prompt-injection-guard``.

spec-131 sub-004 T-4.B / D-131-11: when ``ctx.agent_kind == "subagent"``,
read-only commands (``rg``/``grep``/``find``/``ls``/``cat``) without
shell-metacharacters or destructive predicates short-circuit the IOC
pattern scan. Main-thread invocations still run the full scan.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
GUARD_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "prompt-injection-guard.py"


@pytest.fixture
def guard():
    """Load ``prompt-injection-guard.py`` under a fresh module name."""
    sys.modules.pop("aieng_prompt_injection_guard_subagent", None)
    spec = importlib.util.spec_from_file_location(
        "aieng_prompt_injection_guard_subagent", GUARD_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aieng_prompt_injection_guard_subagent"] = module
    spec.loader.exec_module(module)
    return module


def test_helper_exists(guard) -> None:
    assert hasattr(guard, "_is_subagent_readonly")


def test_rg_with_pattern_passes(guard) -> None:
    assert guard._is_subagent_readonly("rg PATTERN .") == "rg"


def test_grep_recursive_passes(guard) -> None:
    assert guard._is_subagent_readonly("grep -r PATTERN .") == "grep"


def test_find_without_destructive_passes(guard) -> None:
    assert guard._is_subagent_readonly("find . -name '*.py'") == "find"


def test_find_with_delete_blocked(guard) -> None:
    assert guard._is_subagent_readonly("find . -delete") is None


def test_find_with_exec_blocked(guard) -> None:
    assert guard._is_subagent_readonly("find . -exec rm {} ;") is None


def test_cat_simple_passes(guard) -> None:
    assert guard._is_subagent_readonly("cat /tmp/file.txt") == "cat"


def test_cat_with_redirect_blocked(guard) -> None:
    assert guard._is_subagent_readonly("cat secret.key > /tmp/out") is None


def test_ls_passes(guard) -> None:
    assert guard._is_subagent_readonly("ls /etc") == "ls"


def test_pipe_metacharacter_blocked(guard) -> None:
    assert guard._is_subagent_readonly("rg PATTERN . | tee out") is None


def test_semicolon_metacharacter_blocked(guard) -> None:
    assert guard._is_subagent_readonly("ls /etc ; rm -rf /tmp") is None


def test_logical_and_blocked(guard) -> None:
    assert guard._is_subagent_readonly("ls /etc && rm -rf /tmp") is None


def test_unknown_command_blocked(guard) -> None:
    assert guard._is_subagent_readonly("python3 script.py") is None


def test_malformed_quoting_fails_closed(guard) -> None:
    """``shlex.split`` raises ``ValueError`` on unterminated quotes;
    the helper must return None (fail-closed)."""
    assert guard._is_subagent_readonly('rg "unterminated') is None


def test_empty_command_returns_none(guard) -> None:
    assert guard._is_subagent_readonly("") is None
