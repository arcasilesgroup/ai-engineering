"""Contract tests for the shared HX-03 mirror inventory model."""

from __future__ import annotations


def test_inventory_contains_expected_families() -> None:
    from ai_engineering.config.mirror_inventory import get_mirror_families

    families = {family.family_id: family for family in get_mirror_families()}

    assert {
        "governance-template",
        "claude-commands",
        "claude-skills",
        "claude-agents",
        "codex-skills",
        "codex-agents",
        "gemini-skills",
        "gemini-agents",
        "copilot-skills",
        "copilot-agents",
        "specialist-agents",
        "generated-instructions",
        "manual-instructions",
    }.issubset(families)


def test_public_inventory_excludes_internal_and_manual_families() -> None:
    from ai_engineering.config.mirror_inventory import (
        get_mirror_families,
        get_public_mirror_family_ids,
    )

    families = {family.family_id: family for family in get_mirror_families()}
    public_ids = get_public_mirror_family_ids()

    assert families["specialist-agents"].public is False
    assert families["generated-instructions"].generated is True
    assert families["generated-instructions"].edit_policy == "generated-do-not-edit"
    assert families["manual-instructions"].generated is False
    assert families["manual-instructions"].edit_policy == "manual"
    assert "specialist-agents" not in public_ids
    assert "generated-instructions" not in public_ids
    assert "manual-instructions" not in public_ids
    assert {
        "claude-skills",
        "claude-agents",
        "codex-skills",
        "codex-agents",
        "gemini-skills",
        "gemini-agents",
        "copilot-skills",
        "copilot-agents",
    }.issubset(public_ids)


def test_generated_families_declare_non_editable_policy() -> None:
    from ai_engineering.config.mirror_inventory import get_mirror_families

    families = {family.family_id: family for family in get_mirror_families()}

    assert families["codex-skills"].edit_policy == "generated-do-not-edit"
    assert families["copilot-agents"].edit_policy == "generated-do-not-edit"
    assert families["specialist-agents"].edit_policy == "generated-do-not-edit"


def test_provider_maps_match_current_install_contract() -> None:
    from ai_engineering.config.mirror_inventory import (
        get_internal_specialist_agent_targets,
        get_manual_instruction_files,
        get_provider_file_maps,
        get_provider_tree_maps,
    )

    assert get_provider_file_maps()["claude_code"] == {
        "CLAUDE.md": "CLAUDE.md",
    }
    assert get_provider_file_maps()["github_copilot"] == {
        "AGENTS.md": "AGENTS.md",
        "copilot-instructions.md": ".github/copilot-instructions.md",
    }
    assert get_provider_file_maps()["gemini"] == {
        "AGENTS.md": "AGENTS.md",
        "GEMINI.md": "GEMINI.md",
    }
    assert get_provider_file_maps()["codex"] == {
        "AGENTS.md": "AGENTS.md",
    }

    assert get_provider_tree_maps()["claude_code"] == [
        (".claude", ".claude"),
    ]
    assert get_provider_tree_maps()["codex"] == [
        (".codex", ".codex"),
    ]
    assert get_provider_tree_maps()["github_copilot"] == [
        (".github/skills", ".github/skills"),
        (".github/hooks", ".github/hooks"),
        ("agents", ".github/agents"),
        ("instructions", ".github/instructions"),
    ]

    assert get_internal_specialist_agent_targets() == {
        "github_copilot": (
            ".github/agents/internal",
            "src/ai_engineering/templates/project/agents/internal",
        ),
        "gemini": (
            ".gemini/agents/internal",
            "src/ai_engineering/templates/project/.gemini/agents/internal",
        ),
        "codex": (
            ".codex/agents/internal",
            "src/ai_engineering/templates/project/.codex/agents/internal",
        ),
    }
    assert get_manual_instruction_files() == (
        "testing.instructions.md",
        "markdown.instructions.md",
        "sonarqube_mcp.instructions.md",
    )


def test_validator_pairs_and_sync_roots_follow_inventory_contract() -> None:
    from ai_engineering.config.mirror_inventory import (
        get_mirror_families,
        get_validator_pair_roots,
    )
    from ai_engineering.validator._shared import (
        _CLAUDE_COMMANDS_MIRROR,
        _CODEX_AGENTS_MIRROR,
        _CODEX_SKILLS_MIRROR,
        _COPILOT_AGENTS_MIRROR,
        _COPILOT_SKILLS_MIRROR,
        _GEMINI_AGENTS_MIRROR,
        _GEMINI_SKILLS_MIRROR,
    )
    from scripts.sync_command_mirrors import (
        CODEX_AGENTS,
        CODEX_SKILLS,
        GEMINI_AGENTS,
        GITHUB_AGENTS,
        GITHUB_INSTRUCTIONS,
        GITHUB_SKILLS,
        ROOT,
        TPL_CODEX_AGENTS,
        TPL_CODEX_SKILLS,
        TPL_GEMINI_AGENTS,
        TPL_GITHUB_AGENTS,
        TPL_GITHUB_SKILLS,
    )

    families = {family.family_id: family for family in get_mirror_families()}
    validator_pairs = get_validator_pair_roots()

    assert validator_pairs["claude-commands"] == _CLAUDE_COMMANDS_MIRROR
    assert validator_pairs["codex-skills"] == _CODEX_SKILLS_MIRROR
    assert validator_pairs["codex-agents"] == _CODEX_AGENTS_MIRROR
    assert validator_pairs["gemini-skills"] == _GEMINI_SKILLS_MIRROR
    assert validator_pairs["gemini-agents"] == _GEMINI_AGENTS_MIRROR
    assert validator_pairs["copilot-skills"] == _COPILOT_SKILLS_MIRROR
    assert validator_pairs["copilot-agents"] == _COPILOT_AGENTS_MIRROR
    assert validator_pairs["generated-instructions"] == (
        ".github/instructions",
        "src/ai_engineering/templates/project/instructions",
    )

    assert ROOT / families["codex-skills"].repo_surface_rel == CODEX_SKILLS
    assert ROOT / families["codex-skills"].template_surface_rel == TPL_CODEX_SKILLS
    assert ROOT / families["codex-agents"].repo_surface_rel == CODEX_AGENTS
    assert ROOT / families["codex-agents"].template_surface_rel == TPL_CODEX_AGENTS
    assert ROOT / families["gemini-agents"].repo_surface_rel == GEMINI_AGENTS
    assert ROOT / families["gemini-agents"].template_surface_rel == TPL_GEMINI_AGENTS
    assert ROOT / families["copilot-skills"].repo_surface_rel == GITHUB_SKILLS
    assert ROOT / families["copilot-skills"].template_surface_rel == TPL_GITHUB_SKILLS
    assert ROOT / families["copilot-agents"].repo_surface_rel == GITHUB_AGENTS
    assert ROOT / families["copilot-agents"].template_surface_rel == TPL_GITHUB_AGENTS
    assert ROOT / families["generated-instructions"].repo_surface_rel == GITHUB_INSTRUCTIONS
    assert ROOT / families["manual-instructions"].repo_surface_rel == GITHUB_INSTRUCTIONS
