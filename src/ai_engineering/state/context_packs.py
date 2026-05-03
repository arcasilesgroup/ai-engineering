"""Deterministic context packs and learning-funnel helpers for HX-07."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.state.io import write_json_model
from ai_engineering.state.models import (
    ContextPackCeilings,
    ContextPackManifest,
    ContextPackSource,
    ContextPackSourcePlane,
    ContextPackSourceRole,
    HandoffCompact,
    LearningArtifactKind,
    LearningArtifactStatus,
    LearningFunnelAdvisoryResult,
    LearningFunnelArtifact,
    TaskLedgerTask,
)
from ai_engineering.state.work_plane import (
    ActiveWorkPlane,
    read_task_ledger,
    resolve_active_work_plane,
)

CONTEXT_PACKS_DIRNAME = "context-packs"
CONTEXT_PACK_SCHEMA_VERSION = "1.0"
DEFAULT_MAX_SOURCES = 32
DEFAULT_MAX_INLINE_CHARS = 0

_AUTHORITATIVE_CONTROL_PLANE = (
    "CONSTITUTION.md",
    ".ai-engineering/manifest.yml",
    ".ai-engineering/state/decision-store.json",
)
_DERIVED_CAPABILITY_PLANE = (".ai-engineering/state/framework-capabilities.json",)
_OPTIONAL_LEARNING_FUNNEL = (
    ".ai-engineering/LESSONS.md",
    ".ai-engineering/instincts/instincts.yml",
    ".ai-engineering/instincts/proposals.md",
)
_EXCLUDED_RESIDUE = (
    ".ai-engineering/state/framework-events.ndjson",
    ".ai-engineering/state/instinct-observations.ndjson",
    ".ai-engineering/state/strategic-compact.json",
)


def context_packs_dir(project_root: Path) -> Path:
    """Return the active work-plane context-pack directory."""
    return resolve_active_work_plane(project_root).specs_dir / CONTEXT_PACKS_DIRNAME


def context_pack_path(project_root: Path, task_id: str | None = None) -> Path:
    """Return the deterministic context-pack path for a task or active work plane."""
    filename = f"{_safe_task_id(task_id)}.json" if task_id else "active-context-pack.json"
    return context_packs_dir(project_root) / filename


def build_context_pack(
    project_root: Path,
    *,
    task_id: str | None = None,
    max_sources: int = DEFAULT_MAX_SOURCES,
    max_inline_chars: int = DEFAULT_MAX_INLINE_CHARS,
) -> ContextPackManifest:
    """Build a deterministic context-pack manifest from authoritative inputs."""
    work_plane = resolve_active_work_plane(project_root)
    ledger = read_task_ledger(project_root)
    task = _select_task(ledger.tasks if ledger else [], task_id)
    sources: list[ContextPackSource] = []

    for path in _AUTHORITATIVE_CONTROL_PLANE:
        _append_if_exists(
            project_root,
            sources,
            path,
            role=ContextPackSourceRole.AUTHORITATIVE,
            plane=ContextPackSourcePlane.CONTROL_PLANE,
            owner="control-plane",
            reason="bootstrap authority",
        )

    for path in _work_plane_paths(work_plane):
        _append_if_exists(
            project_root,
            sources,
            path,
            role=ContextPackSourceRole.AUTHORITATIVE,
            plane=ContextPackSourcePlane.WORK_PLANE,
            owner="work-plane",
            reason="active work-plane authority",
        )

    if task is not None:
        for ref_path in _task_artifact_paths(task):
            _append_task_artifact_if_exists(
                project_root,
                work_plane,
                sources,
                ref_path,
                role=ContextPackSourceRole.AUTHORITATIVE,
                plane=ContextPackSourcePlane.WORK_PLANE,
                owner="work-plane",
                reason=f"task artifact reference for {task.id}",
            )

    for path in _DERIVED_CAPABILITY_PLANE:
        _append_if_exists(
            project_root,
            sources,
            path,
            role=ContextPackSourceRole.DERIVED,
            plane=ContextPackSourcePlane.CAPABILITY_PLANE,
            owner="capability-plane",
            reason="derived capability projection",
        )

    for path in _OPTIONAL_LEARNING_FUNNEL:
        _append_if_exists(
            project_root,
            sources,
            path,
            role=ContextPackSourceRole.OPTIONAL_ADVISORY,
            plane=ContextPackSourcePlane.LEARNING_FUNNEL,
            owner="learning-funnel",
            reason="optional advisory learning context",
        )

    for path in _EXCLUDED_RESIDUE:
        _append_if_exists(
            project_root,
            sources,
            path,
            role=ContextPackSourceRole.EXCLUDED_RESIDUE,
            plane=ContextPackSourcePlane.RUNTIME_RESIDUE,
            owner="runtime-residue",
            reason="residue excluded from deterministic context authority",
        )

    manifest = ContextPackManifest(
        schemaVersion=CONTEXT_PACK_SCHEMA_VERSION,
        taskId=task.id if task else task_id,
        sources=_dedupe_sources(sources),
        ceilings=ContextPackCeilings(maxSources=max_sources, maxInlineChars=max_inline_chars),
        regenerationInputs=[
            work_plane.spec_path.relative_to(project_root).as_posix(),
            work_plane.plan_path.relative_to(project_root).as_posix(),
            work_plane.ledger_path.relative_to(project_root).as_posix(),
        ],
    )
    return validate_context_pack_manifest(manifest)


def write_context_pack(project_root: Path, *, task_id: str | None = None) -> ContextPackManifest:
    """Write a deterministic context-pack manifest under the active work plane."""
    manifest = build_context_pack(project_root, task_id=task_id)
    write_json_model(context_pack_path(project_root, task_id), manifest)
    return manifest


def validate_handoff_compact(compact: HandoffCompact) -> HandoffCompact:
    """Validate and return a handoff compact."""
    validated = HandoffCompact.model_validate(compact.model_dump(by_alias=True))
    if not validated.task_id.strip() or not validated.objective.strip():
        msg = "Handoff compacts require taskId and objective"
        raise ValueError(msg)
    if not validated.authoritative_refs:
        msg = "Handoff compacts require at least one authoritative ref"
        raise ValueError(msg)
    if not (validated.next_action or "").strip() and not validated.blockers:
        msg = "Handoff compacts require nextAction or blockers"
        raise ValueError(msg)
    if len(validated.inline_notes) > 2000:
        msg = "Handoff compact inlineNotes exceeds 2000 characters"
        raise ValueError(msg)
    return validated


def validate_context_pack_manifest(manifest: ContextPackManifest) -> ContextPackManifest:
    """Validate structural context-pack ceilings and residue rules."""
    included = [
        source
        for source in manifest.sources
        if source.role != ContextPackSourceRole.EXCLUDED_RESIDUE
    ]
    if len(included) > manifest.ceilings.max_sources:
        msg = "Context pack exceeds maxSources"
        raise ValueError(msg)
    if any(source.inline_chars > manifest.ceilings.max_inline_chars for source in included):
        msg = "Context pack exceeds maxInlineChars"
        raise ValueError(msg)
    return manifest


def classify_learning_artifact(path: str) -> LearningFunnelArtifact:
    """Classify a learning-funnel path without promoting it to runtime authority."""
    normalized = path.strip()
    if not normalized:
        msg = "Learning artifact path must be non-empty"
        raise ValueError(msg)

    kind = _learning_kind_for_path(normalized)
    return LearningFunnelArtifact(
        path=normalized,
        kind=kind,
        status=LearningArtifactStatus.ADVISORY,
        provenanceRef=normalized,
    )


def promote_learning_artifact(
    artifact: LearningFunnelArtifact,
    *,
    canonical_destination: str,
    backlink_ref: str | None = None,
) -> LearningFunnelArtifact:
    """Promote an advisory artifact by recording its canonical destination."""
    destination = canonical_destination.strip()
    if not destination:
        msg = "Promoted learning artifacts require canonicalDestination"
        raise ValueError(msg)
    return LearningFunnelArtifact(
        path=artifact.path,
        kind=artifact.kind,
        status=LearningArtifactStatus.PROMOTED,
        canonicalDestination=destination,
        provenanceRef=artifact.provenance_ref or artifact.path,
        backlinkRef=backlink_ref,
    )


def evaluate_learning_artifact(
    artifact: LearningFunnelArtifact,
    *,
    content: str = "",
    existing_paths: tuple[str, ...] = (),
) -> LearningFunnelAdvisoryResult:
    """Flag weak, noisy, or redundant artifacts before promotion."""
    warnings: list[str] = []
    normalized_existing = {path.strip() for path in existing_paths}
    if artifact.path in normalized_existing:
        warnings.append("redundant learning artifact path")

    stripped = content.strip()
    if not stripped:
        warnings.append("weak learning artifact has no content")
    elif len(stripped) > 6000:
        warnings.append("noisy learning artifact exceeds advisory size ceiling")
    elif len(stripped.split()) < 8:
        warnings.append("weak learning artifact is too terse to promote")

    return LearningFunnelAdvisoryResult(eligible=not warnings, warnings=warnings)


def _work_plane_paths(work_plane: ActiveWorkPlane) -> tuple[str, ...]:
    return tuple(
        path.relative_to(work_plane.project_root).as_posix()
        for path in (
            work_plane.spec_path,
            work_plane.plan_path,
            work_plane.current_summary_path,
            work_plane.history_summary_path,
            work_plane.ledger_path,
        )
    )


def _task_artifact_paths(task: TaskLedgerTask) -> list[str]:
    return [ref.path for ref in (*task.handoffs, *task.evidence)]


def _append_if_exists(
    project_root: Path,
    sources: list[ContextPackSource],
    relative_path: str,
    *,
    role: ContextPackSourceRole,
    plane: ContextPackSourcePlane,
    owner: str,
    reason: str,
) -> None:
    if not (project_root / relative_path).exists():
        return
    sources.append(
        ContextPackSource(
            path=relative_path,
            role=role,
            sourcePlane=plane,
            owner=owner,
            inclusionReason=reason,
            inlineChars=0,
        )
    )


def _append_task_artifact_if_exists(
    project_root: Path,
    work_plane: ActiveWorkPlane,
    sources: list[ContextPackSource],
    relative_path: str,
    *,
    role: ContextPackSourceRole,
    plane: ContextPackSourcePlane,
    owner: str,
    reason: str,
) -> None:
    declared_path = Path(relative_path)
    if declared_path.is_absolute():
        return

    project_root_resolved = project_root.resolve()
    for base_dir in (work_plane.specs_dir, project_root):
        candidate = (base_dir / declared_path).resolve()
        try:
            source_path = candidate.relative_to(project_root_resolved).as_posix()
        except ValueError:
            continue
        if candidate.exists():
            _append_if_exists(
                project_root,
                sources,
                source_path,
                role=role,
                plane=plane,
                owner=owner,
                reason=reason,
            )
            return


def _dedupe_sources(sources: list[ContextPackSource]) -> list[ContextPackSource]:
    seen: set[str] = set()
    result: list[ContextPackSource] = []
    for source in sources:
        if source.path in seen:
            continue
        seen.add(source.path)
        result.append(source)
    return sorted(result, key=lambda item: (item.role.value, item.source_plane.value, item.path))


def _select_task(tasks: list[TaskLedgerTask], task_id: str | None) -> TaskLedgerTask | None:
    if task_id:
        return next((task for task in tasks if task.id == task_id), None)
    active_tasks = [task for task in tasks if task.status.value != "done"]
    return active_tasks[0] if len(active_tasks) == 1 else None


def _safe_task_id(task_id: str | None) -> str:
    return (task_id or "active").replace("/", "-").replace(" ", "-")


def _learning_kind_for_path(path: str) -> LearningArtifactKind:
    normalized = path.lower()
    if "lesson" in normalized:
        return LearningArtifactKind.LESSON
    if "proposal" in normalized:
        return LearningArtifactKind.PROPOSAL
    if "instinct" in normalized:
        return LearningArtifactKind.INSTINCT
    return LearningArtifactKind.NOTE
