"""Pydantic models for ai-engineering state files.

Defines schemas for:
- InstallState: runtime state (tooling, platforms, branch policy, readiness).
- OwnershipMap: path-level ownership for safe updates.
- DecisionStore: risk and flow decisions with context hashing.
- AuditEntry: governance event log entries.

Legacy models (InstallManifest and its sub-models) have been removed.
The updater/service.py migration code reads old JSON directly without models.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# --- Enums ---


class OwnershipLevel(StrEnum):
    """Ownership levels for governance paths."""

    FRAMEWORK_MANAGED = "framework-managed"
    TEAM_MANAGED = "team-managed"
    PROJECT_MANAGED = "project-managed"
    SYSTEM_MANAGED = "system-managed"


class FrameworkUpdatePolicy(StrEnum):
    """How framework updates interact with a path."""

    ALLOW = "allow"
    DENY = "deny"
    APPEND_ONLY = "append-only"


class GateHook(StrEnum):
    """Git hook types used as quality gates."""

    PRE_COMMIT = "pre-commit"
    COMMIT_MSG = "commit-msg"
    PRE_PUSH = "pre-push"


class AiProvider(StrEnum):
    """Supported AI coding assistant providers."""

    CLAUDE_CODE = "claude_code"
    GITHUB_COPILOT = "github_copilot"
    GEMINI = "gemini"
    CODEX = "codex"


class RiskCategory(StrEnum):
    """Category of a decision in the decision store."""

    RISK_ACCEPTANCE = "risk-acceptance"
    FLOW_DECISION = "flow-decision"
    ARCHITECTURE_DECISION = "architecture-decision"


class RiskSeverity(StrEnum):
    """Severity level for risk acceptances."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DecisionStatus(StrEnum):
    """Lifecycle status of a decision."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUPERSEDED = "superseded"
    REMEDIATED = "remediated"


# --- Shared Components ---


class UpdateMetadata(BaseModel):
    """Metadata block required on every governance document update."""

    rationale: str
    expected_gain: str = Field(alias="expectedGain")
    potential_impact: str = Field(alias="potentialImpact")

    model_config = {"populate_by_name": True}


# --- OwnershipMap ---


class OwnershipEntry(BaseModel):
    """A single path ownership entry."""

    pattern: str
    owner: OwnershipLevel
    framework_update: FrameworkUpdatePolicy = Field(alias="frameworkUpdate")

    model_config = {"populate_by_name": True}


class OwnershipMap(BaseModel):
    """Path-level ownership map for safe framework updates.

    Determines which paths can be overwritten by framework update flows
    and which are protected (team/project-managed).
    Stored at `.ai-engineering/state/ownership-map.json`.
    """

    schema_version: str = Field(default="1.0", alias="schemaVersion")
    update_metadata: UpdateMetadata | None = Field(default=None, alias="updateMetadata")
    paths: list[OwnershipEntry] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    def is_writable_by_framework(self, path: str) -> bool:
        """Check if a path can be written by framework update flows.

        Returns True for both ``ALLOW`` and ``APPEND_ONLY`` policies.
        Use :meth:`is_update_allowed` for the stricter updater check that
        excludes append-only paths.

        Args:
            path: Relative path to check against ownership patterns.

        Returns:
            True if the path is writable (allow or append-only).
        """
        from fnmatch import fnmatch

        for entry in self.paths:
            if fnmatch(path, entry.pattern):
                return entry.framework_update != FrameworkUpdatePolicy.DENY
        # Default: deny if no rule matches
        return False

    def is_update_allowed(self, path: str) -> bool:
        """Check if a path can be fully replaced by a framework update.

        Stricter than :meth:`is_writable_by_framework`: only ``ALLOW``
        returns True.  ``APPEND_ONLY`` returns False because the updater
        performs full file replacement, not appending.

        Args:
            path: Relative path to check against ownership patterns.

        Returns:
            True only if the matching rule has policy ``ALLOW``.
            False for ``DENY``, ``APPEND_ONLY``, or no matching rule.
        """
        from fnmatch import fnmatch

        for entry in self.paths:
            if fnmatch(path, entry.pattern):
                return entry.framework_update == FrameworkUpdatePolicy.ALLOW
        # No matching rule → deny by default
        return False

    def has_deny_rule(self, path: str) -> bool:
        """Check if a path has an explicit deny rule.

        Used to decide whether creating a new file should be blocked.

        Args:
            path: Relative path to check.

        Returns:
            True if an explicit ``DENY`` rule matches the path.
        """
        from fnmatch import fnmatch

        for entry in self.paths:
            if fnmatch(path, entry.pattern):
                return entry.framework_update == FrameworkUpdatePolicy.DENY
        return False


# --- DecisionStore ---


class Decision(BaseModel):
    """A single risk or flow decision.

    Schema 1.1 adds risk lifecycle fields. All new fields are optional
    for backward compatibility with schema 1.0 data.
    """

    id: str
    context: str
    decision: str
    decided_at: datetime = Field(alias="decidedAt")
    spec: str
    context_hash: str | None = Field(default=None, alias="contextHash")
    expires_at: datetime | None = Field(default=None, alias="expiresAt")

    # Risk lifecycle fields (schema 1.1)
    risk_category: RiskCategory | None = Field(default=None, alias="riskCategory")
    severity: RiskSeverity | None = Field(default=None)
    accepted_by: str | None = Field(default=None, alias="acceptedBy")
    follow_up_action: str | None = Field(default=None, alias="followUpAction")
    status: DecisionStatus = Field(default=DecisionStatus.ACTIVE)
    renewed_from: str | None = Field(default=None, alias="renewedFrom")
    renewal_count: int = Field(default=0, alias="renewalCount")

    model_config = {"populate_by_name": True}


class DecisionStore(BaseModel):
    """Persistent store for risk and flow decisions.

    Prevents prompt fatigue by reusing previously-made decisions.
    Supports context hashing for decision relevance tracking.
    Schema 1.1 adds risk lifecycle support.
    Stored at ``.ai-engineering/state/decision-store.json``.
    """

    schema_version: str = Field(default="1.1", alias="schemaVersion")
    update_metadata: UpdateMetadata | None = Field(default=None, alias="updateMetadata")
    decisions: list[Decision] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    def find_by_context_hash(self, context_hash: str) -> Decision | None:
        """Find a decision by its context hash."""
        for d in self.decisions:
            if d.context_hash == context_hash:
                return d
        return None

    def find_by_id(self, decision_id: str) -> Decision | None:
        """Find a decision by its ID."""
        for d in self.decisions:
            if d.id == decision_id:
                return d
        return None

    def risk_decisions(self) -> list[Decision]:
        """Return only risk acceptance decisions."""
        return [d for d in self.decisions if d.risk_category == RiskCategory.RISK_ACCEPTANCE]


# --- AuditEntry ---


class AuditEntry(BaseModel):
    """A single governance event log entry.

    Appended to `.ai-engineering/state/audit-log.ndjson` (one JSON object per line).

    The ``detail`` field is always a structured dict, enabling enriched events
    (scan results, gate outcomes, deploy signals) for database-ready analytics.
    """

    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    event: str
    actor: str
    detail: dict[str, Any] | None = None
    # VCS context (auto-populated by _emit)
    vcs_provider: str | None = None
    vcs_organization: str | None = None
    vcs_project: str | None = None
    vcs_repository: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
    # Enrichment fields (auto-populated by _emit)
    source: str | None = None
    spec_id: str | None = None
    stack: str | None = None
    duration_ms: int | None = None


# --- InstallState (spec-068: state unification) ---


class ToolEntry(BaseModel):
    """Status of a single tool in the flattened tooling dict.

    Unlike the legacy ``ToolStatus`` (which has only ``ready``),
    this captures install/auth/mode/scopes per tool.
    """

    installed: bool = False
    authenticated: bool = False
    integrity_verified: bool = False
    mode: str = "cli"
    scopes: list[str] = Field(default_factory=list)


class CredentialRef(BaseModel):
    """Reference to a credential stored in the OS secret store.

    Simplified version of ``credentials.models.CredentialRef``.
    Contains only the lookup keys -- never the secret itself.
    """

    service: str
    username: str


class PlatformEntry(BaseModel):
    """Configuration metadata for a single platform (sonar, azure_devops, etc.).

    Absorbs what was previously in ``tools.json`` per-platform configs.
    """

    configured: bool = False
    url: str = ""
    project_key: str = ""
    organization: str = ""
    credential_ref: CredentialRef | None = None


class BranchPolicyState(BaseModel):
    """Runtime state of branch policy/protection setup."""

    applied: bool = False
    mode: str = "api"
    message: str | None = None
    manual_guide: str | None = None


class OperationalState(BaseModel):
    """High-level install-to-operational readiness status."""

    status: str = "pending"
    pending_steps: list[str] = Field(default_factory=list)


class ReleaseState(BaseModel):
    """Last known release metadata for this installation."""

    last_version: str = ""
    last_released_at: datetime | None = None


class InstallState(BaseModel):
    """Runtime state file model (spec-068).

    Stores ONLY runtime state -- no config duplication.
    Persisted at ``.ai-engineering/state/install-state.json``.

    The ``tooling`` and ``platforms`` dicts use string keys so that
    new tools/platforms can be added without model changes.
    """

    schema_version: str = "2.0"
    installed_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    vcs_provider: str | None = None
    ai_providers: list[str] | None = None
    tooling: dict[str, ToolEntry] = Field(default_factory=dict)
    platforms: dict[str, PlatformEntry] = Field(default_factory=dict)
    branch_policy: BranchPolicyState = Field(default_factory=BranchPolicyState)
    operational_readiness: OperationalState = Field(default_factory=OperationalState)
    release: ReleaseState = Field(default_factory=ReleaseState)

    @classmethod
    def from_legacy_dict(
        cls,
        manifest_dict: dict[str, Any],
        tools_state_dict: dict[str, Any] | None = None,
    ) -> InstallState:
        """Convert legacy JSON dicts into InstallState.

        Used by the updater migration code. Operates on raw dicts
        so that the deleted InstallManifest/ToolsState models are
        not required.

        Args:
            manifest_dict: Raw dict from install-manifest.json.
            tools_state_dict: Optional raw dict from tools.json.

        Returns:
            A new InstallState with state fields extracted.
        """
        from datetime import datetime as _dt

        tooling = _extract_tooling_from_dict(manifest_dict.get("toolingReadiness", {}))
        platforms = _extract_platforms_from_dict(tools_state_dict) if tools_state_dict else {}

        installed_at_raw = manifest_dict.get("installedAt")
        installed_at = _dt.fromisoformat(installed_at_raw) if installed_at_raw else _dt.now(tz=UTC)

        providers = manifest_dict.get("providers", {})
        vcs_provider = providers.get("primary")
        ai_prov = manifest_dict.get("ai_providers", manifest_dict.get("aiProviders", {}))
        ai_providers = ai_prov.get("enabled") if ai_prov else None

        bp = manifest_dict.get("branchPolicy", {})
        op = manifest_dict.get("operationalReadiness", {})
        rel = manifest_dict.get("release", {})

        return cls(
            installed_at=installed_at,
            vcs_provider=vcs_provider,
            ai_providers=ai_providers,
            tooling=tooling,
            platforms=platforms,
            branch_policy=BranchPolicyState(
                applied=bp.get("applied", False),
                mode=bp.get("mode", "api"),
                message=bp.get("message"),
                manual_guide=bp.get("manualGuide"),
            ),
            operational_readiness=OperationalState(
                status=op.get("status", "pending"),
                pending_steps=list(op.get("manualSteps", [])),
            ),
            release=ReleaseState(
                last_version=rel.get("lastVersion", rel.get("last_version", "")),
                last_released_at=(
                    _dt.fromisoformat(rel["lastReleasedAt"]) if rel.get("lastReleasedAt") else None
                ),
            ),
        )


def _extract_tooling_from_dict(readiness: dict[str, Any]) -> dict[str, ToolEntry]:
    """Flatten legacy toolingReadiness dict into ToolEntry dict.

    Operates on raw dicts so that the deleted model classes are not needed.
    """
    tooling: dict[str, ToolEntry] = {}

    # VCS providers
    for name in ("gh", "az"):
        provider = readiness.get(name, {})
        if provider:
            tooling[name] = ToolEntry(
                installed=provider.get("installed", False),
                authenticated=provider.get("authenticated", False),
                mode=provider.get("mode", "cli"),
            )

    # Python tools
    python = readiness.get("python", {})
    for tool_name in ("uv", "ruff", "ty"):
        tool = python.get(tool_name, {})
        if tool:
            tooling[tool_name] = ToolEntry(installed=tool.get("ready", False))
    pip_audit = python.get("pipAudit", python.get("pip_audit", {}))
    if pip_audit:
        tooling["pip_audit"] = ToolEntry(installed=pip_audit.get("ready", False))

    # Dotnet
    dotnet = readiness.get("dotnet")
    if dotnet:
        tooling["dotnet"] = ToolEntry(installed=dotnet.get("dotnet", {}).get("ready", False))

    # Next.js
    nextjs = readiness.get("nextjs")
    if nextjs:
        for tool_name in ("node", "npm", "eslint", "prettier"):
            tool = nextjs.get(tool_name, {})
            if tool:
                tooling[tool_name] = ToolEntry(installed=tool.get("ready", False))

    return tooling


def _extract_platforms_from_dict(tools_state_dict: dict[str, Any]) -> dict[str, PlatformEntry]:
    """Convert a legacy tools.json dict into platform entries."""
    platforms: dict[str, PlatformEntry] = {}

    sonar = tools_state_dict.get("sonar", {})
    if sonar.get("configured"):
        cred_ref = None
        raw_ref = sonar.get("credential_ref")
        if raw_ref and raw_ref.get("service_name"):
            cred_ref = CredentialRef(
                service=raw_ref["service_name"],
                username=raw_ref.get("username", ""),
            )
        platforms["sonar"] = PlatformEntry(
            configured=True,
            url=sonar.get("url", ""),
            project_key=sonar.get("project_key", ""),
            organization=sonar.get("organization", ""),
            credential_ref=cred_ref,
        )

    azdo = tools_state_dict.get("azure_devops", {})
    if azdo.get("configured"):
        cred_ref = None
        raw_ref = azdo.get("credential_ref")
        if raw_ref and raw_ref.get("service_name"):
            cred_ref = CredentialRef(
                service=raw_ref["service_name"],
                username=raw_ref.get("username", ""),
            )
        platforms["azure_devops"] = PlatformEntry(
            configured=True,
            url=azdo.get("org_url", ""),
            credential_ref=cred_ref,
        )

    return platforms
