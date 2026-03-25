"""Unit tests for stack add/remove/list operations.

Tests the ``add_stack``, ``remove_stack``, and ``list_status`` functions
from ``ai_engineering.installer.operations`` directly (not via CLI).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ai_engineering.installer.operations import (
    InstallerError,
    add_stack,
    list_status,
    remove_stack,
)

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Manifest YAML templates
# ---------------------------------------------------------------------------

_MANIFEST_SINGLE = """\
schema_version: "2.0"
providers:
  vcs: github
  ides: []
  stacks: [python]
ai_providers:
  enabled: [claude_code]
  primary: claude_code
"""

_MANIFEST_DUAL = """\
schema_version: "2.0"
providers:
  vcs: github
  ides: []
  stacks: [python, rust]
ai_providers:
  enabled: [claude_code]
  primary: claude_code
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def stack_project(tmp_path: Path) -> Path:
    """Create a minimal project with a single-stack manifest."""
    ai_dir = tmp_path / ".ai-engineering"
    ai_dir.mkdir()
    (ai_dir / "state").mkdir()
    (ai_dir / "manifest.yml").write_text(_MANIFEST_SINGLE, encoding="utf-8")
    return tmp_path


@pytest.fixture()
def dual_stack_project(tmp_path: Path) -> Path:
    """Create a minimal project with [python, rust] stacks."""
    ai_dir = tmp_path / ".ai-engineering"
    ai_dir.mkdir()
    (ai_dir / "state").mkdir()
    (ai_dir / "manifest.yml").write_text(_MANIFEST_DUAL, encoding="utf-8")
    return tmp_path


@pytest.fixture()
def mocked_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Suppress audit side-effects so tests run without git/repo context."""
    monkeypatch.setattr("ai_engineering.installer.operations.append_ndjson", MagicMock())
    monkeypatch.setattr(
        "ai_engineering.installer.operations.get_repo_context",
        MagicMock(return_value=None),
    )
    monkeypatch.setattr(
        "ai_engineering.installer.operations.get_git_context",
        MagicMock(return_value=None),
    )


# ---------------------------------------------------------------------------
# TestAddStack
# ---------------------------------------------------------------------------


class TestAddStack:
    def test_add_stack_success(
        self,
        stack_project: Path,
        mocked_audit: None,
    ) -> None:
        """Adding a known stack appends it to the manifest."""
        result = add_stack(stack_project, "rust")
        assert "rust" in result.providers.stacks
        assert "python" in result.providers.stacks

    def test_add_stack_unknown_raises(
        self,
        stack_project: Path,
        mocked_audit: None,
    ) -> None:
        """An unrecognised stack name raises InstallerError."""
        with pytest.raises(InstallerError, match="Unknown stack"):
            add_stack(stack_project, "nonexistent_xyz")

    def test_add_stack_already_installed_raises(
        self,
        stack_project: Path,
        mocked_audit: None,
    ) -> None:
        """Adding a stack that is already present raises InstallerError."""
        with pytest.raises(InstallerError, match="already"):
            add_stack(stack_project, "python")

    def test_add_stack_not_installed_raises(
        self,
        tmp_path: Path,
        mocked_audit: None,
    ) -> None:
        """Adding a stack to a directory without .ai-engineering raises InstallerError."""
        with pytest.raises(InstallerError):
            add_stack(tmp_path, "rust")


# ---------------------------------------------------------------------------
# TestRemoveStack
# ---------------------------------------------------------------------------


class TestRemoveStack:
    def test_remove_stack_success(
        self,
        dual_stack_project: Path,
        mocked_audit: None,
    ) -> None:
        """Removing an existing stack leaves only the others."""
        result = remove_stack(dual_stack_project, "rust")
        assert result.providers.stacks == ["python"]

    def test_remove_stack_not_present_raises(
        self,
        stack_project: Path,
        mocked_audit: None,
    ) -> None:
        """Removing a stack that is not present raises InstallerError."""
        with pytest.raises(InstallerError):
            remove_stack(stack_project, "rust")

    def test_remove_last_stack_succeeds(
        self,
        stack_project: Path,
        mocked_audit: None,
    ) -> None:
        """Removing the sole remaining stack leaves an empty list."""
        result = remove_stack(stack_project, "python")
        assert result.providers.stacks == []


# ---------------------------------------------------------------------------
# TestListStatus
# ---------------------------------------------------------------------------


class TestListStatus:
    def test_list_status_returns_config(
        self,
        stack_project: Path,
    ) -> None:
        """list_status returns a ManifestConfig with the expected stacks."""
        from ai_engineering.config.manifest import ManifestConfig

        result = list_status(stack_project)
        assert isinstance(result, ManifestConfig)
        assert result.providers.stacks == ["python"]

    def test_list_status_not_installed_raises(
        self,
        tmp_path: Path,
    ) -> None:
        """list_status on a bare directory raises InstallerError."""
        with pytest.raises(InstallerError):
            list_status(tmp_path)
