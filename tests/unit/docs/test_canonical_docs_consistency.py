"""Canonical docs consistency tests for AGENTS.md + CLAUDE.md (sub-001).

Spec-127 §18 mandates a slim, voice-aligned root governance surface:

- ``AGENTS.md`` ≤80 lines (§18.2 Boris+Karpathy voice budget).
- Skill / agent counts in both files match ``manifest.yml`` (parameterized
  so M3's 50→46 skill rename and the 26→23 agent rename land cleanly with
  one source of truth).
- The seven-step canonical chain
  ``/ai-brainstorm → /ai-plan → /ai-build → /ai-verify → /ai-review →
  /ai-commit → /ai-pr`` appears verbatim in both files.
- Legacy skill names from D-127-04 (``ai-dispatch``, ``ai-run``,
  ``ai-autopilot`` standalone, ``ai-test``, ``ai-debug``, ``ai-code``)
  are absent from the rewritten root surface — they live in
  ``manifest.yml`` registry until the M3 rename ships, but the prose
  surface speaks the canonical seven-verb vocabulary only.
- ``CLAUDE.md`` ships a ``Governance hooks`` section enumerating
  ``skill_lint``, ``test_layer_isolation``, the eval regression gate, and
  hot-path budgets.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS_MD = REPO_ROOT / "AGENTS.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
MANIFEST = REPO_ROOT / ".ai-engineering" / "manifest.yml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _manifest_total(section: str) -> int:
    """Read ``<section>.total`` from manifest.yml without importing pyyaml."""
    text = MANIFEST.read_text(encoding="utf-8")
    in_section = False
    for line in text.splitlines():
        if line.startswith(f"{section}:"):
            in_section = True
            continue
        if in_section:
            stripped = line.lstrip()
            if not line.startswith(" ") and not line.startswith("\t") and stripped:
                # Left the section.
                in_section = False
                continue
            if stripped.startswith("total:"):
                return int(stripped.split(":", 1)[1].strip())
    raise AssertionError(f"manifest.yml missing {section}.total")


CANONICAL_CHAIN = (
    "/ai-brainstorm → /ai-plan → /ai-build → /ai-verify → /ai-review → /ai-commit → /ai-pr"
)

# Legacy names from D-127-04 that must NOT appear in the rewritten prose.
# (manifest.yml is allowed to retain them until M3 ships the rename.)
LEGACY_NAMES = (
    "/ai-dispatch",
    "/ai-run",
    "/ai-test",
    "/ai-debug",
    "/ai-code",
)


# ---------------------------------------------------------------------------
# AGENTS.md
# ---------------------------------------------------------------------------


class TestAgentsMd:
    def test_agents_md_under_eighty_lines(self):
        lines = AGENTS_MD.read_text(encoding="utf-8").splitlines()
        assert len(lines) <= 80, f"AGENTS.md is {len(lines)} lines (>80 cap)"

    def test_skill_count_matches_manifest(self):
        total = _manifest_total("skills")
        text = AGENTS_MD.read_text(encoding="utf-8")
        assert f"Skills ({total})" in text, (
            f"AGENTS.md missing 'Skills ({total})' heading from manifest"
        )

    def test_agent_count_matches_manifest(self):
        total = _manifest_total("agents")
        text = AGENTS_MD.read_text(encoding="utf-8")
        assert f"Agents ({total})" in text, (
            f"AGENTS.md missing 'Agents ({total})' heading from manifest"
        )

    def test_canonical_seven_step_chain_verbatim(self):
        text = AGENTS_MD.read_text(encoding="utf-8")
        assert CANONICAL_CHAIN in text, (
            "AGENTS.md missing verbatim seven-step chain "
            "/ai-brainstorm → /ai-plan → /ai-build → /ai-verify → "
            "/ai-review → /ai-commit → /ai-pr"
        )

    @pytest.mark.parametrize("legacy", LEGACY_NAMES)
    def test_legacy_skill_names_absent(self, legacy):
        text = AGENTS_MD.read_text(encoding="utf-8")
        # Allow bare slug `ai-test` etc. only inside fenced code blocks
        # referring to the registry; the prose must not invoke them.
        # Simplest invariant: the slash-prefixed form is forbidden anywhere.
        assert legacy not in text, (
            f"AGENTS.md still references legacy skill name {legacy!r} — "
            "use the canonical seven-verb chain instead"
        )

    def test_two_file_state_pattern_referenced(self):
        """Boris+Karpathy voice mandates the two-file state pattern callout."""
        text = AGENTS_MD.read_text(encoding="utf-8")
        # plan.md + LESSONS.md is the canonical pair.
        assert "plan.md" in text, "AGENTS.md missing plan.md callout"
        assert "LESSONS.md" in text, "AGENTS.md missing LESSONS.md callout"


# ---------------------------------------------------------------------------
# CLAUDE.md
# ---------------------------------------------------------------------------


class TestClaudeMd:
    def test_canonical_seven_step_chain_verbatim(self):
        text = CLAUDE_MD.read_text(encoding="utf-8")
        assert CANONICAL_CHAIN in text, (
            "CLAUDE.md missing verbatim seven-step chain "
            "/ai-brainstorm → /ai-plan → /ai-build → /ai-verify → "
            "/ai-review → /ai-commit → /ai-pr"
        )

    def test_governance_hooks_section_present(self):
        text = CLAUDE_MD.read_text(encoding="utf-8")
        assert re.search(r"^##+ Governance hooks", text, flags=re.MULTILINE), (
            "CLAUDE.md missing 'Governance hooks' section"
        )

    @pytest.mark.parametrize(
        "anchor",
        ("skill_lint", "test_layer_isolation", "eval", "hot-path"),
    )
    def test_governance_hooks_enumerates_anchors(self, anchor):
        text = CLAUDE_MD.read_text(encoding="utf-8")
        # Find the Governance hooks section block and require each anchor
        # name to appear inside it.
        match = re.search(r"(?ms)^##+ Governance hooks.*?(?=^##\s|\Z)", text)
        assert match, "CLAUDE.md Governance hooks section not findable"
        block = match.group(0)
        assert anchor in block, f"Governance hooks section must enumerate {anchor!r}"

    def test_hot_path_section_appears_before_step_zero(self):
        """Hot-Path heading precedes Step 0 heading (hot-path-first reorder)."""
        text = CLAUDE_MD.read_text(encoding="utf-8")
        # Match section-heading lines only ("## Hot-Path..." / "## Step 0..."),
        # not in-prose mentions in blockquotes / pointers.
        hp_match = re.search(r"^##+\s+Hot[- ]?Path\b", text, flags=re.MULTILINE | re.IGNORECASE)
        step0_match = re.search(r"^##+\s+Step\s*0\b", text, flags=re.MULTILINE | re.IGNORECASE)
        assert hp_match, "CLAUDE.md missing Hot-Path section heading"
        assert step0_match, "CLAUDE.md missing Step 0 section heading"
        assert hp_match.start() < step0_match.start(), (
            "CLAUDE.md must place the Hot-Path Discipline section heading "
            "before the Step 0 section heading (hot-path-first reorder)"
        )

    @pytest.mark.parametrize("legacy", LEGACY_NAMES)
    def test_legacy_skill_names_absent(self, legacy):
        text = CLAUDE_MD.read_text(encoding="utf-8")
        assert legacy not in text, f"CLAUDE.md still references legacy skill name {legacy!r}"
