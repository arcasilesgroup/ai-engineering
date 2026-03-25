"""Tests for state file migration (spec-068).

Covers:
- migrate install-manifest.json -> install-state.json (config stripped, state preserved)
- migrate tools.json -> platforms merged into install-state.json
- both files absent -> no-op, returns False
- both old and new exist -> old overwrites new
- idempotent (run twice, same result, second returns False)
- tools.json merged into existing install-state.json (not overwritten)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_engineering.updater.service import _migrate_install_manifest, _migrate_tools_json

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_LEGACY_MANIFEST = {
    "schemaVersion": "1.2",
    "frameworkVersion": "0.1.0",
    "installedAt": "2026-03-25T10:00:00Z",
    "installedStacks": ["python"],
    "installedIdes": ["terminal"],
    "aiProviders": {"primary": "claude_code", "enabled": ["claude_code"]},
    "providers": {
        "primary": "github",
        "enabled": ["github"],
        "extensions": {"azure_devops": {"enabled": False}},
    },
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

_TOOLS_JSON = {
    "github": {
        "configured": True,
        "cli_authenticated": True,
        "scopes": ["repo", "read:org"],
    },
    "sonar": {
        "configured": True,
        "url": "https://sonarcloud.io",
        "project_key": "my-project",
        "organization": "my-org",
        "credential_ref": {
            "service_name": "ai-engineering/sonar",
            "username": "token",
            "configured": True,
        },
    },
    "azure_devops": {"configured": False},
}


def _write_json(path: Path, data: dict) -> None:
    """Write *data* as JSON to *path*, creating parents as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    """Read JSON from *path*."""
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# T-2.3.1  install-manifest.json -> install-state.json
# ---------------------------------------------------------------------------


class TestMigrateInstallManifest:
    """install-manifest.json is converted to install-state.json."""

    def test_config_stripped_state_preserved(self, tmp_path: Path) -> None:
        """Config fields (stacks, ides, providers, frameworkVersion) are
        dropped; runtime state fields are preserved."""
        # Arrange
        ai_eng = tmp_path / ".ai-engineering"
        _write_json(ai_eng / "state" / "install-manifest.json", _LEGACY_MANIFEST)

        # Act
        result = _migrate_install_manifest(ai_eng)

        # Assert -- migration happened
        assert result is True

        # Old file gone
        assert not (ai_eng / "state" / "install-manifest.json").exists()

        # New file written
        new_path = ai_eng / "state" / "install-state.json"
        assert new_path.exists()

        data = _read_json(new_path)

        # Config fields absent
        assert "installedStacks" not in data
        assert "installed_stacks" not in data
        assert "frameworkVersion" not in data
        assert "framework_version" not in data
        assert "installedIdes" not in data
        assert "installed_ides" not in data

        # State fields present
        assert data["schema_version"] == "2.0"
        assert data["tooling"]["gh"]["installed"] is True
        assert data["tooling"]["gh"]["mode"] == "cli"
        assert data["branch_policy"]["applied"] is True
        assert data["operational_readiness"]["status"] == "READY"
        assert data["release"]["last_version"] == "0.3.0"


# ---------------------------------------------------------------------------
# T-2.3.2  tools.json -> platforms merged
# ---------------------------------------------------------------------------


class TestMigrateToolsJson:
    """tools.json platform data is merged into install-state.json."""

    def test_tools_json_merged_into_install_state(self, tmp_path: Path) -> None:
        """Configured platforms from tools.json appear in install-state.json."""
        # Arrange
        ai_eng = tmp_path / ".ai-engineering"
        _write_json(ai_eng / "state" / "tools.json", _TOOLS_JSON)

        # Act
        result = _migrate_tools_json(ai_eng)

        # Assert
        assert result is True
        assert not (ai_eng / "state" / "tools.json").exists()

        data = _read_json(ai_eng / "state" / "install-state.json")
        assert "sonar" in data["platforms"]
        assert data["platforms"]["sonar"]["configured"] is True
        assert data["platforms"]["sonar"]["url"] == "https://sonarcloud.io"
        assert data["platforms"]["sonar"]["project_key"] == "my-project"
        assert data["platforms"]["sonar"]["credential_ref"]["service"] == "ai-engineering/sonar"


# ---------------------------------------------------------------------------
# T-2.3.3  both absent -> no-op
# ---------------------------------------------------------------------------


class TestBothAbsentNoop:
    """When neither old file exists, migrations are no-ops."""

    def test_manifest_absent_returns_false(self, tmp_path: Path) -> None:
        """No install-manifest.json -> returns False, no new file."""
        ai_eng = tmp_path / ".ai-engineering"
        (ai_eng / "state").mkdir(parents=True)

        result = _migrate_install_manifest(ai_eng)

        assert result is False
        assert not (ai_eng / "state" / "install-state.json").exists()

    def test_tools_absent_returns_false(self, tmp_path: Path) -> None:
        """No tools.json -> returns False."""
        ai_eng = tmp_path / ".ai-engineering"
        (ai_eng / "state").mkdir(parents=True)

        result = _migrate_tools_json(ai_eng)

        assert result is False


# ---------------------------------------------------------------------------
# T-2.3.4  both old and new exist -> old overwrites new
# ---------------------------------------------------------------------------


class TestOldOverwritesNew:
    """When both install-manifest.json and install-state.json exist,
    the old file takes precedence (re-migration)."""

    def test_old_manifest_overwrites_existing_state(self, tmp_path: Path) -> None:
        """Re-migrate: old manifest data replaces existing install-state.json."""
        # Arrange
        ai_eng = tmp_path / ".ai-engineering"
        state_dir = ai_eng / "state"

        # Write a pre-existing install-state.json with different data
        existing_state = {
            "schema_version": "2.0",
            "installed_at": "2026-01-01T00:00:00Z",
            "tooling": {},
            "platforms": {},
            "branch_policy": {"applied": False, "mode": "api"},
            "operational_readiness": {"status": "pending", "pending_steps": []},
            "release": {"last_version": "0.1.0"},
        }
        _write_json(state_dir / "install-state.json", existing_state)
        _write_json(state_dir / "install-manifest.json", _LEGACY_MANIFEST)

        # Act
        result = _migrate_install_manifest(ai_eng)

        # Assert -- old manifest values win
        assert result is True
        assert not (state_dir / "install-manifest.json").exists()

        data = _read_json(state_dir / "install-state.json")
        assert data["branch_policy"]["applied"] is True  # from legacy, was False
        assert data["release"]["last_version"] == "0.3.0"  # from legacy, was 0.1.0


# ---------------------------------------------------------------------------
# T-2.3.5  idempotent (run twice)
# ---------------------------------------------------------------------------


class TestIdempotent:
    """Running migration twice produces the same result; second is a no-op."""

    def test_manifest_migration_idempotent(self, tmp_path: Path) -> None:
        """First run returns True and creates file. Second run returns False."""
        # Arrange
        ai_eng = tmp_path / ".ai-engineering"
        _write_json(ai_eng / "state" / "install-manifest.json", _LEGACY_MANIFEST)

        # First run
        assert _migrate_install_manifest(ai_eng) is True
        first_data = _read_json(ai_eng / "state" / "install-state.json")

        # Second run -- old file is gone, no-op
        assert _migrate_install_manifest(ai_eng) is False

        # Data unchanged
        second_data = _read_json(ai_eng / "state" / "install-state.json")
        assert first_data == second_data

    def test_tools_migration_idempotent(self, tmp_path: Path) -> None:
        """First run returns True. Second run returns False."""
        # Arrange
        ai_eng = tmp_path / ".ai-engineering"
        _write_json(ai_eng / "state" / "tools.json", _TOOLS_JSON)

        # First run
        assert _migrate_tools_json(ai_eng) is True
        first_data = _read_json(ai_eng / "state" / "install-state.json")

        # Second run -- tools.json gone
        assert _migrate_tools_json(ai_eng) is False
        second_data = _read_json(ai_eng / "state" / "install-state.json")
        assert first_data == second_data


# ---------------------------------------------------------------------------
# T-2.3.6  tools.json merged into existing install-state.json
# ---------------------------------------------------------------------------


class TestToolsMergedIntoExisting:
    """tools.json platforms merge into pre-existing install-state.json
    without overwriting tooling or other sections."""

    def test_existing_tooling_preserved_after_tools_merge(self, tmp_path: Path) -> None:
        """Pre-existing tooling entries survive the tools.json merge."""
        # Arrange
        ai_eng = tmp_path / ".ai-engineering"
        state_dir = ai_eng / "state"

        # Pre-existing install-state with tooling but no platforms
        existing_state = {
            "schema_version": "2.0",
            "installed_at": "2026-03-25T10:00:00Z",
            "tooling": {
                "gh": {
                    "installed": True,
                    "authenticated": True,
                    "mode": "cli",
                    "scopes": ["repo"],
                },
                "ruff": {"installed": True, "authenticated": False, "mode": "cli", "scopes": []},
            },
            "platforms": {
                "azure_devops": {
                    "configured": True,
                    "url": "https://dev.azure.com/my-org",
                    "project_key": "",
                    "organization": "",
                },
            },
            "branch_policy": {"applied": True, "mode": "cli"},
            "operational_readiness": {"status": "READY", "pending_steps": []},
            "release": {"last_version": "0.3.0"},
        }
        _write_json(state_dir / "install-state.json", existing_state)
        _write_json(state_dir / "tools.json", _TOOLS_JSON)

        # Act
        result = _migrate_tools_json(ai_eng)

        # Assert
        assert result is True
        assert not (state_dir / "tools.json").exists()

        data = _read_json(state_dir / "install-state.json")

        # Tooling preserved
        assert data["tooling"]["gh"]["installed"] is True
        assert data["tooling"]["ruff"]["installed"] is True

        # Existing platforms preserved (azure_devops was pre-existing, not in tools.json)
        # Note: azure_devops in tools.json has configured=False, so _extract_platforms
        # doesn't include it -- the pre-existing entry survives
        assert "azure_devops" in data["platforms"]
        assert data["platforms"]["azure_devops"]["url"] == "https://dev.azure.com/my-org"

        # New platform merged
        assert "sonar" in data["platforms"]
        assert data["platforms"]["sonar"]["configured"] is True
        assert data["platforms"]["sonar"]["url"] == "https://sonarcloud.io"

        # Branch policy and other sections untouched
        assert data["branch_policy"]["applied"] is True
        assert data["release"]["last_version"] == "0.3.0"
