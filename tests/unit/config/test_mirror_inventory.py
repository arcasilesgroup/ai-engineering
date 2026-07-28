"""Contract tests for the shared HX-03 mirror inventory model."""

from __future__ import annotations


def test_inventory_contains_expected_families() -> None:
    from ai_engineering.config.mirror_inventory import get_mirror_families

    families = {family.family_id: family for family in get_mirror_families()}

    # spec-128 D-128-04, D-128-07: generated-instructions + manual-instructions
    # families removed (.github/instructions surface deleted entirely).
    assert {
        "governance-template",
        "claude-commands",
        "claude-skills",
        "claude-agents",
        "cursor-agents",
        "antigravity-skills",
        "antigravity-agents",
        "copilot-agents",
        "specialist-agents",
    }.issubset(families)
    assert "generated-instructions" not in families
    assert "manual-instructions" not in families
    # spec-201 D-201-04: the four collapsed skill families are hard-deleted.
    for dead in ("codex-skills", "codex-agents", "cursor-skills", "copilot-skills"):
        assert dead not in families


def test_public_inventory_excludes_internal_and_manual_families() -> None:
    from ai_engineering.config.mirror_inventory import (
        get_mirror_families,
        get_public_mirror_family_ids,
    )

    families = {family.family_id: family for family in get_mirror_families()}
    public_ids = get_public_mirror_family_ids()

    assert families["specialist-agents"].public is False
    # spec-128: generated-instructions + manual-instructions families removed.
    assert "generated-instructions" not in families
    assert "manual-instructions" not in families
    assert "specialist-agents" not in public_ids
    assert "generated-instructions" not in public_ids
    assert "manual-instructions" not in public_ids
    assert {
        "claude-skills",
        "claude-agents",
        "cursor-agents",
        "antigravity-skills",
        "antigravity-agents",
        "copilot-agents",
    }.issubset(public_ids)


def test_generated_families_declare_non_editable_policy() -> None:
    from ai_engineering.config.mirror_inventory import get_mirror_families

    families = {family.family_id: family for family in get_mirror_families()}

    assert families["antigravity-skills"].edit_policy == "generated-do-not-edit"
    assert families["copilot-agents"].edit_policy == "generated-do-not-edit"
    assert families["specialist-agents"].edit_policy == "generated-do-not-edit"


def test_provider_maps_match_current_install_contract() -> None:
    from ai_engineering.config.mirror_inventory import (
        get_internal_specialist_agent_targets,
        get_manual_instruction_files,
        get_provider_file_maps,
        get_provider_tree_maps,
    )

    assert get_provider_file_maps()["claude-code"] == {
        "CLAUDE.md": "CLAUDE.md",
    }
    assert get_provider_file_maps()["github-copilot"] == {
        "AGENTS.md": "AGENTS.md",
        "copilot-instructions.md": ".github/copilot-instructions.md",
    }
    assert "gemini-cli" not in get_provider_file_maps()
    assert get_provider_file_maps()["codex"] == {
        "AGENTS.md": "AGENTS.md",
    }
    assert get_provider_file_maps()["antigravity"] == {
        "AGENTS.md": "AGENTS.md",
    }

    # spec-201 D-201-04/D-201-05: every non-Claude surface carries the
    # shared `.agents/skills` payload, and all 6 surfaces are registered.
    assert get_provider_tree_maps()["claude-code"] == [
        (".claude", ".claude"),
    ]
    assert get_provider_tree_maps()["codex"] == [
        (".codex", ".codex"),
        (".agents/skills", ".agents/skills"),
    ]
    assert get_provider_tree_maps()["github-copilot"] == [
        (".agents/skills", ".agents/skills"),
        (".github/hooks", ".github/hooks"),
        ("agents", ".github/agents"),
    ]
    assert get_provider_tree_maps()["opencode"] == [
        (".opencode", ".opencode"),
        (".agents/skills", ".agents/skills"),
    ]
    assert get_provider_tree_maps()["cursor"] == [
        (".cursor", ".cursor"),
        (".agents/skills", ".agents/skills"),
    ]
    assert get_provider_tree_maps()["antigravity"] == [
        (".agents/skills", ".agents/skills"),
        (".agents/agents", ".agents/agents"),
    ]
    assert set(get_provider_tree_maps()) == {
        "claude-code",
        "github-copilot",
        "codex",
        "opencode",
        "cursor",
        "antigravity",
    }

    # spec-201 D-201-23: the codex specialist-agent target is gone with
    # `.codex/agents` — Codex's agent namespace accepts TOML only.
    assert get_internal_specialist_agent_targets() == {
        "github-copilot": (
            ".github/agents/internal",
            "src/ai_engineering/templates/project/agents/internal",
        ),
        "antigravity": (
            ".agents/agents/internal",
            "src/ai_engineering/templates/project/.agents/agents/internal",
        ),
    }
    # spec-128 D-128-04: manual instruction files removed entirely.
    assert get_manual_instruction_files() == ()


def test_validator_pairs_and_sync_roots_follow_inventory_contract() -> None:
    from ai_engineering.config.mirror_inventory import (
        get_mirror_families,
        get_validator_pair_roots,
    )
    from ai_engineering.validator._shared import (
        _ANTIGRAVITY_AGENTS_MIRROR,
        _ANTIGRAVITY_SKILLS_MIRROR,
        _CLAUDE_COMMANDS_MIRROR,
        _COPILOT_AGENTS_MIRROR,
    )
    from scripts.sync_command_mirrors import (
        ANTIGRAVITY_AGENTS,
        ANTIGRAVITY_SKILLS,
        GITHUB_AGENTS,
        ROOT,
        TPL_ANTIGRAVITY_AGENTS,
        TPL_ANTIGRAVITY_SKILLS,
        TPL_GITHUB_AGENTS,
    )

    families = {family.family_id: family for family in get_mirror_families()}
    validator_pairs = get_validator_pair_roots()

    assert validator_pairs["claude-commands"] == _CLAUDE_COMMANDS_MIRROR
    assert validator_pairs["antigravity-skills"] == _ANTIGRAVITY_SKILLS_MIRROR
    assert validator_pairs["antigravity-agents"] == _ANTIGRAVITY_AGENTS_MIRROR
    assert validator_pairs["copilot-agents"] == _COPILOT_AGENTS_MIRROR
    # spec-201 D-201-04: the four collapsed skill families lose their pairs.
    for dead in ("codex-skills", "codex-agents", "cursor-skills", "copilot-skills"):
        assert dead not in validator_pairs
    # spec-128 D-128-04, D-128-07: generated-instructions + manual-instructions
    # families removed; .github/instructions/ surface deleted entirely.
    assert "generated-instructions" not in families
    assert "manual-instructions" not in families
    assert "generated-instructions" not in validator_pairs
    assert "manual-instructions" not in validator_pairs

    assert ROOT / families["antigravity-skills"].repo_surface_rel == ANTIGRAVITY_SKILLS
    assert ROOT / families["antigravity-skills"].template_surface_rel == TPL_ANTIGRAVITY_SKILLS
    assert ROOT / families["antigravity-agents"].repo_surface_rel == ANTIGRAVITY_AGENTS
    assert ROOT / families["antigravity-agents"].template_surface_rel == TPL_ANTIGRAVITY_AGENTS
    assert ROOT / families["copilot-agents"].repo_surface_rel == GITHUB_AGENTS
    assert ROOT / families["copilot-agents"].template_surface_rel == TPL_GITHUB_AGENTS
