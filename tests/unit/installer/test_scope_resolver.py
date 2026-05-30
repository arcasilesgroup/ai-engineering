"""Unit tests for the scope-aware destination resolver (spec sub-003, D9/D10).

The resolver maps ``(surface, scope, target, relative_dest)`` to the absolute
destination path. Local scope preserves today's behavior (everything under the
repo root); global scope remaps each surface's home-capable destination per the
D9 per-surface map. Cursor and Copilot have no home destination and return a
:class:`GuidanceSentinel` so install can print wire-up steps instead of writing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer.scope import (
    GLOBAL,
    LOCAL,
    GuidanceSentinel,
    brain_root,
    dest,
)


class TestBrainRoot:
    """spec-156 D-156-04: one helper for the global/local brain root idiom."""

    def test_global_brain_root_is_home(self, home: Path, target: Path) -> None:
        assert brain_root(GLOBAL, target) == home

    def test_local_brain_root_is_target(self, home: Path, target: Path) -> None:
        assert brain_root(LOCAL, target) == target


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Monkeypatch HOME / Path.home() to a tmp dir for deterministic global roots."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: fake_home))
    return fake_home


@pytest.fixture
def target(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


# ---------------------------------------------------------------------------
# Local scope -- unchanged repo-rooted behavior
# ---------------------------------------------------------------------------


class TestLocalScope:
    @pytest.mark.parametrize(
        ("surface", "rel"),
        [
            ("claude-code", ".claude/skills/ai-build/SKILL.md"),
            ("claude-code", "CLAUDE.md"),
            ("codex", "AGENTS.md"),
            ("opencode", "AGENTS.md"),
            ("antigravity", "AGENTS.md"),
            ("cursor", ".cursor/rules.md"),
            ("github-copilot", ".github/copilot-instructions.md"),
            ("brain", ".ai-engineering/manifest.yml"),
        ],
    )
    def test_local_is_repo_rooted(self, surface: str, rel: str, target: Path) -> None:
        resolved = dest(surface, LOCAL, target, rel)
        assert resolved == target / rel


# ---------------------------------------------------------------------------
# Global scope -- per-surface home destinations (D9)
# ---------------------------------------------------------------------------


class TestGlobalScope:
    def test_brain_to_home_ai_engineering(self, home: Path, target: Path) -> None:
        resolved = dest("brain", GLOBAL, target, ".ai-engineering/manifest.yml")
        assert resolved == home / ".ai-engineering" / "manifest.yml"

    def test_claude_code_to_home_claude(self, home: Path, target: Path) -> None:
        resolved = dest("claude-code", GLOBAL, target, ".claude/skills/ai-build/SKILL.md")
        assert resolved == home / ".claude" / "skills" / "ai-build" / "SKILL.md"

    def test_claude_code_instruction_file_to_home(self, home: Path, target: Path) -> None:
        resolved = dest("claude-code", GLOBAL, target, "CLAUDE.md")
        assert resolved == home / ".claude" / "CLAUDE.md"

    def test_codex_agents_to_home_codex(self, home: Path, target: Path) -> None:
        resolved = dest("codex", GLOBAL, target, "AGENTS.md")
        assert resolved == home / ".codex" / "AGENTS.md"

    def test_opencode_agents_to_config_opencode(self, home: Path, target: Path) -> None:
        resolved = dest("opencode", GLOBAL, target, "AGENTS.md")
        assert resolved == home / ".config" / "opencode" / "AGENTS.md"

    def test_opencode_tree_to_config_opencode(self, home: Path, target: Path) -> None:
        resolved = dest("opencode", GLOBAL, target, ".opencode/agents/x.md")
        assert resolved == home / ".config" / "opencode" / "agents" / "x.md"

    def test_antigravity_agents_to_home_gemini(self, home: Path, target: Path) -> None:
        resolved = dest("antigravity", GLOBAL, target, "AGENTS.md")
        assert resolved == home / ".gemini" / "AGENTS.md"

    def test_antigravity_never_writes_gemini_md(self, home: Path, target: Path) -> None:
        """R6: the Antigravity home dir must never collide with the retired Gemini CLI."""
        resolved = dest("antigravity", GLOBAL, target, "AGENTS.md")
        assert isinstance(resolved, Path)
        assert resolved.name != "GEMINI.md"
        assert resolved.parent == home / ".gemini"


# ---------------------------------------------------------------------------
# Cursor + Copilot -- no home destination, emit guidance (D9 / OQ1)
# ---------------------------------------------------------------------------


class TestGuidanceSurfaces:
    @pytest.mark.parametrize("surface", ["cursor", "github-copilot"])
    def test_global_returns_guidance_sentinel(self, surface: str, home: Path, target: Path) -> None:
        resolved = dest(surface, GLOBAL, target, ".cursor/rules.md")
        assert isinstance(resolved, GuidanceSentinel)
        assert resolved.surface == surface
        # The sentinel must carry human-facing wire-up guidance.
        assert resolved.message
        assert resolved.steps

    def test_cursor_and_copilot_local_still_write(self, home: Path, target: Path) -> None:
        """Local scope for guidance surfaces is unchanged (repo-rooted)."""
        cursor = dest("cursor", LOCAL, target, ".cursor/rules.md")
        copilot = dest("github-copilot", LOCAL, target, ".github/copilot-instructions.md")
        assert cursor == target / ".cursor" / "rules.md"
        assert copilot == target / ".github" / "copilot-instructions.md"
