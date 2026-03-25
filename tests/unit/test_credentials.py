"""Unit tests for the credential service module.

All OS keyring interactions are mocked -- no real secrets are
stored or retrieved during testing.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ai_engineering.credentials.models import PlatformKind
from ai_engineering.credentials.service import CredentialService

pytestmark = pytest.mark.unit

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
    """Tests for remaining Pydantic models."""

    def test_platform_kind_values(self) -> None:
        assert PlatformKind.GITHUB.value == "github"
        assert PlatformKind.SONAR.value == "sonar"
        assert PlatformKind.AZURE_DEVOPS.value == "azure_devops"


# ---------------------------------------------------------------
# CredentialService -- keyring operations
# ---------------------------------------------------------------


class TestCredentialServiceKeyring:
    """Tests for store / retrieve / delete / exists."""

    def test_service_name(self) -> None:
        assert CredentialService.service_name("sonar") == "ai-engineering/sonar"

    def test_store_calls_set_password(
        self, svc: CredentialService, mock_backend: MagicMock
    ) -> None:
        svc.store("sonar", "token", "s3cr3t")
        mock_backend.set_password.assert_called_once_with("ai-engineering/sonar", "token", "s3cr3t")

    def test_retrieve_returns_value(self, svc: CredentialService, mock_backend: MagicMock) -> None:
        mock_backend.get_password.return_value = "s3cr3t"
        assert svc.retrieve("sonar", "token") == "s3cr3t"

    def test_retrieve_returns_none_when_missing(self, svc: CredentialService) -> None:
        assert svc.retrieve("sonar", "token") is None

    def test_delete_calls_delete_password(
        self, svc: CredentialService, mock_backend: MagicMock
    ) -> None:
        svc.delete("sonar", "token")
        mock_backend.delete_password.assert_called_once_with("ai-engineering/sonar", "token")

    def test_delete_ignores_missing(self, svc: CredentialService, mock_backend: MagicMock) -> None:
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
