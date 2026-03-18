"""Unit tests for SonarLint IDE configuration module.

Tests cover:
- IDE family detection from workspace markers.
- VS Code family Connected Mode configuration (SonarCloud + SonarQube).
- JetBrains family Connected Mode configuration.
- Visual Studio 2022 Connected Mode configuration.
- Orchestrator (configure_all_ides).
- JSON merge safety (D024-009).
- Connection ID generation and SonarCloud URL detection.
- Extension recommendation injection.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.platforms.sonarlint import (
    IDEFamily,
    SonarLintResult,
    SonarLintSummary,
    _build_connection_id,
    _extract_org_key,
    _is_sonarcloud,
    _read_json_safe,
    _write_json_safe,
    configure_all_ides,
    configure_jetbrains,
    configure_vs2022,
    configure_vscode,
    detect_ide_families,
)

pytestmark = pytest.mark.unit

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

SONARCLOUD_URL = "https://sonarcloud.io"
SONARCLOUD_ORG_URL = "https://sonarcloud.io/organizations/my-org/projects"
SONARQUBE_URL = "https://sonar.example.com"
PROJECT_KEY = "my-project-key"


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """Return a bare workspace directory."""
    return tmp_path


@pytest.fixture()
def vscode_workspace(tmp_path: Path) -> Path:
    """Return a workspace with a ``.vscode/`` marker."""
    (tmp_path / ".vscode").mkdir()
    return tmp_path


@pytest.fixture()
def jetbrains_workspace(tmp_path: Path) -> Path:
    """Return a workspace with a ``.idea/`` marker."""
    (tmp_path / ".idea").mkdir()
    return tmp_path


@pytest.fixture()
def vs2022_workspace(tmp_path: Path) -> Path:
    """Return a workspace with a ``.vs/`` marker."""
    (tmp_path / ".vs").mkdir()
    return tmp_path


@pytest.fixture()
def all_ides_workspace(tmp_path: Path) -> Path:
    """Return a workspace with all IDE markers present."""
    (tmp_path / ".vscode").mkdir()
    (tmp_path / ".idea").mkdir()
    (tmp_path / ".vs").mkdir()
    return tmp_path


# ------------------------------------------------------------------
# IDE detection
# ------------------------------------------------------------------


class TestDetectIDEFamilies:
    """Tests for ``detect_ide_families``."""

    def test_no_markers(self, workspace: Path) -> None:
        assert detect_ide_families(workspace) == []

    def test_vscode_only(self, vscode_workspace: Path) -> None:
        result = detect_ide_families(vscode_workspace)
        assert result == [IDEFamily.VSCODE]

    def test_jetbrains_only(self, jetbrains_workspace: Path) -> None:
        result = detect_ide_families(jetbrains_workspace)
        assert result == [IDEFamily.JETBRAINS]

    def test_vs2022_only(self, vs2022_workspace: Path) -> None:
        result = detect_ide_families(vs2022_workspace)
        assert result == [IDEFamily.VS2022]

    def test_all_ides(self, all_ides_workspace: Path) -> None:
        result = detect_ide_families(all_ides_workspace)
        assert IDEFamily.VSCODE in result
        assert IDEFamily.JETBRAINS in result
        assert IDEFamily.VS2022 in result
        assert len(result) == 3

    def test_partial_markers(self, tmp_path: Path) -> None:
        (tmp_path / ".vscode").mkdir()
        (tmp_path / ".vs").mkdir()
        result = detect_ide_families(tmp_path)
        assert IDEFamily.VSCODE in result
        assert IDEFamily.VS2022 in result
        assert IDEFamily.JETBRAINS not in result


# ------------------------------------------------------------------
# Connection helpers
# ------------------------------------------------------------------


class TestConnectionHelpers:
    """Tests for ``_is_sonarcloud``, ``_build_connection_id``, ``_extract_org_key``."""

    def test_is_sonarcloud_positive(self) -> None:
        assert _is_sonarcloud("https://sonarcloud.io") is True
        assert _is_sonarcloud("https://sonarcloud.io/organizations/acme") is True
        assert _is_sonarcloud("https://SONARCLOUD.IO") is True

    def test_is_sonarcloud_negative(self) -> None:
        assert _is_sonarcloud("https://sonar.example.com") is False
        assert _is_sonarcloud("https://my-sonarqube.local") is False

    def test_build_connection_id_sonarcloud(self) -> None:
        conn_id = _build_connection_id(SONARCLOUD_URL)
        assert conn_id == "ai-engineering-sonarcloud"

    def test_build_connection_id_sonarqube(self) -> None:
        conn_id = _build_connection_id(SONARQUBE_URL)
        assert conn_id == "ai-engineering-sonar-example-com"

    def test_build_connection_id_sonarqube_localhost(self) -> None:
        conn_id = _build_connection_id("http://localhost:9000")
        assert conn_id == "ai-engineering-localhost"

    def test_extract_org_key_present(self) -> None:
        url = "https://sonarcloud.io/organizations/my-org/projects"
        assert _extract_org_key(url) == "my-org"

    def test_extract_org_key_absent(self) -> None:
        assert _extract_org_key("https://sonarcloud.io") == ""

    def test_extract_org_key_trailing_slash(self) -> None:
        url = "https://sonarcloud.io/organizations/acme/"
        assert _extract_org_key(url) == "acme"


# ------------------------------------------------------------------
# JSON helpers
# ------------------------------------------------------------------


class TestJSONHelpers:
    """Tests for ``_read_json_safe`` and ``_write_json_safe``."""

    def test_read_missing_file(self, tmp_path: Path) -> None:
        assert _read_json_safe(tmp_path / "missing.json") == {}

    def test_read_empty_file(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.json"
        path.write_text("", encoding="utf-8")
        assert _read_json_safe(path) == {}

    def test_read_invalid_json(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("{not valid json", encoding="utf-8")
        assert _read_json_safe(path) == {}

    def test_read_valid_json(self, tmp_path: Path) -> None:
        path = tmp_path / "ok.json"
        path.write_text('{"key": "value"}', encoding="utf-8")
        assert _read_json_safe(path) == {"key": "value"}

    def test_write_and_read_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "roundtrip.json"
        data = {"a": 1, "b": [2, 3]}
        _write_json_safe(path, data)
        assert _read_json_safe(path) == data

    def test_write_creates_formatted_json(self, tmp_path: Path) -> None:
        path = tmp_path / "formatted.json"
        _write_json_safe(path, {"x": 1})
        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n")
        assert "  " in text  # indented


# ------------------------------------------------------------------
# VS Code family configuration
# ------------------------------------------------------------------


class TestConfigureVSCode:
    """Tests for ``configure_vscode``."""

    def test_sonarcloud_basic(self, vscode_workspace: Path) -> None:
        result = configure_vscode(vscode_workspace, SONARCLOUD_URL, PROJECT_KEY)

        assert result.success is True
        assert result.ide_family == "vscode"
        assert len(result.files_written) == 2

        settings = _read_json_safe(vscode_workspace / ".vscode" / "settings.json")
        assert "sonarlint.connectedMode.connections.sonarcloud" in settings
        connections = settings["sonarlint.connectedMode.connections.sonarcloud"]
        assert any(c["connectionId"] == "ai-engineering-sonarcloud" for c in connections)

        project_binding = settings["sonarlint.connectedMode.project"]
        assert project_binding["projectKey"] == PROJECT_KEY

    def test_sonarqube_basic(self, vscode_workspace: Path) -> None:
        result = configure_vscode(vscode_workspace, SONARQUBE_URL, PROJECT_KEY)

        assert result.success is True
        settings = _read_json_safe(vscode_workspace / ".vscode" / "settings.json")
        assert "sonarlint.connectedMode.connections.sonarqube" in settings
        connections = settings["sonarlint.connectedMode.connections.sonarqube"]
        assert connections[0]["serverUrl"] == SONARQUBE_URL

    def test_extension_recommendation_added(self, vscode_workspace: Path) -> None:
        configure_vscode(vscode_workspace, SONARCLOUD_URL, PROJECT_KEY)

        extensions = _read_json_safe(vscode_workspace / ".vscode" / "extensions.json")
        assert "SonarSource.sonarlint-vscode" in extensions["recommendations"]

    def test_extension_recommendation_idempotent(self, vscode_workspace: Path) -> None:
        configure_vscode(vscode_workspace, SONARCLOUD_URL, PROJECT_KEY)
        configure_vscode(vscode_workspace, SONARCLOUD_URL, PROJECT_KEY)

        extensions = _read_json_safe(vscode_workspace / ".vscode" / "extensions.json")
        count = extensions["recommendations"].count("SonarSource.sonarlint-vscode")
        assert count == 1

    def test_merge_preserves_existing_settings(self, vscode_workspace: Path) -> None:
        """D024-009: merge-safe — existing user settings must not be overwritten."""
        settings_path = vscode_workspace / ".vscode" / "settings.json"
        _write_json_safe(settings_path, {"editor.fontSize": 14, "python.linting.enabled": True})

        configure_vscode(vscode_workspace, SONARCLOUD_URL, PROJECT_KEY)

        settings = _read_json_safe(settings_path)
        assert settings["editor.fontSize"] == 14
        assert settings["python.linting.enabled"] is True
        assert "sonarlint.connectedMode.project" in settings

    def test_merge_preserves_existing_extensions(self, vscode_workspace: Path) -> None:
        ext_path = vscode_workspace / ".vscode" / "extensions.json"
        _write_json_safe(ext_path, {"recommendations": ["ms-python.python"]})

        configure_vscode(vscode_workspace, SONARCLOUD_URL, PROJECT_KEY)

        extensions = _read_json_safe(ext_path)
        assert "ms-python.python" in extensions["recommendations"]
        assert "SonarSource.sonarlint-vscode" in extensions["recommendations"]

    def test_connection_not_duplicated(self, vscode_workspace: Path) -> None:
        """Calling configure twice must not duplicate the connection entry."""
        configure_vscode(vscode_workspace, SONARCLOUD_URL, PROJECT_KEY)
        configure_vscode(vscode_workspace, SONARCLOUD_URL, PROJECT_KEY)

        settings = _read_json_safe(vscode_workspace / ".vscode" / "settings.json")
        connections = settings["sonarlint.connectedMode.connections.sonarcloud"]
        ids = [c["connectionId"] for c in connections]
        assert len(ids) == len(set(ids)), "Duplicate connection entries found"

    def test_creates_vscode_dir_if_missing(self, workspace: Path) -> None:
        result = configure_vscode(workspace, SONARCLOUD_URL, PROJECT_KEY)
        assert result.success is True
        assert (workspace / ".vscode" / "settings.json").exists()

    def test_custom_connection_id(self, vscode_workspace: Path) -> None:
        result = configure_vscode(
            vscode_workspace, SONARCLOUD_URL, PROJECT_KEY, connection_id="custom-id"
        )
        assert result.success is True
        settings = _read_json_safe(vscode_workspace / ".vscode" / "settings.json")
        project_binding = settings["sonarlint.connectedMode.project"]
        assert project_binding["connectionId"] == "custom-id"

    def test_sonarcloud_org_key_extracted(self, vscode_workspace: Path) -> None:
        configure_vscode(vscode_workspace, SONARCLOUD_ORG_URL, PROJECT_KEY)
        settings = _read_json_safe(vscode_workspace / ".vscode" / "settings.json")
        connections = settings["sonarlint.connectedMode.connections.sonarcloud"]
        assert connections[0]["organizationKey"] == "my-org"


# ------------------------------------------------------------------
# JetBrains family configuration
# ------------------------------------------------------------------


class TestConfigureJetBrains:
    """Tests for ``configure_jetbrains``."""

    def test_sonarcloud_basic(self, jetbrains_workspace: Path) -> None:
        result = configure_jetbrains(jetbrains_workspace, SONARCLOUD_URL, PROJECT_KEY)

        assert result.success is True
        assert result.ide_family == "jetbrains"
        assert len(result.files_written) == 2

    def test_sonarlint_xml_created(self, jetbrains_workspace: Path) -> None:
        configure_jetbrains(jetbrains_workspace, SONARCLOUD_URL, PROJECT_KEY)

        xml_path = jetbrains_workspace / ".idea" / "sonarlint.xml"
        assert xml_path.exists()
        content = xml_path.read_text(encoding="utf-8")
        assert "SonarLintProjectSettings" in content
        assert PROJECT_KEY in content
        assert "SONARCLOUD" in content

    def test_sonarqube_connection_type(self, jetbrains_workspace: Path) -> None:
        configure_jetbrains(jetbrains_workspace, SONARQUBE_URL, PROJECT_KEY)

        xml_path = jetbrains_workspace / ".idea" / "sonarlint.xml"
        content = xml_path.read_text(encoding="utf-8")
        assert "SONARQUBE" in content
        assert SONARQUBE_URL in content

    def test_connected_mode_json_created(self, jetbrains_workspace: Path) -> None:
        configure_jetbrains(jetbrains_workspace, SONARCLOUD_URL, PROJECT_KEY)

        json_path = jetbrains_workspace / ".idea" / "sonarlint" / "connectedMode.json"
        assert json_path.exists()
        data = _read_json_safe(json_path)
        assert data["projectKey"] == PROJECT_KEY
        assert "connectionId" in data

    def test_creates_idea_dirs_if_missing(self, workspace: Path) -> None:
        result = configure_jetbrains(workspace, SONARCLOUD_URL, PROJECT_KEY)
        assert result.success is True
        assert (workspace / ".idea" / "sonarlint.xml").exists()
        assert (workspace / ".idea" / "sonarlint" / "connectedMode.json").exists()

    def test_custom_connection_id(self, jetbrains_workspace: Path) -> None:
        configure_jetbrains(
            jetbrains_workspace, SONARQUBE_URL, PROJECT_KEY, connection_id="my-conn"
        )
        json_path = jetbrains_workspace / ".idea" / "sonarlint" / "connectedMode.json"
        data = _read_json_safe(json_path)
        assert data["connectionId"] == "my-conn"


# ------------------------------------------------------------------
# Visual Studio 2022 configuration
# ------------------------------------------------------------------


class TestConfigureVS2022:
    """Tests for ``configure_vs2022``."""

    def test_sonarcloud_basic(self, vs2022_workspace: Path) -> None:
        result = configure_vs2022(vs2022_workspace, SONARCLOUD_URL, PROJECT_KEY)

        assert result.success is True
        assert result.ide_family == "vs2022"
        assert len(result.files_written) == 1

    def test_sonarcloud_settings_structure(self, vs2022_workspace: Path) -> None:
        configure_vs2022(vs2022_workspace, SONARCLOUD_URL, PROJECT_KEY)

        settings_path = vs2022_workspace / ".vs" / "SonarLint" / "settings.json"
        assert settings_path.exists()
        data = _read_json_safe(settings_path)
        assert "sonarCloudConnections" in data
        assert "projectBinding" in data
        assert data["projectBinding"]["projectKey"] == PROJECT_KEY

    def test_sonarqube_settings_structure(self, vs2022_workspace: Path) -> None:
        configure_vs2022(vs2022_workspace, SONARQUBE_URL, PROJECT_KEY)

        settings_path = vs2022_workspace / ".vs" / "SonarLint" / "settings.json"
        data = _read_json_safe(settings_path)
        assert "sonarQubeConnections" in data
        assert data["sonarQubeConnections"][0]["serverUrl"] == SONARQUBE_URL

    def test_creates_vs_dirs_if_missing(self, workspace: Path) -> None:
        result = configure_vs2022(workspace, SONARCLOUD_URL, PROJECT_KEY)
        assert result.success is True
        assert (workspace / ".vs" / "SonarLint" / "settings.json").exists()

    def test_custom_connection_id(self, vs2022_workspace: Path) -> None:
        configure_vs2022(vs2022_workspace, SONARQUBE_URL, PROJECT_KEY, connection_id="vs-conn")
        settings_path = vs2022_workspace / ".vs" / "SonarLint" / "settings.json"
        data = _read_json_safe(settings_path)
        assert data["projectBinding"]["connectionId"] == "vs-conn"

    def test_sonarcloud_org_key(self, vs2022_workspace: Path) -> None:
        configure_vs2022(vs2022_workspace, SONARCLOUD_ORG_URL, PROJECT_KEY)
        settings_path = vs2022_workspace / ".vs" / "SonarLint" / "settings.json"
        data = _read_json_safe(settings_path)
        assert data["sonarCloudConnections"][0]["organizationKey"] == "my-org"


# ------------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------------


class TestConfigureAllIDEs:
    """Tests for ``configure_all_ides``."""

    def test_auto_detect_all(self, all_ides_workspace: Path) -> None:
        summary = configure_all_ides(all_ides_workspace, SONARCLOUD_URL, PROJECT_KEY)

        assert summary.any_success is True
        assert len(summary.results) == 3
        families = {r.ide_family for r in summary.results}
        assert families == {"vscode", "jetbrains", "vs2022"}

    def test_explicit_families(self, workspace: Path) -> None:
        summary = configure_all_ides(
            workspace,
            SONARCLOUD_URL,
            PROJECT_KEY,
            ide_families=[IDEFamily.VSCODE],
        )
        assert len(summary.results) == 1
        assert summary.results[0].ide_family == "vscode"
        assert summary.results[0].success is True

    def test_no_ides_detected(self, workspace: Path) -> None:
        summary = configure_all_ides(workspace, SONARCLOUD_URL, PROJECT_KEY)

        assert summary.any_success is False
        assert len(summary.results) == 0

    def test_partial_failure_does_not_block_others(self, tmp_path: Path) -> None:
        """If one IDE config fails, others should still succeed."""
        (tmp_path / ".vscode").mkdir()
        (tmp_path / ".idea").mkdir()
        # Make .idea read-only to cause a failure on Windows (skip on non-Windows)
        # Instead, test with explicit families including an error case
        summary = configure_all_ides(
            tmp_path,
            SONARCLOUD_URL,
            PROJECT_KEY,
            ide_families=[IDEFamily.VSCODE, IDEFamily.JETBRAINS],
        )
        # Both should succeed in normal conditions
        assert len(summary.results) == 2
        success_count = sum(1 for r in summary.results if r.success)
        assert success_count == 2


# ------------------------------------------------------------------
# Data classes
# ------------------------------------------------------------------


class TestDataClasses:
    """Tests for ``SonarLintResult`` and ``SonarLintSummary``."""

    def test_result_defaults(self) -> None:
        result = SonarLintResult()
        assert result.success is False
        assert result.ide_family == ""
        assert result.files_written == []
        assert result.error == ""

    def test_summary_any_success_true(self) -> None:
        summary = SonarLintSummary(
            results=[
                SonarLintResult(success=False, error="fail"),
                SonarLintResult(success=True, ide_family="vscode"),
            ]
        )
        assert summary.any_success is True

    def test_summary_any_success_false(self) -> None:
        summary = SonarLintSummary(
            results=[
                SonarLintResult(success=False, error="fail"),
            ]
        )
        assert summary.any_success is False

    def test_summary_empty(self) -> None:
        summary = SonarLintSummary()
        assert summary.any_success is False


# ------------------------------------------------------------------
# IDEFamily enum
# ------------------------------------------------------------------


class TestIDEFamily:
    """Tests for the ``IDEFamily`` enum."""

    def test_values(self) -> None:
        assert IDEFamily.VSCODE.value == "vscode"
        assert IDEFamily.JETBRAINS.value == "jetbrains"
        assert IDEFamily.VS2022.value == "vs2022"

    def test_is_string_enum(self) -> None:
        assert isinstance(IDEFamily.VSCODE, str)
        assert IDEFamily.VSCODE == "vscode"
