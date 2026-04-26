"""Spec-104 D-104-07 contract guards for skill markdown.

Verbosity reduction (Phase 7) cuts duplicated content from three skill files
without removing the contractual sections that the four-IDE mirror system
(Claude Code, GitHub Copilot, Codex, Gemini CLI) and downstream agents rely on.

These tests pin the contract: regardless of how many lines are removed,
- ai-commit/SKILL.md MUST keep `## Process`, `## Integration`, `## Quick Reference`
  and frontmatter `argument-hint`.
- ai-pr/SKILL.md MUST keep the same set.
- ai-pr/handlers/watch.md MUST keep `## Procedure` and `## Escalation rules`.
- None of the three files may smuggle in suppression comments.
- All three files must remain valid YAML-frontmatter markdown documents.

These tests PASS today and MUST continue to PASS after Phase 7 cuts. They are
guards, not RED failures. See spec-104 D-104-07 + R-7.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]

_AI_COMMIT_SKILL = _REPO_ROOT / ".claude" / "skills" / "ai-commit" / "SKILL.md"
_AI_PR_SKILL = _REPO_ROOT / ".claude" / "skills" / "ai-pr" / "SKILL.md"
_WATCH_HANDLER = _REPO_ROOT / ".claude" / "skills" / "ai-pr" / "handlers" / "watch.md"

_ALL_FILES = (_AI_COMMIT_SKILL, _AI_PR_SKILL, _WATCH_HANDLER)

# Suppression patterns the framework forbids (CLAUDE.md Don't #8).
_SUPPRESSION_PATTERNS = (
    "# noqa",
    "# nosec",
    "# type: ignore",
    "# NOSONAR",
)


def _read(path: Path) -> str:
    assert path.is_file(), f"required skill file missing: {path}"
    return path.read_text(encoding="utf-8")


def _has_heading(text: str, heading: str) -> bool:
    """Return True if `heading` appears as a markdown H2 line."""
    pattern = rf"^{re.escape(heading)}\s*$"
    return any(re.match(pattern, line) for line in text.splitlines())


def _frontmatter_block(text: str) -> str | None:
    """Return the raw text between the opening and closing `---` fences, or None."""
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return "\n".join(lines[1:idx])
    return None


def test_ai_commit_skill_has_process_section() -> None:
    """ai-commit/SKILL.md keeps `## Process` heading."""
    text = _read(_AI_COMMIT_SKILL)
    assert _has_heading(text, "## Process"), (
        "ai-commit/SKILL.md must keep `## Process` heading after spec-104 Phase 7 cuts"
    )


def test_ai_commit_skill_has_integration_section() -> None:
    """ai-commit/SKILL.md keeps `## Integration` heading."""
    text = _read(_AI_COMMIT_SKILL)
    assert _has_heading(text, "## Integration"), (
        "ai-commit/SKILL.md must keep `## Integration` heading after spec-104 Phase 7 cuts"
    )


def test_ai_commit_skill_has_quick_reference_section() -> None:
    """ai-commit/SKILL.md keeps `## Quick Reference` heading."""
    text = _read(_AI_COMMIT_SKILL)
    assert _has_heading(text, "## Quick Reference"), (
        "ai-commit/SKILL.md must keep `## Quick Reference` heading after spec-104 Phase 7 cuts"
    )


def test_ai_commit_skill_has_argument_hint_frontmatter() -> None:
    """ai-commit/SKILL.md keeps `argument-hint:` field in frontmatter."""
    text = _read(_AI_COMMIT_SKILL)
    block = _frontmatter_block(text)
    assert block is not None, "ai-commit/SKILL.md must have YAML frontmatter"
    assert re.search(r"^argument-hint\s*:", block, flags=re.MULTILINE), (
        "ai-commit/SKILL.md frontmatter must keep `argument-hint:` field"
    )


def test_ai_pr_skill_has_process_section() -> None:
    """ai-pr/SKILL.md keeps `## Process` heading."""
    text = _read(_AI_PR_SKILL)
    assert _has_heading(text, "## Process"), (
        "ai-pr/SKILL.md must keep `## Process` heading after spec-104 Phase 7 cuts"
    )


def test_ai_pr_skill_has_integration_section() -> None:
    """ai-pr/SKILL.md keeps `## Integration` heading."""
    text = _read(_AI_PR_SKILL)
    assert _has_heading(text, "## Integration"), (
        "ai-pr/SKILL.md must keep `## Integration` heading after spec-104 Phase 7 cuts"
    )


def test_ai_pr_skill_has_quick_reference_section() -> None:
    """ai-pr/SKILL.md keeps `## Quick Reference` heading."""
    text = _read(_AI_PR_SKILL)
    assert _has_heading(text, "## Quick Reference"), (
        "ai-pr/SKILL.md must keep `## Quick Reference` heading after spec-104 Phase 7 cuts"
    )


def test_ai_pr_skill_has_argument_hint_frontmatter() -> None:
    """ai-pr/SKILL.md keeps `argument-hint:` field in frontmatter."""
    text = _read(_AI_PR_SKILL)
    block = _frontmatter_block(text)
    assert block is not None, "ai-pr/SKILL.md must have YAML frontmatter"
    assert re.search(r"^argument-hint\s*:", block, flags=re.MULTILINE), (
        "ai-pr/SKILL.md frontmatter must keep `argument-hint:` field"
    )


def test_watch_md_has_procedure_section() -> None:
    """ai-pr/handlers/watch.md keeps `## Procedure` heading."""
    text = _read(_WATCH_HANDLER)
    assert _has_heading(text, "## Procedure"), (
        "ai-pr/handlers/watch.md must keep `## Procedure` heading after spec-104 Phase 7 cuts"
    )


def test_watch_md_has_escalation_rules_section() -> None:
    """ai-pr/handlers/watch.md keeps `## Escalation rules` heading."""
    text = _read(_WATCH_HANDLER)
    assert _has_heading(text, "## Escalation rules"), (
        "ai-pr/handlers/watch.md must keep `## Escalation rules` heading "
        "after spec-104 Phase 7 cuts"
    )


@pytest.mark.parametrize(
    "path",
    _ALL_FILES,
    ids=lambda p: p.relative_to(_REPO_ROOT).as_posix(),
)
def test_all_skills_no_suppression_comments(path: Path) -> None:
    """No skill file may smuggle in linter/scanner suppression comments.

    Aligned with CLAUDE.md Don't #8: fix the code, do not bypass the gate.
    """
    text = _read(path)
    found: list[str] = []
    for pattern in _SUPPRESSION_PATTERNS:
        if pattern in text:
            found.append(pattern)
    assert not found, (
        f"{path.relative_to(_REPO_ROOT).as_posix()} contains suppression "
        f"comment(s): {found}. Remove them and fix the underlying issue."
    )


@pytest.mark.parametrize(
    "path",
    _ALL_FILES,
    ids=lambda p: p.relative_to(_REPO_ROOT).as_posix(),
)
def test_all_skills_have_yaml_frontmatter(path: Path) -> None:
    """Every spec-104-managed skill file must be delimited by `---` frontmatter fences.

    Note: handlers/watch.md historically does not declare frontmatter (it is a
    procedure document, not a skill entry point). For files without an opening
    `---`, this guard is satisfied; for files that DO declare frontmatter, both
    the opening and closing `---` fences must be present.
    """
    text = _read(path)
    if not text.startswith("---"):
        # Procedure documents (e.g., handlers/watch.md) without frontmatter
        # are valid; the guard only enforces well-formed delimiters when present.
        return
    block = _frontmatter_block(text)
    assert block is not None, (
        f"{path.relative_to(_REPO_ROOT).as_posix()} opens with `---` but is "
        "missing the closing `---` fence; frontmatter must be properly delimited."
    )
