"""Pydantic models for .ai-engineering/manifest.yml.

Provides typed, validated access to the project manifest. All fields
are optional with sensible defaults so partial or empty manifests
degrade gracefully.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from ai_engineering.domain.surface import SURFACE_IDS

# --- Nested models ---


class SurfacesConfig(BaseModel):
    """Surface configuration — single source of truth (spec-133 D-133-16).

    A Surface fuses AI Provider + IDE Integration into one capability
    matrix. Every value MUST be a member of
    :data:`ai_engineering.domain.surface.SURFACE_IDS` (closed enum).
    The legacy ``providers.ides`` and ``ai_providers.enabled`` fields
    were deleted in the slim-manifest refactor (no backward compat).
    """

    enabled: list[str] = Field(default_factory=lambda: ["claude-code"])

    @field_validator("enabled")
    @classmethod
    def _validate_closed_enum(cls, value: list[str]) -> list[str]:
        unknown = [s for s in value if s not in SURFACE_IDS]
        if unknown:
            known = ", ".join(sorted(SURFACE_IDS))
            raise ValueError(f"Unknown surface id(s): {unknown}. Known surfaces: {known}.")
        return value


class ProvidersConfig(BaseModel):
    """VCS + technology-stack provider configuration.

    Note: ``ides`` and ``ai_providers`` were deleted from this model;
    use :class:`SurfacesConfig` (manifest field ``surfaces.enabled``)
    for both axes.
    """

    vcs: str = "github"
    stacks: list[str] = Field(default_factory=lambda: ["python"])


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


class RootEntryPointSyncConfig(BaseModel):
    """Structured sync metadata for a governed root entry point."""

    mode: str = ""
    template_path: str = ""
    mirror_paths: list[str] = Field(default_factory=list)


class RootEntryPointConfig(BaseModel):
    """Manifest ownership metadata for a governed root instruction surface."""

    owner: str = ""
    canonical_source: str = ""
    runtime_role: str = ""
    sync: RootEntryPointSyncConfig = Field(default_factory=RootEntryPointSyncConfig)


class OwnershipConfig(BaseModel):
    """Path-ownership glob patterns."""

    framework: list[str] = Field(default_factory=list)
    root_entry_points: dict[str, RootEntryPointConfig] = Field(default_factory=dict)
    team: list[str] = Field(default_factory=list)
    system: list[str] = Field(default_factory=list)


class TelemetryConfig(BaseModel):
    """Telemetry consent and defaults."""

    consent: str = "strict-opt-in"
    default: str = "disabled"


class VersionCheckConfig(BaseModel):
    """Update-available notice settings (spec version-update-notice).

    ``enabled`` gates the PyPI-cache update notice entirely; ``ttl_hours``
    controls both the cache staleness window and the notice throttle;
    ``source`` selects the version source adapter (only ``pypi`` today).
    """

    enabled: bool = True
    ttl_hours: int = 24
    source: str = "pypi"


class PreCommitGateConfig(BaseModel):
    """Pre-commit gate-specific settings (spec-105 D-105-09).

    Currently exposes a single knob:

    * ``auto_stage`` (default ``True``) -- when True, the gate orchestrator
      and the Claude Code auto-format hook re-stage the safe intersection
      ``S_pre & M_post`` after Wave 1 fixers rewrite files on disk.
      When False, file modifications by fixers stay unstaged and the
      operator must ``git add`` them manually.
    """

    auto_stage: bool = True


class GatesConfig(BaseModel):
    """Gate execution settings (spec-105 D-105-02 + D-105-09).

    The ``mode`` field controls the tier dispatch in
    :mod:`ai_engineering.policy.mode_dispatch`:

    * ``regulated`` (default) -- runs Tier 0 + Tier 1 + Tier 2 checks.
    * ``prototyping`` -- runs Tier 0 + Tier 1 only (skips slow Tier 2
      governance checks). Branch-aware escalation, CI override, and
      pre-push target checks may force escalation back to ``regulated``
      regardless of the manifest declaration (D-105-03).

    The ``pre_commit`` nested config carries pre-commit gate-specific
    knobs (currently the spec-105 D-105-09 auto-stage toggle).
    """

    mode: Literal["regulated", "prototyping"] = "regulated"
    pre_commit: PreCommitGateConfig = Field(default_factory=PreCommitGateConfig)


class AutoSpecGateThresholds(BaseModel):
    """Trivial-vs-spec thresholds for ``/ai-brainstorm`` (spec-134 D-134-04).

    All three thresholds are upper bounds (a diff that strictly exceeds
    any one of them routes to full interrogation). The same shape is
    reused for ``regulated_overrides`` — only the default values differ.
    """

    files: int = 3
    loc: int = 50
    cross_module: int = 1


class AutoSpecGateHardTriggers(BaseModel):
    """Hard-trigger toggles for ``/ai-brainstorm`` auto-spec gate.

    Each flag controls whether a vector participates in the gate. The
    default is "all on" — operators can disable a vector to silence
    false positives, but the framework treats every disabled flag as a
    risk acceptance (documented in `auto-spec-gate.md`).
    """

    public_api: bool = True
    state_or_schema: bool = True
    new_dependency: bool = True
    security_surface: bool = True


class AutoSpecGateConfig(BaseModel):
    """Auto-spec gate knob block (spec-134 D-134-04).

    Lives under ``brainstorm.auto_spec_gate`` in ``manifest.yml``. When
    :attr:`enabled` is ``False`` the gate becomes a no-op and every
    call routes to full interrogation. When :attr:`enabled` is ``True``
    the gate consults the thresholds + hard-trigger toggles to classify
    a working-tree diff. ``regulated_overrides`` are substituted over
    ``thresholds`` when ``gates.mode == "regulated"`` (the runtime
    consults the existing :class:`GatesConfig` — no new top-level enum
    is needed).
    """

    enabled: bool = True
    thresholds: AutoSpecGateThresholds = Field(default_factory=AutoSpecGateThresholds)
    hard_triggers: AutoSpecGateHardTriggers = Field(default_factory=AutoSpecGateHardTriggers)
    regulated_overrides: AutoSpecGateThresholds = Field(
        default_factory=lambda: AutoSpecGateThresholds(files=1, loc=20, cross_module=1)
    )


class BrainstormConfig(BaseModel):
    """``brainstorm.*`` manifest block (spec-134 D-134-04).

    Currently exposes only :attr:`auto_spec_gate`; the namespace is
    reserved for future brainstorm-scoped knobs (e.g., max-question
    budgets, evidence-sweep toggles).
    """

    auto_spec_gate: AutoSpecGateConfig = Field(default_factory=AutoSpecGateConfig)


class LifecycleConfig(BaseModel):
    """``lifecycle.*`` manifest block (spec-153 D-153-08).

    Makes spec-retention windows SSOT config rather than hardcoded
    constants in ``spec_lifecycle.py``. Read by the ``sweep``/archival
    verbs to drive DRAFT expiry, the archive directory layout, and the
    orphan reaper.

    * ``draft_ttl_days`` -- DRAFT sidecars older than this sweep to
      ABANDONED (default 30; provisional value confirmed at /ai-plan).
    * ``archive_layout`` -- the on-disk archive shape; the single
      supported value today is ``per-spec-dir``
      (``archive/spec-NNN-<slug>/{spec.md,plan.md}``).
    * ``reap_orphans`` -- when true, ``sweep`` moves stray
      ``spec-*.md`` files out of the ``specs/`` root into their
      archive directory.
    """

    draft_ttl_days: int = 30
    archive_layout: str = "per-spec-dir"
    reap_orphans: bool = True


class PerformanceConcurrencyConfig(BaseModel):
    """Concurrency budget knobs (spec-139 M1 D-139-01).

    Single global cap class that prevents the kernel-panic regression
    documented in the spec-139 brief (macOS M1 Pro: WindowServer
    watchdog 171 s, memory compressor 100% segments).

    * ``max_wave_agents`` -- cap on Phase 2 (deep-plan) and Phase 4
      (implement) fan-out. Default ``"auto"`` defers to a host-capacity
      probe (M2). Positive integers override; ``"auto"`` keeps the
      framework's auto-tune. The env var ``AIENG_MAX_WAVE_AGENTS``
      wins over this field.
    * ``max_quality_agents`` -- cap on Phase 5 (verify+guard+review)
      parallel dispatch. Default ``3`` matches the canonical
      single-round contract. ``AIENG_MAX_QUALITY_AGENTS`` can only
      lower it.
    * ``max_thread_workers`` -- cap on
      ``ThreadPoolExecutor(max_workers=...)`` inside the policy
      orchestrator (``orchestrator.py:489`` and ``:1209``). Default 4
      matches the empirical "most repos have ≤ 4 active checkers"
      observation. ``AIENG_MAX_THREAD_WORKERS`` overrides.
    """

    max_wave_agents: int | Literal["auto"] = "auto"
    max_quality_agents: int = 3
    max_thread_workers: int = 4


class PerformanceBudgetConfig(BaseModel):
    """Session spend budget (spec-201 D-201-13).

    * ``max_session_tokens`` -- the token spend at which
      ``spend-cap-guard.py`` denies an ``Agent`` dispatch on ``PreToolUse``.
      **Ships at 0, which means DISABLED**: a non-zero default would begin
      denying dispatches in every consumer repository at a number nobody
      chose. ``AIENG_MAX_SESSION_TOKENS`` overrides this field, and a literal
      ``0`` in the env disables the cap even when the manifest configures one.

    The unit is tokens, not currency: a per-request cost exists only on the
    OpenAI-compatible path, so a USD cap would be absent on the surface used
    most, while tokens are present on every path.
    """

    max_session_tokens: int = 0


class PerformanceConfig(BaseModel):
    """``performance.*`` manifest block (spec-139, spec-201)."""

    concurrency: PerformanceConcurrencyConfig = Field(default_factory=PerformanceConcurrencyConfig)
    budget: PerformanceBudgetConfig = Field(default_factory=PerformanceBudgetConfig)


class HotPathSlosConfig(BaseModel):
    """Hot-path SLO budgets driving ``ai-eng doctor --check hot-path``.

    Spec-114 D-114-02 ports the spec-112 D-112-08 latency budgets into
    the manifest so operators can tune them without code changes.

    * ``pre_commit_p95_ms`` -- p95 budget for pre-commit hooks (default
      1000 ms; CLAUDE.md hot-path discipline).
    * ``pre_push_p95_ms`` -- p95 budget for pre-push hooks (default
      5000 ms).
    * ``skill_invocation_overhead_p95_ms`` -- p95 budget for the
      ``UserPromptSubmit`` skill dispatcher (default 200 ms; the work
      itself runs after dispatch and is not in scope).
    * ``rolling_window_events`` -- how many recent events per hook the
      doctor pulls from the NDJSON when computing p95 (default 100).
    """

    pre_commit_p95_ms: int = 1000
    pre_push_p95_ms: int = 5000
    skill_invocation_overhead_p95_ms: int = 200
    rolling_window_events: int = 100


class ValueLensConfig(BaseModel):
    """Client-Value Lens audience-level default (spec-186 D-186-02).

    ``default_level`` selects the sponsor-facing framing depth
    (``lite`` | ``full`` | ``ultra``) when ``AIENG_VALUE_LENS_LEVEL`` is
    unset. Resolved by :func:`ai_engineering.value_lens.resolve_level`, which
    falls back to ``full`` on any unknown value.
    """

    default_level: str = "full"


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
    surfaces: SurfacesConfig = Field(default_factory=SurfacesConfig)
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
    version_check: VersionCheckConfig = Field(default_factory=VersionCheckConfig)
    gates: GatesConfig = Field(default_factory=GatesConfig)
    hot_path_slos: HotPathSlosConfig = Field(default_factory=HotPathSlosConfig)
    brainstorm: BrainstormConfig = Field(default_factory=BrainstormConfig)
    lifecycle: LifecycleConfig = Field(default_factory=LifecycleConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    value_lens: ValueLensConfig = Field(default_factory=ValueLensConfig)
