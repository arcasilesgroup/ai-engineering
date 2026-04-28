"""Integration tests for spec-107 G-2 — narrow settings.json template.

Spec-107 D-107-02 requires that
``src/ai_engineering/templates/.claude/settings.json`` ships with an
explicit narrow ``permissions.allow`` list (Read, Write, Edit,
MultiEdit, Bash, Agent, Glob, Grep, Skill, TaskCreate, TaskUpdate,
mcp__context7__*, mcp__notebooklm-mcp__*) instead of the over-broad
``["*"]`` wildcard. Existing project settings.json files MUST NOT be
modified by ``ai-eng install`` / ``ai-eng update`` (NG-1, decision Q3-C).

GREEN as of Phase 2 (T-2.1 / T-2.7) — the template ships narrow and
this test guards against regressions.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = (
    REPO_ROOT / "src" / "ai_engineering" / "templates" / "project" / ".claude" / "settings.json"
)

# Canonical narrow allow list per D-107-02.
EXPECTED_ALLOW = frozenset(
    {
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
    }
)


def test_template_no_wildcard_allow() -> None:
    """G-2: template must NOT ship with ``["*"]`` allow."""
    payload = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    allow = payload.get("permissions", {}).get("allow", [])
    assert "*" not in allow, (
        "settings.json template still ships with wildcard allow — D-107-02 "
        f"requires explicit narrow list. Current allow: {allow!r}"
    )


def test_template_ships_canonical_narrow_list() -> None:
    """G-2: template ``allow`` list must be the canonical 13-entry set."""
    payload = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    allow = frozenset(payload.get("permissions", {}).get("allow", []))
    missing = EXPECTED_ALLOW - allow
    extra = allow - EXPECTED_ALLOW
    assert not missing, f"Template missing canonical allow entries: {sorted(missing)!r}"
    assert not extra, f"Template has unexpected allow entries (drift): {sorted(extra)!r}"


def test_template_preserves_existing_deny_rules() -> None:
    """G-2 + CLAUDE.md Don't #7: deny rules must remain intact."""
    payload = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    deny = payload.get("permissions", {}).get("deny", [])
    # The narrow-template change must not delete deny rules. Confirm at
    # least the canonical no-verify and force-push protections survive.
    required_deny_substrings = (
        "--no-verify",
        "git push --force",
        "rm -rf",
    )
    for required in required_deny_substrings:
        assert any(required in entry for entry in deny), (
            f"deny rule containing {required!r} missing — narrow template "
            "must NEVER weaken existing deny protections (CLAUDE.md Don't #7)"
        )
