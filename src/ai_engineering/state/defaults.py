"""Default state payloads for bootstrapping ai-engineering installations.

Provides factory functions that create default instances of each state model
with sensible initial values. Used by the installer during first-time setup.
"""

from __future__ import annotations

from .models import (
    AzureDevOpsExtension,
    DecisionStore,
    FrameworkUpdatePolicy,
    InstallManifest,
    OwnershipEntry,
    OwnershipLevel,
    OwnershipMap,
    SourcesLock,
    ToolingReadiness,
    UpdateMetadata,
    VcsExtensions,
    VcsProviders,
    VcsProviderStatus,
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


def default_install_manifest(
    *,
    stacks: list[str] | None = None,
    ides: list[str] | None = None,
) -> InstallManifest:
    """Create a default install manifest for a new installation.

    Args:
        stacks: Initial stacks to install. Defaults to ["python"].
        ides: Initial IDEs to install. Defaults to ["terminal"].

    Returns:
        InstallManifest with default tooling readiness.
    """
    return InstallManifest(
        schemaVersion="1.1",
        updateMetadata=default_update_metadata(context="installation manifest"),
        frameworkVersion="0.1.0",
        installedStacks=stacks or ["python"],
        installedIdes=ides or ["terminal"],
        providers=VcsProviders(
            primary="github",
            enabled=["github"],
            extensions=VcsExtensions(
                azure_devops=AzureDevOpsExtension(enabled=False),
            ),
        ),
        toolingReadiness=ToolingReadiness(),
    )


_DEFAULT_OWNERSHIP_PATHS: list[tuple[str, OwnershipLevel, FrameworkUpdatePolicy]] = [
    (".ai-engineering/standards/framework/**", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (".ai-engineering/standards/team/**", OwnershipLevel.TEAM_MANAGED, FrameworkUpdatePolicy.DENY),
    (".ai-engineering/context/**", OwnershipLevel.PROJECT_MANAGED, FrameworkUpdatePolicy.DENY),
    (".ai-engineering/skills/**", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (".ai-engineering/agents/**", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    ("CLAUDE.md", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    ("codex.md", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    ("AGENTS.md", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (".github/copilot-instructions.md", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (".github/copilot/**", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (".github/instructions/**", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (".ai-engineering/state/install-manifest.json", OwnershipLevel.SYSTEM_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (".ai-engineering/state/ownership-map.json", OwnershipLevel.SYSTEM_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (".ai-engineering/state/sources.lock.json", OwnershipLevel.SYSTEM_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (".ai-engineering/state/decision-store.json", OwnershipLevel.SYSTEM_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (".ai-engineering/state/audit-log.ndjson", OwnershipLevel.SYSTEM_MANAGED, FrameworkUpdatePolicy.APPEND_ONLY),
]


def default_ownership_map() -> OwnershipMap:
    """Create the default ownership map with standard path rules.

    Returns:
        OwnershipMap with framework/team/project/system ownership rules.
    """
    return OwnershipMap(
        schemaVersion="1.0",
        updateMetadata=default_update_metadata(context="path ownership map"),
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
        schemaVersion="1.1",
        updateMetadata=default_update_metadata(context="decision store"),
        decisions=[],
    )


def default_sources_lock() -> SourcesLock:
    """Create a default sources lock with no remote sources.

    Returns:
        SourcesLock with remote disabled and empty source list.
    """
    return SourcesLock(
        schemaVersion="1.0",
        updateMetadata=default_update_metadata(context="sources lock"),
        defaultRemoteEnabled=False,
        sources=[],
    )
