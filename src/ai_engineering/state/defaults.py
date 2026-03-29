"""Default state payloads for bootstrapping ai-engineering installations.

Provides factory functions that create default instances of each state model
with sensible initial values. Used by the installer during first-time setup.
"""

from __future__ import annotations

from .models import (
    DecisionStore,
    FrameworkUpdatePolicy,
    InstallState,
    InstinctMeta,
    OwnershipEntry,
    OwnershipLevel,
    OwnershipMap,
    UpdateMetadata,
)


def default_update_metadata(*, context: str) -> UpdateMetadata:
    """Create a standard update metadata block.

    Args:
        context: Brief description of the update context.

    Returns:
        UpdateMetadata with standard rationale/gain/impact.
    """
    return UpdateMetadata(
        rationale=f"initialize {context}",
        expectedGain="consistent framework state tracking",
        potentialImpact="framework tools depend on this file",
    )


def default_install_state() -> InstallState:
    """Create a default install state for a new installation.

    Returns:
        InstallState with empty tooling and platforms dicts.
    """
    return InstallState()


_DEFAULT_OWNERSHIP_PATHS: list[tuple[str, OwnershipLevel, FrameworkUpdatePolicy]] = [
    # -- .ai-engineering/ governance ----------------------------------------
    (".ai-engineering/README.md", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (".ai-engineering/manifest.yml", OwnershipLevel.TEAM_MANAGED, FrameworkUpdatePolicy.DENY),
    (
        ".ai-engineering/runbooks/**",
        OwnershipLevel.FRAMEWORK_MANAGED,
        FrameworkUpdatePolicy.ALLOW,
    ),
    (
        ".ai-engineering/scripts/hooks/**",
        OwnershipLevel.FRAMEWORK_MANAGED,
        FrameworkUpdatePolicy.ALLOW,
    ),
    (
        ".ai-engineering/contexts/languages/**",
        OwnershipLevel.FRAMEWORK_MANAGED,
        FrameworkUpdatePolicy.ALLOW,
    ),
    (
        ".ai-engineering/contexts/frameworks/**",
        OwnershipLevel.FRAMEWORK_MANAGED,
        FrameworkUpdatePolicy.ALLOW,
    ),
    (".ai-engineering/contexts/team/**", OwnershipLevel.TEAM_MANAGED, FrameworkUpdatePolicy.DENY),
    (
        ".ai-engineering/contexts/project-identity.md",
        OwnershipLevel.TEAM_MANAGED,
        FrameworkUpdatePolicy.DENY,
    ),
    (
        ".ai-engineering/contexts/*.md",
        OwnershipLevel.FRAMEWORK_MANAGED,
        FrameworkUpdatePolicy.ALLOW,
    ),
    (
        ".ai-engineering/state/install-state.json",
        OwnershipLevel.SYSTEM_MANAGED,
        FrameworkUpdatePolicy.ALLOW,
    ),
    (
        ".ai-engineering/state/ownership-map.json",
        OwnershipLevel.SYSTEM_MANAGED,
        FrameworkUpdatePolicy.ALLOW,
    ),
    (
        ".ai-engineering/state/decision-store.json",
        OwnershipLevel.SYSTEM_MANAGED,
        FrameworkUpdatePolicy.ALLOW,
    ),
    (
        ".ai-engineering/state/framework-events.ndjson",
        OwnershipLevel.SYSTEM_MANAGED,
        FrameworkUpdatePolicy.APPEND_ONLY,
    ),
    (
        ".ai-engineering/state/framework-capabilities.json",
        OwnershipLevel.SYSTEM_MANAGED,
        FrameworkUpdatePolicy.ALLOW,
    ),
    (
        ".ai-engineering/state/instinct-observations.ndjson",
        OwnershipLevel.SYSTEM_MANAGED,
        FrameworkUpdatePolicy.APPEND_ONLY,
    ),
    (
        ".ai-engineering/instincts/instincts.yml",
        OwnershipLevel.SYSTEM_MANAGED,
        FrameworkUpdatePolicy.ALLOW,
    ),
    (
        ".ai-engineering/instincts/context.md",
        OwnershipLevel.SYSTEM_MANAGED,
        FrameworkUpdatePolicy.ALLOW,
    ),
    (
        ".ai-engineering/instincts/meta.json",
        OwnershipLevel.SYSTEM_MANAGED,
        FrameworkUpdatePolicy.ALLOW,
    ),
    # -- project root files -------------------------------------------------
    ("CLAUDE.md", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    ("AGENTS.md", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    ("GEMINI.md", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (".gitleaks.toml", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (".semgrep.yml", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    # -- .claude/ (specific before glob) ------------------------------------
    (".claude/settings.json", OwnershipLevel.TEAM_MANAGED, FrameworkUpdatePolicy.DENY),
    (".claude/**", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    # -- .codex/ ------------------------------------------------------------
    (".codex/**", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    # -- .gemini/ -----------------------------------------------------------
    (".gemini/**", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    # -- .github/ (specific before globs) -----------------------------------
    (
        ".github/copilot-instructions.md",
        OwnershipLevel.FRAMEWORK_MANAGED,
        FrameworkUpdatePolicy.ALLOW,
    ),
    (".github/CODEOWNERS", OwnershipLevel.TEAM_MANAGED, FrameworkUpdatePolicy.DENY),
    (".github/dependabot.yml", OwnershipLevel.TEAM_MANAGED, FrameworkUpdatePolicy.DENY),
    (
        ".github/pull_request_template.md",
        OwnershipLevel.TEAM_MANAGED,
        FrameworkUpdatePolicy.DENY,
    ),
    (".github/skills/**", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (".github/agents/**", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (".github/instructions/**", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (
        ".github/ISSUE_TEMPLATE/**",
        OwnershipLevel.FRAMEWORK_MANAGED,
        FrameworkUpdatePolicy.ALLOW,
    ),
    (".github/hooks/**", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
]


def default_ownership_map() -> OwnershipMap:
    """Create the default ownership map with standard path rules.

    Returns:
        OwnershipMap with framework/team/project/system ownership rules.
    """
    return OwnershipMap(
        schema_version="1.0",
        update_metadata=default_update_metadata(context="path ownership map"),
        paths=[
            OwnershipEntry(pattern=pattern, owner=owner, frameworkUpdate=policy)
            for pattern, owner, policy in _DEFAULT_OWNERSHIP_PATHS
        ],
    )


def default_decision_store() -> DecisionStore:
    """Create an empty decision store.

    Returns:
        DecisionStore with no decisions.
    """
    return DecisionStore(
        schema_version="1.1",
        update_metadata=default_update_metadata(context="decision store"),
        decisions=[],
    )


def default_instinct_meta() -> InstinctMeta:
    """Create default bookkeeping for simplified instinct learning."""
    return InstinctMeta()
