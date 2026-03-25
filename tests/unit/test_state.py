"""Tests for ai_engineering.state -- models, io, defaults, decision_logic."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ai_engineering.state.decision_logic import (
    compute_context_hash,
    create_decision,
    find_reusable_decision,
    next_decision_id,
)
from ai_engineering.state.defaults import (
    default_decision_store,
    default_install_state,
    default_ownership_map,
)
from ai_engineering.state.io import (
    append_ndjson,
    read_json_model,
    read_ndjson_entries,
    write_json_model,
)
from ai_engineering.state.models import (
    AuditEntry,
    DecisionStore,
    InstallState,
    OwnershipLevel,
    OwnershipMap,
    ToolEntry,
    UpdateMetadata,
)

pytestmark = pytest.mark.unit

# -- InstallState model tests ------------------------------------------------


class TestInstallState:
    """Tests for InstallState model."""

    def test_create_with_defaults(self) -> None:
        state = InstallState()
        assert state.schema_version == "2.0"
        assert state.tooling == {}
        assert state.platforms == {}
        assert state.branch_policy.applied is False
        assert state.operational_readiness.status == "pending"
        assert state.release.last_version == ""

    def test_roundtrip_from_json(self) -> None:
        state = InstallState(
            tooling={"ruff": ToolEntry(installed=True)},
        )
        data = json.loads(state.model_dump_json())
        restored = InstallState.model_validate(data)
        assert restored.tooling["ruff"].installed is True

    def test_default_install_state_factory(self) -> None:
        state = default_install_state()
        assert isinstance(state, InstallState)
        assert state.schema_version == "2.0"
        assert state.tooling == {}


# -- OwnershipMap tests -------------------------------------------------------


class TestOwnershipMap:
    """Tests for OwnershipMap model."""

    def test_writable_by_framework_allow(self) -> None:
        om = default_ownership_map()
        assert om.is_writable_by_framework(".ai-engineering/contexts/languages/python.md") is True

    def test_writable_by_framework_deny(self) -> None:
        om = default_ownership_map()
        assert om.is_writable_by_framework(".ai-engineering/contexts/team/custom.md") is False

    def test_writable_by_framework_no_match_defaults_deny(self) -> None:
        om = default_ownership_map()
        assert om.is_writable_by_framework("some/unknown/path.txt") is False

    def test_append_only_is_writable(self) -> None:
        om = default_ownership_map()
        assert om.is_writable_by_framework(".ai-engineering/state/audit-log.ndjson") is True

    def test_update_allowed_for_framework_managed(self) -> None:
        om = default_ownership_map()
        assert om.is_update_allowed(".ai-engineering/contexts/languages/python.md") is True

    def test_update_denied_for_team_managed(self) -> None:
        om = default_ownership_map()
        assert om.is_update_allowed(".ai-engineering/contexts/team/custom.md") is False

    def test_update_denied_for_append_only(self) -> None:
        om = default_ownership_map()
        assert om.is_update_allowed(".ai-engineering/state/audit-log.ndjson") is False

    def test_update_denied_for_no_match(self) -> None:
        om = default_ownership_map()
        assert om.is_update_allowed("some/unknown/path.txt") is False

    def test_has_deny_rule_true(self) -> None:
        om = default_ownership_map()
        assert om.has_deny_rule(".ai-engineering/contexts/team/core.md") is True

    def test_has_deny_rule_false_for_allow(self) -> None:
        om = default_ownership_map()
        assert om.has_deny_rule(".ai-engineering/standards/framework/core.md") is False

    def test_has_deny_rule_false_for_no_match(self) -> None:
        om = default_ownership_map()
        assert om.has_deny_rule("unknown/path.txt") is False

    def test_claude_tree_ownership(self) -> None:
        """The .claude/** pattern covers settings.json and commands/."""
        om = default_ownership_map()
        assert om.is_update_allowed(".claude/settings.json") is True
        assert om.is_update_allowed(".claude/commands/commit.md") is True


# -- DecisionStore tests ------------------------------------------------------


class TestDecisionStore:
    """Tests for DecisionStore model."""

    def test_empty_store(self) -> None:
        store = DecisionStore()
        assert store.decisions == []

    def test_find_by_id(self) -> None:
        store = default_decision_store()
        create_decision(
            store,
            decision_id="S1-001",
            context="test context",
            decision_text="decided yes",
            spec="001",
        )
        found = store.find_by_id("S1-001")
        assert found is not None
        assert found.decision == "decided yes"

    def test_find_by_id_missing(self) -> None:
        store = default_decision_store()
        assert store.find_by_id("nonexistent") is None


# -- AuditEntry tests ---------------------------------------------------------


class TestAuditEntry:
    """Tests for AuditEntry model."""

    def test_create_minimal(self) -> None:
        entry = AuditEntry(event="install", actor="agent-1")
        assert entry.event == "install"
        assert entry.actor == "agent-1"
        assert entry.spec_id is None
        assert entry.source is None
        assert entry.stack is None
        assert entry.duration_ms is None

    def test_create_full(self) -> None:
        entry = AuditEntry(
            event="task-complete",
            actor="agent-1",
            spec_id="001",
            detail={"message": "created models.py"},
            source="cli",
            stack="python",
            duration_ms=1234,
        )
        assert entry.spec_id == "001"
        assert entry.source == "cli"
        assert entry.stack == "python"
        assert entry.duration_ms == 1234


# -- UpdateMetadata tests -----------------------------------------------------


class TestUpdateMetadata:
    """Tests for UpdateMetadata model."""

    def test_alias_population(self) -> None:
        meta = UpdateMetadata(
            rationale="test",
            expectedGain="gain",
            potentialImpact="impact",
        )
        assert meta.expected_gain == "gain"
        assert meta.potential_impact == "impact"


# -- I/O tests ----------------------------------------------------------------


class TestJsonIO:
    """Tests for JSON read/write operations."""

    def test_write_and_read_install_state(self, tmp_path: Path) -> None:
        path = tmp_path / "state" / "install-state.json"
        state = default_install_state()
        write_json_model(path, state)
        loaded = read_json_model(path, InstallState)
        assert path.exists()
        assert loaded.schema_version == "2.0"

    def test_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "nested" / "file.json"
        store = default_decision_store()
        write_json_model(path, store)
        assert path.exists()

    def test_stable_formatting(self, tmp_path: Path) -> None:
        path = tmp_path / "test.json"
        store = default_decision_store()
        write_json_model(path, store)
        content = path.read_text(encoding="utf-8")
        assert content.endswith("\n")
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    def test_read_missing_file_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError):
            read_json_model(path, InstallState)

    def test_roundtrip_ownership_map(self, tmp_path: Path) -> None:
        path = tmp_path / "ownership-map.json"
        om = default_ownership_map()
        write_json_model(path, om)
        loaded = read_json_model(path, OwnershipMap)
        assert len(loaded.paths) == len(om.paths)
        assert loaded.paths[0].owner == OwnershipLevel.FRAMEWORK_MANAGED


# -- NDJSON I/O tests ---------------------------------------------------------


class TestNdjsonIO:
    """Tests for NDJSON append/read operations."""

    def test_append_and_read(self, tmp_path: Path) -> None:
        path = tmp_path / "audit-log.ndjson"
        entry1 = AuditEntry(event="install", actor="agent-1", spec_id="001")
        entry2 = AuditEntry(event="task-complete", actor="agent-1")
        append_ndjson(path, entry1)
        append_ndjson(path, entry2)
        entries = read_ndjson_entries(path, AuditEntry)
        assert len(entries) == 2
        assert entries[0].event == "install"
        assert entries[1].event == "task-complete"

    def test_read_empty_file(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.ndjson"
        path.write_text("", encoding="utf-8")
        entries = read_ndjson_entries(path, AuditEntry)
        assert entries == []

    def test_read_nonexistent_file(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.ndjson"
        entries = read_ndjson_entries(path, AuditEntry)
        assert entries == []

    def test_append_creates_parent_dirs(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "audit.ndjson"
        entry = AuditEntry(event="test", actor="test-agent")
        append_ndjson(path, entry)
        assert path.exists()

    def test_each_entry_is_one_line(self, tmp_path: Path) -> None:
        path = tmp_path / "log.ndjson"
        for i in range(3):
            append_ndjson(path, AuditEntry(event=f"event-{i}", actor="agent"))
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 3
        for line in lines:
            parsed = json.loads(line)
            assert "event" in parsed


# -- Defaults tests ------------------------------------------------------------


class TestDefaults:
    """Tests for default state factory functions."""

    def test_default_install_state(self) -> None:
        state = default_install_state()
        assert state.schema_version == "2.0"
        assert state.tooling == {}
        assert state.platforms == {}

    def test_default_ownership_map_has_entries(self) -> None:
        om = default_ownership_map()
        assert len(om.paths) > 0

    def test_default_ownership_map_covers_all_levels(self) -> None:
        om = default_ownership_map()
        levels = {entry.owner for entry in om.paths}
        assert OwnershipLevel.FRAMEWORK_MANAGED in levels
        assert OwnershipLevel.TEAM_MANAGED in levels
        assert OwnershipLevel.SYSTEM_MANAGED in levels

    def test_default_decision_store_empty(self) -> None:
        store = default_decision_store()
        assert store.decisions == []


# -- Decision Logic tests -----------------------------------------------------


class TestContextHash:
    """Tests for context hashing."""

    def test_deterministic(self) -> None:
        h1 = compute_context_hash("some context")
        h2 = compute_context_hash("some context")
        assert h1 == h2

    def test_different_contexts_different_hashes(self) -> None:
        h1 = compute_context_hash("context A")
        h2 = compute_context_hash("context B")
        assert h1 != h2

    def test_hash_is_hex_sha256(self) -> None:
        h = compute_context_hash("test")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestFindReusableDecision:
    """Tests for decision reuse lookup."""

    def test_finds_matching_decision(self) -> None:
        store = default_decision_store()
        create_decision(
            store,
            decision_id="S1-001",
            context="should we use pydantic?",
            decision_text="yes, use pydantic v2",
            spec="001",
        )
        found = find_reusable_decision(store, "should we use pydantic?")
        assert found is not None
        assert found.decision == "yes, use pydantic v2"

    def test_returns_none_for_no_match(self) -> None:
        store = default_decision_store()
        found = find_reusable_decision(store, "unknown context")
        assert found is None

    def test_expired_decision_not_reused(self) -> None:
        store = default_decision_store()
        past = datetime.now(tz=UTC) - timedelta(days=1)
        create_decision(
            store,
            decision_id="S1-001",
            context="temporary decision",
            decision_text="do X",
            spec="001",
            expires_at=past,
        )
        store.decisions[0].expires_at = past
        found = find_reusable_decision(store, "temporary decision")
        assert found is None

    def test_non_expired_decision_reused(self) -> None:
        store = default_decision_store()
        future = datetime.now(tz=UTC) + timedelta(days=30)
        create_decision(
            store,
            decision_id="S1-001",
            context="long-lived decision",
            decision_text="do Y",
            spec="001",
            expires_at=future,
        )
        found = find_reusable_decision(store, "long-lived decision")
        assert found is not None


class TestCreateDecision:
    """Tests for decision creation."""

    def test_adds_to_store(self) -> None:
        store = default_decision_store()
        create_decision(
            store,
            decision_id="S1-001",
            context="test",
            decision_text="decided",
            spec="001",
        )
        assert len(store.decisions) == 1
        assert store.decisions[0].id == "S1-001"

    def test_sets_context_hash(self) -> None:
        store = default_decision_store()
        expected_hash = compute_context_hash("test context")
        d = create_decision(
            store,
            decision_id="S1-001",
            context="test context",
            decision_text="ok",
            spec="001",
        )
        assert d.context_hash == expected_hash


class TestNextDecisionId:
    """Tests for sequential decision ID generation."""

    def test_first_id_in_session(self) -> None:
        store = default_decision_store()
        assert next_decision_id(store, "S1") == "S1-001"

    def test_increments_correctly(self) -> None:
        store = default_decision_store()
        create_decision(store, decision_id="S1-001", context="a", decision_text="x", spec="001")
        create_decision(store, decision_id="S1-002", context="b", decision_text="y", spec="001")
        result = next_decision_id(store, "S1")
        assert result == "S1-003"

    def test_different_sessions_independent(self) -> None:
        store = default_decision_store()
        create_decision(store, decision_id="S1-001", context="a", decision_text="x", spec="001")
        result = next_decision_id(store, "S2")
        assert result == "S2-001"


# -- Schema 1.1 backward compatibility ----------------------------------------


class TestSchema11BackwardCompat:
    """Tests for Decision schema 1.1 backward compatibility."""

    def test_default_store_schema_11(self) -> None:
        store = default_decision_store()
        assert store.schema_version == "1.1"

    def test_old_decision_validates(self) -> None:
        from ai_engineering.state.models import Decision, DecisionStatus

        raw = {
            "id": "S1-001",
            "context": "old decision",
            "decision": "decided",
            "decidedAt": "2025-01-01T00:00:00Z",
            "spec": "001",
        }
        d = Decision.model_validate(raw)
        assert d.risk_category is None
        assert d.severity is None
        assert d.status == DecisionStatus.ACTIVE
        assert d.renewal_count == 0

    def test_risk_decisions_empty_for_old_data(self) -> None:
        from ai_engineering.state.models import DecisionStore

        store = DecisionStore.model_validate(
            {
                "schemaVersion": "1.0",
                "decisions": [
                    {
                        "id": "S1-001",
                        "context": "test",
                        "decision": "decided",
                        "decidedAt": "2025-01-01T00:00:00Z",
                        "spec": "001",
                    }
                ],
            }
        )
        assert store.risk_decisions() == []

    def test_risk_decisions_returns_risk_acceptance(self) -> None:
        from ai_engineering.state.models import DecisionStore, RiskCategory

        store = DecisionStore.model_validate(
            {
                "schemaVersion": "1.1",
                "decisions": [
                    {
                        "id": "RA-001",
                        "context": "cve risk",
                        "decision": "accept",
                        "decidedAt": "2025-01-01T00:00:00Z",
                        "spec": "004",
                        "riskCategory": "risk-acceptance",
                    }
                ],
            }
        )
        risk = store.risk_decisions()
        assert len(risk) == 1
        assert risk[0].risk_category == RiskCategory.RISK_ACCEPTANCE


# -- AiProvider enum tests (kept: enum still exists) ---------------------------


class TestAiProvider:
    """Tests for AiProvider enum."""

    def test_enum_values(self) -> None:
        from ai_engineering.state.models import AiProvider

        assert AiProvider.CLAUDE_CODE == "claude_code"
        assert AiProvider.GITHUB_COPILOT == "github_copilot"
        assert AiProvider.GEMINI == "gemini"
        assert AiProvider.CODEX == "codex"

    def test_is_str_enum(self) -> None:
        from ai_engineering.state.models import AiProvider

        assert isinstance(AiProvider.CLAUDE_CODE, str)


# -- Audit enrichment helpers --------------------------------------------------


class TestAuditEnrichment:
    """Tests for audit.py enrichment cache functions."""

    def setup_method(self) -> None:
        from ai_engineering.state.audit import _reset_enrichment_cache

        _reset_enrichment_cache()

    def teardown_method(self) -> None:
        from ai_engineering.state.audit import _reset_enrichment_cache

        _reset_enrichment_cache()

    def test_read_active_spec_from_frontmatter(self, tmp_path: Path) -> None:
        from ai_engineering.state.audit import _read_active_spec

        specs_dir = tmp_path / ".ai-engineering" / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec.md").write_text('---\nid: "055"\n---\n\n# Test Spec\n')
        assert _read_active_spec(tmp_path) == "055"

    def test_read_active_spec_placeholder_returns_none(self, tmp_path: Path) -> None:
        from ai_engineering.state.audit import _read_active_spec

        specs_dir = tmp_path / ".ai-engineering" / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec.md").write_text("# No active spec\n\nRun /ai-brainstorm.\n")
        assert _read_active_spec(tmp_path) is None

    def test_read_active_spec_missing_file(self, tmp_path: Path) -> None:
        from ai_engineering.state.audit import _read_active_spec

        assert _read_active_spec(tmp_path) is None

    def test_read_active_spec_fallback_nnn_pattern(self, tmp_path: Path) -> None:
        from ai_engineering.state.audit import _read_active_spec

        specs_dir = tmp_path / ".ai-engineering" / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec.md").write_text("---\ntitle: test\n---\n\n055-radical-simplification\n")
        assert _read_active_spec(tmp_path) == "055"

    def test_read_active_spec_caches_result(self, tmp_path: Path) -> None:
        from ai_engineering.state.audit import _read_active_spec

        specs_dir = tmp_path / ".ai-engineering" / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec.md").write_text('---\nid: "055"\n---\n')
        assert _read_active_spec(tmp_path) == "055"
        (specs_dir / "spec.md").write_text('---\nid: "999"\n---\n')
        assert _read_active_spec(tmp_path) == "055"

    def test_read_active_stack_from_manifest_yml(self, tmp_path: Path) -> None:
        """_read_active_stack reads from manifest.yml (not install-manifest.json)."""
        from ai_engineering.state.audit import _read_active_stack

        ai_dir = tmp_path / ".ai-engineering"
        ai_dir.mkdir(parents=True)
        (ai_dir / "manifest.yml").write_text(
            "schema_version: '2.0'\nproviders:\n  stacks:\n    - python\n    - rust\n"
        )
        assert _read_active_stack(tmp_path) == "python"

    def test_read_active_stack_missing_file(self, tmp_path: Path) -> None:
        from ai_engineering.state.audit import _read_active_stack

        # ManifestConfig returns defaults when no manifest.yml exists
        assert _read_active_stack(tmp_path) == "python"

    def test_read_active_stack_empty_stacks(self, tmp_path: Path) -> None:
        from ai_engineering.state.audit import _read_active_stack

        ai_dir = tmp_path / ".ai-engineering"
        ai_dir.mkdir(parents=True)
        (ai_dir / "manifest.yml").write_text("schema_version: '2.0'\nproviders:\n  stacks: []\n")
        assert _read_active_stack(tmp_path) is None

    def test_reset_clears_cache(self, tmp_path: Path) -> None:
        from ai_engineering.state.audit import (
            _read_active_spec,
            _reset_enrichment_cache,
        )

        specs_dir = tmp_path / ".ai-engineering" / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec.md").write_text('---\nid: "055"\n---\n')
        assert _read_active_spec(tmp_path) == "055"
        _reset_enrichment_cache()
        (specs_dir / "spec.md").write_text('---\nid: "099"\n---\n')
        assert _read_active_spec(tmp_path) == "099"
