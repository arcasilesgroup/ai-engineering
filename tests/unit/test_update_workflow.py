"""Unit tests for packaged update workflow sequencing."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.commands.update_workflow import UpdateWorkflowStatus, run_update_workflow
from ai_engineering.updater.service import FileChange, UpdateResult


def _result(*, dry_run: bool, changes: list[FileChange] | None = None) -> UpdateResult:
    return UpdateResult(dry_run=dry_run, changes=changes or [])


def test_noninteractive_preview_runs_single_dry_run(tmp_path: Path) -> None:
    calls: list[bool] = []

    def runner(target: Path, *, dry_run: bool) -> UpdateResult:
        assert target == tmp_path
        calls.append(dry_run)
        return _result(dry_run=dry_run)

    result = run_update_workflow(
        tmp_path,
        apply=False,
        interactive=False,
        update_runner=runner,
    )

    assert result.status == UpdateWorkflowStatus.PREVIEW
    assert result.result.dry_run is True
    assert calls == [True]


def test_noninteractive_apply_runs_single_apply(tmp_path: Path) -> None:
    calls: list[bool] = []

    def runner(target: Path, *, dry_run: bool) -> UpdateResult:
        assert target == tmp_path
        calls.append(dry_run)
        return _result(dry_run=dry_run)

    result = run_update_workflow(
        tmp_path,
        apply=True,
        interactive=False,
        update_runner=runner,
    )

    assert result.status == UpdateWorkflowStatus.APPLIED
    assert result.result.dry_run is False
    assert calls == [False]


def test_interactive_no_changes_skips_confirmation_and_apply(tmp_path: Path) -> None:
    calls: list[bool] = []

    def runner(target: Path, *, dry_run: bool) -> UpdateResult:
        assert target == tmp_path
        calls.append(dry_run)
        return _result(dry_run=dry_run)

    result = run_update_workflow(
        tmp_path,
        apply=False,
        interactive=True,
        confirm_apply=lambda _preview: True,
        update_runner=runner,
    )

    assert result.status == UpdateWorkflowStatus.NO_CHANGES
    assert result.preview is result.result
    assert calls == [True]


def test_interactive_decline_keeps_preview_only(tmp_path: Path) -> None:
    preview = _result(
        dry_run=True,
        changes=[FileChange(path=Path("a"), action="update", reason_code="template-drift")],
    )
    calls: list[bool] = []

    def runner(target: Path, *, dry_run: bool) -> UpdateResult:
        assert target == tmp_path
        calls.append(dry_run)
        return preview

    result = run_update_workflow(
        tmp_path,
        apply=False,
        interactive=True,
        confirm_apply=lambda received: received is not preview,
        update_runner=runner,
    )

    assert result.status == UpdateWorkflowStatus.DECLINED
    assert result.preview is preview
    assert result.result is preview
    assert calls == [True]


def test_interactive_confirm_sequences_preview_then_apply(tmp_path: Path) -> None:
    preview = _result(
        dry_run=True,
        changes=[FileChange(path=Path("a"), action="update", reason_code="template-drift")],
    )
    applied = _result(
        dry_run=False,
        changes=[FileChange(path=Path("a"), action="update", reason_code="template-drift")],
    )
    calls: list[bool] = []

    def runner(target: Path, *, dry_run: bool) -> UpdateResult:
        assert target == tmp_path
        calls.append(dry_run)
        return preview if dry_run else applied

    result = run_update_workflow(
        tmp_path,
        apply=False,
        interactive=True,
        confirm_apply=lambda received: received is preview,
        update_runner=runner,
    )

    assert result.status == UpdateWorkflowStatus.APPLIED
    assert result.preview is preview
    assert result.result is applied
    assert calls == [True, False]
