"""Tests for InstallState model (spec-068 state unification).

Covers:
- Serialize/deserialize roundtrip (model -> JSON -> model)
- Default values (empty InstallState has sensible defaults)
- Platform credential refs (sonar with credential_ref, empty platforms)
- from_legacy() conversion (InstallManifest -> InstallState)
- Tooling dict flexibility (custom tool names serialize correctly)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from ai_engineering.state.models import (
    BranchPolicyState,
    CredentialRef,
    InstallState,
    OperationalState,
    PlatformEntry,
    ReleaseState,
    ToolEntry,
)

pytestmark = pytest.mark.unit


# -- Serialize / Deserialize Roundtrip ------------------------------------


class TestInstallStateRoundtrip:
    """InstallState survives JSON serialization and deserialization."""

    def test_full_roundtrip(self) -> None:
        """Model -> JSON string -> model produces identical values."""
        # Arrange
        ts = datetime(2026, 3, 25, 10, 0, 0, tzinfo=UTC)
        state = InstallState(
            installed_at=ts,
            tooling={
                "gh": ToolEntry(installed=True, authenticated=True, mode="cli", scopes=["repo"]),
                "ruff": ToolEntry(installed=True),
            },
            platforms={
                "sonar": PlatformEntry(
                    configured=True,
                    url="https://sonarcloud.io",
                    project_key="my-project",
                    organization="my-org",
                    credential_ref=CredentialRef(service="ai-engineering/sonar", username="token"),
                ),
            },
            branch_policy=BranchPolicyState(applied=True, mode="cli"),
            operational_readiness=OperationalState(status="READY"),
            release=ReleaseState(last_version="0.4.0", last_released_at=ts),
        )

        # Act
        json_str = state.model_dump_json()
        restored = InstallState.model_validate_json(json_str)

        # Assert
        assert restored.schema_version == "2.0"
        assert restored.installed_at == ts
        assert restored.tooling["gh"].authenticated is True
        assert restored.tooling["gh"].scopes == ["repo"]
        assert restored.tooling["ruff"].installed is True
        assert restored.platforms["sonar"].url == "https://sonarcloud.io"
        assert restored.branch_policy.applied is True
        assert restored.operational_readiness.status == "READY"
        assert restored.release.last_version == "0.4.0"

    def test_roundtrip_via_dict(self) -> None:
        """Model -> dict -> model preserves all fields."""
        # Arrange
        ts = datetime(2026, 1, 1, tzinfo=UTC)
        state = InstallState(
            installed_at=ts,
            tooling={"gitleaks": ToolEntry(installed=True)},
            platforms={},
        )

        # Act
        data = state.model_dump(mode="json")
        restored = InstallState.model_validate(data)

        # Assert
        assert restored.tooling["gitleaks"].installed is True
        assert restored.platforms == {}

    def test_roundtrip_from_spec_json(self) -> None:
        """The exact JSON schema from the spec parses correctly."""
        # Arrange
        raw = {
            "schema_version": "2.0",
            "installed_at": "2026-03-25T10:00:00Z",
            "tooling": {
                "gh": {
                    "installed": True,
                    "authenticated": True,
                    "mode": "cli",
                    "scopes": ["repo"],
                },
                "az": {"installed": False, "authenticated": False, "mode": "api"},
                "gitleaks": {"installed": True},
                "ruff": {"installed": True},
                "semgrep": {"installed": False},
            },
            "platforms": {
                "sonar": {
                    "configured": True,
                    "url": "https://sonarcloud.io",
                    "project_key": "my-project",
                    "organization": "my-org",
                    "credential_ref": {
                        "service": "ai-engineering/sonar",
                        "username": "token",
                    },
                },
            },
            "branch_policy": {"applied": True, "mode": "cli"},
            "operational_readiness": {"status": "READY", "pending_steps": []},
            "release": {
                "last_version": "0.4.0",
                "last_released_at": "2026-03-20T00:00:00Z",
            },
        }

        # Act
        state = InstallState.model_validate(raw)

        # Assert
        assert state.schema_version == "2.0"
        assert len(state.tooling) == 5
        assert state.tooling["gh"].scopes == ["repo"]
        assert state.tooling["semgrep"].installed is False
        assert state.platforms["sonar"].credential_ref is not None
        assert state.platforms["sonar"].credential_ref.service == "ai-engineering/sonar"
        assert state.release.last_version == "0.4.0"


# -- Default Values -------------------------------------------------------


class TestInstallStateDefaults:
    """Empty or minimal InstallState has sensible defaults."""

    def test_minimal_construction(self) -> None:
        """Only installed_at is required; everything else has defaults."""
        # Arrange / Act
        state = InstallState(installed_at=datetime(2026, 1, 1, tzinfo=UTC))

        # Assert
        assert state.schema_version == "2.0"
        assert state.tooling == {}
        assert state.platforms == {}
        assert state.branch_policy.applied is False
        assert state.branch_policy.mode == "api"
        assert state.operational_readiness.status == "pending"
        assert state.operational_readiness.pending_steps == []
        assert state.release.last_version == ""
        assert state.release.last_released_at is None

    def test_tool_entry_defaults(self) -> None:
        """ToolEntry defaults to not-installed, not-authenticated, cli mode."""
        # Arrange / Act
        entry = ToolEntry()

        # Assert
        assert entry.installed is False
        assert entry.authenticated is False
        assert entry.mode == "cli"
        assert entry.scopes == []

    def test_platform_entry_defaults(self) -> None:
        """PlatformEntry defaults to not-configured with empty strings."""
        # Arrange / Act
        entry = PlatformEntry()

        # Assert
        assert entry.configured is False
        assert entry.url == ""
        assert entry.project_key == ""
        assert entry.organization == ""
        assert entry.credential_ref is None

    def test_branch_policy_defaults(self) -> None:
        """BranchPolicyState defaults."""
        # Arrange / Act
        bp = BranchPolicyState()

        # Assert
        assert bp.applied is False
        assert bp.mode == "api"
        assert bp.message is None
        assert bp.manual_guide is None

    def test_operational_state_defaults(self) -> None:
        """OperationalState defaults to pending with no steps."""
        # Arrange / Act
        ops = OperationalState()

        # Assert
        assert ops.status == "pending"
        assert ops.pending_steps == []

    def test_release_state_defaults(self) -> None:
        """ReleaseState defaults to empty version, no release date."""
        # Arrange / Act
        rel = ReleaseState()

        # Assert
        assert rel.last_version == ""
        assert rel.last_released_at is None


# -- Platform Credential Refs ---------------------------------------------


class TestPlatformCredentialRefs:
    """Platform entries with credential references."""

    def test_sonar_with_credential_ref(self) -> None:
        """Sonar platform entry includes a credential reference."""
        # Arrange
        entry = PlatformEntry(
            configured=True,
            url="https://sonarcloud.io",
            project_key="my-project",
            organization="my-org",
            credential_ref=CredentialRef(
                service="ai-engineering/sonar",
                username="token",
            ),
        )

        # Assert
        assert entry.credential_ref is not None
        assert entry.credential_ref.service == "ai-engineering/sonar"
        assert entry.credential_ref.username == "token"

    def test_platform_without_credential_ref(self) -> None:
        """Platform entry with no credential ref defaults to None."""
        # Arrange / Act
        entry = PlatformEntry(configured=True, url="https://example.com")

        # Assert
        assert entry.credential_ref is None

    def test_credential_ref_serializes(self) -> None:
        """CredentialRef roundtrips through JSON."""
        # Arrange
        ref = CredentialRef(service="ai-engineering/github", username="pat")

        # Act
        data = json.loads(ref.model_dump_json())

        # Assert
        assert data["service"] == "ai-engineering/github"
        assert data["username"] == "pat"

    def test_multiple_platforms(self) -> None:
        """InstallState supports multiple platform entries."""
        # Arrange
        ts = datetime(2026, 1, 1, tzinfo=UTC)
        state = InstallState(
            installed_at=ts,
            platforms={
                "sonar": PlatformEntry(
                    configured=True,
                    credential_ref=CredentialRef(service="ai-engineering/sonar", username="token"),
                ),
                "azure_devops": PlatformEntry(
                    configured=True,
                    url="https://dev.azure.com/org",
                    credential_ref=CredentialRef(service="ai-engineering/azdo", username="pat"),
                ),
            },
        )

        # Assert
        assert len(state.platforms) == 2
        assert state.platforms["sonar"].configured is True
        assert state.platforms["azure_devops"].url == "https://dev.azure.com/org"


# -- from_legacy() Conversion ---------------------------------------------


class TestFromLegacy:
    """Converting old InstallManifest + ToolsState into new InstallState."""

    def test_basic_manifest_conversion(self) -> None:
        """Extracts state fields from legacy manifest dict, drops config."""
        # Arrange
        legacy = {
            "schemaVersion": "1.2",
            "frameworkVersion": "0.1.0",
            "installedAt": "2026-03-25T10:00:00Z",
            "installedStacks": ["python"],
            "installedIdes": ["terminal"],
            "toolingReadiness": {
                "gh": {
                    "installed": True,
                    "configured": True,
                    "authenticated": True,
                    "mode": "cli",
                },
                "az": {
                    "installed": False,
                    "configured": False,
                    "authenticated": False,
                    "mode": "api",
                },
                "gitHooks": {
                    "installed": True,
                    "integrityVerified": True,
                    "hookHashes": {},
                },
                "python": {
                    "uv": {"ready": True},
                    "ruff": {"ready": True},
                    "ty": {"ready": False},
                    "pipAudit": {"ready": True},
                },
            },
            "branchPolicy": {"applied": True, "mode": "cli"},
            "operationalReadiness": {
                "status": "READY",
                "manualStepsRequired": False,
                "manualSteps": [],
            },
            "release": {"lastVersion": "0.3.0", "lastReleasedAt": "2026-03-20T00:00:00Z"},
        }

        # Act
        from ai_engineering.state.models import InstallManifest

        manifest = InstallManifest.model_validate(legacy)
        state = InstallState.from_legacy(manifest)

        # Assert -- state fields preserved
        assert state.schema_version == "2.0"
        assert state.installed_at == datetime(2026, 3, 25, 10, 0, 0, tzinfo=UTC)
        assert state.tooling["gh"].installed is True
        assert state.tooling["gh"].authenticated is True
        assert state.tooling["gh"].mode == "cli"
        assert state.tooling["az"].installed is False
        assert state.tooling["az"].mode == "api"
        assert state.branch_policy.applied is True
        assert state.branch_policy.mode == "cli"
        assert state.operational_readiness.status == "READY"
        assert state.release.last_version == "0.3.0"

        # Assert -- config fields NOT present (no installedStacks, etc.)
        data = state.model_dump(mode="json")
        assert "installedStacks" not in data
        assert "installed_stacks" not in data
        assert "frameworkVersion" not in data
        assert "framework_version" not in data

    def test_legacy_python_tools_flattened(self) -> None:
        """Legacy nested python.ruff, python.uv -> flat ruff, uv entries."""
        # Arrange
        legacy = {
            "installedAt": "2026-01-01T00:00:00Z",
            "toolingReadiness": {
                "python": {
                    "uv": {"ready": True},
                    "ruff": {"ready": True},
                    "ty": {"ready": False},
                    "pipAudit": {"ready": True},
                },
            },
        }

        from ai_engineering.state.models import InstallManifest

        manifest = InstallManifest.model_validate(legacy)
        state = InstallState.from_legacy(manifest)

        # Assert -- Python tools flattened into top-level tooling
        assert state.tooling["ruff"].installed is True
        assert state.tooling["uv"].installed is True
        assert state.tooling["pip_audit"].installed is True
        assert state.tooling["ty"].installed is False

    def test_legacy_with_tools_state_merges_platforms(self) -> None:
        """ToolsState dict merges platform data into InstallState.platforms."""
        # Arrange
        legacy = {
            "installedAt": "2026-01-01T00:00:00Z",
        }
        tools_state_dict = {
            "github": {
                "configured": True,
                "cli_authenticated": True,
                "scopes": ["repo", "read:org"],
            },
            "sonar": {
                "configured": True,
                "url": "https://sonarcloud.io",
                "project_key": "my-proj",
                "organization": "my-org",
                "credential_ref": {
                    "service_name": "ai-engineering/sonar",
                    "username": "token",
                    "configured": True,
                },
            },
            "azure_devops": {
                "configured": False,
            },
        }

        from ai_engineering.state.models import InstallManifest

        manifest = InstallManifest.model_validate(legacy)
        state = InstallState.from_legacy(manifest, tools_state_dict=tools_state_dict)

        # Assert -- platforms populated from tools_state
        assert "sonar" in state.platforms
        assert state.platforms["sonar"].configured is True
        assert state.platforms["sonar"].url == "https://sonarcloud.io"
        assert state.platforms["sonar"].project_key == "my-proj"
        assert state.platforms["sonar"].credential_ref is not None
        assert state.platforms["sonar"].credential_ref.service == "ai-engineering/sonar"

    def test_legacy_without_tools_state_empty_platforms(self) -> None:
        """Without tools_state, platforms dict is empty."""
        # Arrange
        legacy = {"installedAt": "2026-01-01T00:00:00Z"}

        from ai_engineering.state.models import InstallManifest

        manifest = InstallManifest.model_validate(legacy)
        state = InstallState.from_legacy(manifest)

        # Assert
        assert state.platforms == {}

    def test_legacy_branch_policy_preserves_manual_guide(self) -> None:
        """manual_guide field carries over from legacy BranchPolicyStatus."""
        # Arrange
        legacy = {
            "installedAt": "2026-01-01T00:00:00Z",
            "branchPolicy": {
                "applied": False,
                "mode": "manual",
                "manualGuide": "See https://docs.example.com/branch-policy",
                "message": "Manual setup required",
            },
        }

        from ai_engineering.state.models import InstallManifest

        manifest = InstallManifest.model_validate(legacy)
        state = InstallState.from_legacy(manifest)

        # Assert
        assert state.branch_policy.applied is False
        assert state.branch_policy.mode == "manual"
        assert state.branch_policy.manual_guide == "See https://docs.example.com/branch-policy"
        assert state.branch_policy.message == "Manual setup required"


# -- Tooling Dict Flexibility ---------------------------------------------


class TestToolingFlexibility:
    """The dict[str, ToolEntry] design allows arbitrary tool names."""

    def test_custom_tool_name(self) -> None:
        """Any string key works in the tooling dict."""
        # Arrange
        ts = datetime(2026, 1, 1, tzinfo=UTC)
        state = InstallState(
            installed_at=ts,
            tooling={
                "custom_linter": ToolEntry(installed=True, mode="cli"),
                "my-company-scanner": ToolEntry(installed=False),
            },
        )

        # Act
        data = json.loads(state.model_dump_json())

        # Assert
        assert data["tooling"]["custom_linter"]["installed"] is True
        assert data["tooling"]["my-company-scanner"]["installed"] is False

    def test_add_tool_after_construction(self) -> None:
        """Tools can be added to the dict dynamically."""
        # Arrange
        ts = datetime(2026, 1, 1, tzinfo=UTC)
        state = InstallState(
            installed_at=ts,
            tooling={"ruff": ToolEntry(installed=True)},
        )

        # Act
        state.tooling["new_tool"] = ToolEntry(installed=True, mode="api")

        # Assert
        assert len(state.tooling) == 2
        assert state.tooling["new_tool"].mode == "api"

    def test_empty_tooling_serializes(self) -> None:
        """Empty tooling dict serializes as {}."""
        # Arrange
        ts = datetime(2026, 1, 1, tzinfo=UTC)
        state = InstallState(installed_at=ts)

        # Act
        data = json.loads(state.model_dump_json())

        # Assert
        assert data["tooling"] == {}
