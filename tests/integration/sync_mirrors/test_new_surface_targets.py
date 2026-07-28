"""Tests for the per-Surface mirror targets (spec-133 D-133-06).

spec-201 D-201-04 collapsed the skill trees to two, so the OpenCode
and Cursor skill generators were deleted with their trees; both
surfaces now read the shared ``.agents/skills`` payload. Their
agent (and, for OpenCode, command) generators survive per D-201-22.
"""

from __future__ import annotations

from pathlib import Path


def test_opencode_target_module_imports() -> None:
    from scripts.sync_mirrors import opencode_target
    from scripts.sync_mirrors.opencode_target import (
        generate_opencode_agent,
        generate_opencode_command,
    )

    assert callable(generate_opencode_agent)
    assert callable(generate_opencode_command)
    assert not hasattr(opencode_target, "generate_opencode_skill"), (
        "spec-201 D-201-04 deleted the OpenCode skill generator with "
        ".opencode/skills; OpenCode reads .agents/skills now."
    )


def test_cursor_target_module_imports() -> None:
    from scripts.sync_mirrors import cursor_target
    from scripts.sync_mirrors.cursor_target import (
        generate_cursor_agent,
        generate_cursor_hooks_json,
    )

    assert callable(generate_cursor_agent)
    assert callable(generate_cursor_hooks_json)
    assert not hasattr(cursor_target, "generate_cursor_skill"), (
        "spec-201 D-201-04 deleted the Cursor skill generator with "
        ".cursor/skills; Cursor reads .agents/skills now."
    )


def test_antigravity_target_module_imports() -> None:
    from scripts.sync_mirrors.antigravity_target import (
        generate_antigravity_agent,
        generate_antigravity_skill,
    )

    assert callable(generate_antigravity_skill)
    assert callable(generate_antigravity_agent)


def test_opencode_command_wraps_skill_with_description(tmp_path: Path) -> None:
    """spec-128 Wave 5: command body must reference the skill + carry description."""
    skill_dir = tmp_path / "ai-foo"
    skill_dir.mkdir()
    skill = skill_dir / "SKILL.md"
    skill.write_text(
        "---\nname: ai-foo\ndescription: forces interrogation BEFORE code\n---\n\n# Foo\n",
        encoding="utf-8",
    )
    from scripts.sync_mirrors.opencode_target import generate_opencode_command

    out = generate_opencode_command("foo", skill)
    assert out.startswith("---\n"), "Frontmatter must lead the command file"
    assert "description: 'forces interrogation BEFORE code'" in out
    assert "`ai-foo`" in out, "Body must reference the skill name for lazy-load"
    assert "$ARGUMENTS" in out, "Body must forward user args verbatim"
    assert "mirror_family: opencode-commands" in out


def test_opencode_command_handles_malformed_skill_frontmatter(tmp_path: Path) -> None:
    """Defensive: empty / broken frontmatter falls back to generic stub."""
    skill_dir = tmp_path / "ai-broken"
    skill_dir.mkdir()
    skill = skill_dir / "SKILL.md"
    skill.write_text("no frontmatter here\n", encoding="utf-8")
    from scripts.sync_mirrors.opencode_target import generate_opencode_command

    out = generate_opencode_command("broken", skill)
    assert "Invoke the ai-broken skill" in out


def test_opencode_plugin_entry_is_generated_not_handwritten() -> None:
    """spec-201 sub-005 T-5.7: `.opencode/plugin/` is a generated dual-write."""
    from scripts.sync_mirrors.core import OPENCODE_PLUGIN, TPL_OPENCODE_PLUGIN
    from scripts.sync_mirrors.opencode_target import generate_opencode_plugin

    expected = generate_opencode_plugin()
    for target in (
        OPENCODE_PLUGIN / "ai-engineering.ts",
        TPL_OPENCODE_PLUGIN / "ai-engineering.ts",
    ):
        assert target.is_file(), f"missing generated plugin entry: {target}"
        assert target.read_text(encoding="utf-8") == expected


def test_cursor_hooks_json_is_generated_and_schema_valid() -> None:
    """spec-201 D-201-17: the config Cursor loads, dual-written and valid.

    Cursor 3.12.17's `uWo` validator requires a positive-integer `version` and
    an object `hooks` keyed by members of its 21-step enum; the deny-capable
    subset is `sWo`.
    """
    import json

    from scripts.sync_mirrors.core import CURSOR_HOOKS, TPL_CURSOR_HOOKS
    from scripts.sync_mirrors.cursor_target import generate_cursor_hooks_json

    expected = generate_cursor_hooks_json()
    for target in (CURSOR_HOOKS, TPL_CURSOR_HOOKS):
        assert target.is_file(), f"missing generated cursor hook config: {target}"
        assert target.read_text(encoding="utf-8") == expected

    config = json.loads(expected)
    assert isinstance(config["version"], int) and config["version"] >= 1
    deny_capable = {
        "beforeShellExecution",
        "beforeMCPExecution",
        "beforeReadFile",
        "beforeTabFileRead",
        "subagentStart",
        "preToolUse",
    }
    assert "beforeShellExecution" in config["hooks"], "the deny lane is the point"
    assert set(config["hooks"]) <= deny_capable | {
        "afterShellExecution",
        "afterMCPExecution",
        "afterFileEdit",
    }
    for entries in config["hooks"].values():
        for entry in entries:
            # Cursor's `pff` fails OPEN on an invalid regex, so match-all only.
            assert entry["matcher"] == ""
            assert entry["command"].endswith("cursor-hook-bridge.py")


def test_hook_script_surface_mirrors_typescript_twins() -> None:
    """spec-201 sub-005 T-5.4: every canonical `.ts` hook has a managed twin.

    Surface 10 mirrored `*.py` only, so `opencode-hook-bridge.ts` was a
    hand-copied twin that `dev sync --check` could never see drift on.
    """
    from scripts.sync_mirrors.core import _HOOK_SCRIPT_PATTERNS, ROOT, TPL_HOOK_SCRIPTS

    assert "*.ts" in _HOOK_SCRIPT_PATTERNS

    src_root = ROOT / ".ai-engineering" / "scripts" / "hooks"
    ts_files = sorted(src_root.rglob("*.ts"))
    assert ts_files, "expected at least one canonical TypeScript hook script"
    for src in ts_files:
        twin = TPL_HOOK_SCRIPTS / src.relative_to(src_root)
        assert twin.is_file(), f"{src} has no installer-template twin at {twin}"
        assert twin.read_bytes() == src.read_bytes(), f"{twin} drifted from {src}"


def test_antigravity_skill_generation_smoke(tmp_path: Path) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "---\nname: ai-baz\ndescription: smoke\n---\n\n# Baz\n",
        encoding="utf-8",
    )
    from scripts.sync_mirrors.antigravity_target import generate_antigravity_skill

    out = generate_antigravity_skill("baz", skill)
    assert "ai-baz" in out
