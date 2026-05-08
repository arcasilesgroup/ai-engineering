"""Packaged workflow for the ``ai-eng update`` command.

The CLI remains responsible for parsing flags, prompting, and rendering.
This module owns update sequencing so command adapters do not directly mix
preview/apply branching with the framework mutation call.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from ai_engineering.updater.service import UpdateResult, update


class UpdateWorkflowStatus(StrEnum):
    """High-level outcome of an update workflow run."""

    PREVIEW = "preview"
    APPLIED = "applied"
    DECLINED = "declined"
    NO_CHANGES = "no-changes"


class UpdateRunner(Protocol):
    """Callable shape for running the updater with a dry-run flag."""

    def __call__(self, target: Path, *, dry_run: bool) -> UpdateResult: ...


@dataclass(frozen=True)
class UpdateWorkflowResult:
    """Result returned to the CLI adapter for rendering and exit handling."""

    status: UpdateWorkflowStatus
    result: UpdateResult
    preview: UpdateResult | None = None


def run_update_workflow(
    target: Path,
    *,
    apply: bool,
    interactive: bool,
    confirm_apply: Callable[[UpdateResult], bool] | None = None,
    update_runner: UpdateRunner = update,
) -> UpdateWorkflowResult:
    """Run update preview/apply sequencing without doing CLI rendering."""
    if not interactive:
        result = update_runner(target, dry_run=not apply)
        status = UpdateWorkflowStatus.APPLIED if apply else UpdateWorkflowStatus.PREVIEW
        return UpdateWorkflowResult(status=status, result=result)

    preview = update_runner(target, dry_run=True)
    if preview.available_count == 0 and preview.orphan_count == 0:
        return UpdateWorkflowResult(
            status=UpdateWorkflowStatus.NO_CHANGES,
            result=preview,
            preview=preview,
        )

    if confirm_apply is None:
        msg = "interactive update workflow requires a confirmation callback"
        raise ValueError(msg)

    if not confirm_apply(preview):
        return UpdateWorkflowResult(
            status=UpdateWorkflowStatus.DECLINED,
            result=preview,
            preview=preview,
        )

    applied = update_runner(target, dry_run=False)
    return UpdateWorkflowResult(
        status=UpdateWorkflowStatus.APPLIED,
        result=applied,
        preview=preview,
    )
