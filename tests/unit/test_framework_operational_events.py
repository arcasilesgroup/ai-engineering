"""Tests for operational framework events: hooks, errors, and gates."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.state.io import read_ndjson_entries
from ai_engineering.state.models import FrameworkEvent
from ai_engineering.state.observability import (
    emit_framework_error,
    emit_git_hook_outcome,
    emit_ide_hook_outcome,
    framework_events_path,
)

pytestmark = pytest.mark.unit


def _write_manifest(tmp_path: Path) -> None:
    manifest_path = tmp_path / ".ai-engineering" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("name: demo-project\n", encoding="utf-8")


class TestOperationalEvents:
    def test_ide_hook_events_are_distinct_and_structured(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path)

        emit_ide_hook_outcome(
            tmp_path,
            engine="claude_code",
            hook_kind="user-prompt-submit",
            component="hook.telemetry-skill",
            outcome="success",
            source="hook",
            session_id="session-1",
            trace_id="trace-1",
        )

        entries = read_ndjson_entries(framework_events_path(tmp_path), FrameworkEvent)
        assert len(entries) == 1
        assert entries[0].kind == "ide_hook"
        assert entries[0].detail["hook_kind"] == "user-prompt-submit"
        assert entries[0].outcome == "success"

    def test_framework_error_uses_stable_code_and_bounded_summary(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path)

        emit_framework_error(
            tmp_path,
            engine="github_copilot",
            component="hook.copilot-error",
            error_code="hook_error",
            summary='token="local-test-placeholder" ' + ("x" * 300),
            source="hook",
        )

        entry = read_ndjson_entries(framework_events_path(tmp_path), FrameworkEvent)[0]
        assert entry.kind == "framework_error"
        assert entry.detail["error_code"] == "hook_error"
        assert "[REDACTED]" in entry.detail["summary"]
        assert len(entry.detail["summary"]) <= 214

    def test_git_hook_outcome_includes_failed_checks_and_reasons(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path)

        emit_git_hook_outcome(
            tmp_path,
            hook_kind="pre-commit",
            checks={"ruff-lint": "fail", "gitleaks": "pass"},
            failed_checks=["ruff-lint"],
            failure_reasons={"ruff-lint": "line too long"},
            source="gate-engine",
        )

        entry = read_ndjson_entries(framework_events_path(tmp_path), FrameworkEvent)[0]
        assert entry.kind == "git_hook"
        assert entry.outcome == "failure"
        assert entry.detail["hook_kind"] == "pre-commit"
        assert entry.detail["checks"]["ruff-lint"] == "fail"
        assert entry.detail["failed_checks"] == ["ruff-lint"]
        assert entry.detail["failure_reasons"]["ruff-lint"] == "line too long"
