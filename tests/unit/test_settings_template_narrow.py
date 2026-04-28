"""Unit tests for spec-107 G-2: narrow settings.json template (D-107-02).

Pure structural assertions on the shipped template — no I/O beyond reading
the template file. Confirms the `permissions.allow` list ships as the
canonical narrow 13-entry set and that `permissions.deny` keeps every
canonical guard rule intact (CLAUDE.md Don't #7).

Companion integration test in
``tests/integration/test_settings_template_narrow.py`` covers the same
contract; this unit-level test runs in milliseconds and gates regressions
without touching the doctor harness.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = (
    REPO_ROOT / "src" / "ai_engineering" / "templates" / "project" / ".claude" / "settings.json"
)

CANONICAL_ALLOW = (
    "Read",
    "Write",
    "Edit",
    "MultiEdit",
    "Bash",
    "Agent",
    "Glob",
    "Grep",
    "Skill",
    "TaskCreate",
    "TaskUpdate",
    "mcp__context7__*",
    "mcp__notebooklm-mcp__*",
)

REQUIRED_DENY_SUBSTRINGS = (
    "rm -rf",
    "git push --force",
    "git push -f",
    "git reset --hard",
    "--no-verify",
)


@pytest.fixture(scope="module")
def settings_payload() -> dict:
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_allow_is_list_not_wildcard(settings_payload: dict) -> None:
    """`permissions.allow` must be a list and must not contain ``"*"``."""
    allow = settings_payload["permissions"]["allow"]
    assert isinstance(allow, list), f"allow must be a list, got {type(allow).__name__}"
    assert "*" not in allow, (
        f"narrow template still contains the wildcard sentinel; allow={allow!r}"
    )


@pytest.mark.unit
def test_allow_has_canonical_thirteen_entries(settings_payload: dict) -> None:
    """All 13 canonical narrow allow entries must be present."""
    allow = set(settings_payload["permissions"]["allow"])
    for entry in CANONICAL_ALLOW:
        assert entry in allow, f"canonical allow entry {entry!r} missing from narrow template"
    assert len(allow) == len(CANONICAL_ALLOW), (
        f"narrow template drift: expected {len(CANONICAL_ALLOW)} entries, got {sorted(allow)!r}"
    )


@pytest.mark.unit
def test_deny_rules_preserved(settings_payload: dict) -> None:
    """Every canonical deny substring must survive the narrow-template change.

    CLAUDE.md Don't #7: never disable or modify `.claude/settings.json`
    deny rules. spec-107 narrows allow only — deny stays intact.
    """
    deny = settings_payload["permissions"]["deny"]
    assert isinstance(deny, list)
    assert len(deny) >= 5, f"deny array suspiciously short: {deny!r}"
    for required in REQUIRED_DENY_SUBSTRINGS:
        assert any(required in entry for entry in deny), (
            f"deny rule containing {required!r} missing — narrow template "
            "must NEVER weaken existing deny protections (CLAUDE.md Don't #7)"
        )


@pytest.mark.unit
def test_hooks_block_intact(settings_payload: dict) -> None:
    """Hooks block must remain present and untouched by the narrow change."""
    hooks = settings_payload.get("hooks", {})
    assert isinstance(hooks, dict)
    for required_event in ("UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop"):
        assert required_event in hooks, (
            f"hooks.{required_event} missing — narrow template must not regress hook wiring"
        )
