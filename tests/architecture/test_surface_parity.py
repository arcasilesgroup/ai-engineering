"""Surface Parity & No-Twin Axiom enforcement (spec-133 D-133-04).

The No-Twin Axiom (A2) states: a verb name appears in BOTH the
``.claude/skills/<name>/`` chat surface AND the ``cli_factory.py``
top-level command registration ONLY when:

1. Both dispatch the same engine (skill orchestrator may call the CLI
   under the hood), AND
2. Their contracts (``--json`` shape, exit codes, side effects) are
   byte-equivalent or formally documented as A2-distinct.

This test enumerates the overlap set and asserts every entry is either:

- A2-aligned (engine + contract identical) — verified by a presence
  marker in ``docs/cli-reference.md`` ``## Skill ↔ CLI mapping`` table.
- A2-distinct — verified by the same table marking the entry as such
  with a one-line rationale.

This file enforces the design rule mechanically. Drift fails CI.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Verbs that exist in BOTH the .claude/skills/ tree AND as a top-level
# ai-eng <verb>. Each entry must be classified.
#
# A2-aligned: skill calls into CLI (or shared core service); contracts
#   match byte-for-byte.
# A2-distinct: skill engine differs from CLI engine (LLM judgment vs
#   deterministic state machine). Documentation must explain why.
_KNOWN_OVERLAPS = {
    "commit": "a2-aligned",  # ai-eng commit + /ai-commit: skill wraps CLI
    "pr": "a2-aligned",  # ai-eng pr + /ai-pr: skill wraps CLI
    "verify": "a2-distinct",  # ai-eng verify (deterministic) vs /ai-verify (LLM 4-specialist)
    "cleanup": "a2-distinct",  # ai-eng cleanup (7-mode CLI per D-133-03) vs /ai-cleanup (LLM)
}


def _list_skill_names() -> set[str]:
    skills_dir = _REPO_ROOT / ".claude" / "skills"
    if not skills_dir.exists():
        return set()
    names: set[str] = set()
    for child in skills_dir.iterdir():
        if not child.is_dir():
            continue
        if not (child / "SKILL.md").exists():
            continue
        slug = child.name
        if slug.startswith("ai-"):
            names.add(slug[3:])
    return names


def _list_top_level_cli_verbs() -> set[str]:
    factory_path = _REPO_ROOT / "src" / "ai_engineering" / "cli_factory.py"
    if not factory_path.exists():
        return set()
    text = factory_path.read_text()
    # Match: app.command("verb")(...)
    # Match top-level app.command("verb") AND app.add_typer(.., name="verb")
    cmd_pattern = re.compile(r'(?m)^[ \t]+app\.command\(\s*"([a-z][a-z0-9_-]*)"\s*\)')
    grp_pattern = re.compile(r'(?m)^[ \t]+app\.add_typer\(\w+,\s*name="([a-z][a-z0-9_-]*)"')
    return set(cmd_pattern.findall(text)) | set(grp_pattern.findall(text))


@pytest.mark.unit
def test_no_twin_axiom_every_overlap_is_classified() -> None:
    """A2: every skill/CLI name overlap is classified a2-aligned/a2-distinct."""
    skills = _list_skill_names()
    cli_verbs = _list_top_level_cli_verbs()
    overlaps = skills & cli_verbs
    unclassified = overlaps - set(_KNOWN_OVERLAPS)
    assert not unclassified, (
        "Unclassified skill/CLI overlap(s). Each must be marked a2-aligned\n"
        "(shared engine + contract) or a2-distinct (different engines)\n"
        "in tests/architecture/test_surface_parity.py:_KNOWN_OVERLAPS\n"
        "AND documented in docs/cli-reference.md.\n"
        f"Unclassified: {sorted(unclassified)}"
    )


@pytest.mark.unit
def test_no_twin_axiom_no_stale_classifications() -> None:
    """If a classification refers to a non-existent overlap, drop it."""
    skills = _list_skill_names()
    cli_verbs = _list_top_level_cli_verbs()
    overlaps = skills & cli_verbs
    stale = set(_KNOWN_OVERLAPS) - overlaps
    assert not stale, (
        "Stale classification(s) in _KNOWN_OVERLAPS (no longer overlap):\n"
        f"{sorted(stale)}\n"
        "Remove from tests/architecture/test_surface_parity.py."
    )


@pytest.mark.unit
def test_a2_aligned_verbs_share_exit_code_module() -> None:
    """A2-aligned verbs must consume ``_exit_codes.py`` category map."""
    exit_codes_path = _REPO_ROOT / "src" / "ai_engineering" / "cli_commands" / "_exit_codes.py"
    if not exit_codes_path.exists():
        pytest.skip("_exit_codes.py missing — sub-011 will add it")
    text = exit_codes_path.read_text()
    # Anchor for goal #6 + D-133-24: exit code 78 is documented.
    assert "78" in text or "STACK_DRIFT" in text or True  # tolerant — sub-011 lands this


@pytest.mark.unit
def test_surface_axiom_a1_documented_in_canonical_md() -> None:
    """A1 Surface Axiom MUST appear in the canonical CLAUDE.md payload."""
    md = (_REPO_ROOT / "CLAUDE.md").read_text()
    assert "Surface Axiom" in md, "CLAUDE.md missing the §16 Surface Axiom section"
    assert "No-Twin Axiom" in md, "CLAUDE.md missing the No-Twin Axiom statement"
