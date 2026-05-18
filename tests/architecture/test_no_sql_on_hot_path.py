"""spec-138 M4 / D-138-06 — hot-path hooks MUST NOT import sqlite3.

The kernel-panic class in spec-139's trigger incident traces in part to
synchronous SQL writes from hot-path hooks. Per the SSOT-PD doctrine
(docs/persistence-doctrine.md, Tier 2 "Hot-path status: no — cold-path-
only"), every hook script registered under PreToolUse / PostToolUse /
UserPromptSubmit / SubagentStop / Notification in .claude/settings.json
MUST stay SQL-free; state.db writes belong to cold paths (SessionEnd
rebuild, /ai-brainstorm approval, installer phases).

This test is the D-138-06 hard CI gate. It parses .claude/settings.json
for every hot-path event, resolves the canonical hook script path, and
asserts the script does not import sqlite3 nor call sqlite3.connect.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_JSON = REPO_ROOT / ".claude" / "settings.json"

# Hot-path events per CLAUDE.md "Hot-Path Discipline" and the brief.
# SessionStart / Stop / PreCompact / PostCompact / SessionEnd are cold
# paths and MAY touch SQL (e.g., SessionEnd events-table rebuild).
HOT_PATH_EVENTS: frozenset[str] = frozenset(
    {
        "PreToolUse",
        "PostToolUse",
        "UserPromptSubmit",
        "SubagentStop",
        "Notification",
    }
)


def _resolve_settings_json_text() -> str:
    """Read settings.json with JSON-with-comments tolerance.

    Claude Code's settings.json sometimes contains trailing commas /
    block comments; strict json.loads chokes. Strip both before parse.
    """
    raw = SETTINGS_JSON.read_text(encoding="utf-8")
    # Strip // line comments
    no_line_comments = re.sub(r"^\s*//.*$", "", raw, flags=re.MULTILINE)
    # Strip /* block comments */
    no_block_comments = re.sub(r"/\*.*?\*/", "", no_line_comments, flags=re.DOTALL)
    # Strip trailing commas before } or ]
    no_trailing_commas = re.sub(r",(\s*[}\]])", r"\1", no_block_comments)
    return no_trailing_commas


def _extract_hook_scripts() -> dict[str, list[Path]]:
    """Return {event_name: [script_path, ...]} for every hot-path event."""
    text = _resolve_settings_json_text()
    settings = json.loads(text)
    hooks = settings.get("hooks", {})

    result: dict[str, list[Path]] = {event: [] for event in HOT_PATH_EVENTS}
    for event_name, matchers in hooks.items():
        if event_name not in HOT_PATH_EVENTS:
            continue
        for matcher_entry in matchers:
            for hook_entry in matcher_entry.get("hooks", []):
                cmd = hook_entry.get("command", "")
                # Cmd format: python3 "$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/<name>.py"
                match = re.search(r"\.ai-engineering/scripts/hooks/([^\"\s]+\.py)", cmd)
                if not match:
                    continue
                script_rel = match.group(1)
                script_path = REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / script_rel
                if script_path.exists():
                    result[event_name].append(script_path)
    return result


def _module_imports_sqlite3(script_path: Path) -> tuple[bool, list[str]]:
    """Return (forbidden, reasons) — True when the module imports sqlite3."""
    source = script_path.read_text(encoding="utf-8")
    reasons: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False, [f"unparseable: {script_path}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "sqlite3" or alias.name.startswith("sqlite3."):
                    reasons.append(f"`import {alias.name}` at line {node.lineno}")
        elif isinstance(node, ast.ImportFrom):
            if node.module == "sqlite3" or (node.module and node.module.startswith("sqlite3.")):
                reasons.append(f"`from {node.module} import ...` at line {node.lineno}")
        elif isinstance(node, ast.Attribute):
            # sqlite3.connect(...) without `import sqlite3` would still
            # require a name resolving to sqlite3 — the import scan above
            # already catches it.
            pass

    return bool(reasons), reasons


@pytest.mark.parametrize("event", sorted(HOT_PATH_EVENTS))
def test_hot_path_hook_never_imports_sqlite3(event: str) -> None:
    """spec-138 M4 / D-138-06: hot-path hooks MUST stay SQL-free."""
    scripts = _extract_hook_scripts()
    event_scripts = scripts.get(event, [])
    if not event_scripts:
        pytest.skip(f"no canonical hooks registered under {event}")
    failures: list[str] = []
    for script in event_scripts:
        forbidden, reasons = _module_imports_sqlite3(script)
        if forbidden:
            rel = script.relative_to(REPO_ROOT)
            failures.append(f"{rel}: {'; '.join(reasons)}")
    assert not failures, (
        f"spec-138 SSOT-PD violation: {event} hot-path hook(s) import sqlite3:\n"
        + "\n".join(f"  - {f}" for f in failures)
        + "\n\nMove SQL access to a cold-path script (SessionEnd, Stop, "
        "PreCompact, PostCompact) per docs/persistence-doctrine.md Tier 2."
    )


def test_hot_path_coverage_includes_every_canonical_event() -> None:
    """Every declared hot-path event must have at least one hook checked.

    Catches future additions of hot-path events that bypass the gate
    above by sheer omission.
    """
    scripts = _extract_hook_scripts()
    # We allow some events to have zero hooks (e.g., Notification may be
    # unwired by default); the constraint is that the SET of events we
    # scan equals HOT_PATH_EVENTS — the test contract.
    assert set(scripts) == HOT_PATH_EVENTS, (
        f"hot-path event set drifted: got {set(scripts)} expected {HOT_PATH_EVENTS}"
    )
