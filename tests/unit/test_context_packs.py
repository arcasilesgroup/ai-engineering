"""Tests for HX-07 deterministic context packs and learning funnel helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.state.context_packs import (
    build_context_pack,
    classify_learning_artifact,
    context_pack_path,
    evaluate_learning_artifact,
    promote_learning_artifact,
    validate_handoff_compact,
    write_context_pack,
)
from ai_engineering.state.io import write_json_model
from ai_engineering.state.models import (
    ContextPackSourceRole,
    HandoffCompact,
    HandoffRef,
    LearningArtifactKind,
    LearningArtifactStatus,
    TaskLedger,
    TaskLedgerTask,
    TaskLifecycleState,
)


def _write_pack_fixture(root: Path) -> None:
    ai = root / ".ai-engineering"
    specs = ai / "specs"
    specs.mkdir(parents=True)
    (root / "CONSTITUTION.md").write_text("# Constitution\n", encoding="utf-8")
    (ai / "manifest.yml").write_text("name: test\n", encoding="utf-8")
    (ai / "state").mkdir()
    (ai / "state" / "decision-store.json").write_text("{}\n", encoding="utf-8")
    (ai / "state" / "framework-capabilities.json").write_text("{}\n", encoding="utf-8")
    (ai / "state" / "framework-events.ndjson").write_text("{}\n", encoding="utf-8")
    (ai / "state" / "strategic-compact.json").write_text("{}\n", encoding="utf-8")
    (ai / "LESSONS.md").write_text("# Lessons\n", encoding="utf-8")
    (ai / "instincts").mkdir()
    (ai / "instincts" / "observations.yml").write_text("schemaVersion: '2.0'\n", encoding="utf-8")
    (specs / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (specs / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (specs / "current-summary.md").write_text("# Current\n", encoding="utf-8")
    (specs / "history-summary.md").write_text("# History\n", encoding="utf-8")
    (specs / "handoffs").mkdir()
    (specs / "handoffs" / "build.md").write_text("handoff\n", encoding="utf-8")
    write_json_model(
        specs / "task-ledger.json",
        TaskLedger(
            tasks=[
                TaskLedgerTask(
                    id="T-1",
                    title="Build context pack",
                    status=TaskLifecycleState.IN_PROGRESS,
                    owner_role="Build",
                    handoffs=[
                        HandoffRef(kind="build", path=".ai-engineering/specs/handoffs/build.md")
                    ],
                )
            ]
        ),
    )


@pytest.mark.skip(reason="Spec-123 removed task-ledger surface from work_plane")
def test_build_context_pack_classifies_authority_and_residue(tmp_path: Path) -> None:
    _write_pack_fixture(tmp_path)

    manifest = build_context_pack(tmp_path, task_id="T-1")
    sources = {source.path: source for source in manifest.sources}

    assert sources["CONSTITUTION.md"].role == ContextPackSourceRole.AUTHORITATIVE
    assert sources[".ai-engineering/specs/task-ledger.json"].role == (
        ContextPackSourceRole.AUTHORITATIVE
    )
    assert sources[".ai-engineering/state/framework-capabilities.json"].role == (
        ContextPackSourceRole.DERIVED
    )
    assert sources[".ai-engineering/LESSONS.md"].role == ContextPackSourceRole.OPTIONAL_ADVISORY
    assert sources[".ai-engineering/state/framework-events.ndjson"].role == (
        ContextPackSourceRole.EXCLUDED_RESIDUE
    )
    assert sources[".ai-engineering/specs/handoffs/build.md"].role == (
        ContextPackSourceRole.AUTHORITATIVE
    )
    assert all(source.inline_chars == 0 for source in manifest.sources)


@pytest.mark.skip(reason="Spec-123 removed task-ledger surface from work_plane")
def test_context_pack_resolves_task_artifacts_relative_to_active_work_plane(
    tmp_path: Path,
) -> None:
    _write_pack_fixture(tmp_path)
    specs = tmp_path / ".ai-engineering" / "specs"
    write_json_model(
        specs / "task-ledger.json",
        TaskLedger(
            tasks=[
                TaskLedgerTask(
                    id="T-1",
                    title="Build context pack",
                    status=TaskLifecycleState.IN_PROGRESS,
                    owner_role="Build",
                    handoffs=[HandoffRef(kind="build", path="handoffs/build.md")],
                )
            ]
        ),
    )

    manifest = build_context_pack(tmp_path, task_id="T-1")
    sources = {source.path: source for source in manifest.sources}

    assert ".ai-engineering/specs/handoffs/build.md" in sources


def test_write_context_pack_persists_under_active_work_plane(tmp_path: Path) -> None:
    _write_pack_fixture(tmp_path)

    manifest = write_context_pack(tmp_path, task_id="T-1")

    pack_path = context_pack_path(tmp_path, "T-1")
    assert pack_path == tmp_path / ".ai-engineering" / "specs" / "context-packs" / "T-1.json"
    assert pack_path.is_file()
    assert manifest.task_id == "T-1"


def test_context_pack_enforces_source_count_ceiling(tmp_path: Path) -> None:
    _write_pack_fixture(tmp_path)

    with pytest.raises(ValueError, match="maxSources"):
        build_context_pack(tmp_path, task_id="T-1", max_sources=1)


def test_handoff_compact_requires_reference_first_resume_fields() -> None:
    compact = HandoffCompact(
        taskId="T-1",
        objective="Continue implementation",
        authoritativeRefs=[".ai-engineering/specs/task-ledger.json"],
        nextAction="Run focused tests",
    )

    assert validate_handoff_compact(compact).task_id == "T-1"

    invalid = HandoffCompact(
        taskId="T-2",
        objective="Continue implementation",
        authoritativeRefs=[".ai-engineering/specs/task-ledger.json"],
    )
    with pytest.raises(ValueError, match="nextAction or blockers"):
        validate_handoff_compact(invalid)


def test_learning_artifact_classification_is_advisory_by_default() -> None:
    artifact = classify_learning_artifact(".ai-engineering/observations/proposals.md")

    assert artifact.kind == LearningArtifactKind.PROPOSAL
    assert artifact.status == LearningArtifactStatus.ADVISORY
    assert artifact.canonical_destination is None


def test_learning_artifact_promotion_requires_canonical_destination() -> None:
    artifact = classify_learning_artifact(".ai-engineering/observations/proposals.md")

    promoted = promote_learning_artifact(
        artifact,
        canonical_destination=".ai-engineering/state/decision-store.json",
        backlink_ref=".ai-engineering/observations/proposals.md",
    )

    assert promoted.status == LearningArtifactStatus.PROMOTED
    assert promoted.canonical_destination == ".ai-engineering/state/decision-store.json"
    assert promoted.backlink_ref == ".ai-engineering/observations/proposals.md"

    with pytest.raises(ValueError, match="canonicalDestination"):
        promote_learning_artifact(
            artifact,
            canonical_destination="",
        )


def test_learning_artifact_advisory_checks_flag_weak_noisy_and_redundant() -> None:
    artifact = classify_learning_artifact(".ai-engineering/LESSONS.md")

    weak = evaluate_learning_artifact(artifact, content="too short")
    noisy = evaluate_learning_artifact(artifact, content="word " * 6001)
    redundant = evaluate_learning_artifact(
        artifact,
        content="This lesson has enough useful words to be considered for promotion.",
        existing_paths=(".ai-engineering/LESSONS.md",),
    )

    assert weak.eligible is False
    assert weak.warnings == ["weak learning artifact is too terse to promote"]
    assert noisy.eligible is False
    assert noisy.warnings == ["noisy learning artifact exceeds advisory size ceiling"]
    assert redundant.eligible is False
    assert redundant.warnings == ["redundant learning artifact path"]
