"""Tests for the no-verify-guard.py token-aware matcher (spec-131 sub-004 T-4.E).

The pre-spec-131 ``Bash(*--no-verify*)`` substring glob in
``.claude/settings.json:19`` produced false positives on legitimate
operations:

* ``AIENG_VERIFY_NO_VERIFY=1 git status`` (env-var prefix happens to
  contain the substring).
* ``python3 -c "print('--no-verify')"`` (the literal lives inside a
  quoted Python string).
* ``git log --grep='--no-verify'`` (legit search of the git log).

Replacement: a ``no-verify-guard.py`` PreToolUse hook that shlex-parses
the Bash argv and denies ONLY when ``--no-verify`` appears as a discrete
token under a git verb that supports the flag (``commit``, ``push``,
``merge``, ``rebase``, ``cherry-pick``).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GUARD_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "no-verify-guard.py"


@pytest.fixture
def guard():
    """Load ``no-verify-guard.py`` under a fresh module name."""
    sys.modules.pop("aieng_no_verify_guard", None)
    spec = importlib.util.spec_from_file_location("aieng_no_verify_guard", GUARD_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aieng_no_verify_guard"] = module
    spec.loader.exec_module(module)
    return module


def test_helper_exists(guard) -> None:
    assert hasattr(guard, "_is_no_verify_attempt")


def test_git_commit_no_verify_blocked(guard) -> None:
    assert guard._is_no_verify_attempt("git commit --no-verify -m msg") is True


def test_git_push_no_verify_blocked(guard) -> None:
    assert guard._is_no_verify_attempt("git push --no-verify") is True


def test_git_merge_no_verify_blocked(guard) -> None:
    assert guard._is_no_verify_attempt("git merge --no-verify branch") is True


def test_git_rebase_no_verify_blocked(guard) -> None:
    assert guard._is_no_verify_attempt("git rebase --no-verify upstream") is True


def test_git_cherry_pick_no_verify_blocked(guard) -> None:
    assert guard._is_no_verify_attempt("git cherry-pick --no-verify HEAD~1") is True


def test_git_log_grep_no_verify_allowed(guard) -> None:
    """``git log --grep='--no-verify'`` — ``--no-verify`` lives inside a
    quoted literal and is NOT a discrete token after shlex.split."""
    assert guard._is_no_verify_attempt("git log --grep='--no-verify'") is False


def test_env_prefix_with_no_verify_substring_allowed(guard) -> None:
    """``AIENG_VERIFY_NO_VERIFY=1 git status`` — env-var prefix that
    happens to contain the substring must not block."""
    assert guard._is_no_verify_attempt("AIENG_VERIFY_NO_VERIFY=1 git status") is False


def test_python_with_quoted_literal_allowed(guard) -> None:
    """``python3 -c "print('--no-verify')"`` — not git, no discrete token."""
    assert guard._is_no_verify_attempt("python3 -c \"print('--no-verify')\"") is False


def test_unrelated_git_command_allowed(guard) -> None:
    assert guard._is_no_verify_attempt("git status") is False


def test_malformed_argv_fails_closed(guard) -> None:
    """spec-147 G1: ``shlex.split`` raises on unterminated quoting; the
    matcher now fails CLOSED (returns True) — an unparseable command on
    a security boundary is treated as a deny candidate, not waved
    through. Better to block a rare legitimate quote error than to let a
    crafted unparseable ``--no-verify`` bypass the guard."""
    assert guard._is_no_verify_attempt('git commit "unterminated --no-verify') is True


def test_empty_argv_returns_false(guard) -> None:
    assert guard._is_no_verify_attempt("") is False


def test_settings_json_no_longer_has_catchall() -> None:
    """``.claude/settings.json`` must drop EVERY substring glob for ``--no-verify``.

    spec-132 T-4 / operator-pain #16: the four git-specific globs
    (``Bash(git commit*--no-verify*)``, ``push``, ``merge``, ``rebase``)
    block legitimate commits whose message text or branch name contains
    the literal substring (e.g. ``git commit -m "feat: add --no-verify
    support"``). The token-aware ``no-verify-guard.py`` hook is the
    canonical defence — the globs supersede it with false positives.
    """
    settings_path = REPO / ".claude" / "settings.json"
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    deny = payload["permissions"]["deny"]
    assert "Bash(*--no-verify*)" not in deny, (
        "spec-131 sub-004 T-4.E removed the substring catch-all in favour "
        "of no-verify-guard.py token-aware matcher"
    )
    # spec-132 T-4: the four git-specific globs are GONE; the hook is the
    # sole defence. Asserting their absence prevents accidental reintroduction.
    for verb in ("commit", "push", "merge", "rebase"):
        assert f"Bash(git {verb}*--no-verify*)" not in deny, (
            f"Bash(git {verb}*--no-verify*) reintroduced — operator-pain #16"
            " resurfaces: substring globs block legitimate commits whose"
            " message text contains the literal '--no-verify'."
        )


def test_no_verify_guard_wired_in_pretooluse() -> None:
    """``no-verify-guard.py`` is registered as a PreToolUse hook."""
    settings_path = REPO / ".claude" / "settings.json"
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    pre = payload["hooks"]["PreToolUse"]
    found = False
    for entry in pre:
        for h in entry.get("hooks", []):
            if "no-verify-guard.py" in h.get("command", ""):
                found = True
                break
    assert found, "no-verify-guard.py must be wired as a PreToolUse hook"
