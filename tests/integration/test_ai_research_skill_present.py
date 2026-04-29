"""RED-phase test for spec-111 T-1.1 — /ai-research skill + IDE mirrors presence.

Spec acceptance:
    The ``/ai-research`` multi-tier research skill (local → MCPs gratis →
    web → NotebookLM persistent) must ship as a Claude Code SKILL.md
    backed by 7 handler files, plus full IDE-adapted mirrors for Codex,
    Gemini CLI, and GitHub Copilot.

Verifiable by ``tests/integration/test_ai_research_skill_present.py::
test_skill_and_mirrors_exist`` which asserts:

1. ``.claude/skills/ai-research/SKILL.md`` exists at repo root.
2. All 7 handler files exist under ``.claude/skills/ai-research/handlers/``:
   ``classify-query.md``, ``tier0-local.md``, ``tier1-free-mcps.md``,
   ``tier2-web.md``, ``tier3-notebooklm.md``,
   ``synthesize-with-citations.md``, ``persist-artifact.md``.
3. Mirror SKILL.md exists for each non-Claude IDE surface:
   ``.codex/skills/ai-research/SKILL.md``,
   ``.gemini/skills/ai-research/SKILL.md``,
   ``.github/skills/ai-research/SKILL.md``.

Status: RED. None of these files exist yet. T-1.2 creates the canonical
SKILL.md, T-1.3 creates the 7 handler files, and T-1.4 syncs the IDE
mirrors via the standard sync-mirrors tool. This test deliberately fails
now to drive those GREEN tasks.
"""

from __future__ import annotations

from pathlib import Path

# Repo root: tests/integration/<this file> → up 3 levels.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

CLAUDE_SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "ai-research"
CLAUDE_SKILL_FILE = CLAUDE_SKILL_DIR / "SKILL.md"
HANDLERS_DIR = CLAUDE_SKILL_DIR / "handlers"

EXPECTED_HANDLER_FILES = (
    "classify-query.md",
    "tier0-local.md",
    "tier1-free-mcps.md",
    "tier2-web.md",
    "tier3-notebooklm.md",
    "synthesize-with-citations.md",
    "persist-artifact.md",
)

MIRROR_SKILL_FILES = (
    REPO_ROOT / ".codex" / "skills" / "ai-research" / "SKILL.md",
    REPO_ROOT / ".gemini" / "skills" / "ai-research" / "SKILL.md",
    REPO_ROOT / ".github" / "skills" / "ai-research" / "SKILL.md",
)


def test_skill_and_mirrors_exist() -> None:
    """Canonical /ai-research SKILL.md, 7 handlers, and 3 IDE mirrors are present.

    Asserts:
    1. ``.claude/skills/ai-research/SKILL.md`` is a regular file at the
       repository root.
    2. Each of the 7 expected handler files exists under
       ``.claude/skills/ai-research/handlers/``.
    3. Mirror ``SKILL.md`` exists at ``.codex/skills/ai-research/``,
       ``.gemini/skills/ai-research/``, and ``.github/skills/ai-research/``.
    """
    assert CLAUDE_SKILL_FILE.is_file(), (
        f"Canonical /ai-research SKILL.md must exist at: {CLAUDE_SKILL_FILE}. "
        "Generate it per spec-111 T-1.2."
    )

    missing_handlers = [
        name for name in EXPECTED_HANDLER_FILES if not (HANDLERS_DIR / name).is_file()
    ]
    assert not missing_handlers, (
        f"/ai-research must ship all 7 handler files under {HANDLERS_DIR}. "
        f"Missing: {missing_handlers}. Expected: {list(EXPECTED_HANDLER_FILES)}. "
        "Generate them per spec-111 T-1.3."
    )

    missing_mirrors = [str(path) for path in MIRROR_SKILL_FILES if not path.is_file()]
    assert not missing_mirrors, (
        "Full IDE-adapted mirrors of /ai-research SKILL.md must exist for "
        "Codex, Gemini CLI, and GitHub Copilot. "
        f"Missing: {missing_mirrors}. "
        "Run sync-mirrors per spec-111 T-1.4."
    )
