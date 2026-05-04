"""Pin: Codex PreToolUse hooks must cover file-write tools, not just Bash.

P1.1 from the 2026-05-04 harness audit: Codex hooks were configured with
``"matcher": "Bash"`` only, leaving ``edit``, ``patch``, ``apply_patch``
and ``write`` tool invocations unguarded. The injection-guard, strategic-
compact, instinct-observe, and codex-hook-bridge PreToolUse hooks all
have to fire on those tools to keep parity with Claude Code (which
matches the broader tool surface natively).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CODEX_HOOKS_PATH = REPO / ".codex" / "hooks.json"

# Tools that MUST be covered by every PreToolUse hook in Codex.
_REQUIRED_PRE_TOOL_MATCHERS = {"Bash", "edit", "patch", "apply_patch"}


@pytest.fixture(scope="module")
def codex_config() -> dict:
    return json.loads(CODEX_HOOKS_PATH.read_text(encoding="utf-8"))


def _matcher_set(matcher: str) -> set[str]:
    """Parse a Codex hook matcher (regex-style ``A|B|C``) into a set."""
    return {token.strip() for token in matcher.split("|") if token.strip()}


def test_pre_tool_use_covers_required_matchers(codex_config: dict) -> None:
    """Every PreToolUse hook must match Bash + the file-write tool family."""
    pre_tool_entries = codex_config["hooks"].get("PreToolUse", [])
    assert pre_tool_entries, "Codex PreToolUse list is empty — no guards wired"

    for entry in pre_tool_entries:
        matcher = entry.get("matcher", "")
        actual = _matcher_set(matcher)
        missing = _REQUIRED_PRE_TOOL_MATCHERS - actual
        hook_names = [h["command"].split("/")[-1].split()[0] for h in entry.get("hooks", [])]
        assert not missing, (
            f"PreToolUse matcher {matcher!r} is missing {sorted(missing)}; "
            f"hooks affected: {hook_names}. Update .codex/hooks.json."
        )


def test_required_pre_tool_hooks_present(codex_config: dict) -> None:
    """The four guards (codex-hook-bridge, prompt-injection-guard,
    strategic-compact, instinct-observe) must all be wired under PreToolUse."""
    expected = {
        "codex-hook-bridge.py",
        "prompt-injection-guard.py",
        "strategic-compact.py",
        "instinct-observe.py",
    }
    seen: set[str] = set()
    for entry in codex_config["hooks"].get("PreToolUse", []):
        for hook in entry.get("hooks", []):
            cmd = hook["command"]
            for name in expected:
                if name in cmd:
                    seen.add(name)
    missing = expected - seen
    assert not missing, f"PreToolUse missing canonical guards: {sorted(missing)}"
