"""Tests for the canonical framework observability artifacts from spec-082."""

from __future__ import annotations

import json
from pathlib import Path

from ai_engineering.state.io import read_ndjson_entries
from ai_engineering.state.models import (
    CapabilityKind,
    CapabilityToolScope,
    FrameworkCapabilitiesCatalog,
    FrameworkEvent,
    MutationClass,
    TopologyRole,
    WriteScopeClass,
)
from ai_engineering.state.observability import (
    FRAMEWORK_CAPABILITIES_REL,
    FRAMEWORK_CAPABILITIES_SCHEMA_VERSION,
    FRAMEWORK_EVENT_SCHEMA_VERSION,
    FRAMEWORK_EVENTS_REL,
    append_framework_event,
    append_framework_events,
    build_framework_capabilities,
    build_framework_event,
    framework_capabilities_path,
    framework_events_path,
    write_framework_capabilities,
)


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
        assert entries[1].engine == "copilot"
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

    def test_append_framework_events_chains_batch_without_rereading_file(
        self, tmp_path: Path
    ) -> None:
        from ai_engineering.state.audit_chain import compute_entry_hash

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

        append_framework_events(tmp_path, [first, second])

        raw_lines = framework_events_path(tmp_path).read_text(encoding="utf-8").splitlines()
        first_payload = json.loads(raw_lines[0])
        second_payload = json.loads(raw_lines[1])
        assert first_payload["prev_event_hash"] is None
        assert second_payload["prev_event_hash"] == compute_entry_hash(first_payload)


class TestFrameworkVersionStamp:
    """spec-190 D-190-01: the pip build path stamps frameworkVersion."""

    def test_pip_envelope_carries_non_empty_framework_version(self, tmp_path: Path) -> None:
        event = build_framework_event(
            tmp_path,
            engine="claude_code",
            kind="skill_invoked",
            component="hook.skill",
        )
        dumped = event.model_dump(by_alias=True)
        assert dumped["frameworkVersion"]
        assert isinstance(dumped["frameworkVersion"], str)


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
            "constitution",
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

    def test_build_framework_capabilities_includes_authoritative_capability_cards(
        self, tmp_path: Path
    ) -> None:
        _write_manifest(tmp_path)

        catalog = build_framework_capabilities(tmp_path)
        cards_by_name = {card.name: card for card in catalog.capability_cards}

        assert set(cards_by_name) == {
            "ai-brainstorm",
            "ai-dispatch",
            "ai-build",
            "ai-plan",
        }
        build_card = cards_by_name["ai-build"]
        assert build_card.capability_kind == CapabilityKind.AGENT
        assert build_card.topology_role == TopologyRole.PUBLIC_FIRST_CLASS
        assert MutationClass.CODE_WRITE in build_card.mutation_classes
        assert WriteScopeClass.SOURCE in build_card.write_scope_classes
        assert CapabilityToolScope.EDIT in build_card.tool_scope

        plan_card = cards_by_name["ai-plan"]
        assert MutationClass.SPEC_WRITE in plan_card.mutation_classes
        assert MutationClass.CODE_WRITE not in plan_card.mutation_classes

    def test_write_framework_capabilities_persists_canonical_catalog(self, tmp_path: Path) -> None:
        """spec-148 P4: catalog lives in ``framework-capabilities.json`` (files-only).

        Reverses the spec-125 cutover: the writer rebuilds the catalog and
        writes the JSON file via the durable repository. We assert the file
        exists and probe it via the canonical repository reader.
        """
        from ai_engineering.state.repository import DurableStateRepository

        _write_manifest(tmp_path)

        catalog = write_framework_capabilities(tmp_path)

        # spec-148 P4: framework-capabilities.json is the canonical sink.
        assert framework_capabilities_path(tmp_path).is_file()

        repo = DurableStateRepository(tmp_path)
        loaded = repo.load_framework_capabilities()
        payload = loaded.model_dump(mode="json", by_alias=True)
        assert payload["schemaVersion"] == FRAMEWORK_CAPABILITIES_SCHEMA_VERSION
        assert payload["skills"][0]["name"] == catalog.skills[0].name
        assert payload["agents"][0]["name"] == catalog.agents[0].name
        assert {entry["name"] for entry in payload["contextClasses"]} >= {
            "language",
            "constitution",
        }
        assert {entry["name"] for entry in payload["capabilityCards"]} == {
            "ai-brainstorm",
            "ai-dispatch",
            "ai-build",
            "ai-plan",
        }


# ---------------------------------------------------------------------------
# spec-190 D-190-02: error-storm coalescing (pip functional twin)
# ---------------------------------------------------------------------------


class TestErrorStormCoalescing:
    """emit_framework_error must mirror the hook _lib coalescer semantics."""

    @staticmethod
    def _emit(tmp_path: Path) -> None:
        from ai_engineering.state.observability import emit_framework_error

        emit_framework_error(
            tmp_path,
            engine="ai_engineering",
            component="pip.storm",
            error_code="hook_execution_failed",
            summary="identical boom",
            session_id="sess-1",
        )

    @staticmethod
    def _events(tmp_path: Path) -> list[dict]:
        path = tmp_path / FRAMEWORK_EVENTS_REL
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_repeats_coalesce(self, tmp_path: Path, monkeypatch) -> None:
        _write_manifest(tmp_path)
        monkeypatch.setenv("AIENG_ERROR_STORM_THRESHOLD", "5")
        for _ in range(5):
            self._emit(tmp_path)
        errors = [e for e in self._events(tmp_path) if e.get("kind") == "framework_error"]
        assert len(errors) == 2
        assert errors[-1]["detail"].get("occurrences") == 5

    def test_storm_control_emitted_once(self, tmp_path: Path, monkeypatch) -> None:
        _write_manifest(tmp_path)
        monkeypatch.setenv("AIENG_ERROR_STORM_THRESHOLD", "5")
        for _ in range(12):
            self._emit(tmp_path)
        controls = [
            e
            for e in self._events(tmp_path)
            if e.get("kind") == "control_outcome"
            and e.get("detail", {}).get("control") == "framework_error_storm"
        ]
        assert len(controls) == 1
        assert controls[0]["detail"]["category"] == "observability"

    def test_distinct_summaries_do_not_coalesce(self, tmp_path: Path, monkeypatch) -> None:
        from ai_engineering.state.observability import emit_framework_error

        _write_manifest(tmp_path)
        monkeypatch.setenv("AIENG_ERROR_STORM_THRESHOLD", "5")
        for i in range(3):
            emit_framework_error(
                tmp_path,
                engine="ai_engineering",
                component="pip.storm",
                error_code="hook_execution_failed",
                summary=f"distinct-{i}",
                session_id="sess-1",
            )
        errors = [e for e in self._events(tmp_path) if e.get("kind") == "framework_error"]
        assert len(errors) == 3
