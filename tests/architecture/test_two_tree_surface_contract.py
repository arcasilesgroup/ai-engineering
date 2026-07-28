"""The two-tree skill-surface contract (spec-201 D-201-04).

Skill trees collapse from seven to two:

* ``.claude/skills`` — Claude Code, the sole surface whose search paths
  are compiled in and cannot be extended by configuration;
* ``.agents/skills`` — the shared tree every other surface reads
  (Codex, Copilot, OpenCode, Cursor, Antigravity).

Per-surface ``agents/``, ``commands/`` and ``hooks/`` trees are out of
scope and deliberately survive (D-201-22); only ``.codex/agents`` dies,
as a namespace squat Codex never reads (D-201-23).

This module is the canonical assertion that the four redundant trees
stay deleted. Deleting a tree while its generator write site is still
live gets it silently resurrected by the next ``ai-eng dev sync``
(RK-16), and nothing else in the corpus would notice.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATE_PROJECT = _REPO_ROOT / "src" / "ai_engineering" / "templates" / "project"

MIN_SKILL_DIRS = 54
MIN_HANDLER_DIRS = 18

# Trees hard-deleted by spec-201. Any re-appearance means a generator
# write site came back to life — fix the generator, do not re-delete.
DELETED_TREES: tuple[str, ...] = (
    ".codex/skills",
    ".codex/agents",
    ".github/skills",
    ".github/chatmodes",
    ".opencode/skills",
    "src/ai_engineering/templates/project/.codex/skills",
    "src/ai_engineering/templates/project/.codex/agents",
    "src/ai_engineering/templates/project/.github/skills",
    "src/ai_engineering/templates/project/.opencode/skills",
    "src/ai_engineering/templates/project/.cursor/skills",
)

# The two surviving trees, at repo root and in the template payload.
SURVIVING_TREES: tuple[str, ...] = (
    ".claude/skills",
    ".agents/skills",
    "src/ai_engineering/templates/project/.claude/skills",
    "src/ai_engineering/templates/project/.agents/skills",
)


def _skill_dirs(tree: Path) -> list[Path]:
    return sorted(path for path in tree.glob("ai-*") if path.is_dir())


def _handler_dirs(tree: Path) -> list[Path]:
    return sorted(path for path in tree.glob("ai-*/handlers") if path.is_dir())


@pytest.mark.parametrize("relative", DELETED_TREES)
def test_collapsed_tree_is_absent(relative: str) -> None:
    """spec-201 D-201-04/D-201-23: the collapsed trees stay deleted."""
    tree = _REPO_ROOT / relative
    assert not tree.exists(), (
        f"{relative} exists again. A deleted tree whose generator write "
        "site is still live is resurrected by the next `ai-eng dev sync` "
        "(RK-16). Remove the write site in scripts/sync_mirrors/core.py, "
        "then re-run the sync — do not simply delete the tree again."
    )


@pytest.mark.parametrize("relative", SURVIVING_TREES)
def test_surviving_tree_carries_the_full_skill_set(relative: str) -> None:
    """The two surviving trees each hold the complete skill payload."""
    tree = _REPO_ROOT / relative
    assert tree.is_dir(), f"{relative} is missing — it is one of the two canonical skill trees."

    skill_dirs = _skill_dirs(tree)
    assert len(skill_dirs) >= MIN_SKILL_DIRS, (
        f"{relative} holds {len(skill_dirs)} ai-* skill directories, "
        f"expected at least {MIN_SKILL_DIRS}."
    )

    handler_dirs = _handler_dirs(tree)
    assert len(handler_dirs) >= MIN_HANDLER_DIRS, (
        f"{relative} holds {len(handler_dirs)} handlers/ directories, "
        f"expected at least {MIN_HANDLER_DIRS}. /ai-build stops at "
        "preflight when its handler files are missing."
    )


def test_template_payload_has_exactly_two_skill_trees() -> None:
    """No third skill tree creeps back into the installer payload."""
    trees = sorted(
        path.relative_to(_TEMPLATE_PROJECT).as_posix()
        for path in _TEMPLATE_PROJECT.glob("*/skills")
        if path.is_dir()
    )
    assert trees == [".agents/skills", ".claude/skills"], (
        f"Template payload ships skill trees {trees}; spec-201 D-201-04 "
        "allows exactly .agents/skills and .claude/skills."
    )
