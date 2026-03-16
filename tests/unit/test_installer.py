"""Unit tests for installer/service.py — mocked install orchestrator.

Covers:
- InstallResult dataclass defaults and properties.
- _STATE_FILES and _AUDIT_LOG_PATH constants.
- CopyResult dataclass defaults and counting.
- install() orchestration with all dependencies mocked.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.credentials.models import SonarConfig, ToolsState
from ai_engineering.hooks.manager import HookInstallResult
from ai_engineering.installer.service import (
    _AUDIT_LOG_PATH,
    _STATE_FILES,
    InstallResult,
    _resolve_sonar_cicd_config,
    install,
)
from ai_engineering.installer.templates import CopyResult

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Module-level patch prefix shortcuts
# ---------------------------------------------------------------------------

_SVC = "ai_engineering.installer.service"

# ---------------------------------------------------------------------------
# InstallResult dataclass
# ---------------------------------------------------------------------------


class TestInstallResultDefaults:
    """Verify InstallResult default field values."""

    def test_governance_files_default(self) -> None:
        result = InstallResult()
        assert isinstance(result.governance_files, CopyResult)
        assert result.governance_files.created == []
        assert result.governance_files.skipped == []

    def test_project_files_default(self) -> None:
        result = InstallResult()
        assert isinstance(result.project_files, CopyResult)
        assert result.project_files.created == []

    def test_state_files_default(self) -> None:
        result = InstallResult()
        assert result.state_files == []

    def test_hooks_default(self) -> None:
        result = InstallResult()
        assert isinstance(result.hooks, HookInstallResult)
        assert result.hooks.installed == []
        assert result.hooks.skipped == []
        assert result.hooks.conflicts == []

    def test_already_installed_default(self) -> None:
        result = InstallResult()
        assert result.already_installed is False

    def test_readiness_status_default(self) -> None:
        result = InstallResult()
        assert result.readiness_status == "pending"

    def test_manual_steps_default(self) -> None:
        result = InstallResult()
        assert result.manual_steps == []

    def test_total_created_empty(self) -> None:
        result = InstallResult()
        assert result.total_created == 0

    def test_total_skipped_empty(self) -> None:
        result = InstallResult()
        assert result.total_skipped == 0

    def test_total_created_counts_all_categories(self) -> None:
        # Arrange
        result = InstallResult()
        result.governance_files = CopyResult(
            created=[Path("a"), Path("b")],
            skipped=[],
        )
        result.project_files = CopyResult(
            created=[Path("c")],
            skipped=[],
        )
        result.state_files = [Path("d"), Path("e"), Path("f")]

        # Assert
        assert result.total_created == 6

    def test_total_skipped_counts_both_categories(self) -> None:
        # Arrange
        result = InstallResult()
        result.governance_files = CopyResult(
            created=[],
            skipped=[Path("a"), Path("b")],
        )
        result.project_files = CopyResult(
            created=[],
            skipped=[Path("c")],
        )

        # Assert
        assert result.total_skipped == 3


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestStateFilesConstant:
    """Verify _STATE_FILES contains expected entries."""

    def test_contains_install_manifest(self) -> None:
        assert "install-manifest" in _STATE_FILES
        assert _STATE_FILES["install-manifest"] == "state/install-manifest.json"

    def test_contains_ownership_map(self) -> None:
        assert "ownership-map" in _STATE_FILES
        assert _STATE_FILES["ownership-map"] == "state/ownership-map.json"

    def test_contains_decision_store(self) -> None:
        assert "decision-store" in _STATE_FILES
        assert _STATE_FILES["decision-store"] == "state/decision-store.json"

    def test_has_exactly_three_entries(self) -> None:
        assert len(_STATE_FILES) == 3


class TestAuditLogPath:
    """Verify _AUDIT_LOG_PATH is correct."""

    def test_audit_log_path_value(self) -> None:
        assert _AUDIT_LOG_PATH == "state/audit-log.ndjson"


# ---------------------------------------------------------------------------
# CopyResult dataclass
# ---------------------------------------------------------------------------


class TestCopyResult:
    """Verify CopyResult defaults and counting."""

    def test_defaults(self) -> None:
        result = CopyResult()
        assert result.created == []
        assert result.skipped == []

    def test_with_counts(self) -> None:
        result = CopyResult(
            created=[Path("a"), Path("b"), Path("c")],
            skipped=[Path("d")],
        )
        assert len(result.created) == 3
        assert len(result.skipped) == 1


# ---------------------------------------------------------------------------
# install() orchestration (fully mocked)
# ---------------------------------------------------------------------------


def _build_install_mocks() -> dict[str, MagicMock]:
    """Build a dict of mock objects for all install() collaborators.

    Returns a dict keyed by short names (e.g. "copy_template_tree")
    whose values are MagicMock instances with sensible defaults.
    """
    mocks: dict[str, MagicMock] = {}

    mocks["get_ai_engineering_template_root"] = MagicMock(return_value=Path("/fake/templates"))
    mocks["copy_template_tree"] = MagicMock(return_value=CopyResult())
    mocks["copy_project_templates"] = MagicMock(return_value=CopyResult())
    mocks["write_json_model"] = MagicMock()
    mocks["append_ndjson"] = MagicMock()
    mocks["install_hooks"] = MagicMock(return_value=HookInstallResult())
    mocks["read_json_model"] = MagicMock()
    mocks["check_tools_for_stacks"] = MagicMock()
    mocks["check_vcs_auth"] = MagicMock()
    mocks["generate_pipelines"] = MagicMock()
    mocks["apply_branch_policy"] = MagicMock()
    mocks["get_provider"] = MagicMock()
    mocks["ensure_tool"] = MagicMock()
    mocks["provider_required_tools"] = MagicMock(return_value=[])

    # Default: _run_operational_phases reads a manifest that does not exist,
    # so it returns early.  We mock Path.exists on the manifest path to False
    # to avoid entering the operational phase.
    mocks["default_install_manifest"] = MagicMock()
    mocks["default_ownership_map"] = MagicMock()
    mocks["default_decision_store"] = MagicMock()

    return mocks


def _patch_all(mocks: dict[str, MagicMock]):
    """Return a contextlib-style stack of patches for install().

    Usage::

        with _patch_all(mocks):
            result = install(...)
    """
    import contextlib

    return contextlib.ExitStack().__enter__() or _apply_patches(mocks)


def _apply_patches(mocks: dict[str, MagicMock]):
    """Apply all patches for the install service module."""
    import contextlib

    stack = contextlib.ExitStack()
    stack.enter_context(
        patch(f"{_SVC}.get_ai_engineering_template_root", mocks["get_ai_engineering_template_root"])
    )
    stack.enter_context(patch(f"{_SVC}.copy_template_tree", mocks["copy_template_tree"]))
    stack.enter_context(patch(f"{_SVC}.copy_project_templates", mocks["copy_project_templates"]))
    stack.enter_context(patch(f"{_SVC}.write_json_model", mocks["write_json_model"]))
    stack.enter_context(patch(f"{_SVC}.append_ndjson", mocks["append_ndjson"]))
    stack.enter_context(patch(f"{_SVC}.install_hooks", mocks["install_hooks"]))
    stack.enter_context(patch(f"{_SVC}.read_json_model", mocks["read_json_model"]))
    stack.enter_context(patch(f"{_SVC}.check_tools_for_stacks", mocks["check_tools_for_stacks"]))
    stack.enter_context(patch(f"{_SVC}.check_vcs_auth", mocks["check_vcs_auth"]))
    stack.enter_context(patch(f"{_SVC}.generate_pipelines", mocks["generate_pipelines"]))
    stack.enter_context(patch(f"{_SVC}.apply_branch_policy", mocks["apply_branch_policy"]))
    stack.enter_context(patch(f"{_SVC}.get_provider", mocks["get_provider"]))
    stack.enter_context(patch(f"{_SVC}.ensure_tool", mocks["ensure_tool"]))
    stack.enter_context(patch(f"{_SVC}.provider_required_tools", mocks["provider_required_tools"]))
    stack.enter_context(
        patch(f"{_SVC}.default_install_manifest", mocks["default_install_manifest"])
    )
    stack.enter_context(patch(f"{_SVC}.default_ownership_map", mocks["default_ownership_map"]))
    stack.enter_context(patch(f"{_SVC}.default_decision_store", mocks["default_decision_store"]))
    return stack


@pytest.fixture()
def mocks():
    """Provide fully-mocked collaborators for install()."""
    return _build_install_mocks()


@pytest.fixture()
def patched(mocks):
    """Activate all patches and yield the mocks dict."""
    stack = _apply_patches(mocks)
    try:
        yield mocks
    finally:
        stack.close()


class TestInstallCallsCopyTemplateTree:
    """install() calls copy_template_tree with correct args."""

    def test_called_with_template_root_and_ai_eng_dir(self, patched, tmp_path: Path) -> None:
        # Act
        with patch.object(Path, "exists", return_value=True):
            install(tmp_path)

        # Assert
        patched["copy_template_tree"].assert_called_once_with(
            Path("/fake/templates"),
            tmp_path / ".ai-engineering",
            exclude=["agents/", "skills/"],
        )


class TestInstallCallsCopyProjectTemplates:
    """install() calls copy_project_templates with correct target."""

    def test_called_with_target(self, patched, tmp_path: Path) -> None:
        # Act
        with patch.object(Path, "exists", return_value=True):
            install(tmp_path)

        # Assert
        patched["copy_project_templates"].assert_called_once_with(
            tmp_path,
            providers=None,
        )


class TestInstallCreatesStateFiles:
    """install() creates state files that don't exist."""

    def test_writes_state_files_when_missing(self, patched, tmp_path: Path) -> None:
        # Act
        with patch.object(Path, "exists", return_value=False):
            result = install(tmp_path, stacks=["python"])

        # Assert
        assert patched["write_json_model"].call_count >= 3
        assert len(result.state_files) == 3


class TestInstallSkipsExistingStateFiles:
    """install() skips state files that already exist."""

    def test_no_writes_when_all_exist(self, patched, tmp_path: Path) -> None:
        # Act
        with patch.object(Path, "exists", return_value=True):
            result = install(tmp_path)

        # Assert
        state_write_calls = [
            c
            for c in patched["write_json_model"].call_args_list
            if any(
                name in str(c)
                for name in [
                    "ownership-map",
                    "decision-store",
                ]
            )
        ]
        assert len(state_write_calls) == 0
        assert result.state_files == []


class TestInstallUpdatesManifest:
    """install() passes stacks and ides to default_install_manifest."""

    def test_stacks_and_ides_forwarded(self, patched, tmp_path: Path) -> None:
        with patch.object(Path, "exists", return_value=False):
            install(tmp_path, stacks=["python", "dotnet"], ides=["vscode", "terminal"])

        patched["default_install_manifest"].assert_called_once_with(
            stacks=["python", "dotnet"],
            ides=["vscode", "terminal"],
            vcs_provider="github",
            ai_providers=None,
        )

    def test_default_stacks_none_forwarded(self, patched, tmp_path: Path) -> None:
        with patch.object(Path, "exists", return_value=False):
            install(tmp_path)

        patched["default_install_manifest"].assert_called_once_with(
            stacks=None,
            ides=None,
            vcs_provider="github",
            ai_providers=None,
        )


class TestInstallCallsInstallHooks:
    """install() calls install_hooks when not skipped."""

    def test_hooks_called(self, patched, tmp_path: Path) -> None:
        with patch.object(Path, "exists", return_value=True):
            install(tmp_path)

        patched["install_hooks"].assert_called_once_with(tmp_path)

    def test_hooks_suppresses_file_not_found(self, patched, tmp_path: Path) -> None:
        """FileNotFoundError from install_hooks is suppressed gracefully."""
        patched["install_hooks"].side_effect = FileNotFoundError("no .git")
        with patch.object(Path, "exists", return_value=True):
            result = install(tmp_path)

        # Should not raise; result.hooks stays at default
        assert isinstance(result.hooks, HookInstallResult)


class TestInstallCallsCheckToolsForStacks:
    """install() calls check_tools_for_stacks in operational phase."""

    def test_called_when_manifest_exists(self, patched, tmp_path: Path) -> None:
        # Simulate manifest existing for _run_operational_phases
        from ai_engineering.installer.auth import AuthResult
        from ai_engineering.installer.branch_policy import BranchPolicyResult
        from ai_engineering.installer.cicd import CicdGenerationResult
        from ai_engineering.state.defaults import default_install_manifest as real_manifest

        manifest = real_manifest(stacks=["python"])
        patched["read_json_model"].return_value = manifest
        patched["check_tools_for_stacks"].return_value = MagicMock(tools=[])
        patched["check_vcs_auth"].return_value = AuthResult(
            provider="github",
            mode="cli",
            authenticated=True,
            message="ok",
        )
        patched["generate_pipelines"].return_value = CicdGenerationResult(
            provider="github",
        )
        patched["apply_branch_policy"].return_value = BranchPolicyResult(
            applied=True,
            mode="cli",
            message="ok",
        )
        patched["provider_required_tools"].return_value = []

        with patch.object(Path, "exists", return_value=True):
            install(tmp_path, stacks=["python"])

        patched["check_tools_for_stacks"].assert_called_once_with(manifest.installed_stacks)


class TestInstallCallsCheckVcsAuth:
    """install() calls check_vcs_auth in operational phase."""

    def test_called_when_manifest_exists(self, patched, tmp_path: Path) -> None:
        from ai_engineering.installer.auth import AuthResult
        from ai_engineering.installer.branch_policy import BranchPolicyResult
        from ai_engineering.installer.cicd import CicdGenerationResult
        from ai_engineering.state.defaults import default_install_manifest as real_manifest

        manifest = real_manifest(stacks=["python"])
        patched["read_json_model"].return_value = manifest
        patched["check_tools_for_stacks"].return_value = MagicMock(tools=[])
        patched["check_vcs_auth"].return_value = AuthResult(
            provider="github",
            mode="cli",
            authenticated=True,
            message="ok",
        )
        patched["generate_pipelines"].return_value = CicdGenerationResult(
            provider="github",
        )
        patched["apply_branch_policy"].return_value = BranchPolicyResult(
            applied=True,
            mode="cli",
            message="ok",
        )
        patched["provider_required_tools"].return_value = []

        with patch.object(Path, "exists", return_value=True):
            install(tmp_path)

        patched["check_vcs_auth"].assert_called_once()


class TestInstallCallsGeneratePipelines:
    """install() calls generate_pipelines in operational phase."""

    def test_called_when_manifest_exists(self, patched, tmp_path: Path) -> None:
        from ai_engineering.installer.auth import AuthResult
        from ai_engineering.installer.branch_policy import BranchPolicyResult
        from ai_engineering.installer.cicd import CicdGenerationResult
        from ai_engineering.state.defaults import default_install_manifest as real_manifest

        manifest = real_manifest(stacks=["python"])
        patched["read_json_model"].return_value = manifest
        patched["check_tools_for_stacks"].return_value = MagicMock(tools=[])
        patched["check_vcs_auth"].return_value = AuthResult(
            provider="github",
            mode="cli",
            authenticated=True,
            message="ok",
        )
        patched["generate_pipelines"].return_value = CicdGenerationResult(
            provider="github",
        )
        patched["apply_branch_policy"].return_value = BranchPolicyResult(
            applied=True,
            mode="cli",
            message="ok",
        )
        patched["provider_required_tools"].return_value = []

        with patch.object(Path, "exists", return_value=True):
            install(tmp_path, stacks=["python"])

        patched["generate_pipelines"].assert_called_once_with(
            tmp_path,
            provider="github",
            stacks=manifest.installed_stacks,
            sonar_config=None,
        )


class TestInstallCallsApplyBranchPolicy:
    """install() calls apply_branch_policy in operational phase."""

    def test_called_when_manifest_exists(self, patched, tmp_path: Path) -> None:
        from ai_engineering.installer.auth import AuthResult
        from ai_engineering.installer.branch_policy import BranchPolicyResult
        from ai_engineering.installer.cicd import CicdGenerationResult
        from ai_engineering.state.defaults import default_install_manifest as real_manifest

        manifest = real_manifest(stacks=["python"])
        patched["read_json_model"].return_value = manifest
        patched["check_tools_for_stacks"].return_value = MagicMock(tools=[])
        patched["check_vcs_auth"].return_value = AuthResult(
            provider="github",
            mode="cli",
            authenticated=True,
            message="ok",
        )
        patched["generate_pipelines"].return_value = CicdGenerationResult(
            provider="github",
        )
        patched["apply_branch_policy"].return_value = BranchPolicyResult(
            applied=True,
            mode="cli",
            message="ok",
        )
        patched["provider_required_tools"].return_value = []

        with patch.object(Path, "exists", return_value=True):
            install(tmp_path)

        patched["apply_branch_policy"].assert_called_once()
        bp_call = patched["apply_branch_policy"].call_args
        assert bp_call.kwargs["branch"] == "main"
        assert "ai-eng-gate" in bp_call.kwargs["required_checks"]


class TestInstallAppendsAuditLog:
    """install() appends an audit log entry."""

    def test_append_ndjson_called(self, patched, tmp_path: Path) -> None:
        # Act
        with patch.object(Path, "exists", return_value=True):
            install(tmp_path)

        # Assert
        patched["append_ndjson"].assert_called_once()
        audit_call = patched["append_ndjson"].call_args
        audit_path = Path(audit_call[0][0])
        assert audit_path.parts[-2:] == ("state", "audit-log.ndjson")

    def test_audit_entry_event_is_install(self, patched, tmp_path: Path) -> None:
        # Act
        with patch.object(Path, "exists", return_value=True):
            install(tmp_path)

        # Assert
        audit_entry = patched["append_ndjson"].call_args[0][1]
        assert audit_entry.event == "install"
        assert audit_entry.actor == "ai-engineering-cli"


class TestInstallReturnsInstallResult:
    """install() returns an InstallResult with populated fields."""

    def test_returns_install_result_type(self, patched, tmp_path: Path) -> None:
        with patch.object(Path, "exists", return_value=True):
            result = install(tmp_path)

        assert isinstance(result, InstallResult)

    def test_governance_files_from_copy_template_tree(self, patched, tmp_path: Path) -> None:
        # Arrange
        expected = CopyResult(created=[Path("x")], skipped=[])
        patched["copy_template_tree"].return_value = expected

        # Act
        with patch.object(Path, "exists", return_value=True):
            result = install(tmp_path)

        # Assert
        assert result.governance_files is expected

    def test_project_files_from_copy_project_templates(self, patched, tmp_path: Path) -> None:
        # Arrange
        expected = CopyResult(created=[Path("y")], skipped=[Path("z")])
        patched["copy_project_templates"].return_value = expected

        # Act
        with patch.object(Path, "exists", return_value=True):
            result = install(tmp_path)

        # Assert
        assert result.project_files is expected

    def test_hooks_from_install_hooks(self, patched, tmp_path: Path) -> None:
        # Arrange
        expected = HookInstallResult(installed=["pre-commit"], skipped=[], conflicts=[])
        patched["install_hooks"].return_value = expected

        # Act
        with patch.object(Path, "exists", return_value=True):
            result = install(tmp_path)

        # Assert
        assert result.hooks is expected


class TestInstallWithEmptyStacks:
    """install() with empty stacks list."""

    def test_empty_stacks_forwarded(self, patched, tmp_path: Path) -> None:
        with patch.object(Path, "exists", return_value=False):
            install(tmp_path, stacks=[])

        patched["default_install_manifest"].assert_called_once_with(
            stacks=[],
            ides=None,
            vcs_provider="github",
            ai_providers=None,
        )

    def test_returns_valid_result(self, patched, tmp_path: Path) -> None:
        with patch.object(Path, "exists", return_value=False):
            result = install(tmp_path, stacks=[])

        assert isinstance(result, InstallResult)


class TestInstallWithMultipleStacks:
    """install() with multiple stacks."""

    def test_multiple_stacks_forwarded(self, patched, tmp_path: Path) -> None:
        with patch.object(Path, "exists", return_value=False):
            install(tmp_path, stacks=["python", "dotnet"])

        patched["default_install_manifest"].assert_called_once_with(
            stacks=["python", "dotnet"],
            ides=None,
            vcs_provider="github",
            ai_providers=None,
        )


class TestInstallAlreadyInstalled:
    """install() sets already_installed when nothing new was created."""

    def test_already_installed_when_no_new_files(self, patched, tmp_path: Path) -> None:
        # Arrange
        patched["copy_template_tree"].return_value = CopyResult(
            created=[],
            skipped=[Path("a")],
        )
        patched["copy_project_templates"].return_value = CopyResult(
            created=[],
            skipped=[Path("b")],
        )

        # Act
        with patch.object(Path, "exists", return_value=True):
            result = install(tmp_path)

        # Assert
        assert result.already_installed is True

    def test_not_already_installed_when_governance_created(
        self,
        patched,
        tmp_path: Path,
    ) -> None:
        # Arrange
        patched["copy_template_tree"].return_value = CopyResult(
            created=[Path("new_file")],
            skipped=[],
        )

        # Act
        with patch.object(Path, "exists", return_value=True):
            result = install(tmp_path)

        # Assert
        assert result.already_installed is False


class TestInstallVcsProvider:
    """install() forwards vcs_provider to state generation."""

    def test_azure_devops_provider_forwarded(self, patched, tmp_path: Path) -> None:
        with patch.object(Path, "exists", return_value=False):
            install(tmp_path, vcs_provider="azure_devops")

        patched["default_install_manifest"].assert_called_once_with(
            stacks=None,
            ides=None,
            vcs_provider="azure_devops",
            ai_providers=None,
        )


class TestResolveSonarCicdConfig:
    """Tests for Sonar CI/CD resolution from tools state."""

    def test_returns_none_when_not_configured(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # Arrange
        monkeypatch.setattr(
            "ai_engineering.installer.service.CredentialService.load_tools_state",
            lambda *_: ToolsState(),
        )

        # Act & Assert
        assert _resolve_sonar_cicd_config(tmp_path) is None

    def test_returns_none_for_sonarcloud_without_org(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # Arrange
        state = ToolsState(
            sonar=SonarConfig(
                configured=True,
                url="https://sonarcloud.io",
                project_key="my-key",
                organization="",
            )
        )
        monkeypatch.setattr(
            "ai_engineering.installer.service.CredentialService.load_tools_state",
            lambda *_: state,
        )

        # Act & Assert
        assert _resolve_sonar_cicd_config(tmp_path) is None

    def test_returns_config_when_configured(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # Arrange
        state = ToolsState(
            sonar=SonarConfig(
                configured=True,
                url="https://sonarcloud.io",
                project_key="my-key",
                organization="my-org",
            )
        )
        monkeypatch.setattr(
            "ai_engineering.installer.service.CredentialService.load_tools_state",
            lambda *_: state,
        )

        # Act
        resolved = _resolve_sonar_cicd_config(tmp_path)

        # Assert
        assert resolved is not None
        assert resolved.enabled is True
        assert resolved.project_key == "my-key"
        assert resolved.organization == "my-org"
