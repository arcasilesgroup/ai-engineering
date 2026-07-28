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
    from scripts.sync_mirrors.cursor_target import generate_cursor_agent

    assert callable(generate_cursor_agent)
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


def test_antigravity_skill_generation_smoke(tmp_path: Path) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "---\nname: ai-baz\ndescription: smoke\n---\n\n# Baz\n",
        encoding="utf-8",
    )
    from scripts.sync_mirrors.antigravity_target import generate_antigravity_skill

    out = generate_antigravity_skill("baz", skill)
    assert "ai-baz" in out
