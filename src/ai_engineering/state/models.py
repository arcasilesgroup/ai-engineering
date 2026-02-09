"""Pydantic models for system-managed governance state files."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class UpdateMetadata(BaseModel):
    """Document metadata for governance artifacts."""

    rationale: str
    expectedGain: str
    potentialImpact: str


class ReadinessFlags(BaseModel):
    """Simple readiness booleans for tools."""

    installed: bool
    configured: bool
    authenticated: bool


class AzReadiness(ReadinessFlags):
    """Azure CLI readiness includes `requiredNow` flag."""

    requiredNow: bool = False


class ToolReady(BaseModel):
    """Single tool readiness state."""

    ready: bool


class PythonReadiness(BaseModel):
    """Python tooling readiness set."""

    uv: ToolReady
    ruff: ToolReady
    ty: ToolReady
    pipAudit: ToolReady


class HooksReadiness(BaseModel):
    """Git hook readiness state."""

    installed: bool
    integrityVerified: bool


class ToolingReadiness(BaseModel):
    """Aggregated tooling readiness state."""

    gh: ReadinessFlags
    az: AzReadiness
    gitHooks: HooksReadiness
    python: PythonReadiness


class AzureDevOpsExtension(BaseModel):
    """Provider extension placeholder for ADO compatibility."""

    enabled: bool = False
    organization: str | None = None
    project: str | None = None
    repository: str | None = None


class VcsExtensions(BaseModel):
    """Provider extension set for VCS backends."""

    azure_devops: AzureDevOpsExtension


class VcsProvider(BaseModel):
    """VCS provider configuration."""

    primary: str = "github"
    enabled: list[str] = Field(default_factory=lambda: ["github"])
    extensions: VcsExtensions


class Providers(BaseModel):
    """Provider root object."""

    vcs: VcsProvider


class InstallManifest(BaseModel):
    """System-managed installation manifest."""

    schemaVersion: str = "1.1"
    updateMetadata: UpdateMetadata
    frameworkVersion: str
    installedAt: str
    installedStacks: list[str] = Field(default_factory=list)
    installedIdes: list[str] = Field(default_factory=list)
    providers: Providers
    toolingReadiness: ToolingReadiness


class OwnershipPathRule(BaseModel):
    """Ownership rule for path pattern."""

    pattern: str
    owner: Literal[
        "framework-managed",
        "team-managed",
        "project-managed",
        "system-managed",
    ]
    frameworkUpdate: Literal["allow", "deny", "append-only"]


class OwnershipMap(BaseModel):
    """Path ownership contract used by updater."""

    schemaVersion: str = "1.0"
    updateMetadata: UpdateMetadata
    paths: list[OwnershipPathRule]


class SignatureMetadata(BaseModel):
    """Remote source signature metadata scaffold."""

    algorithm: str | None = None
    keyId: str | None = None
    signature: str | None = None
    verified: bool = False


class SourceCache(BaseModel):
    """Remote source cache metadata."""

    ttlHours: int = 24
    lastFetchedAt: str | None = None


class SkillSource(BaseModel):
    """Single remote skill source lock entry."""

    url: str
    trusted: bool = True
    checksum: str | None = None
    signatureMetadata: SignatureMetadata
    cache: SourceCache


class SourcesLock(BaseModel):
    """Remote source lock file model."""

    schemaVersion: str = "1.0"
    updateMetadata: UpdateMetadata
    generatedAt: str
    defaultRemoteEnabled: bool = True
    sources: list[SkillSource]


class DecisionScope(BaseModel):
    """Scope for a persisted risk decision."""

    repo: str
    pathPattern: str | None = None
    policyId: str
    policyVersion: str | None = None


class DecisionRecord(BaseModel):
    """Persisted decision record."""

    id: str
    scope: DecisionScope
    contextHash: str
    severity: Literal["low", "medium", "high", "critical"]
    decision: str
    rationale: str
    createdAt: str
    createdBy: str | None = None
    expiresAt: str | None = None


class DecisionStore(BaseModel):
    """Machine-readable decision store."""

    schemaVersion: str = "1.0"
    updateMetadata: UpdateMetadata
    decisions: list[DecisionRecord] = Field(default_factory=list)


class AuditEvent(BaseModel):
    """Append-only audit event."""

    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    event: str
    actor: str
    details: dict[str, Any] = Field(default_factory=dict)
