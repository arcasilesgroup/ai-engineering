"""Unit tests for canonical framework event emission via state.audit."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ai_engineering.state.audit import (
    emit_build_event,
    emit_deploy_event,
    emit_gate_event,
    emit_guard_advisory,
    emit_guard_drift,
    emit_guard_gate,
    emit_scan_event,
)
from ai_engineering.state.io import read_ndjson_entries
from ai_engineering.state.models import FrameworkEvent, GateHook


def _entries(path: Path) -> list[FrameworkEvent]:
    return read_ndjson_entries(
        path / ".ai-engineering" / "state" / "framework-events.ndjson", FrameworkEvent
    )


class TestControlAndOperationEmitters:
    def test_emit_scan_event_writes_control_outcome(self, tmp_path: Path) -> None:
        emit_scan_event(
            tmp_path,
            mode="security",
            score=85,
            findings={"high": 0, "medium": 1},
            outcome="failure",
        )

        entry = _entries(tmp_path)[0]
        assert entry.kind == "control_outcome"
        assert entry.detail["category"] == "quality"
        assert entry.detail["control"] == "security"
        assert entry.outcome == "failure"

    def test_emit_build_event_writes_framework_operation(self, tmp_path: Path) -> None:
        emit_build_event(tmp_path, mode="implement", files_changed=3, lines_added=50)

        entry = _entries(tmp_path)[0]
        assert entry.kind == "framework_operation"
        assert entry.detail["operation"] == "build"
        assert entry.detail["files_changed"] == 3

    def test_emit_deploy_event_writes_framework_operation(self, tmp_path: Path) -> None:
        emit_deploy_event(
            tmp_path,
            environment="staging",
            strategy="rolling",
            version="1.0.0",
            result="success",
        )

        entry = _entries(tmp_path)[0]
        assert entry.kind == "framework_operation"
        assert entry.detail["operation"] == "deploy"
        assert entry.detail["environment"] == "staging"

    def test_emit_guard_advisory_writes_control_outcome(self, tmp_path: Path) -> None:
        emit_guard_advisory(tmp_path, files_checked=5, warnings=2, concerns=1)

        entry = _entries(tmp_path)[0]
        assert entry.kind == "control_outcome"
        assert entry.detail["control"] == "guard-advisory"
        assert entry.outcome == "warning"

    def test_emit_guard_gate_writes_control_outcome(self, tmp_path: Path) -> None:
        emit_guard_gate(tmp_path, verdict="PASS", task="risk-check", agent="build")

        entry = _entries(tmp_path)[0]
        assert entry.kind == "control_outcome"
        assert entry.detail["control"] == "risk-check"
        assert entry.outcome == "success"

    def test_emit_guard_drift_writes_control_outcome(self, tmp_path: Path) -> None:
        emit_guard_drift(tmp_path, decisions_checked=10, drifted=2, critical=1)

        entry = _entries(tmp_path)[0]
        assert entry.kind == "control_outcome"
        assert entry.detail["control"] == "guard-drift"
        assert entry.outcome == "failure"


class TestEmitGateEventCanonical:
    def test_emits_git_hook_event_to_framework_stream(self, tmp_path: Path) -> None:
        from ai_engineering.policy.gates import GateCheckResult, GateResult

        result = GateResult(
            hook=GateHook.PRE_COMMIT,
            checks=[
                GateCheckResult(name="ruff-lint", passed=False, output="line too long"),
                GateCheckResult(name="gitleaks", passed=True, output=""),
            ],
        )

        emit_gate_event(tmp_path, result)

        entries = _entries(tmp_path)
        assert len(entries) == 1
        assert entries[0].kind == "git_hook"
        assert entries[0].detail["hook_kind"] == "pre-commit"
        assert entries[0].detail["failed_checks"] == ["ruff-lint"]
        assert entries[0].detail["failure_reasons"]["ruff-lint"] == "line too long"

    def test_fail_open_when_framework_stream_cannot_be_written(self, tmp_path: Path) -> None:
        from ai_engineering.policy.gates import GateCheckResult, GateResult

        result = GateResult(
            hook=GateHook.PRE_COMMIT,
            checks=[GateCheckResult(name="ruff-lint", passed=False, output="bad")],
        )

        with patch(
            "ai_engineering.state.audit.emit_git_hook_outcome",
            side_effect=OSError("disk full"),
        ):
            emit_gate_event(tmp_path, result)

        framework_path = tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson"
        assert not framework_path.exists()
