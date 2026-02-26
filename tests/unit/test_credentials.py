"""Unit tests for the credential service module.

All OS keyring interactions are mocked — no real secrets are
stored or retrieved during testing.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ai_engineering.credentials.models import (
    AzureDevOpsConfig,
    CredentialRef,
    GitHubConfig,
    PlatformKind,
    SonarConfig,
    ToolsState,
)
from ai_engineering.credentials.service import CredentialService


# ---------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------


@pytest.fixture()
def mock_backend() -> MagicMock:
    """Return a mock keyring backend."""
    backend = MagicMock()
    backend.get_password.return_value = None
    return backend


@pytest.fixture()
def svc(mock_backend: MagicMock) -> CredentialService:
    """Return a CredentialService wired to the mock backend."""
    return CredentialService(backend=mock_backend)


# ---------------------------------------------------------------
# Models
# ---------------------------------------------------------------


class TestModels:
    """Tests for Pydantic models."""

    def test_credential_ref_defaults(self) -> None:
        ref = CredentialRef(service_name="ai-engineering/sonar", username="token")
        assert ref.configured is False

    def test_tools_state_defaults(self) -> None:
        state = ToolsState()
        assert state.github.configured is False
        assert state.sonar.configured is False
        assert state.azure_devops.configured is False

    def test_tools_state_round_trip(self) -> None:
        state = ToolsState(
            github=GitHubConfig(configured=True, cli_authenticated=True, scopes=["repo"]),
            sonar=SonarConfig(
                configured=True,
                url="https://sonarcloud.io",
                project_key="my-proj",
                credential_ref=CredentialRef(
                    service_name="ai-engineering/sonar",
                    username="token",
                    configured=True,
                ),
            ),
            azure_devops=AzureDevOpsConfig(configured=False),
        )
        payload = state.model_dump_json()
        restored = ToolsState.model_validate_json(payload)
        assert restored.github.scopes == ["repo"]
        assert restored.sonar.url == "https://sonarcloud.io"
        assert restored.sonar.credential_ref is not None
        assert restored.sonar.credential_ref.configured is True

    def test_platform_kind_values(self) -> None:
        assert PlatformKind.GITHUB.value == "github"
        assert PlatformKind.SONAR.value == "sonar"
        assert PlatformKind.AZURE_DEVOPS.value == "azure_devops"


# ---------------------------------------------------------------
# CredentialService — keyring operations
# ---------------------------------------------------------------


class TestCredentialServiceKeyring:
    """Tests for store / retrieve / delete / exists."""

    def test_service_name(self) -> None:
        assert CredentialService.service_name("sonar") == "ai-engineering/sonar"

    def test_store_calls_set_password(
        self, svc: CredentialService, mock_backend: MagicMock
    ) -> None:
        svc.store("sonar", "token", "s3cr3t")
        mock_backend.set_password.assert_called_once_with(
            "ai-engineering/sonar", "token", "s3cr3t"
        )

    def test_retrieve_returns_value(
        self, svc: CredentialService, mock_backend: MagicMock
    ) -> None:
        mock_backend.get_password.return_value = "s3cr3t"
        assert svc.retrieve("sonar", "token") == "s3cr3t"

    def test_retrieve_returns_none_when_missing(self, svc: CredentialService) -> None:
        assert svc.retrieve("sonar", "token") is None

    def test_delete_calls_delete_password(
        self, svc: CredentialService, mock_backend: MagicMock
    ) -> None:
        svc.delete("sonar", "token")
        mock_backend.delete_password.assert_called_once_with(
            "ai-engineering/sonar", "token"
        )

    def test_delete_ignores_missing(
        self, svc: CredentialService, mock_backend: MagicMock
    ) -> None:
        mock_backend.delete_password.side_effect = Exception("not found")
        svc.delete("sonar", "token")  # should not raise

    def test_exists_returns_true_when_present(
        self, svc: CredentialService, mock_backend: MagicMock
    ) -> None:
        mock_backend.get_password.return_value = "s3cr3t"
        assert svc.exists("sonar", "token") is True

    def test_exists_returns_false_when_absent(self, svc: CredentialService) -> None:
        assert svc.exists("sonar", "token") is False


# ---------------------------------------------------------------
# CredentialService — tools.json state
# ---------------------------------------------------------------


class TestToolsJsonState:
    """Tests for load / save tools.json."""

    def test_load_returns_defaults_when_missing(self, tmp_path: Path) -> None:
        state = CredentialService.load_tools_state(tmp_path)
        assert state.github.configured is False
        assert state.sonar.configured is False

    def test_save_creates_file(self, tmp_path: Path) -> None:
        state = ToolsState(github=GitHubConfig(configured=True))
        CredentialService.save_tools_state(tmp_path, state)
        path = tmp_path / "tools.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["github"]["configured"] is True

    def test_load_reads_saved_state(self, tmp_path: Path) -> None:
        original = ToolsState(
            sonar=SonarConfig(configured=True, url="https://sonarcloud.io")
        )
        CredentialService.save_tools_state(tmp_path, original)
        loaded = CredentialService.load_tools_state(tmp_path)
        assert loaded.sonar.configured is True
        assert loaded.sonar.url == "https://sonarcloud.io"

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        nested = tmp_path / "deep" / "state"
        CredentialService.save_tools_state(nested, ToolsState())
        assert (nested / "tools.json").exists()


# ---------------------------------------------------------------
# Masking
# ---------------------------------------------------------------


class TestMaskSecret:
    """Tests for secret masking utility."""

    def test_mask_long_secret(self) -> None:
        assert CredentialService.mask_secret("abcdefgh") == "abcd***"

    def test_mask_short_secret(self) -> None:
        assert CredentialService.mask_secret("abc") == "***"

    def test_mask_exact_boundary(self) -> None:
        assert CredentialService.mask_secret("abcd") == "***"

    def test_mask_custom_visible_chars(self) -> None:
        assert CredentialService.mask_secret("abcdefgh", visible_chars=2) == "ab***"

    def test_mask_empty_string(self) -> None:
        assert CredentialService.mask_secret("") == "***"
