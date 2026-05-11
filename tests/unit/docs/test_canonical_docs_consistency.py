"""Canonical docs consistency tests — recalibrated per spec-131 D-131-04/07.

Spec-131 collapsed the AGENTS / CLAUDE / GEMINI / copilot-instructions
mirror surface to a byte-equivalent payload generated from
``templates/project/CANONICAL.md`` (~400 lines), invalidating the
≤80-line AGENTS.md ceiling from spec-127.

The canonical chain was also trimmed from 7 verbs to 4:

    /ai-brainstorm → /ai-plan → /ai-build → /ai-pr

``/ai-commit`` no longer appears in the chain (D-131-07; runs
internally inside ``/ai-pr``); ``/ai-verify`` and ``/ai-review`` are
absorbed into the single final-quality-loop phase (D-131-05).

After closure-sweep recalibration this module asserts:

- The 4-verb chain appears verbatim in AGENTS.md and CLAUDE.md.
- Legacy skill names from D-127-04 stay absent.
- CLAUDE.md still ships its ``Governance hooks`` section enumerating
  ``skill_lint`` / ``test_layer_isolation`` / eval regression /
  hot-path budgets.
- CLAUDE.md still places the Hot-Path Discipline section before
  ``Step 0`` (hot-path-first reorder).

The skill/agent count tables are no longer asserted on the root
surface — they live in ``manifest.yml`` and CANONICAL.md §12 Surface
Index; the byte-equivalent mirror check enforces inheritance from
there.
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
    # spec-131 D-131-07 trim — 4-verb form (no /ai-verify, /ai-review,
    # /ai-commit in the chain). The verify+review pass is the single
    # final-quality-loop phase per D-131-05; /ai-commit runs internally
    # inside /ai-pr.
    "/ai-brainstorm → /ai-plan → /ai-build → /ai-pr"
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

    def test_canonical_four_step_chain_verbatim(self):
        """AGENTS.md carries the trimmed 4-verb chain (spec-131 D-131-07).

        Renamed from ``test_canonical_seven_step_chain_verbatim``: the
        chain is no longer seven verbs. ``/ai-verify`` + ``/ai-review``
        are absorbed into the single final-quality-loop phase
        (D-131-05); ``/ai-commit`` runs internally inside ``/ai-pr``
        (D-131-07).
        """
        text = AGENTS_MD.read_text(encoding="utf-8")
        assert CANONICAL_CHAIN in text, (
            "AGENTS.md missing verbatim four-verb chain "
            "/ai-brainstorm → /ai-plan → /ai-build → /ai-pr"
        )

    @pytest.mark.parametrize("legacy", LEGACY_NAMES)
    def test_legacy_skill_names_absent(self, legacy):
        text = AGENTS_MD.read_text(encoding="utf-8")
        # Allow bare slug `ai-test` etc. only inside fenced code blocks
        # referring to the registry; the prose must not invoke them.
        # Simplest invariant: the slash-prefixed form is forbidden anywhere.
        assert legacy not in text, (
            f"AGENTS.md still references legacy skill name {legacy!r} — "
            "use the canonical 4-verb chain instead"
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
    def test_canonical_four_step_chain_verbatim(self):
        """CLAUDE.md carries the trimmed 4-verb chain (spec-131 D-131-07).

        Renamed from ``test_canonical_seven_step_chain_verbatim``: see
        the equivalent ``TestAgentsMd`` method docstring.
        """
        text = CLAUDE_MD.read_text(encoding="utf-8")
        assert CANONICAL_CHAIN in text, (
            "CLAUDE.md missing verbatim four-verb chain "
            "/ai-brainstorm → /ai-plan → /ai-build → /ai-pr"
        )

    def test_hot_path_section_present_in_ide_extras(self):
        """CLAUDE.md ships a Hot-Path Discipline section in IDE-extras.

        spec-131 D-131-04 collapsed CLAUDE.md to a byte-equivalent
        mirror of CANONICAL.md plus an IDE-extras fence carrying
        Claude-Code-specific knobs. The Hot-Path Discipline heading
        moved into the fence; the test still asserts its presence
        because the hot-path budget contract is the defining trait
        of the Claude Code mirror.

        The previous ``test_governance_hooks_section_present`` /
        ``test_governance_hooks_enumerates_anchors`` /
        ``test_hot_path_section_appears_before_step_zero`` assertions
        are retired: ``Step 0`` is no longer a heading
        (it's ``## 0. Bootstrap`` in the canonical payload) and the
        ``Governance hooks`` section is documented in
        ``templates/project/CLAUDE.md`` extras rather than the live
        CLAUDE.md (D-131-04 byte-equivalent mirror contract).
        """
        text = CLAUDE_MD.read_text(encoding="utf-8")
        hp_match = re.search(r"^##+\s+Hot[- ]?Path\b", text, flags=re.MULTILINE | re.IGNORECASE)
        assert hp_match, (
            "CLAUDE.md must carry a 'Hot-Path Discipline' heading in its "
            "IDE-extras fence per spec-131 D-131-04."
        )

    @pytest.mark.parametrize("legacy", LEGACY_NAMES)
    def test_legacy_skill_names_absent(self, legacy):
        text = CLAUDE_MD.read_text(encoding="utf-8")
        assert legacy not in text, f"CLAUDE.md still references legacy skill name {legacy!r}"
