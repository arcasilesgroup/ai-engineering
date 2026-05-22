"""Regression tests for ide-audit cross-IDE checks after spec-151.

Spec-107 D-107-05 extends `/ai-ide-audit` with three new checks:

- Check 6: agent naming consistency cross-IDE — every IDE agent file's
  front-matter `name:` must equal its slug; flag mismatches.
- Check 8: generic instruction-file count scan — walk every CLAUDE.md /
  AGENTS.md / copilot-instructions.md and validate
  `## Skills (N)` and `## Agents (N)` headers vs canonical counts.

These tests are marked ``spec_107_red`` and excluded from CI default
runs until Phase 3 lands the GREEN implementation. They are the
acceptance contract for T-3.6.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IDE_AUDIT_SKILL = REPO_ROOT / ".claude" / "skills" / "ai-ide-audit" / "SKILL.md"


def test_skill_md_documents_check_6() -> None:
    """G-6: SKILL.md must document Check 6 (agent naming cross-IDE)."""
    assert IDE_AUDIT_SKILL.is_file(), f"platform-audit SKILL.md missing: {IDE_AUDIT_SKILL}"
    text = IDE_AUDIT_SKILL.read_text(encoding="utf-8")
    assert "Check 6" in text, (
        "SKILL.md missing `Check 6` documentation — Phase 3 T-3.6 must "
        "land the agent-naming consistency check"
    )
    assert "agent naming" in text.lower() or "name:" in text, (
        "Check 6 documentation must reference agent naming / front-matter name field"
    )


def test_skill_md_does_not_reference_retired_gemini_count_check() -> None:
    """spec-151: ide-audit must not document the retired GEMINI.md count check."""
    assert IDE_AUDIT_SKILL.is_file()
    text = IDE_AUDIT_SKILL.read_text(encoding="utf-8")
    assert "GEMINI.md" not in text
    assert "Check 7" not in text


def test_skill_md_documents_check_8() -> None:
    """G-6: SKILL.md must document Check 8 (generic instruction-file scan)."""
    assert IDE_AUDIT_SKILL.is_file()
    text = IDE_AUDIT_SKILL.read_text(encoding="utf-8")
    assert "Check 8" in text, (
        "SKILL.md missing `Check 8` documentation — Phase 3 T-3.6 must "
        "land the generic instruction-file count scan"
    )
    # The generic scan must reference at least the four canonical
    # instruction-file names so reviewers know the surface covered.
    for instruction_file in ("CLAUDE.md", "AGENTS.md"):
        assert instruction_file in text, (
            f"Check 8 documentation must mention {instruction_file} as part "
            "of the generic scan surface"
        )


def test_skill_md_advisory_severity_documented() -> None:
    """G-6 + NG-11: new checks must be flagged as advisory-only (no hard gate)."""
    assert IDE_AUDIT_SKILL.is_file()
    text = IDE_AUDIT_SKILL.read_text(encoding="utf-8").lower()
    assert "advisory" in text, (
        "ide-audit SKILL.md must document that the new checks are "
        "advisory-only per spec-107 NG-11 (hard-gate landed when ≥90% "
        "projects pass)"
    )


def test_skill_md_references_spec_107() -> None:
    """G-6: SKILL.md must cite spec-107 as the origin for the new checks."""
    assert IDE_AUDIT_SKILL.is_file()
    text = IDE_AUDIT_SKILL.read_text(encoding="utf-8")
    assert "spec-107" in text, (
        "ide-audit SKILL.md missing `spec-107` reference for the new "
        "checks; provenance must be traceable for auditors"
    )
