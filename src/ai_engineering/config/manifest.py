"""Pydantic models for .ai-engineering/manifest.yml.

Provides typed, validated access to the project manifest. All fields
are optional with sensible defaults so partial or empty manifests
degrade gracefully.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# --- Nested models ---


class AiProvidersConfig(BaseModel):
    """AI coding assistant provider configuration."""

    enabled: list[str] = Field(default_factory=lambda: ["claude_code"])
    primary: str = "claude_code"


class ProvidersConfig(BaseModel):
    """VCS, IDE, and stack provider configuration."""

    vcs: str = "github"
    ides: list[str] = Field(default_factory=lambda: ["terminal"])
    stacks: list[str] = Field(default_factory=lambda: ["python"])
    ai_providers: AiProvidersConfig = Field(default_factory=AiProvidersConfig)


class ArtifactFeedsConfig(BaseModel):
    """Artifact feed pointers (e.g. python -> pyproject.toml)."""

    python: str = "pyproject.toml"


class AzureDevOpsWorkItems(BaseModel):
    """Azure DevOps work-item board settings."""

    area_path: str = ""
    iteration_path: str | None = None


class GitHubWorkItems(BaseModel):
    """GitHub Issues / Projects work-item settings."""

    team_label: str = ""
    project: int | None = None


class WorkItemHierarchy(BaseModel, extra="allow"):
    """Close-policy per work-item type.

    Known types have defaults; extra keys are preserved so teams can
    define custom work-item types (e.g. ``custom_type: track_only``).
    """

    feature: str = "never_close"
    user_story: str = "close_on_pr"
    task: str = "close_on_pr"
    bug: str = "close_on_pr"


class WorkItemsConfig(BaseModel):
    """Work-item / issue-tracker integration."""

    provider: str = "github"
    azure_devops: AzureDevOpsWorkItems = Field(default_factory=AzureDevOpsWorkItems)
    github: GitHubWorkItems = Field(default_factory=GitHubWorkItems)
    hierarchy: WorkItemHierarchy = Field(default_factory=WorkItemHierarchy)


class QualityConfig(BaseModel):
    """Quality gate thresholds."""

    coverage: int = 80
    duplication: int = 3
    cyclomatic: int = 10
    cognitive: int = 15


class AutoUpdateConfig(BaseModel):
    """Documentation auto-update toggles."""

    readme: bool = True
    changelog: bool = True
    solution_intent: bool = True


class ExternalPortalConfig(BaseModel):
    """External documentation portal settings."""

    enabled: bool = False
    source: str | None = None
    update_method: str = "pr"


class DocumentationConfig(BaseModel):
    """Documentation automation settings."""

    auto_update: AutoUpdateConfig = Field(default_factory=AutoUpdateConfig)
    external_portal: ExternalPortalConfig = Field(default_factory=ExternalPortalConfig)


class CicdConfig(BaseModel):
    """CI/CD pipeline settings."""

    standards_url: str | None = None


class SkillEntry(BaseModel, extra="allow"):
    """Single skill registry entry."""

    type: str = ""
    tags: list[str] = Field(default_factory=list)


class SkillsConfig(BaseModel):
    """Skills registry metadata."""

    total: int = 0
    prefix: str = "ai-"
    registry: dict[str, SkillEntry] = Field(default_factory=dict)


class AgentsConfig(BaseModel):
    """Agent roster metadata."""

    total: int = 0
    names: list[str] = Field(default_factory=list)


class OwnershipConfig(BaseModel):
    """Path-ownership glob patterns."""

    framework: list[str] = Field(default_factory=list)
    team: list[str] = Field(default_factory=list)
    system: list[str] = Field(default_factory=list)


class TelemetryConfig(BaseModel):
    """Telemetry consent and defaults."""

    consent: str = "strict-opt-in"
    default: str = "disabled"


# --- Root model ---


class ManifestConfig(BaseModel):
    """Typed representation of .ai-engineering/manifest.yml.

    Every field is optional with a sensible default, so an empty or
    partial YAML file still produces a valid model instance.
    """

    schema_version: str = "2.0"
    framework_version: str = ""
    name: str = ""
    version: str = ""

    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    artifact_feeds: ArtifactFeedsConfig = Field(default_factory=ArtifactFeedsConfig)
    work_items: WorkItemsConfig = Field(default_factory=WorkItemsConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    documentation: DocumentationConfig = Field(default_factory=DocumentationConfig)
    cicd: CicdConfig = Field(default_factory=CicdConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    ownership: OwnershipConfig = Field(default_factory=OwnershipConfig)
    tooling: list[str] = Field(default_factory=list)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
