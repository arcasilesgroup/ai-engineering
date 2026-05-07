"""Default state payloads for bootstrapping ai-engineering installations.

Provides factory functions that create default instances of each state model
with sensible initial values. Used by the installer during first-time setup.
"""

from __future__ import annotations

from collections.abc import Mapping

from ai_engineering.config.manifest import RootEntryPointConfig

from .control_plane import resolve_control_plane_contract
from .models import (
    DecisionStore,
    InstallState,
    InstinctMeta,
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


def projection_update_metadata(*, context: str, source: str) -> UpdateMetadata:
    """Create metadata for generated state projections."""
    return UpdateMetadata(
        rationale=f"generate {context} from {source}",
        expectedGain="derived projection for downstream tooling; not a peer authority",
        potentialImpact=f"regenerate this snapshot from {source} when the source contract changes",
    )


def default_install_state() -> InstallState:
    """Create a default install state for a new installation.

    Returns:
        InstallState with empty tooling and platforms dicts.
    """
    return InstallState()


def default_ownership_paths(
    *,
    root_entry_points: Mapping[str, RootEntryPointConfig] | None = None,
) -> list[tuple[str, OwnershipLevel, FrameworkUpdatePolicy]]:  # noqa: F821  # ty:ignore[unresolved-reference]
    """Return the default ownership rule table for bootstrap and repair flows."""
    return [
        (entry.pattern, entry.owner, entry.framework_update)
        for entry in resolve_control_plane_contract(
            root_entry_points=root_entry_points,
        ).ownership_entries()
    ]


def default_ownership_map(
    *,
    root_entry_points: Mapping[str, RootEntryPointConfig] | None = None,
) -> OwnershipMap:
    """Create the default ownership map with standard path rules.

    Args:
        root_entry_points: Optional manifest contract for governed root
            instruction surfaces. When omitted, no governed root-entry rules are
            synthesized.

    Returns:
        OwnershipMap with framework/team/project/system ownership rules.
    """
    contract = resolve_control_plane_contract(root_entry_points=root_entry_points)
    return OwnershipMap(
        schema_version="1.0",
        update_metadata=projection_update_metadata(
            context="path ownership map",
            source="ai_engineering.state.control_plane.resolve_control_plane_contract",
        ),
        paths=list(contract.ownership_entries()),
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
