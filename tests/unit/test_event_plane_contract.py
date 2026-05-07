"""RED contract tests for HX-05 T-3.1 canonical event normalization."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from ai_engineering.state import observability as runtime_obs
from ai_engineering.state.event_schema import validate_event_schema

_HOOKS_DIR = Path(__file__).parents[2] / ".ai-engineering" / "scripts" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

hook_obs = importlib.import_module("_lib.observability")


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    manifest_path = tmp_path / ".ai-engineering" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("name: demo-project\n", encoding="utf-8")
    return tmp_path


def test_validate_event_schema_rejects_noncanonical_event_kind() -> None:
    event = {
        "schemaVersion": "1.0",
        "timestamp": "2026-05-01T12:00:00Z",
        "project": "demo-project",
        "engine": "codex",
        "kind": "skill_invoked_malformed",
        "outcome": "warn",
        "component": "hook.codex-bridge",
        "correlationId": "corr-1",
        "detail": {"reason": "no_ai_prefix"},
    }

    assert validate_event_schema(event) is False


def test_runtime_and_hook_builders_normalize_legacy_copilot_provider_id(
    project_root: Path,
) -> None:
    runtime_entry = runtime_obs.build_framework_event(
        project_root,
        engine="github_copilot",
        kind="agent_dispatched",
        component="hook.copilot-agent",
        correlation_id="corr-1",
        trace_id="trace-1",
    )
    hook_entry = hook_obs.build_framework_event(
        project_root,
        engine="github_copilot",
        kind="agent_dispatched",
        component="hook.copilot-agent",
        correlation_id="corr-1",
        trace_id="trace-1",
    )

    runtime_payload = runtime_entry.model_dump(by_alias=True, exclude_none=True)

    assert runtime_payload["engine"] == "copilot"
    assert hook_entry["engine"] == "copilot"


def test_runtime_and_hook_builders_share_canonical_root_trace_fields(
    project_root: Path,
) -> None:
    runtime_entry = runtime_obs.build_framework_event(
        project_root,
        engine="claude_code",
        kind="skill_invoked",
        component="hook.telemetry-skill",
        correlation_id="corr-2",
        session_id="session-2",
        trace_id="trace-2",
        parent_id="parent-2",
    )
    hook_entry = hook_obs.build_framework_event(
        project_root,
        engine="claude_code",
        kind="skill_invoked",
        component="hook.telemetry-skill",
        correlation_id="corr-2",
        session_id="session-2",
        trace_id="trace-2",
        parent_id="parent-2",
    )

    runtime_payload = runtime_entry.model_dump(by_alias=True, exclude_none=True)

    assert set(runtime_payload) == set(hook_entry)
    assert runtime_payload["traceId"] == "trace-2"
    assert hook_entry["traceId"] == "trace-2"


def test_runtime_and_hook_observability_expose_task_trace_emitters() -> None:
    runtime_emit = getattr(runtime_obs, "emit_task_trace", None)
    hook_emit = getattr(hook_obs, "emit_task_trace", None)

    assert callable(runtime_emit)
    assert callable(hook_emit)

    runtime_entry = runtime_emit(  # type: ignore[operator]
        Path("/tmp/demo-project"),
        task_id="HX-05-T-3.1",
        lifecycle_phase="in-progress",
        component="state.task-ledger",
        correlation_id="corr-task-1",
        trace_id="trace-task-1",
        artifact_refs=(".ai-engineering/specs/current-summary.md",),
    )
    hook_entry = hook_emit(  # type: ignore[operator]
        Path("/tmp/demo-project"),
        task_id="HX-05-T-3.1",
        lifecycle_phase="in-progress",
        component="state.task-ledger",
        correlation_id="corr-task-1",
        trace_id="trace-task-1",
        artifact_refs=(".ai-engineering/specs/current-summary.md",),
    )

    runtime_payload = runtime_entry.model_dump(by_alias=True, exclude_none=True)

    assert runtime_payload["kind"] == "task_trace"
    assert runtime_payload["traceId"] == "trace-task-1"
    assert runtime_payload["detail"] == {
        "task_id": "HX-05-T-3.1",
        "lifecycle_phase": "in-progress",
        "artifact_refs": [".ai-engineering/specs/current-summary.md"],
    }
    assert hook_entry["kind"] == "task_trace"
    assert hook_entry["traceId"] == "trace-task-1"
    assert hook_entry["detail"] == {
        "task_id": "HX-05-T-3.1",
        "lifecycle_phase": "in-progress",
        "artifact_refs": [".ai-engineering/specs/current-summary.md"],
    }
