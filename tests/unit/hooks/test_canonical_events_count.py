"""CI guard for canonical hook event count + dead-wiring detection.

Per spec-122-d D-122-27: the `.claude/settings.json` hook registry is
the source of truth for canonical event vocabulary. CLAUDE.md and the
template README must agree on the count, and every wired command must
resolve to a script that exists on disk (no dead wirings).

After spec-122-d audit (2026-05-05): 11 canonical events, 0 dead wirings.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SETTINGS_PATH = REPO_ROOT / ".claude" / "settings.json"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"

# Locked count -- bump this only after auditing the new event in
# settings.json AND updating CLAUDE.md to match. The point of the
# guard is to make drift visible in code review.
EXPECTED_EVENT_COUNT = 11

EXPECTED_EVENT_NAMES = frozenset(
    {
        "UserPromptSubmit",
        "PreToolUse",
        "PostToolUse",
        "PostToolUseFailure",
        "Stop",
        "PreCompact",
        "PostCompact",
        "SessionStart",
        "SubagentStop",
        "Notification",
        "SessionEnd",
    }
)


def _load_settings() -> dict:
    return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))


def test_settings_json_event_count() -> None:
    """`hooks` registry has exactly the documented number of events."""
    cfg = _load_settings()
    hooks = cfg.get("hooks", {})
    assert len(hooks) == EXPECTED_EVENT_COUNT, (
        f"Expected {EXPECTED_EVENT_COUNT} events; got {len(hooks)}. "
        f"Either update settings.json or update EXPECTED_EVENT_COUNT "
        f"in this test (and CLAUDE.md)."
    )


def test_settings_json_event_names_match() -> None:
    """Event names exactly match the canonical set (catches typos)."""
    cfg = _load_settings()
    actual = frozenset(cfg.get("hooks", {}).keys())
    missing = EXPECTED_EVENT_NAMES - actual
    extra = actual - EXPECTED_EVENT_NAMES
    assert not missing, f"Missing canonical events: {sorted(missing)}"
    assert not extra, (
        f"Unknown events: {sorted(extra)}. Add to EXPECTED_EVENT_NAMES + CLAUDE.md if intentional."
    )


def test_no_dead_wirings() -> None:
    """Every hook command resolves to a script that exists on disk."""
    cfg = _load_settings()
    hooks = cfg.get("hooks", {})
    pattern = re.compile(r'CLAUDE_PROJECT_DIR/([^"]+)')
    dead: list[tuple[str, str]] = []
    for event, matchers in hooks.items():
        for matcher in matchers:
            for h in matcher.get("hooks", []):
                cmd = h.get("command", "")
                m = pattern.search(cmd)
                if not m:
                    continue
                rel = m.group(1)
                if not (REPO_ROOT / rel).is_file():
                    dead.append((event, rel))
    assert not dead, (
        f"Dead hook wirings ({len(dead)}): {dead}. Either restore the script or drop the matcher."
    )


def test_claude_md_documents_event_count() -> None:
    """CLAUDE.md states the canonical count -- prevents doc drift."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    assert f"{EXPECTED_EVENT_COUNT} canonical hook events" in text, (
        f"CLAUDE.md must state '{EXPECTED_EVENT_COUNT} canonical hook "
        f"events' (current count). Update Hooks Configuration section."
    )
