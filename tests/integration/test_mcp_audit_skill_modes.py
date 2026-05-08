"""GREEN test for spec-107 G-10 — /ai-mcp-audit skill 3 modes.

Spec-107 D-107-08 introduces the `/ai-mcp-audit` skill with three
modes propagated to all four IDE locations (Claude Code, GitHub
Copilot, Codex, Gemini):

- **Mode 1 — `scan`**: LLM-driven coherence analysis of installed
  skills + MCP servers; emits VERDE/ROJO verdicts per surface.
- **Mode 2 — `audit-update <skill>`**: diff baseline vs current SKILL
  payload; flags rug-pull patterns (silent SKILL prompt mutations).
- **Mode 3 — `baseline set [--target <skill-or-all>]`**: snapshot
  current SKILL payloads to ``state/sentinel-baseline.json``.

Phase 5 acceptance contract for T-5.1 / T-5.2 / T-5.3 / T-5.4 / T-5.5 / T-5.12.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_PATHS = [
    REPO_ROOT / ".claude" / "skills" / "ai-mcp-audit" / "SKILL.md",
    REPO_ROOT / ".github" / "skills" / "ai-mcp-audit" / "SKILL.md",
    REPO_ROOT / ".codex" / "skills" / "ai-mcp-audit" / "SKILL.md",
    REPO_ROOT / ".gemini" / "skills" / "ai-mcp-audit" / "SKILL.md",
]


def test_skill_exists_in_all_four_ide_surfaces() -> None:
    """G-10: ai-mcp-audit skill must ship in 4 IDE surface directories."""
    missing = [p for p in SKILL_PATHS if not p.is_file()]
    assert not missing, (
        f"ai-mcp-audit skill missing from: {[str(p) for p in missing]} "
        "— Phase 5 T-5.1 / T-5.5 must create the canonical Claude Code "
        "SKILL.md and sync it to .github/.codex/.gemini/ via "
        "scripts/sync_command_mirrors.py"
    )


def test_skill_documents_three_modes() -> None:
    """G-10: each surface documents Mode 1 (scan), Mode 2 (audit-update), Mode 3 (baseline)."""
    for path in SKILL_PATHS:
        if not path.is_file():
            pytest.skip(f"{path} missing — covered by sibling test")
        text = path.read_text(encoding="utf-8")
        for mode_keyword in ("scan", "audit-update", "baseline"):
            assert mode_keyword in text.lower(), (
                f"{path} missing mode keyword '{mode_keyword}' — "
                f"Phase 5 T-5.2 / T-5.3 / T-5.4 must document all 3 modes"
            )


def test_skill_frontmatter_declares_effort_high() -> None:
    """G-10: skill frontmatter must declare effort: high (security-critical)."""
    canonical = SKILL_PATHS[0]
    if not canonical.is_file():
        pytest.skip("canonical SKILL.md missing — covered by sibling test")
    text = canonical.read_text(encoding="utf-8")
    assert "effort: high" in text or "effort:high" in text, (
        "ai-mcp-audit/SKILL.md frontmatter missing `effort: high` — "
        "spec-107 D-107-08 mandates high-effort classification (security)"
    )


def test_skill_references_baseline_state_file() -> None:
    """G-10: skill must reference state/sentinel-baseline.json for Mode 3."""
    canonical = SKILL_PATHS[0]
    if not canonical.is_file():
        pytest.skip("canonical SKILL.md missing — covered by sibling test")
    text = canonical.read_text(encoding="utf-8")
    assert "sentinel-baseline.json" in text, (
        "ai-mcp-audit/SKILL.md missing reference to "
        "state/sentinel-baseline.json — Phase 5 T-5.4 must document the "
        "baseline snapshot location for Mode 3"
    )


def test_skill_frontmatter_declares_canonical_name() -> None:
    """G-10: skill frontmatter must declare the canonical name `ai-mcp-audit`."""
    canonical = SKILL_PATHS[0]
    if not canonical.is_file():
        pytest.skip("canonical SKILL.md missing — covered by sibling test")
    text = canonical.read_text(encoding="utf-8")
    assert "name: ai-mcp-audit" in text, (
        "ai-mcp-audit/SKILL.md frontmatter missing `name: ai-mcp-audit` — "
        "Phase 5 T-5.1 must declare canonical skill name"
    )


def test_skill_documents_cold_path_and_hot_path_distinction() -> None:
    """G-10: skill must document the cold-path vs hot-path division (D-107-08)."""
    canonical = SKILL_PATHS[0]
    if not canonical.is_file():
        pytest.skip("canonical SKILL.md missing — covered by sibling test")
    text = canonical.read_text(encoding="utf-8").lower()
    assert "cold" in text and "hot" in text, (
        "ai-mcp-audit/SKILL.md missing cold-path vs hot-path division — "
        "spec-107 D-107-08 mandates explicit hot/cold path documentation"
    )
    assert "prompt-injection-guard" in text, (
        "ai-mcp-audit/SKILL.md missing reference to prompt-injection-guard — "
        "spec-107 D-107-08 cross-references the runtime hot-path counterpart"
    )
