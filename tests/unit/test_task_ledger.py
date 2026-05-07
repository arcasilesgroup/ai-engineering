from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_engineering.state.models import TaskLedger, TaskLedgerTask, TaskLifecycleState


def test_task_ledger_task_accepts_artifact_refs_and_alias_fields() -> None:
    task = TaskLedgerTask.model_validate(
        {
            "id": "T-2.1",
            "title": "Define task ledger schema",
            "status": "review",
            "ownerRole": "orchestrator",
            "dependencies": ["T-2.0"],
            "writeScope": ["src/ai_engineering/state/**", "tests/unit/test_task_ledger.py"],
            "handoffs": [
                {
                    "kind": "review-note",
                    "path": ".ai-engineering/specs/spec-117/handoffs/T-2.1.md",
                }
            ],
            "evidence": [
                {
                    "kind": "pytest",
                    "path": ".ai-engineering/specs/spec-117/evidence/T-2.1.log",
                }
            ],
        }
    )

    assert task.status == TaskLifecycleState.REVIEW
    assert task.owner_role == "orchestrator"
    assert task.write_scope == [
        "src/ai_engineering/state/**",
        "tests/unit/test_task_ledger.py",
    ]
    assert task.handoffs[0].kind == "review-note"
    assert task.evidence[0].kind == "pytest"


def test_blocked_task_requires_blocked_reason() -> None:
    with pytest.raises(ValidationError, match="Blocked tasks require blockedReason"):
        TaskLedgerTask(
            id="T-2.2",
            title="Persist ledger",
            status=TaskLifecycleState.BLOCKED,
            ownerRole="build",
        )


def test_non_blocked_task_rejects_blocked_reason() -> None:
    with pytest.raises(ValidationError, match="blockedReason is only allowed for blocked tasks"):
        TaskLedgerTask(
            id="T-2.2",
            title="Persist ledger",
            status=TaskLifecycleState.DONE,
            ownerRole="build",
            blockedReason="Waiting on review",
        )


def test_task_ledger_rejects_duplicate_task_ids() -> None:
    task = TaskLedgerTask(
        id="T-2.1",
        title="Define task ledger schema",
        ownerRole="orchestrator",
    )

    with pytest.raises(ValidationError, match="Task ids must be unique"):
        TaskLedger(tasks=[task, task])


def test_task_ledger_task_rejects_self_dependencies() -> None:
    with pytest.raises(ValidationError, match="Task cannot depend on itself"):
        TaskLedgerTask(
            id="T-2.1",
            title="Define task ledger schema",
            ownerRole="orchestrator",
            dependencies=["T-2.1"],
        )
