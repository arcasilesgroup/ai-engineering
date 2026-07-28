"""Contract tests for bounded quality remediation in build/autopilot skills."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

BUILD_HANDLER_REL = Path("skills/ai-build/handlers/quality.md")
AUTO_HANDLER_REL = Path("skills/ai-autopilot/handlers/phase-quality.md")
AUTO_DELIVER_REL = Path("skills/ai-autopilot/handlers/phase-deliver.md")
AUTO_SKILL_REL = Path("skills/ai-autopilot/SKILL.md")
BUILD_SKILL_REL = Path("skills/ai-build/SKILL.md")

# spec-201 D-201-04: skill trees collapse to two — .claude (Claude Code,
# whose search paths are compiled in) and .agents (every other surface).
ROOT_SURFACES = (".claude", ".agents")
TEMPLATE_HANDLER_SURFACES = (".claude", ".agents")
TEMPLATE_SKILL_SURFACES = (".agents", ".claude")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_build_quality_handler_defines_one_bounded_remediation_pass() -> None:
    text = _read(REPO_ROOT / ".claude" / BUILD_HANDLER_REL)
    lower = text.lower()

    assert "one bounded quality-remediation pass" in lower
    assert "final reassessment" in lower
    assert "0 blockers + 0 criticals + 0 highs" in text
    assert "Do NOT perform a second remediation pass" in text
    assert "Proceed to Phase 4 with issues documented in the PR body" not in text


def test_autopilot_quality_handler_defines_manifest_aware_phase_5b() -> None:
    text = _read(REPO_ROOT / ".claude" / AUTO_HANDLER_REL)

    assert "Phase 5b -- Bounded Remediation Pass" in text
    assert "quality_remediation:" in text
    assert "max_attempts: 1" in text
    assert "Do NOT re-decompose" in text
    assert "Do NOT perform a second remediation pass" in text


def test_quality_remediation_requires_cross_platform_reproducers() -> None:
    for rel in (BUILD_HANDLER_REL, AUTO_HANDLER_REL):
        text = _read(REPO_ROOT / ".claude" / rel)
        assert "Cross-platform reproducers" in text
        assert "Windows PowerShell" in text
        assert "POSIX shell pipeline" in text


def test_quality_remediation_propagates_to_root_handler_mirrors() -> None:
    for surface in ROOT_SURFACES:
        build = _read(REPO_ROOT / surface / BUILD_HANDLER_REL)
        auto = _read(REPO_ROOT / surface / AUTO_HANDLER_REL)
        assert "one bounded quality-remediation pass" in build.lower(), surface
        assert "Phase 5b -- Bounded Remediation Pass" in auto, surface


def test_quality_remediation_propagates_to_template_handler_mirrors() -> None:
    template_root = REPO_ROOT / "src" / "ai_engineering" / "templates" / "project"
    for surface in TEMPLATE_HANDLER_SURFACES:
        build = _read(template_root / surface / BUILD_HANDLER_REL)
        auto = _read(template_root / surface / AUTO_HANDLER_REL)
        assert "one bounded quality-remediation pass" in build.lower(), surface
        assert "Phase 5b -- Bounded Remediation Pass" in auto, surface


def test_autopilot_phase_5b_visible_on_all_skill_surfaces() -> None:
    for surface in ROOT_SURFACES:
        text = _read(REPO_ROOT / surface / AUTO_SKILL_REL)
        assert "Phase 5b" in text, surface
        assert "one bounded quality-remediation pass" in text.lower(), surface

    template_root = REPO_ROOT / "src" / "ai_engineering" / "templates" / "project"
    for surface in TEMPLATE_SKILL_SURFACES:
        text = _read(template_root / surface / AUTO_SKILL_REL)
        assert "Phase 5b" in text, surface
        assert "one bounded quality-remediation pass" in text.lower(), surface


def test_build_quality_remediation_visible_on_all_skill_surfaces() -> None:
    for surface in ROOT_SURFACES:
        text = _read(REPO_ROOT / surface / BUILD_SKILL_REL)
        assert "bounded quality-remediation pass" in text.lower(), surface
        assert "## Quality Outcome" in text, surface

    template_root = REPO_ROOT / "src" / "ai_engineering" / "templates" / "project"
    for surface in TEMPLATE_SKILL_SURFACES:
        text = _read(template_root / surface / BUILD_SKILL_REL)
        assert "bounded quality-remediation pass" in text.lower(), surface
        assert "## Quality Outcome" in text, surface


def test_autopilot_deliver_uses_final_reassessment_not_round_three() -> None:
    for surface in ROOT_SURFACES:
        text = _read(REPO_ROOT / surface / AUTO_DELIVER_REL)
        assert "round 3" not in text.lower(), surface
        assert "terminal final reassessment" in text, surface
        assert "quality_remediation.max_attempts: 1" in text, surface

    template_root = REPO_ROOT / "src" / "ai_engineering" / "templates" / "project"
    for surface in TEMPLATE_HANDLER_SURFACES:
        text = _read(template_root / surface / AUTO_DELIVER_REL)
        assert "round 3" not in text.lower(), surface
        assert "terminal final reassessment" in text, surface
        assert "quality_remediation.max_attempts: 1" in text, surface


def test_canonical_rule_mentions_bounded_quality_loop() -> None:
    root_docs = (
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "CLAUDE.md",
        REPO_ROOT / ".github" / "copilot-instructions.md",
    )
    for path in root_docs:
        text = _read(path)
        assert "Bounded fail-loud quality loop" in text, str(path)
        assert "no second remediation pass" in text, str(path)

    template_docs = (
        REPO_ROOT / "src" / "ai_engineering" / "templates" / "project" / "CANONICAL.md",
        REPO_ROOT / "src" / "ai_engineering" / "templates" / "project" / "AGENTS.md",
        REPO_ROOT / "src" / "ai_engineering" / "templates" / "project" / "CLAUDE.md",
        REPO_ROOT / "src" / "ai_engineering" / "templates" / "project" / "copilot-instructions.md",
    )
    for path in template_docs:
        text = _read(path)
        assert "Bounded fail-loud quality loop" in text, str(path)
        assert "no second remediation pass" in text, str(path)
