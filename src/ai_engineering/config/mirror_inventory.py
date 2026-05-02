"""Shared mirror-family inventory for HX-03 mirror governance."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MirrorFamily:
    """One governed mirror family or boundary classification."""

    family_id: str
    provider: str | None
    public: bool
    generated: bool
    edit_policy: str
    transform_mode: str
    repo_surface_rel: str | None = None
    template_surface_rel: str | None = None


@dataclass(frozen=True)
class GovernanceMirrorRule:
    """Validator rule for the governance template projection."""

    canonical_rel: str
    mirror_rel: str
    glob_patterns: tuple[str, ...]
    exclusions: tuple[str, ...]


_MIRROR_FAMILIES: tuple[MirrorFamily, ...] = (
    MirrorFamily(
        family_id="governance-template",
        provider=None,
        public=False,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="copy-filtered",
        template_surface_rel="src/ai_engineering/templates/.ai-engineering",
    ),
    MirrorFamily(
        family_id="claude-commands",
        provider="claude_code",
        public=True,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="copy",
        repo_surface_rel=".claude/commands",
        template_surface_rel="src/ai_engineering/templates/project/.claude/commands",
    ),
    MirrorFamily(
        family_id="claude-skills",
        provider="claude_code",
        public=True,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="copy",
        repo_surface_rel=".claude/skills",
        template_surface_rel="src/ai_engineering/templates/project/.claude/skills",
    ),
    MirrorFamily(
        family_id="claude-agents",
        provider="claude_code",
        public=True,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="copy",
        repo_surface_rel=".claude/agents",
        template_surface_rel="src/ai_engineering/templates/project/.claude/agents",
    ),
    MirrorFamily(
        family_id="codex-skills",
        provider="codex",
        public=True,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="translate",
        repo_surface_rel=".codex/skills",
        template_surface_rel="src/ai_engineering/templates/project/.codex/skills",
    ),
    MirrorFamily(
        family_id="codex-agents",
        provider="codex",
        public=True,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="translate",
        repo_surface_rel=".codex/agents",
        template_surface_rel="src/ai_engineering/templates/project/.codex/agents",
    ),
    MirrorFamily(
        family_id="gemini-skills",
        provider="gemini",
        public=True,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="translate",
        repo_surface_rel=".gemini/skills",
        template_surface_rel="src/ai_engineering/templates/project/.gemini/skills",
    ),
    MirrorFamily(
        family_id="gemini-agents",
        provider="gemini",
        public=True,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="translate",
        repo_surface_rel=".gemini/agents",
        template_surface_rel="src/ai_engineering/templates/project/.gemini/agents",
    ),
    MirrorFamily(
        family_id="copilot-skills",
        provider="github_copilot",
        public=True,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="render-filtered",
        repo_surface_rel=".github/skills",
        template_surface_rel="src/ai_engineering/templates/project/.github/skills",
    ),
    MirrorFamily(
        family_id="copilot-agents",
        provider="github_copilot",
        public=True,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="render",
        repo_surface_rel=".github/agents",
        template_surface_rel="src/ai_engineering/templates/project/agents",
    ),
    MirrorFamily(
        family_id="specialist-agents",
        provider="github_copilot",
        public=False,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="copy-internal",
        repo_surface_rel=".github/agents",
        template_surface_rel="src/ai_engineering/templates/project/agents",
    ),
    MirrorFamily(
        family_id="generated-instructions",
        provider="github_copilot",
        public=False,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="render-from-context",
        repo_surface_rel=".github/instructions",
        template_surface_rel="src/ai_engineering/templates/project/instructions",
    ),
    MirrorFamily(
        family_id="manual-instructions",
        provider="github_copilot",
        public=False,
        generated=False,
        edit_policy="manual",
        transform_mode="manual",
        repo_surface_rel=".github/instructions",
        template_surface_rel="src/ai_engineering/templates/project/instructions",
    ),
)

_GOVERNANCE_MIRROR_RULE = GovernanceMirrorRule(
    canonical_rel=".ai-engineering",
    mirror_rel="src/ai_engineering/templates/.ai-engineering",
    glob_patterns=("contexts/**/*.md", "runbooks/**/*.md", "README.md"),
    exclusions=("context/", "contexts/team/", "CONSTITUTION.md", "state/", "evals/", "tasks/"),
)

_VALIDATOR_PAIR_ROOTS: dict[str, tuple[str, str]] = {
    "claude-commands": (
        ".claude/commands",
        "src/ai_engineering/templates/project/.claude/commands",
    ),
    "claude-skills": (
        ".claude/skills",
        "src/ai_engineering/templates/project/.claude/skills",
    ),
    "claude-agents": (
        ".claude/agents",
        "src/ai_engineering/templates/project/.claude/agents",
    ),
    "codex-skills": (
        ".codex/skills",
        "src/ai_engineering/templates/project/.codex/skills",
    ),
    "codex-agents": (
        ".codex/agents",
        "src/ai_engineering/templates/project/.codex/agents",
    ),
    "gemini-skills": (
        ".gemini/skills",
        "src/ai_engineering/templates/project/.gemini/skills",
    ),
    "gemini-agents": (
        ".gemini/agents",
        "src/ai_engineering/templates/project/.gemini/agents",
    ),
    "copilot-skills": (
        ".github/skills",
        "src/ai_engineering/templates/project/.github/skills",
    ),
    "generated-instructions": (
        ".github/instructions",
        "src/ai_engineering/templates/project/instructions",
    ),
    "copilot-agents": (
        ".github/agents",
        "src/ai_engineering/templates/project/agents",
    ),
}

_MANUAL_INSTRUCTION_FILES: tuple[str, ...] = (
    "testing.instructions.md",
    "markdown.instructions.md",
    "sonarqube_mcp.instructions.md",
)

_PROVIDER_FILE_MAPS: dict[str, dict[str, str]] = {
    "claude_code": {
        "CLAUDE.md": "CLAUDE.md",
    },
    "github_copilot": {
        "AGENTS.md": "AGENTS.md",
        "copilot-instructions.md": ".github/copilot-instructions.md",
    },
    "gemini": {
        "AGENTS.md": "AGENTS.md",
        "GEMINI.md": "GEMINI.md",
    },
    "codex": {
        "AGENTS.md": "AGENTS.md",
    },
}

_PROVIDER_TREE_MAPS: dict[str, list[tuple[str, str]]] = {
    "claude_code": [
        (".claude", ".claude"),
    ],
    "github_copilot": [
        (".github/skills", ".github/skills"),
        (".github/hooks", ".github/hooks"),
        ("agents", ".github/agents"),
        ("instructions", ".github/instructions"),
    ],
    "gemini": [
        (".gemini", ".gemini"),
    ],
    "codex": [
        (".codex", ".codex"),
    ],
}

_SPECIALIST_AGENT_TARGETS: dict[str, tuple[str, str]] = {
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


def get_mirror_families() -> tuple[MirrorFamily, ...]:
    """Return the governed mirror-family inventory."""
    return _MIRROR_FAMILIES


def get_mirror_family_index() -> dict[str, MirrorFamily]:
    """Return the mirror inventory keyed by family id."""
    return {family.family_id: family for family in _MIRROR_FAMILIES}


def get_public_mirror_family_ids() -> frozenset[str]:
    """Return public generated mirror family ids only."""
    return frozenset(
        family.family_id for family in _MIRROR_FAMILIES if family.public and family.generated
    )


def get_governance_mirror_rule() -> tuple[str, str, list[str], list[str]]:
    """Return the governance mirror validator rule in legacy tuple form."""
    return (
        _GOVERNANCE_MIRROR_RULE.canonical_rel,
        _GOVERNANCE_MIRROR_RULE.mirror_rel,
        list(_GOVERNANCE_MIRROR_RULE.glob_patterns),
        list(_GOVERNANCE_MIRROR_RULE.exclusions),
    )


def get_validator_pair_roots() -> dict[str, tuple[str, str]]:
    """Return validator canonical/template root pairs keyed by family id."""
    return dict(_VALIDATOR_PAIR_ROOTS)


def get_provider_file_maps() -> dict[str, dict[str, str]]:
    """Return provider-specific root file overlays."""
    return {provider: dict(files) for provider, files in _PROVIDER_FILE_MAPS.items()}


def get_provider_tree_maps() -> dict[str, list[tuple[str, str]]]:
    """Return provider-specific template tree mappings."""
    return {provider: list(trees) for provider, trees in _PROVIDER_TREE_MAPS.items()}


def get_internal_specialist_agent_targets() -> dict[str, tuple[str, str]]:
    """Return provider-local repo/template roots for internal specialist agents."""
    return {
        provider: (repo_rel, template_rel)
        for provider, (repo_rel, template_rel) in _SPECIALIST_AGENT_TARGETS.items()
    }


def get_manual_instruction_files() -> tuple[str, ...]:
    """Return the hand-maintained Copilot instruction filenames."""
    return _MANUAL_INSTRUCTION_FILES


def get_generated_provenance_fields(family_id: str, canonical_source: str) -> dict[str, str]:
    """Return provenance fields for a generated mirror family."""
    family = get_mirror_family_index()[family_id]
    return {
        "mirror_family": family.family_id,
        "generated_by": "ai-eng sync",
        "canonical_source": canonical_source,
        "edit_policy": family.edit_policy,
    }


__all__ = [
    "MirrorFamily",
    "get_generated_provenance_fields",
    "get_governance_mirror_rule",
    "get_internal_specialist_agent_targets",
    "get_manual_instruction_files",
    "get_mirror_families",
    "get_mirror_family_index",
    "get_provider_file_maps",
    "get_provider_tree_maps",
    "get_public_mirror_family_ids",
    "get_validator_pair_roots",
]
