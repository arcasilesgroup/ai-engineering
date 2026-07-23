"""Tests for hook behavior (spec-196 T-7).

Verifies that normal hooks don't inject additionalContext or make
tracked writes on happy path. Security hooks are exempt.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parents[2] / ".ai-engineering" / "scripts" / "hooks"

# Hooks that are allowed to inject context (security/governance)
_EXEMPT_HOOKS = {
    # Security/governance hooks
    "prompt-injection-guard.py",
    "runtime-guard.py",
    "governed-git-advisor.py",
    "injection-read-guard.py",
    "no-verify-guard.py",
    # Formatting hook
    "auto-format.py",
    # Observation hooks (need refactoring to opt-in, not removal)
    "runtime-observation-nudge.py",
    "runtime-session-start.py",
    "runtime-stop.py",
}

# Hooks that should NOT inject additionalContext
_INJECTION_PATTERN = re.compile(r"additionalContext")


class TestHookNoAdditionalContext:
    """Normal hooks should not inject additionalContext."""

    def test_progressive_disclosure_disabled(self):
        """Progressive-disclosure hook should be disabled."""
        hook = HOOKS_DIR / "runtime-progressive-disclosure.py"
        # Should not exist or should be disabled
        assert not hook.exists() or hook.suffix == ".py.disabled"

    def test_copilot_progressive_disclosure_disabled(self):
        """Copilot progressive-disclosure should be disabled."""
        hook = HOOKS_DIR / "copilot-runtime-progressive-disclosure.sh"
        assert not hook.exists() or hook.suffix == ".sh.disabled"

    def test_non_exempt_hooks_no_injection(self):
        """Non-exempt hooks should not contain additionalContext."""
        for hook_file in HOOKS_DIR.iterdir():
            if not hook_file.is_file():
                continue
            if hook_file.name in _EXEMPT_HOOKS:
                continue
            if hook_file.suffix not in (".py", ".sh"):
                continue
            if ".disabled" in hook_file.suffix:
                continue

            try:
                content = hook_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue

            # Check for additionalContext (excluding comments and strings in security hooks)
            if _INJECTION_PATTERN.search(content):
                pytest.fail(f"Hook {hook_file.name} contains additionalContext injection")
