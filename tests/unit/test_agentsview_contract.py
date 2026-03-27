"""Tests for the spec-082 agentsview source contract artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_engineering.state.agentsview import (
    AGENTSVIEW_CONTRACT_VERSION,
    AGENTSVIEW_SOURCE_NAME,
    build_agentsview_contract,
    write_agentsview_contract,
    write_agentsview_fixture_bundle,
)
from ai_engineering.state.observability import (
    emit_framework_operation,
    emit_skill_invoked,
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
  total: 1
  prefix: "ai-"
  registry:
    ai-brainstorm:
      type: workflow
      tags: [planning]
agents:
  total: 1
  names: [plan]
providers:
  stacks: [python]
  ides: []
  vcs: github
""".strip()
        + "\n",
        encoding="utf-8",
    )


class TestAgentsviewContract:
    def test_build_contract_is_local_first_and_no_project_config(self) -> None:
        contract = build_agentsview_contract()
        assert contract["version"] == AGENTSVIEW_CONTRACT_VERSION
        assert contract["source"] == AGENTSVIEW_SOURCE_NAME
        assert contract["independent_install"] is True
        assert contract["requires_project_config"] is False
        assert contract["privacy"]["includes_transcripts"] is False

    def test_write_agentsview_contract_persists_json(self, tmp_path: Path) -> None:
        path = write_agentsview_contract(tmp_path / "agentsview-source-contract.json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["source"] == AGENTSVIEW_SOURCE_NAME
        assert payload["artifacts"]["events"].endswith("framework-events.ndjson")

    def test_write_agentsview_fixture_bundle_copies_canonical_artifacts(
        self, tmp_path: Path
    ) -> None:
        _write_manifest(tmp_path)
        write_framework_capabilities(tmp_path)
        emit_skill_invoked(
            tmp_path,
            engine="claude_code",
            skill_name="ai-brainstorm",
            component="hook.telemetry-skill",
            source="hook",
        )
        emit_framework_operation(
            tmp_path,
            operation="install",
            component="installer",
            source="cli",
        )

        bundle = write_agentsview_fixture_bundle(tmp_path, tmp_path / "fixtures" / "agentsview")

        assert set(bundle) == {"contract", "events", "capabilities"}
        assert bundle["contract"].exists()
        assert bundle["events"].exists()
        assert bundle["capabilities"].exists()
        events = bundle["events"].read_text(encoding="utf-8").strip().splitlines()
        payload = json.loads(events[0])
        assert payload["kind"] in {"skill_invoked", "framework_operation"}
