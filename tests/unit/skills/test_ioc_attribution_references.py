"""Spec-146 sub-003: IOC attribution has one active home."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

CANONICAL_ATTRIBUTION = ".ai-engineering/security/iocs/IOCS_ATTRIBUTION.md"
LEGACY_ATTRIBUTION = ".ai-engineering/references/IOCS_ATTRIBUTION.md"
TEMPLATE_CANONICAL_ATTRIBUTION = (
    "src/ai_engineering/templates/.ai-engineering/security/iocs/IOCS_ATTRIBUTION.md"
)
TEMPLATE_LEGACY_ATTRIBUTION = (
    "src/ai_engineering/templates/.ai-engineering/references/IOCS_ATTRIBUTION.md"
)

ACTIVE_SKILL_FILES = (
    ".claude/skills/ai-mcp-audit/SKILL.md",
    ".codex/skills/ai-mcp-audit/SKILL.md",
    ".gemini/skills/ai-mcp-audit/SKILL.md",
    ".github/skills/ai-mcp-audit/SKILL.md",
)


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_ioc_attribution_uses_security_iocs_home_only() -> None:
    """The live repo keeps IOC attribution under security/iocs only."""
    canonical = PROJECT_ROOT / CANONICAL_ATTRIBUTION
    legacy = PROJECT_ROOT / LEGACY_ATTRIBUTION

    assert canonical.is_file(), f"missing canonical IOC attribution: {CANONICAL_ATTRIBUTION}"
    assert not legacy.exists(), (
        f"legacy IOC attribution duplicate still exists: {LEGACY_ATTRIBUTION}"
    )


def test_ioc_attribution_template_uses_security_iocs_home_only() -> None:
    """Fresh installs ship IOC attribution next to the installed IOC catalog."""
    canonical = PROJECT_ROOT / TEMPLATE_CANONICAL_ATTRIBUTION
    legacy = PROJECT_ROOT / TEMPLATE_LEGACY_ATTRIBUTION

    assert canonical.is_file(), (
        f"missing template IOC attribution at canonical home: {TEMPLATE_CANONICAL_ATTRIBUTION}"
    )
    assert not legacy.exists(), (
        f"template still ships legacy IOC attribution duplicate: {TEMPLATE_LEGACY_ATTRIBUTION}"
    )


def test_mcp_audit_skill_references_canonical_ioc_attribution() -> None:
    """Active skill mirrors point operators at the canonical IOC attribution file."""
    for relative_path in ACTIVE_SKILL_FILES:
        text = _read(relative_path)
        assert CANONICAL_ATTRIBUTION in text, f"{relative_path} missing canonical IOC path"
        assert LEGACY_ATTRIBUTION not in text, f"{relative_path} still references legacy IOC path"
