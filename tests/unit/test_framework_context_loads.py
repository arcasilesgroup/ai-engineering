"""Tests for canonical context load events."""

from __future__ import annotations

import json
from pathlib import Path

from ai_engineering.state.io import read_ndjson_entries
from ai_engineering.state.models import FrameworkEvent
from ai_engineering.state.observability import emit_declared_context_loads, framework_events_path


def _seed_project(
    tmp_path: Path,
    *,
    constitution_paths: tuple[str, ...] = (".ai-engineering/CONSTITUTION.md",),
) -> None:
    manifest_path = tmp_path / ".ai-engineering" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        """
name: demo-project
providers:
  stacks: [python, react]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    for rel in (
        ".ai-engineering/contexts/languages/python.md",
        ".ai-engineering/contexts/frameworks/react.md",
        ".ai-engineering/contexts/team/conventions.md",
        ".ai-engineering/contexts/cli-ux.md",
        ".ai-engineering/contexts/mcp-integrations.md",
        ".ai-engineering/specs/spec.md",
        ".ai-engineering/specs/plan.md",
        ".ai-engineering/state/decision-store.json",
    ):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("seed\n", encoding="utf-8")

    for rel in constitution_paths:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("seed\n", encoding="utf-8")


class TestDeclaredContextLoads:
    def test_emits_distinct_context_classes_with_initiator_attribution(
        self, tmp_path: Path
    ) -> None:
        _seed_project(tmp_path)

        emit_declared_context_loads(
            tmp_path,
            engine="claude_code",
            initiator_kind="skill",
            initiator_name="ai-code",
            component="hook.telemetry-skill",
            source="hook",
            session_id="session-1",
            trace_id="trace-1",
            correlation_id="corr-1",
        )

        entries = read_ndjson_entries(framework_events_path(tmp_path), FrameworkEvent)
        classes = {entry.detail["context_class"] for entry in entries}

        assert classes == {
            "language",
            "framework",
            "shared-framework",
            "team",
            "constitution",
            "spec",
            "plan",
            "decision-store",
        }
        shared_context_names = {
            entry.detail["context_name"]
            for entry in entries
            if entry.detail["context_class"] == "shared-framework"
        }
        assert shared_context_names == {"cli-ux", "mcp-integrations"}
        assert all(entry.kind == "context_load" for entry in entries)
        assert all(entry.detail["initiator_kind"] == "skill" for entry in entries)
        assert all(entry.detail["initiator_name"] == "ai-code" for entry in entries)
        assert all(entry.detail["load_mode"] == "declared" for entry in entries)

    def test_missing_declared_context_emits_failure(self, tmp_path: Path) -> None:
        _seed_project(tmp_path)
        (tmp_path / ".ai-engineering/specs/plan.md").unlink()

        emit_declared_context_loads(
            tmp_path,
            engine="claude_code",
            initiator_kind="skill",
            initiator_name="ai-dispatch",
            component="hook.telemetry-skill",
            source="hook",
            session_id="session-2",
            trace_id="trace-2",
            correlation_id="corr-2",
        )

        entries = read_ndjson_entries(framework_events_path(tmp_path), FrameworkEvent)
        plan_event = next(entry for entry in entries if entry.detail["context_class"] == "plan")
        assert plan_event.outcome == "failure"

    def test_root_constitution_is_preferred_when_present(self, tmp_path: Path) -> None:
        # spec-123 D-123-17: workspace-charter stub deleted; only root
        # CONSTITUTION.md remains. Test asserts the canonical path emits.
        _seed_project(
            tmp_path,
            constitution_paths=("CONSTITUTION.md",),
        )

        emit_declared_context_loads(
            tmp_path,
            engine="claude_code",
            initiator_kind="skill",
            initiator_name="ai-start",
            component="hook.telemetry-skill",
            source="hook",
            session_id="session-3",
            trace_id="trace-3",
            correlation_id="corr-3",
        )

        entries = read_ndjson_entries(framework_events_path(tmp_path), FrameworkEvent)
        constitution_event = next(
            entry for entry in entries if entry.detail["context_class"] == "constitution"
        )
        assert constitution_event.outcome == "success"
        assert constitution_event.detail["path"] == "CONSTITUTION.md"

    def test_active_pointer_redirects_declared_spec_contexts(self, tmp_path: Path) -> None:
        _seed_project(tmp_path)
        resolved_specs_dir = tmp_path / "resolved-work-plane"
        resolved_specs_dir.mkdir()
        (resolved_specs_dir / "spec.md").write_text("resolved spec\n", encoding="utf-8")
        (resolved_specs_dir / "plan.md").write_text("resolved plan\n", encoding="utf-8")
        (tmp_path / ".ai-engineering" / "specs" / "active-work-plane.json").write_text(
            json.dumps({"specsDir": "resolved-work-plane"}),
            encoding="utf-8",
        )

        emit_declared_context_loads(
            tmp_path,
            engine="claude_code",
            initiator_kind="skill",
            initiator_name="ai-start",
            component="hook.telemetry-skill",
            source="hook",
            session_id="session-5",
            trace_id="trace-5",
            correlation_id="corr-5",
        )

        entries = read_ndjson_entries(framework_events_path(tmp_path), FrameworkEvent)
        spec_event = next(entry for entry in entries if entry.detail["context_class"] == "spec")
        plan_event = next(entry for entry in entries if entry.detail["context_class"] == "plan")
        assert spec_event.detail["path"] == "resolved-work-plane/spec.md"
        assert plan_event.detail["path"] == "resolved-work-plane/plan.md"
