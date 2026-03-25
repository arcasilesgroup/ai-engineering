"""Pydantic models for ai-engineering state files.

Defines schemas for:
- InstallManifest: installation metadata, stacks, IDEs, tooling readiness.
- OwnershipMap: path-level ownership for safe updates.
- DecisionStore: risk and flow decisions with context hashing.
- AuditEntry: governance event log entries.
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


# --- InstallManifest ---


class ToolStatus(BaseModel):
    """Status of a single tool."""

    ready: bool = False


class PythonTooling(BaseModel):
    """Python-specific tooling readiness."""

    uv: ToolStatus = Field(default_factory=ToolStatus)
    ruff: ToolStatus = Field(default_factory=ToolStatus)
    ty: ToolStatus = Field(default_factory=ToolStatus)
    pip_audit: ToolStatus = Field(default_factory=ToolStatus, alias="pipAudit")

    model_config = {"populate_by_name": True}


class DotnetTooling(BaseModel):
    """`.NET`-specific tooling readiness."""

    dotnet: ToolStatus = Field(default_factory=ToolStatus)

    model_config = {"populate_by_name": True}


class NextjsTooling(BaseModel):
    """Next.js/TypeScript-specific tooling readiness."""

    node: ToolStatus = Field(default_factory=ToolStatus)
    npm: ToolStatus = Field(default_factory=ToolStatus)
    eslint: ToolStatus = Field(default_factory=ToolStatus)
    prettier: ToolStatus = Field(default_factory=ToolStatus)

    model_config = {"populate_by_name": True}


class VcsProviderStatus(BaseModel):
    """Status of a VCS provider."""

    installed: bool = False
    configured: bool = False
    authenticated: bool = False
    required_now: bool = Field(default=False, alias="requiredNow")
    mode: str = "cli"
    message: str | None = None

    model_config = {"populate_by_name": True}


class AzureDevOpsExtension(BaseModel):
    """Azure DevOps extension configuration."""

    enabled: bool = False
    organization: str | None = None
    project: str | None = None
    repository: str | None = None


class VcsExtensions(BaseModel):
    """VCS provider extensions."""

    azure_devops: AzureDevOpsExtension = Field(
        default_factory=AzureDevOpsExtension,
        alias="azure_devops",
    )

    model_config = {"populate_by_name": True}


class VcsProviders(BaseModel):
    """VCS provider configuration."""

    primary: str = "github"
    enabled: list[str] = Field(default_factory=lambda: ["github"])
    extensions: VcsExtensions = Field(default_factory=VcsExtensions)


class GitHooksStatus(BaseModel):
    """Git hooks installation status."""

    installed: bool = False
    integrity_verified: bool = Field(default=False, alias="integrityVerified")
    hook_hashes: dict[str, str] = Field(default_factory=dict, alias="hookHashes")

    model_config = {"populate_by_name": True}


class ToolingReadiness(BaseModel):
    """Overall tooling readiness status."""

    gh: VcsProviderStatus = Field(default_factory=VcsProviderStatus)
    az: VcsProviderStatus = Field(default_factory=VcsProviderStatus)
    git_hooks: GitHooksStatus = Field(default_factory=GitHooksStatus, alias="gitHooks")
    python: PythonTooling = Field(default_factory=PythonTooling)
    dotnet: DotnetTooling | None = None
    nextjs: NextjsTooling | None = None

    model_config = {"populate_by_name": True}


class BranchPolicyStatus(BaseModel):
    """Status of branch policy/protection setup."""

    applied: bool = False
    mode: str = "api"
    manual_guide: str | None = Field(default=None, alias="manualGuide")
    message: str | None = None

    model_config = {"populate_by_name": True}


class AiProviderConfig(BaseModel):
    """AI provider selection for a project."""

    primary: str = "claude_code"
    enabled: list[str] = Field(default_factory=lambda: ["claude_code"])

    model_config = {"populate_by_name": True}


class OperationalReadiness(BaseModel):
    """High-level install-to-operational readiness status."""

    status: str = "pending"
    manual_steps_required: bool = Field(default=False, alias="manualStepsRequired")
    manual_steps: list[str] = Field(default_factory=list, alias="manualSteps")
    deferred_setup: bool = Field(default=False, alias="deferredSetup")

    model_config = {"populate_by_name": True}


class ReleaseInfo(BaseModel):
    """Last known release metadata for this installation."""

    last_version: str = Field(default="", alias="lastVersion")
    last_released_at: datetime | None = Field(default=None, alias="lastReleasedAt")

    model_config = {"populate_by_name": True}


class InstallManifest(BaseModel):
    """Installation manifest for the ai-engineering framework.

    Tracks what stacks, IDEs, and tools are installed and their readiness state.
    Stored at `.ai-engineering/state/install-manifest.json`.
    """

    schema_version: str = Field(default="1.2", alias="schemaVersion")
    update_metadata: UpdateMetadata | None = Field(default=None, alias="updateMetadata")
    framework_version: str = Field(default="0.1.0", alias="frameworkVersion")
    installed_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), alias="installedAt"
    )
    installed_stacks: list[str] = Field(default_factory=list, alias="installedStacks")
    installed_ides: list[str] = Field(default_factory=list, alias="installedIdes")
    ai_providers: AiProviderConfig = Field(default_factory=AiProviderConfig, alias="aiProviders")
    providers: VcsProviders = Field(default_factory=VcsProviders)
    tooling_readiness: ToolingReadiness = Field(
        default_factory=ToolingReadiness, alias="toolingReadiness"
    )
    branch_policy: BranchPolicyStatus = Field(
        default_factory=BranchPolicyStatus,
        alias="branchPolicy",
    )
    operational_readiness: OperationalReadiness = Field(
        default_factory=OperationalReadiness,
        alias="operationalReadiness",
    )
    release: ReleaseInfo = Field(default_factory=ReleaseInfo)
    external_references: dict[str, str] = Field(default_factory=dict, alias="externalReferences")

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
    """New-generation state file model (spec-068).

    Stores ONLY runtime state -- no config duplication.
    Replaces both ``InstallManifest`` and ``ToolsState``.
    Persisted at ``.ai-engineering/state/install-state.json``.

    The ``tooling`` and ``platforms`` dicts use string keys so that
    new tools/platforms can be added without model changes.
    """

    schema_version: str = "2.0"
    installed_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    tooling: dict[str, ToolEntry] = Field(default_factory=dict)
    platforms: dict[str, PlatformEntry] = Field(default_factory=dict)
    branch_policy: BranchPolicyState = Field(default_factory=BranchPolicyState)
    operational_readiness: OperationalState = Field(default_factory=OperationalState)
    release: ReleaseState = Field(default_factory=ReleaseState)

    @classmethod
    def from_legacy(
        cls,
        manifest: InstallManifest,
        tools_state_dict: dict[str, Any] | None = None,
    ) -> InstallState:
        """Convert a legacy InstallManifest (+ optional ToolsState dict) into InstallState.

        Extracts runtime state from the old manifest. Config-only fields
        (installed_stacks, installed_ides, ai_providers, framework_version)
        are intentionally dropped -- they belong in ``ManifestConfig``.

        Args:
            manifest: The legacy InstallManifest model instance.
            tools_state_dict: Optional raw dict from tools.json (ToolsState).
                If provided, platform data is merged into ``platforms``.

        Returns:
            A new InstallState with state fields extracted.
        """
        tooling = _extract_tooling(manifest.tooling_readiness)
        platforms = _extract_platforms(tools_state_dict) if tools_state_dict else {}

        return cls(
            installed_at=manifest.installed_at,
            tooling=tooling,
            platforms=platforms,
            branch_policy=BranchPolicyState(
                applied=manifest.branch_policy.applied,
                mode=manifest.branch_policy.mode,
                message=manifest.branch_policy.message,
                manual_guide=manifest.branch_policy.manual_guide,
            ),
            operational_readiness=OperationalState(
                status=manifest.operational_readiness.status,
                pending_steps=list(manifest.operational_readiness.manual_steps),
            ),
            release=ReleaseState(
                last_version=manifest.release.last_version,
                last_released_at=manifest.release.last_released_at,
            ),
        )


def _extract_tooling(readiness: ToolingReadiness) -> dict[str, ToolEntry]:
    """Flatten legacy ToolingReadiness into a flat dict of ToolEntry.

    VCS providers (gh, az) map directly.  Stack-specific tools
    (python.ruff, python.uv, etc.) are promoted to top-level keys.
    """
    tooling: dict[str, ToolEntry] = {}

    # VCS providers -> direct mapping
    for name, provider in [("gh", readiness.gh), ("az", readiness.az)]:
        tooling[name] = ToolEntry(
            installed=provider.installed,
            authenticated=provider.authenticated,
            mode=provider.mode,
        )

    # Python tools -> flatten (ready maps to installed)
    if readiness.python is not None:
        tooling["uv"] = ToolEntry(installed=readiness.python.uv.ready)
        tooling["ruff"] = ToolEntry(installed=readiness.python.ruff.ready)
        tooling["ty"] = ToolEntry(installed=readiness.python.ty.ready)
        tooling["pip_audit"] = ToolEntry(installed=readiness.python.pip_audit.ready)

    # Dotnet tools -> flatten
    if readiness.dotnet is not None:
        tooling["dotnet"] = ToolEntry(installed=readiness.dotnet.dotnet.ready)

    # Next.js tools -> flatten
    if readiness.nextjs is not None:
        tooling["node"] = ToolEntry(installed=readiness.nextjs.node.ready)
        tooling["npm"] = ToolEntry(installed=readiness.nextjs.npm.ready)
        tooling["eslint"] = ToolEntry(installed=readiness.nextjs.eslint.ready)
        tooling["prettier"] = ToolEntry(installed=readiness.nextjs.prettier.ready)

    return tooling


def _extract_platforms(tools_state_dict: dict[str, Any]) -> dict[str, PlatformEntry]:
    """Convert a legacy ToolsState dict into platform entries.

    Maps each platform section from tools.json into a PlatformEntry.
    Only configured platforms are included.
    """
    platforms: dict[str, PlatformEntry] = {}

    # Sonar
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

    # Azure DevOps
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
