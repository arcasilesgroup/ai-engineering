"""Pydantic models for ai-engineering state files.

Defines schemas for:
- InstallState: runtime state (tooling, platforms, branch policy, readiness).
- OwnershipMap: path-level ownership for safe updates.
- DecisionStore: risk and flow decisions with context hashing.
- AuditEntry: legacy governance event log entries retained for historical reads.
- FrameworkEvent / FrameworkCapabilitiesCatalog: canonical framework observability.
- InstinctObservation / InstinctMeta: simplified project-local instinct learning state.

Legacy models (InstallManifest and its sub-models) have been removed.
The updater/service.py migration code reads old JSON directly without models.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

_PLACEHOLDER_LINEAGE_VALUES = frozenset({"", "RECONSTRUCTED"})


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

    The on-disk decision ledger also carries richer historical metadata
    (for example titles, descriptions, and legacy source annotations).
    Those additive fields are preserved during load/save round-trips.
    """

    id: str
    context: str
    decision: str
    decided_at: datetime = Field(alias="decidedAt")
    spec: str
    context_hash: str | None = Field(default=None, alias="contextHash")
    expires_at: datetime | None = Field(default=None, alias="expiresAt")
    source: str | None = None

    # Risk lifecycle fields (schema 1.1)
    risk_category: RiskCategory | None = Field(default=None, alias="riskCategory")
    severity: RiskSeverity | None = Field(default=None)
    accepted_by: str | None = Field(default=None, alias="acceptedBy")
    follow_up_action: str | None = Field(default=None, alias="followUpAction")
    status: DecisionStatus = Field(default=DecisionStatus.ACTIVE)
    renewed_from: str | None = Field(default=None, alias="renewedFrom")
    renewal_count: int = Field(default=0, alias="renewalCount")

    # spec-105 additive fields: link a decision to the gate finding(s) it accepts.
    # Both optional for backward compatibility with pre-spec-105 decision-store entries.
    finding_id: str | None = Field(default=None, alias="findingId")
    batch_id: str | None = Field(default=None, alias="batchId")

    # spec-107 D-107-10 (H2) additive: hash-chain pointer over the prior
    # decision entry's canonical-JSON payload (excluding this field).
    # ``None`` for the chain anchor (first entry) and for legacy entries
    # written before spec-107 landed -- additive backward-compat.
    prev_event_hash: str | None = Field(default=None, alias="prevEventHash")

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    def lineage_value(self, field_name: Literal["source", "spec"]) -> str | None:
        """Return a normalized lineage field, or ``None`` for placeholders."""
        raw_value = getattr(self, field_name, None)
        if not isinstance(raw_value, str):
            return None
        value = raw_value.strip()
        if not value or value in _PLACEHOLDER_LINEAGE_VALUES:
            return None
        return value


class DecisionStore(BaseModel):
    """Persistent store for risk and flow decisions.

    Prevents prompt fatigue by reusing previously-made decisions.
    Supports context hashing for decision relevance tracking.
    Schema 1.1 adds risk lifecycle support.
    The full ``decisions`` ledger remains the canonical historical record;
    ``active_decisions`` is an additive normalized slice of the current
    governance posture.
    Stored at ``.ai-engineering/state/decision-store.json``.
    """

    schema_version: str = Field(default="1.1", alias="schemaVersion")
    update_metadata: UpdateMetadata | None = Field(default=None, alias="updateMetadata")
    decisions: list[Decision] = Field(default_factory=list)
    active_decisions: list[Decision] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    def refresh_active_decisions(self) -> None:
        """Rebuild the operational active-decision view from the full ledger."""
        self.active_decisions = [
            decision
            for decision in self.decisions
            if decision.status == DecisionStatus.ACTIVE
            and decision.lineage_value("source") is not None
            and decision.lineage_value("spec") is not None
        ]

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
    """Legacy governance event log entry.

    Retained for historical reads of ``audit-log.ndjson``. New framework
    observability writes use ``FrameworkEvent`` instead.

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


# --- Framework Observability (spec-082) ---


class FrameworkEvent(BaseModel):
    """Canonical framework event entry.

    Appended to ``.ai-engineering/state/framework-events.ndjson`` as the v1
    local-first observability stream. This intentionally excludes transcripts
    and raw tool bodies; structured metadata lives in ``detail``.
    """

    schema_version: str = Field(default="1.0", alias="schemaVersion")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    project: str
    engine: str
    kind: str
    outcome: str
    component: str
    source: str | None = None
    correlation_id: str = Field(alias="correlationId")
    session_id: str | None = Field(default=None, alias="sessionId")
    trace_id: str | None = Field(default=None, alias="traceId")
    parent_id: str | None = Field(default=None, alias="parentId")
    detail: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class CapabilityDescriptor(BaseModel):
    """Single entry inside the framework capability catalog."""

    name: str
    kind: str | None = None
    surface: str | None = None
    tags: list[str] = Field(default_factory=list)


class CapabilityKind(StrEnum):
    """Capability card subject type."""

    SKILL = "skill"
    AGENT = "agent"


class MutationClass(StrEnum):
    """Mutation authority classes exposed by capability cards."""

    READ = "read"
    ADVISE = "advise"
    SPEC_WRITE = "spec-write"
    CODE_WRITE = "code-write"
    STATE_WRITE = "state-write"
    GIT_WRITE = "git-write"
    BOARD_WRITE = "board-write"
    TELEMETRY_EMIT = "telemetry-emit"


class WriteScopeClass(StrEnum):
    """Normalized artifact classes for task write scopes."""

    NONE = "none"
    SOURCE = "source"
    TEST = "test"
    SPEC = "spec"
    STATE = "state"
    MANIFEST = "manifest"
    MIRROR = "mirror"
    DOCUMENTATION = "documentation"
    HOOK = "hook"
    GENERATED = "generated"
    GIT = "git"
    BOARD = "board"
    TELEMETRY = "telemetry"
    UNKNOWN = "unknown"


class CapabilityToolScope(StrEnum):
    """Tool categories a capability may request while executing a packet."""

    READ = "read"
    SEARCH = "search"
    EDIT = "edit"
    TERMINAL = "terminal"
    TEST = "test"
    VALIDATE = "validate"
    GIT = "git"
    GITHUB = "github"
    SUBAGENT = "subagent"
    MEMORY = "memory"
    BROWSER = "browser"
    NOTEBOOK = "notebook"
    POSTMAN = "postman"


class TopologyRole(StrEnum):
    """Execution topology role for first-class and internal capabilities."""

    PUBLIC_FIRST_CLASS = "public-first-class"
    ORCHESTRATOR = "orchestrator"
    LEAF = "leaf"
    INTERNAL_SPECIALIST = "internal-specialist"
    SYSTEM_ACTOR = "system-actor"


class ProviderCompatibilityStatus(StrEnum):
    """Provider support state for a capability card."""

    COMPATIBLE = "compatible"
    DEGRADED = "degraded"
    UNSUPPORTED = "unsupported"


class ProviderCompatibility(BaseModel):
    """Provider-specific support signal for a capability."""

    provider: str
    status: ProviderCompatibilityStatus = ProviderCompatibilityStatus.COMPATIBLE
    reason: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class CapabilityCard(BaseModel):
    """Authoritative machine-readable capability contract for a skill or agent."""

    name: str
    capability_kind: CapabilityKind = Field(alias="capabilityKind")
    topology_role: TopologyRole = Field(alias="topologyRole")
    mutation_classes: list[MutationClass] = Field(alias="mutationClasses")
    write_scope_classes: list[WriteScopeClass] = Field(alias="writeScopeClasses")
    tool_scope: list[CapabilityToolScope] = Field(alias="toolScope")
    provider_compatibility: list[ProviderCompatibility] = Field(
        default_factory=list,
        alias="providerCompatibility",
    )
    accepts_task_packets: bool = Field(default=True, alias="acceptsTaskPackets")
    public: bool = True

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("name")
    @classmethod
    def _validate_non_empty_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Capability cards require a non-empty name"
            raise ValueError(msg)
        return stripped

    @field_validator("mutation_classes", "write_scope_classes", "tool_scope")
    @classmethod
    def _validate_non_empty_lists(cls, values: list[object]) -> list[object]:
        if not values:
            msg = "Capability card authority lists must be non-empty"
            raise ValueError(msg)
        return values


class CapabilityTaskPacket(BaseModel):
    """Task acceptance inputs derived from the HX-02 work plane."""

    task_id: str = Field(alias="taskId")
    owner_role: str = Field(alias="ownerRole")
    mutation_classes: list[MutationClass] = Field(
        default_factory=list,
        alias="mutationClasses",
    )
    write_scope: list[str] = Field(default_factory=list, alias="writeScope")
    tool_requests: list[CapabilityToolScope] = Field(
        default_factory=list,
        alias="toolRequests",
    )
    provider: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    handoffs: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class CapabilityAcceptanceResult(BaseModel):
    """Deterministic acceptance result for one capability/task packet pair."""

    accepted: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ContextPackSourceRole(StrEnum):
    """Authority role for one context-pack source."""

    AUTHORITATIVE = "authoritative"
    DERIVED = "derived"
    OPTIONAL_ADVISORY = "optional-advisory"
    EXCLUDED_RESIDUE = "excluded-residue"


class ContextPackSourcePlane(StrEnum):
    """Plane that owns or produces a context-pack source."""

    CONTROL_PLANE = "control-plane"
    WORK_PLANE = "work-plane"
    STATE_PLANE = "state-plane"
    CAPABILITY_PLANE = "capability-plane"
    LEARNING_FUNNEL = "learning-funnel"
    RUNTIME_RESIDUE = "runtime-residue"


class ContextPackSource(BaseModel):
    """One classified source in a deterministic context pack."""

    path: str
    role: ContextPackSourceRole
    source_plane: ContextPackSourcePlane = Field(alias="sourcePlane")
    owner: str
    inclusion_reason: str = Field(alias="inclusionReason")
    inline_chars: int = Field(default=0, alias="inlineChars")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("path", "owner", "inclusion_reason")
    @classmethod
    def _validate_non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Context-pack sources require non-empty path, owner, and reason"
            raise ValueError(msg)
        return stripped

    @field_validator("inline_chars")
    @classmethod
    def _validate_inline_chars(cls, value: int) -> int:
        if value < 0:
            msg = "inlineChars cannot be negative"
            raise ValueError(msg)
        return value


class ContextPackCeilings(BaseModel):
    """Structural ceilings for generated context packs."""

    max_sources: int = Field(default=32, alias="maxSources")
    max_inline_chars: int = Field(default=0, alias="maxInlineChars")

    model_config = ConfigDict(populate_by_name=True)


class ContextPackManifest(BaseModel):
    """Deterministic context-pack manifest derived from authoritative inputs."""

    schema_version: str = Field(default="1.0", alias="schemaVersion")
    task_id: str | None = Field(default=None, alias="taskId")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), alias="generatedAt"
    )
    sources: list[ContextPackSource] = Field(default_factory=list)
    ceilings: ContextPackCeilings = Field(default_factory=ContextPackCeilings)
    regeneration_inputs: list[str] = Field(default_factory=list, alias="regenerationInputs")

    model_config = ConfigDict(populate_by_name=True)


class HandoffCompact(BaseModel):
    """Reference-first handoff compact that can be resumed from disk alone."""

    schema_version: str = Field(default="1.0", alias="schemaVersion")
    task_id: str = Field(alias="taskId")
    objective: str
    authoritative_refs: list[str] = Field(alias="authoritativeRefs")
    evidence_refs: list[str] = Field(default_factory=list, alias="evidenceRefs")
    next_action: str | None = Field(default=None, alias="nextAction")
    blockers: list[str] = Field(default_factory=list)
    inline_notes: str = Field(default="", alias="inlineNotes")

    model_config = ConfigDict(populate_by_name=True)


class LearningArtifactKind(StrEnum):
    """Learning-funnel artifact kind."""

    NOTE = "note"
    LESSON = "lesson"
    INSTINCT = "instinct"
    PROPOSAL = "proposal"


class LearningArtifactStatus(StrEnum):
    """Lifecycle state for a learning-funnel artifact."""

    ADVISORY = "advisory"
    PROMOTION_CANDIDATE = "promotion-candidate"
    PROMOTED = "promoted"
    REJECTED = "rejected"


class LearningFunnelArtifact(BaseModel):
    """Classified learning-funnel artifact with promotion boundaries."""

    path: str
    kind: LearningArtifactKind
    status: LearningArtifactStatus = LearningArtifactStatus.ADVISORY
    canonical_destination: str | None = Field(default=None, alias="canonicalDestination")
    provenance_ref: str | None = Field(default=None, alias="provenanceRef")
    backlink_ref: str | None = Field(default=None, alias="backlinkRef")

    model_config = ConfigDict(populate_by_name=True)


class LearningFunnelAdvisoryResult(BaseModel):
    """Deterministic advisory checks for learning-funnel promotion candidates."""

    eligible: bool = True
    warnings: list[str] = Field(default_factory=list)


class FrameworkCapabilitiesCatalog(BaseModel):
    """Machine-readable catalog for skills, agents, contexts, and hooks."""

    schema_version: str = Field(default="1.0", alias="schemaVersion")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), alias="generatedAt"
    )
    skills: list[CapabilityDescriptor] = Field(default_factory=list)
    agents: list[CapabilityDescriptor] = Field(default_factory=list)
    context_classes: list[CapabilityDescriptor] = Field(
        default_factory=list, alias="contextClasses"
    )
    hook_kinds: list[CapabilityDescriptor] = Field(default_factory=list, alias="hookKinds")
    capability_cards: list[CapabilityCard] = Field(default_factory=list, alias="capabilityCards")
    update_metadata: UpdateMetadata | None = Field(default=None, alias="updateMetadata")

    model_config = {"populate_by_name": True}


# --- Simplified Instinct Learning (spec-080) ---


class InstinctObservation(BaseModel):
    """Sanitized hook observation for local instinct learning."""

    schema_version: str = Field(default="1.0", alias="schemaVersion")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    engine: str
    kind: str
    tool: str
    outcome: str
    session_id: str | None = Field(default=None, alias="sessionId")
    detail: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class InstinctMeta(BaseModel):
    """Bookkeeping for extraction timing."""

    schema_version: str = Field(default="1.0", alias="schemaVersion")
    last_extracted_at: datetime | None = Field(default=None, alias="lastExtractedAt")
    delta_threshold: int = Field(default=20, alias="deltaThreshold")

    model_config = {"populate_by_name": True}


# --- Work Plane Task Ledger (HX-02) ---


class TaskLifecycleState(StrEnum):
    """Lifecycle states for work-plane ledger tasks."""

    PLANNED = "planned"
    IN_PROGRESS = "in-progress"
    REVIEW = "review"
    VERIFY = "verify"
    BLOCKED = "blocked"
    DONE = "done"


class HandoffRef(BaseModel):
    """Reference to a handoff artifact rooted at the active work plane."""

    kind: str
    path: str
    summary: str | None = None

    model_config = ConfigDict(extra="allow")

    @field_validator("kind", "path")
    @classmethod
    def _validate_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Artifact refs require non-empty kind and path"
            raise ValueError(msg)
        return stripped


class EvidenceRef(BaseModel):
    """Reference to an evidence artifact rooted at the active work plane."""

    kind: str
    path: str
    summary: str | None = None

    model_config = ConfigDict(extra="allow")

    @field_validator("kind", "path")
    @classmethod
    def _validate_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Artifact refs require non-empty kind and path"
            raise ValueError(msg)
        return stripped


class TaskLedgerTask(BaseModel):
    """Single task entry inside the active work-plane ledger."""

    id: str
    title: str
    status: TaskLifecycleState = TaskLifecycleState.PLANNED
    owner_role: str = Field(alias="ownerRole")
    dependencies: list[str] = Field(default_factory=list)
    write_scope: list[str] = Field(default_factory=list, alias="writeScope")
    blocked_reason: str | None = Field(default=None, alias="blockedReason")
    handoffs: list[HandoffRef] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    @field_validator("id", "title", "owner_role")
    @classmethod
    def _validate_non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Task fields must be non-empty strings"
            raise ValueError(msg)
        return stripped

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, value: TaskLifecycleState | str) -> TaskLifecycleState | str:
        if isinstance(value, str):
            return value.strip().lower().replace("_", "-")
        return value

    @field_validator("dependencies")
    @classmethod
    def _validate_dependencies(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()

        for value in values:
            dependency_id = value.strip()
            if not dependency_id:
                msg = "Dependencies must be non-empty"
                raise ValueError(msg)
            if dependency_id in seen:
                msg = "Dependencies must be unique"
                raise ValueError(msg)
            seen.add(dependency_id)
            normalized.append(dependency_id)

        return normalized

    @field_validator("write_scope")
    @classmethod
    def _validate_write_scope(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []

        for value in values:
            scope = value.strip()
            if not scope:
                msg = "Write scopes must be non-empty"
                raise ValueError(msg)
            normalized.append(scope)

        return normalized

    @model_validator(mode="after")
    def _validate_task_consistency(self) -> TaskLedgerTask:
        if self.id in self.dependencies:
            msg = "Task cannot depend on itself"
            raise ValueError(msg)
        if self.status == TaskLifecycleState.BLOCKED and not (self.blocked_reason or "").strip():
            msg = "Blocked tasks require blockedReason"
            raise ValueError(msg)
        if self.status != TaskLifecycleState.BLOCKED and (self.blocked_reason or "").strip():
            msg = "blockedReason is only allowed for blocked tasks"
            raise ValueError(msg)
        return self


class TaskLedger(BaseModel):
    """Structured task ledger for the active work plane."""

    schema_version: str = Field(default="1.0", alias="schemaVersion")
    tasks: list[TaskLedgerTask] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    @model_validator(mode="after")
    def _validate_unique_task_ids(self) -> TaskLedger:
        task_ids = [task.id for task in self.tasks]
        if len(task_ids) != len(set(task_ids)):
            msg = "Task ids must be unique"
            raise ValueError(msg)
        return self


# --- spec-101: required_tools registry + per-tool install records ---


class Platform(StrEnum):
    """Supported host operating systems for tool eligibility (D-101-03)."""

    DARWIN = "darwin"
    LINUX = "linux"
    WINDOWS = "windows"


class ToolScope(StrEnum):
    """Install scope for a tool entry in the required_tools registry."""

    USER_GLOBAL = "user_global"
    USER_GLOBAL_UV_TOOL = "user_global_uv_tool"
    PROJECT_LOCAL = "project_local"
    SDK_BUNDLED = "sdk_bundled"


class ToolInstallState(StrEnum):
    """Per-tool runtime install outcomes recorded after install or doctor."""

    INSTALLED = "installed"
    SKIPPED_PLATFORM_UNSUPPORTED = "skipped_platform_unsupported"
    SKIPPED_PLATFORM_UNSUPPORTED_STACK = "skipped_platform_unsupported_stack"
    NOT_INSTALLED_PROJECT_LOCAL = "not_installed_project_local"
    FAILED_NEEDS_MANUAL = "failed_needs_manual"


class PythonEnvMode(StrEnum):
    """python_env.mode values surfaced from manifest.yml (D-101-12)."""

    UV_TOOL = "uv-tool"
    VENV = "venv"
    SHARED_PARENT = "shared-parent"


class ToolSpec(BaseModel):
    """Single tool entry inside a stack's required_tools list (D-101-01)."""

    name: str
    scope: ToolScope = ToolScope.USER_GLOBAL
    platform_unsupported: list[Platform] | None = None
    unsupported_reason: str | None = None

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def _enforce_platform_invariants(self) -> ToolSpec:
        """Tool-level cap: max 2-of-3 OSes; reason required when present."""
        platforms = self.platform_unsupported
        if platforms is None:
            return self

        # D-101-03 abuse-prevention: tool-level may not list all 3 OSes.
        if len(set(platforms)) >= 3:
            raise ValueError(
                "platform_unsupported at tool-level may list AT MOST 2 of 3 OSes; "
                "use stack-level platform_unsupported_stack for 3-OS escalation (D-101-13)"
            )

        # D-101-03: every platform_unsupported requires a non-empty reason.
        reason = (self.unsupported_reason or "").strip()
        if not reason:
            raise ValueError(
                "platform_unsupported requires a non-empty unsupported_reason (D-101-03)"
            )

        return self


class StackSpec(BaseModel):
    """Per-stack wrapper for a tool list, with optional 3-OS escalation."""

    name: str
    tools: list[ToolSpec] = Field(default_factory=list)
    platform_unsupported_stack: list[Platform] | None = None
    unsupported_reason: str | None = None

    model_config = {"frozen": True}

    @model_validator(mode="before")
    @classmethod
    def _coerce_raw_block(cls, data: Any) -> Any:
        """Accept either the bare-list shape or the nested-dict shape.

        Tests pass either:
        - {"name": "<key>", "raw": [<tool dicts>]}  (bare list)
        - {"name": "<key>", "raw": {"platform_unsupported_stack": ..., "tools": [...]}}
        - or already-shaped dicts via standard model construction
        """
        if not isinstance(data, dict):
            return data

        raw = data.get("raw")
        if raw is None:
            return data

        rest = {k: v for k, v in data.items() if k != "raw"}

        if isinstance(raw, list):
            return {**rest, "tools": raw}

        if isinstance(raw, dict):
            return {**rest, **raw}

        return data

    @model_validator(mode="after")
    def _require_reason_for_stack_unsupported(self) -> StackSpec:
        """Stack-level escalation requires a non-empty reason (D-101-13)."""
        if self.platform_unsupported_stack is not None:
            reason = (self.unsupported_reason or "").strip()
            if not reason:
                raise ValueError(
                    "platform_unsupported_stack requires a non-empty unsupported_reason (D-101-13)"
                )
        return self


class RequiredToolsBlock(BaseModel):
    """Top-level 15-key required_tools block (baseline + 14 stacks).

    Mirrors the shape declared at ``.ai-engineering/manifest.yml`` under
    ``required_tools`` (D-101-01). The ``baseline`` key is mandatory; each
    stack key is optional so partial declarations remain valid for projects
    that opt out of specific stacks.
    """

    baseline: StackSpec
    python: StackSpec | None = None
    typescript: StackSpec | None = None
    javascript: StackSpec | None = None
    java: StackSpec | None = None
    csharp: StackSpec | None = None
    go: StackSpec | None = None
    php: StackSpec | None = None
    rust: StackSpec | None = None
    kotlin: StackSpec | None = None
    swift: StackSpec | None = None
    dart: StackSpec | None = None
    sql: StackSpec | None = None
    bash: StackSpec | None = None
    cpp: StackSpec | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_raw_blocks(cls, data: Any) -> Any:
        """Coerce manifest-style values into StackSpec inputs.

        Each key's value can be a bare list of tool dicts OR a nested dict
        with ``platform_unsupported_stack`` + ``unsupported_reason`` + ``tools``.
        Convert into the ``{"name": <key>, "raw": <value>}`` envelope so the
        StackSpec ``model_validator(mode="before")`` can normalise both shapes.
        """
        if not isinstance(data, dict):
            return data

        coerced: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, StackSpec):
                coerced[key] = value
                continue
            if isinstance(value, (list, dict)):
                coerced[key] = {"name": key, "raw": value}
            else:
                coerced[key] = value
        return coerced


class ToolInstallRecord(BaseModel):
    """Per-tool install outcome captured after install/doctor runs."""

    state: ToolInstallState
    mechanism: str
    version: str | None = None
    verified_at: datetime
    os_release: str | None = None


# Permissive semver-style version regex: digits with optional dotted parts.
# Accepts "21", "8.2", "9", "1.2.3"; rejects "abc", "v1", "21.beta".
_SDK_MIN_VERSION_RE = re.compile(r"^\d+(\.\d+)*$")


class SdkPrereq(BaseModel):
    """Language-SDK prerequisite descriptor (D-101-14).

    Models a single entry in ``manifest.prereqs.sdk_per_stack`` — the SDK that
    must be present before a stack's tools can be installed. ``install_link``
    surfaces the official installer URL the user is directed to on EXIT 81.
    """

    name: str = Field(min_length=1)
    min_version: str | None = None
    install_link: HttpUrl

    model_config = {"frozen": True}

    @field_validator("min_version")
    @classmethod
    def _validate_min_version(cls, value: str | None) -> str | None:
        """Reject non-semver-shaped ``min_version`` values (e.g. ``"abc"``)."""
        if value is None:
            return value
        if not _SDK_MIN_VERSION_RE.match(value):
            msg = f"min_version must be a semver-shaped string, got {value!r}"
            raise ValueError(msg)
        return value


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
    # spec-101 extensions: per-tool install outcomes + python_env mode echo.
    required_tools_state: dict[str, ToolInstallRecord] = Field(default_factory=dict)
    python_env_mode_recorded: PythonEnvMode | None = None
    # spec-101 T-5.2: idempotency flag for the first-run BREAKING banner.
    # The PipelineRunner emits the banner exactly once per project, then sets
    # this to True so subsequent runs stay quiet. Persisted alongside the
    # rest of install-state.json.
    breaking_banner_seen: bool = False
    # spec-107 D-107-09 (H1): per-tool SHA256 hash baseline for rug-pull
    # detection. Maps "stack:tool" -> hex digest. Empty dict on first install
    # is interpreted as "populate baseline silently"; non-empty dict triggers
    # the H1 mismatch check on every subsequent install/sync. Additive
    # backward-compat (default empty dict accommodates pre-spec-107 state files).
    tool_spec_hashes: dict[str, str] = Field(default_factory=dict)

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


# --- spec-104: gate-findings v1 schema ---


class GateSeverity(StrEnum):
    """Severity classification for a single gate finding (D-104-06)."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class GateProducedBy(StrEnum):
    """Producer of a ``gate-findings.json`` document (D-104-06)."""

    AI_COMMIT = "ai-commit"
    AI_PR = "ai-pr"
    WATCH_LOOP = "watch-loop"


class WallClockMs(BaseModel):
    """Wall-clock telemetry block emitted with every gate-findings document.

    Three keys exactly per D-104-06: Wave 1 fixers, Wave 2 checkers, total.
    ``extra="forbid"`` enforces the closed schema (rejects unknown phases).
    """

    wave1_fixers: int
    wave2_checkers: int
    total: int

    model_config = ConfigDict(extra="forbid", frozen=True)


class GateFinding(BaseModel):
    """Single check finding emitted by the orchestrator (D-104-06).

    ``rule_id`` MUST be a stable identifier (CVE-XXXX, semgrep rule-id,
    gitleaks rule-id, ruff code, ty error code) — never a human-readable
    message. The model is frozen because findings are immutable records
    once captured.
    """

    check: str
    rule_id: str
    file: str
    line: int = Field(ge=1)
    column: int | None = None
    severity: GateSeverity
    message: str
    auto_fixable: bool
    auto_fix_command: str | None = None

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def _enforce_auto_fix_command_when_fixable(self) -> GateFinding:
        """``auto_fixable=True`` requires a non-null ``auto_fix_command``."""
        if self.auto_fixable and self.auto_fix_command is None:
            raise ValueError("auto_fixable=True requires a non-null auto_fix_command (D-104-06)")
        return self


class AutoFixedEntry(BaseModel):
    """Auto-fix metadata: which check repaired which files and rules."""

    check: str
    files: list[str] = Field(min_length=1)
    rules_fixed: list[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class AcceptedFinding(BaseModel):
    """A gate finding that was bypassed by an active risk-acceptance Decision.

    Emitted in ``gate-findings.json`` v1.1 (spec-105 D-105-08) under the
    ``accepted_findings`` array. Each entry carries enough context to
    audit which DEC bypassed which finding and when that bypass expires.
    """

    check: str
    rule_id: str
    file: str
    line: int = Field(ge=1)
    severity: GateSeverity
    message: str
    dec_id: str
    expires_at: datetime | None = None

    model_config = ConfigDict(frozen=True)


class GateFindingsDocument(BaseModel):
    """Top-level container for ``gate-findings.json`` schema v1 / v1.1.

    Emitted by the orchestrator at
    ``.ai-engineering/state/gate-findings.json`` and by the watch loop
    at ``.ai-engineering/state/watch-residuals.json``. Versioned via the
    ``schema`` literal so consumers (spec-105 risk-accept) can reject
    unknown versions with an actionable message.

    spec-105 D-105-08 broadens the accepted ``schema`` literal to a Union
    of v1 and v1.1 and adds two additive arrays (``accepted_findings``,
    ``expiring_soon``) to support the orchestrator-level risk-acceptance
    lookup. ``extra="ignore"`` is set defensively so a v1 reader can
    consume a v1.1 document by silently dropping unknown fields, and a
    future minor version bump remains backward-compatible.
    """

    schema_: Literal["ai-engineering/gate-findings/v1", "ai-engineering/gate-findings/v1.1"] = (
        Field(alias="schema")
    )
    session_id: UUID4
    produced_by: GateProducedBy
    produced_at: datetime
    branch: str
    commit_sha: str | None = None
    findings: list[GateFinding] = Field(default_factory=list)
    auto_fixed: list[AutoFixedEntry] = Field(default_factory=list)
    cache_hits: list[str] = Field(default_factory=list)
    cache_misses: list[str] = Field(default_factory=list)
    wall_clock_ms: WallClockMs

    # spec-105 v1.1 additive fields. Default empty so legacy v1 producers
    # remain valid without modification.
    accepted_findings: list[AcceptedFinding] = Field(default_factory=list)
    expiring_soon: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, frozen=True, extra="ignore")


class WatchLoopState(BaseModel):
    """Watch loop runtime state used by D-104-05 wall-clock bounds.

    ``watch_started_at`` anchors the passive-phase 4h cap; the orchestrator
    updates ``last_active_action_at`` whenever the loop applies a fix or
    resolves a conflict (active-phase 30min cap reset). ``fix_attempts``
    tracks per-check retries (per-check >= 3 still triggers STOP).
    """

    watch_started_at: datetime
    last_active_action_at: datetime
    fix_attempts: dict[str, int] = Field(default_factory=dict)
    iteration_count: int = 0
    exit_code: int | None = None

    model_config = ConfigDict(frozen=True)
