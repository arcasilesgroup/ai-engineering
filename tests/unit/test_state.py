"""Tests for ai_engineering.state — models, io, defaults, decision_logic."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
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
    default_install_manifest,
    default_ownership_map,
    default_sources_lock,
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
    FrameworkUpdatePolicy,
    InstallManifest,
    OwnershipLevel,
    OwnershipMap,
    SourcesLock,
    UpdateMetadata,
)


# ── Models ──────────────────────────────────────────────────────────────


class TestInstallManifest:
    """Tests for InstallManifest model."""

    def test_create_with_defaults(self) -> None:
        manifest = InstallManifest()
        assert manifest.schema_version == "1.1"
        assert manifest.installed_stacks == []
        assert manifest.installed_ides == []

    def test_roundtrip_from_json(self) -> None:
        raw = {
            "schemaVersion": "1.1",
            "frameworkVersion": "0.1.0",
            "installedAt": "2026-01-01T00:00:00Z",
            "installedStacks": ["python"],
            "installedIdes": ["vscode"],
        }
        m = InstallManifest.model_validate(raw)
        assert m.installed_stacks == ["python"]
        assert m.installed_ides == ["vscode"]

    def test_serialize_by_alias(self) -> None:
        manifest = InstallManifest(
            installedStacks=["python"],
            installedIdes=["terminal"],
        )
        data = manifest.model_dump(by_alias=True)
        assert "installedStacks" in data
        assert "installedIdes" in data
        assert "installed_stacks" not in data


class TestOwnershipMap:
    """Tests for OwnershipMap model."""

    def test_writable_by_framework_allow(self) -> None:
        om = default_ownership_map()
        assert om.is_writable_by_framework(".ai-engineering/standards/framework/core.md") is True

    def test_writable_by_framework_deny(self) -> None:
        om = default_ownership_map()
        assert om.is_writable_by_framework(".ai-engineering/standards/team/custom.md") is False

    def test_writable_by_framework_no_match_defaults_deny(self) -> None:
        om = default_ownership_map()
        assert om.is_writable_by_framework("some/unknown/path.txt") is False

    def test_append_only_is_writable(self) -> None:
        om = default_ownership_map()
        assert om.is_writable_by_framework(".ai-engineering/state/audit-log.ndjson") is True


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


class TestAuditEntry:
    """Tests for AuditEntry model."""

    def test_create_minimal(self) -> None:
        entry = AuditEntry(event="install", actor="agent-1")
        assert entry.event == "install"
        assert entry.actor == "agent-1"
        assert entry.spec is None

    def test_create_full(self) -> None:
        entry = AuditEntry(
            event="task-complete",
            actor="agent-1",
            spec="001-rewrite-v2",
            task="9.1",
            detail="created models.py",
            session="S9",
        )
        assert entry.task == "9.1"
        assert entry.session == "S9"


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


class TestSourcesLock:
    """Tests for SourcesLock model."""

    def test_empty_sources(self) -> None:
        lock = SourcesLock()
        assert lock.sources == []
        assert lock.default_remote_enabled is True


# ── I/O ─────────────────────────────────────────────────────────────────


class TestJsonIO:
    """Tests for JSON read/write operations."""

    def test_write_and_read_manifest(self, tmp_path: Path) -> None:
        path = tmp_path / "state" / "install-manifest.json"
        manifest = default_install_manifest(stacks=["python"], ides=["vscode"])

        write_json_model(path, manifest)
        assert path.exists()

        loaded = read_json_model(path, InstallManifest)
        assert loaded.installed_stacks == ["python"]
        assert loaded.installed_ides == ["vscode"]

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
        # Stable: sorted keys, 2-space indent, trailing newline
        assert content.endswith("\n")
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    def test_read_missing_file_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError):
            read_json_model(path, InstallManifest)

    def test_roundtrip_ownership_map(self, tmp_path: Path) -> None:
        path = tmp_path / "ownership-map.json"
        om = default_ownership_map()
        write_json_model(path, om)
        loaded = read_json_model(path, OwnershipMap)
        assert len(loaded.paths) == len(om.paths)
        assert loaded.paths[0].owner == OwnershipLevel.FRAMEWORK_MANAGED

    def test_roundtrip_sources_lock(self, tmp_path: Path) -> None:
        path = tmp_path / "sources.lock.json"
        lock = default_sources_lock()
        write_json_model(path, lock)
        loaded = read_json_model(path, SourcesLock)
        assert loaded.default_remote_enabled is False


class TestNdjsonIO:
    """Tests for NDJSON append/read operations."""

    def test_append_and_read(self, tmp_path: Path) -> None:
        path = tmp_path / "audit-log.ndjson"

        entry1 = AuditEntry(event="install", actor="agent-1", spec="001")
        entry2 = AuditEntry(event="task-complete", actor="agent-1", task="9.1")

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


# ── Defaults ────────────────────────────────────────────────────────────


class TestDefaults:
    """Tests for default state factory functions."""

    def test_default_install_manifest(self) -> None:
        manifest = default_install_manifest()
        assert manifest.installed_stacks == ["python"]
        assert manifest.installed_ides == ["terminal"]
        assert manifest.schema_version == "1.1"

    def test_default_install_manifest_custom(self) -> None:
        manifest = default_install_manifest(stacks=["python", "node"], ides=["vscode"])
        assert manifest.installed_stacks == ["python", "node"]
        assert manifest.installed_ides == ["vscode"]

    def test_default_ownership_map_has_entries(self) -> None:
        om = default_ownership_map()
        assert len(om.paths) > 0

    def test_default_ownership_map_covers_all_levels(self) -> None:
        om = default_ownership_map()
        levels = {entry.owner for entry in om.paths}
        assert OwnershipLevel.FRAMEWORK_MANAGED in levels
        assert OwnershipLevel.TEAM_MANAGED in levels
        assert OwnershipLevel.PROJECT_MANAGED in levels
        assert OwnershipLevel.SYSTEM_MANAGED in levels

    def test_default_decision_store_empty(self) -> None:
        store = default_decision_store()
        assert store.decisions == []

    def test_default_sources_lock_remote_disabled(self) -> None:
        lock = default_sources_lock()
        assert lock.default_remote_enabled is False
        assert lock.sources == []


# ── Decision Logic ──────────────────────────────────────────────────────


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
        assert len(h) == 64  # SHA-256 produces 64 hex chars
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
        past = datetime.utcnow() - timedelta(days=1)
        create_decision(
            store,
            decision_id="S1-001",
            context="temporary decision",
            decision_text="do X",
            spec="001",
            expires_at=past,
        )
        # The decision was created with utcnow decided_at but past expiry
        # Override the expiry on the stored decision
        store.decisions[0].expires_at = past
        found = find_reusable_decision(store, "temporary decision")
        assert found is None

    def test_non_expired_decision_reused(self) -> None:
        store = default_decision_store()
        future = datetime.utcnow() + timedelta(days=30)
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
        d = create_decision(
            store,
            decision_id="S1-001",
            context="test context",
            decision_text="ok",
            spec="001",
        )
        expected_hash = compute_context_hash("test context")
        assert d.context_hash == expected_hash


class TestNextDecisionId:
    """Tests for sequential decision ID generation."""

    def test_first_id_in_session(self) -> None:
        store = default_decision_store()
        assert next_decision_id(store, "S1") == "S1-001"

    def test_increments_correctly(self) -> None:
        store = default_decision_store()
        create_decision(
            store, decision_id="S1-001", context="a", decision_text="x", spec="001"
        )
        create_decision(
            store, decision_id="S1-002", context="b", decision_text="y", spec="001"
        )
        assert next_decision_id(store, "S1") == "S1-003"

    def test_different_sessions_independent(self) -> None:
        store = default_decision_store()
        create_decision(
            store, decision_id="S1-001", context="a", decision_text="x", spec="001"
        )
        assert next_decision_id(store, "S2") == "S2-001"


# ── Schema 1.1 backward compatibility ──────────────────────────────────


class TestSchema11BackwardCompat:
    """Tests for Decision schema 1.1 backward compatibility."""

    def test_default_store_schema_11(self) -> None:
        store = default_decision_store()
        assert store.schema_version == "1.1"

    def test_old_decision_validates(self) -> None:
        """A decision without risk fields validates with defaults."""
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
        """Old decisions without riskCategory are not returned by risk_decisions."""
        from ai_engineering.state.models import DecisionStore
        store = DecisionStore.model_validate({
            "schemaVersion": "1.0",
            "decisions": [{
                "id": "S1-001",
                "context": "test",
                "decision": "decided",
                "decidedAt": "2025-01-01T00:00:00Z",
                "spec": "001",
            }],
        })
        assert store.risk_decisions() == []

    def test_risk_decisions_returns_risk_acceptance(self) -> None:
        """Decisions with riskCategory are returned by risk_decisions."""
        from ai_engineering.state.models import DecisionStore, RiskCategory
        store = DecisionStore.model_validate({
            "schemaVersion": "1.1",
            "decisions": [{
                "id": "RA-001",
                "context": "cve risk",
                "decision": "accept",
                "decidedAt": "2025-01-01T00:00:00Z",
                "spec": "004",
                "riskCategory": "risk_acceptance",
            }],
        })
        risk = store.risk_decisions()
        assert len(risk) == 1
        assert risk[0].risk_category == RiskCategory.RISK_ACCEPTANCE
