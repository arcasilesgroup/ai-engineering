"""Pydantic models for ai-engineering state files.

Defines schemas for:
- InstallManifest: installation metadata, stacks, IDEs, tooling readiness.
- OwnershipMap: path-level ownership for safe updates.
- DecisionStore: risk and flow decisions with context hashing.
- AuditEntry: governance event log entries.
- SourcesLock: remote skill source integrity metadata.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# --- Enums ---


class OwnershipLevel(str, Enum):
    """Ownership levels for governance paths."""

    FRAMEWORK_MANAGED = "framework-managed"
    TEAM_MANAGED = "team-managed"
    PROJECT_MANAGED = "project-managed"
    SYSTEM_MANAGED = "system-managed"


class FrameworkUpdatePolicy(str, Enum):
    """How framework updates interact with a path."""

    ALLOW = "allow"
    DENY = "deny"
    APPEND_ONLY = "append-only"


class GateHook(str, Enum):
    """Git hook types used as quality gates."""

    PRE_COMMIT = "pre-commit"
    COMMIT_MSG = "commit-msg"
    PRE_PUSH = "pre-push"


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


class VcsProviderStatus(BaseModel):
    """Status of a VCS provider."""

    installed: bool = False
    configured: bool = False
    authenticated: bool = False
    required_now: bool = Field(default=False, alias="requiredNow")

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

    model_config = {"populate_by_name": True}


class ToolingReadiness(BaseModel):
    """Overall tooling readiness status."""

    gh: VcsProviderStatus = Field(default_factory=VcsProviderStatus)
    az: VcsProviderStatus = Field(default_factory=VcsProviderStatus)
    git_hooks: GitHooksStatus = Field(default_factory=GitHooksStatus, alias="gitHooks")
    python: PythonTooling = Field(default_factory=PythonTooling)

    model_config = {"populate_by_name": True}


class InstallManifest(BaseModel):
    """Installation manifest for the ai-engineering framework.

    Tracks what stacks, IDEs, and tools are installed and their readiness state.
    Stored at `.ai-engineering/state/install-manifest.json`.
    """

    schema_version: str = Field(default="1.1", alias="schemaVersion")
    update_metadata: UpdateMetadata | None = Field(default=None, alias="updateMetadata")
    framework_version: str = Field(default="0.1.0", alias="frameworkVersion")
    installed_at: datetime = Field(default_factory=datetime.utcnow, alias="installedAt")
    installed_stacks: list[str] = Field(default_factory=list, alias="installedStacks")
    installed_ides: list[str] = Field(default_factory=list, alias="installedIdes")
    providers: VcsProviders = Field(default_factory=VcsProviders)
    tooling_readiness: ToolingReadiness = Field(
        default_factory=ToolingReadiness, alias="toolingReadiness"
    )

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
        """Check if a path can be written by framework update flows."""
        from fnmatch import fnmatch

        for entry in self.paths:
            if fnmatch(path, entry.pattern):
                return entry.framework_update != FrameworkUpdatePolicy.DENY
        # Default: deny if no rule matches
        return False


# --- DecisionStore ---


class Decision(BaseModel):
    """A single risk or flow decision."""

    id: str
    context: str
    decision: str
    decided_at: datetime = Field(alias="decidedAt")
    spec: str
    context_hash: str | None = Field(default=None, alias="contextHash")
    expires_at: datetime | None = Field(default=None, alias="expiresAt")

    model_config = {"populate_by_name": True}


class DecisionStore(BaseModel):
    """Persistent store for risk and flow decisions.

    Prevents prompt fatigue by reusing previously-made decisions.
    Supports context hashing for decision relevance tracking.
    Stored at `.ai-engineering/state/decision-store.json`.
    """

    schema_version: str = Field(default="1.0", alias="schemaVersion")
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


# --- AuditEntry ---


class AuditEntry(BaseModel):
    """A single governance event log entry.

    Appended to `.ai-engineering/state/audit-log.ndjson` (one JSON object per line).
    """

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event: str
    actor: str
    spec: str | None = None
    task: str | None = None
    detail: str | None = None
    session: str | None = None


# --- SourcesLock ---


class SignatureMetadata(BaseModel):
    """Cryptographic signature metadata for a remote source."""

    algorithm: str | None = None
    key_id: str | None = Field(default=None, alias="keyId")
    signature: str | None = None
    verified: bool = False

    model_config = {"populate_by_name": True}


class CacheConfig(BaseModel):
    """Cache configuration for a remote source."""

    ttl_hours: int = Field(default=24, alias="ttlHours")
    last_fetched_at: datetime | None = Field(default=None, alias="lastFetchedAt")

    model_config = {"populate_by_name": True}


class RemoteSource(BaseModel):
    """A trusted remote skill source."""

    url: str
    trusted: bool = True
    checksum: str | None = None
    signature_metadata: SignatureMetadata = Field(
        default_factory=SignatureMetadata,
        alias="signatureMetadata",
    )
    cache: CacheConfig = Field(default_factory=CacheConfig)

    model_config = {"populate_by_name": True}


class SourcesLock(BaseModel):
    """Lock file for trusted remote skill sources.

    Provides deterministic and safe skill resolution with integrity checking.
    Stored at `.ai-engineering/state/sources.lock.json`.
    """

    schema_version: str = Field(default="1.0", alias="schemaVersion")
    update_metadata: UpdateMetadata | None = Field(default=None, alias="updateMetadata")
    generated_at: datetime = Field(default_factory=datetime.utcnow, alias="generatedAt")
    default_remote_enabled: bool = Field(default=True, alias="defaultRemoteEnabled")
    sources: list[RemoteSource] = Field(default_factory=list)

    model_config = {"populate_by_name": True}
