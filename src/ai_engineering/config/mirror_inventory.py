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
        provider="claude-code",
        public=True,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="copy",
        repo_surface_rel=".claude/commands",
        template_surface_rel="src/ai_engineering/templates/project/.claude/commands",
    ),
    MirrorFamily(
        family_id="claude-skills",
        provider="claude-code",
        public=True,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="copy",
        repo_surface_rel=".claude/skills",
        template_surface_rel="src/ai_engineering/templates/project/.claude/skills",
    ),
    MirrorFamily(
        family_id="claude-agents",
        provider="claude-code",
        public=True,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="copy",
        repo_surface_rel=".claude/agents",
        template_surface_rel="src/ai_engineering/templates/project/.claude/agents",
    ),
    MirrorFamily(
        family_id="cursor-agents",
        provider="cursor",
        public=True,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="translate",
        template_surface_rel="src/ai_engineering/templates/project/.cursor/agents",
    ),
    # spec-201 D-201-23: `.codex/agents` was hard-deleted, and OpenCode's
    # agent files had been claiming the `codex-agents` family (which also
    # rewrote their cross-references into `.codex/agents/`, the live
    # `/ai-review` preflight bug D-201-04 names). OpenCode agents now own
    # their family; per D-201-22 the agent tree itself does NOT collapse.
    MirrorFamily(
        family_id="opencode-agents",
        provider="opencode",
        public=True,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="translate",
        repo_surface_rel=".opencode/agents",
        template_surface_rel="src/ai_engineering/templates/project/.opencode/agents",
    ),
    MirrorFamily(
        family_id="antigravity-skills",
        provider="antigravity",
        public=True,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="translate",
        repo_surface_rel=".agents/skills",
        template_surface_rel="src/ai_engineering/templates/project/.agents/skills",
    ),
    MirrorFamily(
        family_id="antigravity-agents",
        provider="antigravity",
        public=True,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="translate",
        repo_surface_rel=".agents/agents",
        template_surface_rel="src/ai_engineering/templates/project/.agents/agents",
    ),
    MirrorFamily(
        family_id="copilot-agents",
        provider="github-copilot",
        public=True,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="render",
        repo_surface_rel=".github/agents",
        template_surface_rel="src/ai_engineering/templates/project/agents",
    ),
    MirrorFamily(
        family_id="specialist-agents",
        provider="github-copilot",
        public=False,
        generated=True,
        edit_policy="generated-do-not-edit",
        transform_mode="copy-internal",
        repo_surface_rel=".github/agents",
        template_surface_rel="src/ai_engineering/templates/project/agents",
    ),
    # spec-128 D-128-04, D-128-07: generated-instructions and manual-instructions
    # families removed — .github/instructions/ surface deleted entirely.
)

_GOVERNANCE_MIRROR_RULE = GovernanceMirrorRule(
    canonical_rel=".ai-engineering",
    mirror_rel="src/ai_engineering/templates/.ai-engineering",
    glob_patterns=("reference/**/*.md", "README.md"),
    exclusions=("team/", "CONSTITUTION.md", "state/", "tasks/", "runtime/"),
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
    "cursor-agents": (
        "src/ai_engineering/templates/project/.cursor/agents",
        "src/ai_engineering/templates/project/.cursor/agents",
    ),
    # spec-201: repo-root `.opencode/agents` is dual-written by Surface 5b,
    # so it can finally be pair-validated against its template twin.
    "opencode-agents": (
        ".opencode/agents",
        "src/ai_engineering/templates/project/.opencode/agents",
    ),
    "antigravity-skills": (
        ".agents/skills",
        "src/ai_engineering/templates/project/.agents/skills",
    ),
    "antigravity-agents": (
        ".agents/agents",
        "src/ai_engineering/templates/project/.agents/agents",
    ),
    # spec-128 D-128-04, D-128-07: generated-instructions removed.
    "copilot-agents": (
        ".github/agents",
        "src/ai_engineering/templates/project/agents",
    ),
}

# spec-128 D-128-04: manual instruction files removed entirely.
_MANUAL_INSTRUCTION_FILES: tuple[str, ...] = ()

_PROVIDER_FILE_MAPS: dict[str, dict[str, str]] = {
    "claude-code": {
        "CLAUDE.md": "CLAUDE.md",
    },
    "github-copilot": {
        "AGENTS.md": "AGENTS.md",
        "copilot-instructions.md": ".github/copilot-instructions.md",
    },
    "codex": {
        "AGENTS.md": "AGENTS.md",
    },
    "antigravity": {
        "AGENTS.md": "AGENTS.md",
    },
}

# spec-201 D-201-05: every enabled surface is registered here, and every
# non-Claude surface carries the shared `.agents/skills` payload. The
# validator previously knew four providers while the manifest enabled
# six, which is why `dev sync --check` reported clean over a rotting
# surface.
_PROVIDER_TREE_MAPS: dict[str, list[tuple[str, str]]] = {
    "claude-code": [
        (".claude", ".claude"),
    ],
    "github-copilot": [
        (".agents/skills", ".agents/skills"),
        (".github/hooks", ".github/hooks"),
        ("agents", ".github/agents"),
    ],
    "codex": [
        (".codex", ".codex"),
        (".agents/skills", ".agents/skills"),
    ],
    "opencode": [
        (".opencode", ".opencode"),
        (".agents/skills", ".agents/skills"),
    ],
    "cursor": [
        (".cursor", ".cursor"),
        (".agents/skills", ".agents/skills"),
    ],
    # spec-201: mirrors installer/templates.py — the two real subtrees, so
    # the shared skills row deduplicates against the other surfaces.
    "antigravity": [
        (".agents/skills", ".agents/skills"),
        (".agents/agents", ".agents/agents"),
    ],
}

_SPECIALIST_AGENT_TARGETS: dict[str, tuple[str, str]] = {
    "github-copilot": (
        ".github/agents/internal",
        "src/ai_engineering/templates/project/agents/internal",
    ),
    "antigravity": (
        ".agents/agents/internal",
        "src/ai_engineering/templates/project/.agents/agents/internal",
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
