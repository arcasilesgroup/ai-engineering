"""Shared control-plane authority contract for ownership and provenance.

This module centralizes the control-plane paths that runtime and validation
surfaces need to reason about consistently: constitutional authority,
workspace-charter compatibility aliases, and governed root-entry ownership.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from ai_engineering.config.manifest import RootEntryPointConfig

from .models import FrameworkUpdatePolicy, OwnershipEntry, OwnershipLevel

_CONSTITUTIONAL_PRIMARY = "CONSTITUTION.md"
_CONSTITUTIONAL_ALIASES: tuple[str, ...] = ()

_DEFAULT_ROOT_ENTRY_POINT_PATHS: tuple[str, ...] = (
    "CLAUDE.md",
    "AGENTS.md",
    "GEMINI.md",
    ".github/copilot-instructions.md",
)

_ROOT_ENTRY_POINT_OWNER_RULES: dict[
    str,
    tuple[OwnershipLevel, FrameworkUpdatePolicy],
] = {
    "framework": (
        OwnershipLevel.FRAMEWORK_MANAGED,
        FrameworkUpdatePolicy.ALLOW,
    ),
    "framework-managed": (
        OwnershipLevel.FRAMEWORK_MANAGED,
        FrameworkUpdatePolicy.ALLOW,
    ),
    "team": (
        OwnershipLevel.TEAM_MANAGED,
        FrameworkUpdatePolicy.DENY,
    ),
    "team-managed": (
        OwnershipLevel.TEAM_MANAGED,
        FrameworkUpdatePolicy.DENY,
    ),
    "project": (
        OwnershipLevel.PROJECT_MANAGED,
        FrameworkUpdatePolicy.DENY,
    ),
    "project-managed": (
        OwnershipLevel.PROJECT_MANAGED,
        FrameworkUpdatePolicy.DENY,
    ),
    "system": (
        OwnershipLevel.SYSTEM_MANAGED,
        FrameworkUpdatePolicy.ALLOW,
    ),
    "system-managed": (
        OwnershipLevel.SYSTEM_MANAGED,
        FrameworkUpdatePolicy.ALLOW,
    ),
}

_DEFAULT_CONTROL_PLANE_RULES: tuple[tuple[str, OwnershipLevel, FrameworkUpdatePolicy], ...] = (
    (".ai-engineering/README.md", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (".ai-engineering/manifest.yml", OwnershipLevel.TEAM_MANAGED, FrameworkUpdatePolicy.DENY),
    (".ai-engineering/runbooks/**", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
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
    (".ai-engineering/LESSONS.md", OwnershipLevel.TEAM_MANAGED, FrameworkUpdatePolicy.APPEND_ONLY),
    (_CONSTITUTIONAL_PRIMARY, OwnershipLevel.TEAM_MANAGED, FrameworkUpdatePolicy.DENY),
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
        ".ai-engineering/instincts/meta.json",
        OwnershipLevel.SYSTEM_MANAGED,
        FrameworkUpdatePolicy.ALLOW,
    ),
    (
        ".ai-engineering/instincts/proposals.md",
        OwnershipLevel.SYSTEM_MANAGED,
        FrameworkUpdatePolicy.ALLOW,
    ),
    (".gitleaks.toml", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (".semgrep.yml", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (".claude/settings.json", OwnershipLevel.TEAM_MANAGED, FrameworkUpdatePolicy.DENY),
    (".claude/**", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (".codex/**", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
    (".gemini/**", OwnershipLevel.FRAMEWORK_MANAGED, FrameworkUpdatePolicy.ALLOW),
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
)

_STATE_PLANE_DURABLE_RULES: tuple[str, ...] = (
    ".ai-engineering/state/decision-store.json",
    ".ai-engineering/state/framework-events.ndjson",
    ".ai-engineering/state/install-state.json",
)

_STATE_PLANE_DERIVED_RULES: tuple[str, ...] = (
    ".ai-engineering/state/ownership-map.json",
    ".ai-engineering/state/framework-capabilities.json",
)

_STATE_PLANE_RESIDUE_RULES: tuple[str, ...] = (
    ".ai-engineering/state/gate-findings.json",
    ".ai-engineering/state/watch-residuals.json",
    ".ai-engineering/state/gate-cache/**",
    ".ai-engineering/state/locks/**",
)

_STATE_PLANE_SPEC_LOCAL_EVIDENCE_RULES: tuple[str, ...] = (
    ".ai-engineering/state/spec-116-t31-audit-classification.json",
    ".ai-engineering/state/spec-116-t41-audit-findings.json",
    ".ai-engineering/specs/evidence/spec-116/spec-116-t31-audit-classification.json",
    ".ai-engineering/specs/evidence/spec-116/spec-116-t41-audit-findings.json",
)

_STATE_PLANE_DEFERRED_RULES: tuple[str, ...] = (
    ".ai-engineering/state/instinct-observations.ndjson",
)

_STATE_PLANE_SPEC_LOCAL_EVIDENCE_RELOCATION_MAP: dict[str, str] = {
    ".ai-engineering/state/spec-116-t31-audit-classification.json": (
        ".ai-engineering/specs/evidence/spec-116/spec-116-t31-audit-classification.json"
    ),
    ".ai-engineering/state/spec-116-t41-audit-findings.json": (
        ".ai-engineering/specs/evidence/spec-116/spec-116-t41-audit-findings.json"
    ),
}
_STATE_PLANE_SPEC_LOCAL_EVIDENCE_CANONICAL_TO_LEGACY: dict[str, str] = {
    canonical: legacy
    for legacy, canonical in _STATE_PLANE_SPEC_LOCAL_EVIDENCE_RELOCATION_MAP.items()
}


class StatePlaneArtifactClass(StrEnum):
    """Classification families for state-plane artifacts."""

    DURABLE = "durable"
    DERIVED = "derived"
    RESIDUE = "residue"
    SPEC_LOCAL_EVIDENCE = "spec-local-evidence"
    DEFERRED = "deferred"


def _matches_state_plane_rule(relative_path: str, rule: str) -> bool:
    if rule.endswith("/**"):
        return relative_path.startswith(rule[:-3])
    return relative_path == rule


@dataclass(frozen=True)
class ControlPlaneContract:
    """Resolved ownership/provenance contract for the control plane."""

    constitutional_primary: str
    constitutional_aliases: tuple[str, ...]
    ownership_rules: tuple[tuple[str, OwnershipLevel, FrameworkUpdatePolicy], ...]

    def ownership_entries(self) -> tuple[OwnershipEntry, ...]:
        """Render the contract as concrete ownership entries."""
        return tuple(
            OwnershipEntry(pattern=pattern, owner=owner, framework_update=policy)
            for pattern, owner, policy in self.ownership_rules
        )


@dataclass(frozen=True)
class StatePlaneContract:
    """Resolved classification contract for durable, derived, and residue state."""

    durable_rules: tuple[str, ...]
    derived_rules: tuple[str, ...]
    residue_rules: tuple[str, ...]
    spec_local_evidence_rules: tuple[str, ...]
    deferred_rules: tuple[str, ...] = ()

    def canonical_relative_path(self, relative_path: str) -> str:
        """Return the canonical repo-relative path for a state-plane artifact."""
        normalized = relative_path.strip().replace("\\", "/")
        if not normalized:
            msg = "State-plane path resolution requires a non-empty path"
            raise ValueError(msg)
        return _STATE_PLANE_SPEC_LOCAL_EVIDENCE_RELOCATION_MAP.get(normalized, normalized)

    def compatibility_shim_relative_path(self, relative_path: str) -> str | None:
        """Return the legacy compatibility shim path when one exists."""
        normalized = relative_path.strip().replace("\\", "/")
        if not normalized:
            msg = "State-plane path resolution requires a non-empty path"
            raise ValueError(msg)

        if normalized in _STATE_PLANE_SPEC_LOCAL_EVIDENCE_RELOCATION_MAP:
            return normalized
        return _STATE_PLANE_SPEC_LOCAL_EVIDENCE_CANONICAL_TO_LEGACY.get(normalized)

    def classify(self, relative_path: str) -> StatePlaneArtifactClass:
        """Classify one repo-relative state-plane artifact path."""
        normalized = self.canonical_relative_path(relative_path)

        for rule in self.durable_rules:
            if _matches_state_plane_rule(normalized, rule):
                return StatePlaneArtifactClass.DURABLE
        for rule in self.derived_rules:
            if _matches_state_plane_rule(normalized, rule):
                return StatePlaneArtifactClass.DERIVED
        for rule in self.residue_rules:
            if _matches_state_plane_rule(normalized, rule):
                return StatePlaneArtifactClass.RESIDUE
        for rule in self.spec_local_evidence_rules:
            if _matches_state_plane_rule(normalized, rule):
                return StatePlaneArtifactClass.SPEC_LOCAL_EVIDENCE
        for rule in self.deferred_rules:
            if _matches_state_plane_rule(normalized, rule):
                return StatePlaneArtifactClass.DEFERRED

        msg = f"Unclassified state-plane path: {relative_path}"
        raise ValueError(msg)

    def is_required_for_correctness(self, relative_path: str) -> bool:
        """Return True only for the durable cross-spec core."""
        return self.classify(relative_path) is StatePlaneArtifactClass.DURABLE

    def requires_compatibility_shim(self, relative_path: str) -> bool:
        """Return True when relocation must preserve a readable compatibility path."""
        normalized = relative_path.strip().replace("\\", "/")
        if not normalized:
            msg = "State-plane classification requires a non-empty path"
            raise ValueError(msg)
        return normalized in _STATE_PLANE_SPEC_LOCAL_EVIDENCE_RELOCATION_MAP


def _resolve_root_entry_point_ownership(
    owner: str,
) -> tuple[OwnershipLevel, FrameworkUpdatePolicy]:
    normalized = owner.strip().lower()
    return _ROOT_ENTRY_POINT_OWNER_RULES.get(
        normalized,
        (
            OwnershipLevel.FRAMEWORK_MANAGED,
            FrameworkUpdatePolicy.ALLOW,
        ),
    )


def _resolve_root_entry_point_rules(
    *,
    root_entry_points: Mapping[str, RootEntryPointConfig] | None = None,
) -> tuple[tuple[str, OwnershipLevel, FrameworkUpdatePolicy], ...]:
    configured = dict(root_entry_points or {})
    if not configured:
        return ()

    ordered_paths = [path for path in _DEFAULT_ROOT_ENTRY_POINT_PATHS if path in configured]
    for path in sorted(configured):
        if path not in ordered_paths:
            ordered_paths.append(path)

    resolved: list[tuple[str, OwnershipLevel, FrameworkUpdatePolicy]] = []
    for path in ordered_paths:
        entry = configured.get(path)
        if entry is None:
            continue
        owner, policy = _resolve_root_entry_point_ownership(entry.owner)
        resolved.append((path, owner, policy))

    return tuple(resolved)


def resolve_control_plane_contract(
    *,
    root_entry_points: Mapping[str, RootEntryPointConfig] | None = None,
) -> ControlPlaneContract:
    """Resolve the shared control-plane ownership/provenance contract."""
    return ControlPlaneContract(
        constitutional_primary=_CONSTITUTIONAL_PRIMARY,
        constitutional_aliases=_CONSTITUTIONAL_ALIASES,
        ownership_rules=(
            *_DEFAULT_CONTROL_PLANE_RULES,
            *_resolve_root_entry_point_rules(root_entry_points=root_entry_points),
        ),
    )


def resolve_state_plane_contract() -> StatePlaneContract:
    """Resolve the shared durable-versus-residue state-plane contract."""
    return StatePlaneContract(
        durable_rules=_STATE_PLANE_DURABLE_RULES,
        derived_rules=_STATE_PLANE_DERIVED_RULES,
        residue_rules=_STATE_PLANE_RESIDUE_RULES,
        spec_local_evidence_rules=_STATE_PLANE_SPEC_LOCAL_EVIDENCE_RULES,
        deferred_rules=_STATE_PLANE_DEFERRED_RULES,
    )


def resolve_state_plane_artifact_path(project_root: Path, relative_path: str) -> Path:
    """Resolve a state-plane artifact to its canonical normalized path."""
    contract = resolve_state_plane_contract()
    return project_root / contract.canonical_relative_path(relative_path)


def resolve_constitution_context_path(project_root: Path) -> Path:
    """Resolve the active constitution path using the shared compatibility order."""
    contract = resolve_control_plane_contract()
    for rel_path in (contract.constitutional_primary, *contract.constitutional_aliases):
        candidate = project_root / rel_path
        if candidate.is_file():
            return candidate
    return project_root / contract.constitutional_primary
