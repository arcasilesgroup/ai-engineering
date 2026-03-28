"""Tests for the canonical framework observability artifacts from spec-082."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_engineering.state.io import read_ndjson_entries
from ai_engineering.state.models import FrameworkCapabilitiesCatalog, FrameworkEvent
from ai_engineering.state.observability import (
    FRAMEWORK_CAPABILITIES_REL,
    FRAMEWORK_CAPABILITIES_SCHEMA_VERSION,
    FRAMEWORK_EVENT_SCHEMA_VERSION,
    FRAMEWORK_EVENTS_REL,
    append_framework_event,
    build_framework_capabilities,
    framework_capabilities_path,
    framework_events_path,
    write_framework_capabilities,
)

pytestmark = pytest.mark.unit


def _write_manifest(tmp_path: Path) -> None:
    manifest_path = tmp_path / ".ai-engineering" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        """
schema_version: "2.0"
name: demo-project
skills:
  total: 2
  prefix: "ai-"
  registry:
    ai-brainstorm:
      type: workflow
      tags: [planning]
    ai-dispatch:
      type: workflow
      tags: [execution]
agents:
  total: 2
  names: [plan, build]
""".strip()
        + "\n",
        encoding="utf-8",
    )


class TestFrameworkEventPaths:
    def test_framework_events_path_is_canonical(self, tmp_path: Path) -> None:
        assert framework_events_path(tmp_path) == tmp_path / FRAMEWORK_EVENTS_REL

    def test_framework_capabilities_path_is_canonical(self, tmp_path: Path) -> None:
        assert framework_capabilities_path(tmp_path) == tmp_path / FRAMEWORK_CAPABILITIES_REL


class TestFrameworkEvents:
    def test_append_framework_event_is_versioned_and_append_only(self, tmp_path: Path) -> None:
        first = FrameworkEvent(
            project="demo-project",
            engine="claude_code",
            kind="skill_invoked",
            outcome="success",
            component="hook.skill",
            correlationId="corr-1",
            detail={"skill": "ai-brainstorm"},
        )
        second = FrameworkEvent(
            project="demo-project",
            engine="github_copilot",
            kind="agent_dispatched",
            outcome="success",
            component="hook.agent",
            correlationId="corr-2",
            detail={"agent": "ai-build"},
        )

        append_framework_event(tmp_path, first)
        append_framework_event(tmp_path, second)

        event_path = framework_events_path(tmp_path)
        assert event_path.exists()

        raw_lines = event_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(raw_lines) == 2
        assert json.loads(raw_lines[0])["schemaVersion"] == FRAMEWORK_EVENT_SCHEMA_VERSION
        assert json.loads(raw_lines[1])["schemaVersion"] == FRAMEWORK_EVENT_SCHEMA_VERSION

        entries = read_ndjson_entries(event_path, FrameworkEvent)
        assert [entry.kind for entry in entries] == ["skill_invoked", "agent_dispatched"]
        assert entries[0].correlation_id == "corr-1"
        assert entries[1].correlation_id == "corr-2"

    def test_append_framework_event_never_writes_new_framework_data_to_audit_log(
        self, tmp_path: Path
    ) -> None:
        audit_path = tmp_path / ".ai-engineering" / "state" / "audit-log.ndjson"
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.write_text('{"event":"legacy"}\n', encoding="utf-8")

        append_framework_event(
            tmp_path,
            FrameworkEvent(
                project="demo-project",
                engine="claude_code",
                kind="skill_invoked",
                outcome="success",
                component="hook.skill",
                correlationId="corr-1",
                detail={"skill": "ai-dispatch"},
            ),
        )

        assert audit_path.read_text(encoding="utf-8") == '{"event":"legacy"}\n'
        assert framework_events_path(tmp_path).exists()


class TestFrameworkCapabilities:
    def test_build_framework_capabilities_uses_manifest_registry_and_static_taxonomy(
        self, tmp_path: Path
    ) -> None:
        _write_manifest(tmp_path)

        catalog = build_framework_capabilities(tmp_path)

        assert isinstance(catalog, FrameworkCapabilitiesCatalog)
        assert catalog.schema_version == FRAMEWORK_CAPABILITIES_SCHEMA_VERSION
        assert {skill.name for skill in catalog.skills} == {"ai-brainstorm", "ai-dispatch"}
        assert {agent.name for agent in catalog.agents} == {"ai-build", "ai-plan"}
        assert {entry.name for entry in catalog.context_classes} == {
            "language",
            "framework",
            "shared-framework",
            "team",
            "project-identity",
            "spec",
            "plan",
            "decision-store",
        }
        assert {entry.name for entry in catalog.hook_kinds} == {
            "session-start",
            "session-end",
            "user-prompt-submit",
            "pre-tool-use",
            "post-tool-use",
            "stop",
            "error-occurred",
            "pre-commit",
            "commit-msg",
            "pre-push",
        }

    def test_write_framework_capabilities_persists_canonical_catalog(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path)

        catalog = write_framework_capabilities(tmp_path)
        path = framework_capabilities_path(tmp_path)

        assert path.exists()
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["schemaVersion"] == FRAMEWORK_CAPABILITIES_SCHEMA_VERSION
        assert payload["skills"][0]["name"] == catalog.skills[0].name
        assert payload["agents"][0]["name"] == catalog.agents[0].name
        assert {entry["name"] for entry in payload["contextClasses"]} >= {
            "language",
            "project-identity",
        }
