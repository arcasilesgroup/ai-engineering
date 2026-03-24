"""Verify every handlers/*.md reference in SKILL.md routing tables exists on disk.

Skills use handler files for sub-command dispatch. Each SKILL.md may reference
handlers via markdown table rows or prose mentions. This test parses those
references and asserts every referenced handler file exists relative to the
SKILL.md that declares it.

Covers all four IDE mirrors:
  - .claude/skills/ai-*/SKILL.md
  - .agents/skills/*/SKILL.md
  - src/ai_engineering/templates/project/.claude/skills/ai-*/SKILL.md
  - src/ai_engineering/templates/project/.agents/skills/*/SKILL.md
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]

_SKILL_ROOTS: list[tuple[str, Path]] = [
    ("root/.claude", _REPO_ROOT / ".claude" / "skills"),
    ("root/.agents", _REPO_ROOT / ".agents" / "skills"),
    (
        "template/.claude",
        _REPO_ROOT / "src" / "ai_engineering" / "templates" / "project" / ".claude" / "skills",
    ),
    (
        "template/.agents",
        _REPO_ROOT / "src" / "ai_engineering" / "templates" / "project" / ".agents" / "skills",
    ),
]

# Matches both backtick-wrapped and bare handler references:
#   `handlers/foo.md`   handlers/foo.md
_HANDLER_REF_RE = re.compile(r"`?handlers/[\w-]+\.md`?")


def _find_handler_refs(text: str) -> list[str]:
    """Extract all handlers/*.md references from SKILL.md content.

    Returns de-duplicated, sorted list of relative paths like 'handlers/foo.md'.
    """
    refs: set[str] = set()
    for match in _HANDLER_REF_RE.findall(text):
        # Strip surrounding backticks if present.
        refs.add(match.strip("`"))
    return sorted(refs)


def _collect_skill_handler_pairs() -> list[tuple[str, Path, str]]:
    """Scan all SKILL.md files for handler references.

    Returns list of (test_id, skill_md_path, handler_relative_path) tuples.
    Each tuple represents one assertion: the handler file must exist.
    """
    pairs: list[tuple[str, Path, str]] = []
    for label, skills_dir in _SKILL_ROOTS:
        if not skills_dir.is_dir():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            skill_md = skill_dir / "SKILL.md"
            if not skill_dir.is_dir() or not skill_md.exists():
                continue
            text = skill_md.read_text(encoding="utf-8")
            for ref in _find_handler_refs(text):
                test_id = f"{label}/{skill_dir.name}/{ref}"
                pairs.append((test_id, skill_md, ref))
    return pairs


_HANDLER_PAIRS = _collect_skill_handler_pairs()


@pytest.mark.parametrize(
    ("_id", "skill_md", "handler_ref"),
    _HANDLER_PAIRS,
    ids=[p[0] for p in _HANDLER_PAIRS],
)
def test_handler_file_exists(_id: str, skill_md: Path, handler_ref: str) -> None:
    """Every handler referenced in a SKILL.md routing table must exist on disk."""
    handler_path = skill_md.parent / handler_ref
    assert handler_path.is_file(), (
        f"{skill_md.relative_to(_REPO_ROOT)} references '{handler_ref}' "
        f"but {handler_path.relative_to(_REPO_ROOT)} does not exist"
    )


def test_at_least_one_handler_pair_found() -> None:
    """Sanity check: the collector must find handler references.

    If this fails, either no SKILL.md has handler references (unlikely)
    or the regex/path scanning is broken.
    """
    assert len(_HANDLER_PAIRS) > 0, (
        "No handler references found in any SKILL.md -- "
        "check _SKILL_ROOTS paths and _HANDLER_REF_RE pattern"
    )


def test_all_skill_roots_contribute() -> None:
    """Every configured skill root that exists on disk must contribute at least one pair.

    Ensures we are not silently skipping an entire mirror tree.
    """
    existing_roots = {label for label, path in _SKILL_ROOTS if path.is_dir()}
    contributing_roots = {"/".join(test_id.split("/", 3)[:2]) for test_id, _, _ in _HANDLER_PAIRS}
    # Only check roots that actually have skills with handler refs.
    # Some roots may legitimately exist but have no handler-routing skills (unlikely
    # given the 4-way mirror, but guard against future structural changes).
    missing = existing_roots - contributing_roots
    assert not missing, (
        f"Skill roots exist on disk but contributed zero handler references: {missing}. "
        f"Either the mirror is incomplete or handler parsing is broken."
    )
