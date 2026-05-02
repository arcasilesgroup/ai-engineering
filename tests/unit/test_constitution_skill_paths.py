from __future__ import annotations

from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

_AI_CONSTITUTION_SKILL_PATHS = (
    ".github/skills/ai-constitution/SKILL.md",
    ".claude/skills/ai-constitution/SKILL.md",
    ".codex/skills/ai-constitution/SKILL.md",
    ".gemini/skills/ai-constitution/SKILL.md",
    "src/ai_engineering/templates/project/.github/skills/ai-constitution/SKILL.md",
    "src/ai_engineering/templates/project/.claude/skills/ai-constitution/SKILL.md",
    "src/ai_engineering/templates/project/.codex/skills/ai-constitution/SKILL.md",
    "src/ai_engineering/templates/project/.gemini/skills/ai-constitution/SKILL.md",
)

_VERIFIER_ARCHITECTURE_PATHS = (
    ".github/agents/internal/verifier-architecture.md",
    ".claude/agents/verifier-architecture.md",
    ".codex/agents/internal/verifier-architecture.md",
    ".gemini/agents/internal/verifier-architecture.md",
    "src/ai_engineering/templates/project/agents/internal/verifier-architecture.md",
    "src/ai_engineering/templates/project/.claude/agents/verifier-architecture.md",
    "src/ai_engineering/templates/project/.codex/agents/internal/verifier-architecture.md",
    "src/ai_engineering/templates/project/.gemini/agents/internal/verifier-architecture.md",
)

_BRAINSTORM_INTERROGATE_PATHS = (
    ".github/skills/ai-brainstorm/handlers/interrogate.md",
    ".claude/skills/ai-brainstorm/handlers/interrogate.md",
    ".codex/skills/ai-brainstorm/handlers/interrogate.md",
    ".gemini/skills/ai-brainstorm/handlers/interrogate.md",
    "src/ai_engineering/templates/project/.github/skills/ai-brainstorm/handlers/interrogate.md",
    "src/ai_engineering/templates/project/.claude/skills/ai-brainstorm/handlers/interrogate.md",
    "src/ai_engineering/templates/project/.codex/skills/ai-brainstorm/handlers/interrogate.md",
    "src/ai_engineering/templates/project/.gemini/skills/ai-brainstorm/handlers/interrogate.md",
)

_AI_INSTINCT_SKILL_PATHS = (
    ".github/skills/ai-instinct/SKILL.md",
    ".claude/skills/ai-instinct/SKILL.md",
    ".codex/skills/ai-instinct/SKILL.md",
    ".gemini/skills/ai-instinct/SKILL.md",
    "src/ai_engineering/templates/project/.github/skills/ai-instinct/SKILL.md",
    "src/ai_engineering/templates/project/.claude/skills/ai-instinct/SKILL.md",
    "src/ai_engineering/templates/project/.codex/skills/ai-instinct/SKILL.md",
    "src/ai_engineering/templates/project/.gemini/skills/ai-instinct/SKILL.md",
)

_RUNBOOK_ARCHITECTURE_DRIFT_PATHS = (
    ".ai-engineering/runbooks/architecture-drift.md",
    "src/ai_engineering/templates/.ai-engineering/runbooks/architecture-drift.md",
)

_RUNBOOK_REFINE_PATHS = (
    ".ai-engineering/runbooks/refine.md",
    "src/ai_engineering/templates/.ai-engineering/runbooks/refine.md",
)

_RUNBOOK_WORK_ITEM_AUDIT_PATHS = (
    ".ai-engineering/runbooks/work-item-audit.md",
    "src/ai_engineering/templates/.ai-engineering/runbooks/work-item-audit.md",
)

_WORKSPACE_CHARTER_PATHS = (
    ".ai-engineering/CONSTITUTION.md",
    "src/ai_engineering/templates/.ai-engineering/CONSTITUTION.md",
)

_CONTROL_PLANE_README_PATHS = (
    ".ai-engineering/README.md",
    "src/ai_engineering/templates/.ai-engineering/README.md",
)


@pytest.mark.parametrize("relative_path", _AI_CONSTITUTION_SKILL_PATHS)
def test_ai_constitution_skills_write_root_constitution_with_legacy_read_fallback(
    relative_path: str,
) -> None:
    content = (_PROJECT_ROOT / relative_path).read_text(encoding="utf-8")

    assert "Generate and maintain `CONSTITUTION.md`" in content
    assert "save to `CONSTITUTION.md`" in content
    assert "- **Writes**: `CONSTITUTION.md`" in content

    assert "Generate and maintain `.ai-engineering/CONSTITUTION.md`" not in content
    assert "save to `.ai-engineering/CONSTITUTION.md`" not in content
    assert "- **Writes**: `.ai-engineering/CONSTITUTION.md`" not in content

    assert ".ai-engineering/CONSTITUTION.md" in content


@pytest.mark.parametrize("relative_path", _VERIFIER_ARCHITECTURE_PATHS)
def test_verifier_architecture_reads_root_constitution_with_legacy_fallback(
    relative_path: str,
) -> None:
    content = (_PROJECT_ROOT / relative_path).read_text(encoding="utf-8")

    assert "Read `CONSTITUTION.md` if it exists for project boundaries." in content
    assert (
        "Fall back to `.ai-engineering/CONSTITUTION.md` only when migrating legacy installs."
        in content
    )
    assert (
        "Read `.ai-engineering/CONSTITUTION.md` if it exists for project boundaries." not in content
    )


@pytest.mark.parametrize("relative_path", _BRAINSTORM_INTERROGATE_PATHS)
def test_ai_brainstorm_interrogate_reads_root_constitution_with_legacy_fallback(
    relative_path: str,
) -> None:
    content = (_PROJECT_ROOT / relative_path).read_text(encoding="utf-8")

    assert (
        "Read constitution (`CONSTITUTION.md`) for project boundaries and stakeholders." in content
    )
    assert "fall back to `.ai-engineering/CONSTITUTION.md` for legacy installs." in content
    assert (
        "Read constitution (`.ai-engineering/CONSTITUTION.md`) for project boundaries and stakeholders"
        not in content
    )


@pytest.mark.parametrize("relative_path", _AI_INSTINCT_SKILL_PATHS)
def test_ai_instinct_reads_root_constitution_with_legacy_fallback(relative_path: str) -> None:
    content = (_PROJECT_ROOT / relative_path).read_text(encoding="utf-8")

    assert "Read project context: `CONSTITUTION.md`, `.ai-engineering/manifest.yml`" in content
    assert (
        "If only `.ai-engineering/CONSTITUTION.md` exists, use it as a compatibility fallback."
        in content
    )
    assert (
        "Read project context: `.ai-engineering/CONSTITUTION.md`, `.ai-engineering/manifest.yml`"
        not in content
    )


@pytest.mark.parametrize("relative_path", _RUNBOOK_ARCHITECTURE_DRIFT_PATHS)
def test_architecture_drift_runbook_prefers_root_constitution_with_legacy_fallback(
    relative_path: str,
) -> None:
    content = (_PROJECT_ROOT / relative_path).read_text(encoding="utf-8")

    assert (
        "`docs/solution-intent.md`, `CONSTITUTION.md`, and `.ai-engineering/state/decision-store.json`"
        in content
    )
    assert "`CONSTITUTION.md` exists with boundary rules." in content
    assert "cat CONSTITUTION.md || cat .ai-engineering/CONSTITUTION.md" in content
    assert (
        "`docs/solution-intent.md`, `.ai-engineering/CONSTITUTION.md`, and `.ai-engineering/state/decision-store.json`"
        not in content
    )


@pytest.mark.parametrize("relative_path", _RUNBOOK_REFINE_PATHS)
def test_refine_runbook_prefers_root_constitution_with_legacy_fallback(
    relative_path: str,
) -> None:
    content = (_PROJECT_ROOT / relative_path).read_text(encoding="utf-8")

    assert "`CONSTITUTION.md` exists for boundary constraint extraction." in content
    assert "cat CONSTITUTION.md || cat .ai-engineering/CONSTITUTION.md" in content
    assert (
        "`.ai-engineering/CONSTITUTION.md` exists for boundary constraint extraction."
        not in content
    )


@pytest.mark.parametrize("relative_path", _RUNBOOK_WORK_ITEM_AUDIT_PATHS)
def test_work_item_audit_runbook_prefers_root_constitution_with_legacy_fallback(
    relative_path: str,
) -> None:
    content = (_PROJECT_ROOT / relative_path).read_text(encoding="utf-8")

    assert (
        "`CONSTITUTION.md` (fall back to `.ai-engineering/CONSTITUTION.md` for legacy installs)"
        in content
    )
    assert "`.ai-engineering/CONSTITUTION.md`\n" not in content


@pytest.mark.parametrize("relative_path", _WORKSPACE_CHARTER_PATHS)
def test_workspace_charter_is_demoted_from_step_zero_constitution(relative_path: str) -> None:
    content = (_PROJECT_ROOT / relative_path).read_text(encoding="utf-8")

    assert "# WORKSPACE CHARTER" in content
    assert "Root `CONSTITUTION.md` is the sole constitutional authority" in content
    assert "It is not a\nsecond constitution and it is not loaded at Step 0." in content
    assert "supreme governing authority" not in content
    assert "loaded at Step 0 of every skill and agent invocation" not in content


@pytest.mark.parametrize("relative_path", _CONTROL_PLANE_README_PATHS)
def test_control_plane_readme_describes_root_constitution_as_sole_authority(
    relative_path: str,
) -> None:
    content = (_PROJECT_ROOT / relative_path).read_text(encoding="utf-8")

    assert "`CONSTITUTION.md` is the sole constitutional surface" in content
    assert (
        "`.ai-engineering/CONSTITUTION.md` is retained only as a subordinate workspace charter compatibility alias"
        in content
    )
    assert (
        "`CONSTITUTION.md` and `.ai-engineering/CONSTITUTION.md` keep the hard-rule subset"
        not in content
    )


def test_solution_intent_describes_root_constitution_as_canonical_authority() -> None:
    content = (_PROJECT_ROOT / "docs/solution-intent.md").read_text(encoding="utf-8")

    assert "`CONSTITUTION.md` is the sole constitutional hard-rule source" in content
    assert "| Constitution | `CONSTITUTION.md` |" in content
    assert (
        "| Workspace charter (compatibility alias) | `.ai-engineering/CONSTITUTION.md` |" in content
    )
    assert (
        "`CONSTITUTION.md` and `.ai-engineering/CONSTITUTION.md` keep spec-driven development"
        not in content
    )
    assert "| Constitution | `.ai-engineering/CONSTITUTION.md` |" not in content
