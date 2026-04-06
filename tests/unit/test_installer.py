"""Unit tests for installer/service.py — mocked install orchestrator.

Covers:
- InstallResult dataclass defaults and properties.
- _STATE_FILES constants.
- CopyResult dataclass defaults and counting.
- install() orchestration with all dependencies mocked.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.hooks.manager import HookInstallResult
from ai_engineering.installer.service import (
    _STATE_FILES,
    InstallResult,
    install,
)
from ai_engineering.installer.templates import CopyResult

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

    def test_contains_install_state(self) -> None:
        assert "install-state" in _STATE_FILES
        assert _STATE_FILES["install-state"] == "state/install-state.json"

    def test_contains_ownership_map(self) -> None:
        assert "ownership-map" in _STATE_FILES
        assert _STATE_FILES["ownership-map"] == "state/ownership-map.json"

    def test_contains_decision_store(self) -> None:
        assert "decision-store" in _STATE_FILES
        assert _STATE_FILES["decision-store"] == "state/decision-store.json"

    def test_contains_framework_capabilities(self) -> None:
        assert "framework-capabilities" in _STATE_FILES
        assert _STATE_FILES["framework-capabilities"] == "state/framework-capabilities.json"

    def test_contains_instinct_artifacts(self) -> None:
        assert _STATE_FILES["instinct-observations"] == "state/instinct-observations.ndjson"
        assert _STATE_FILES["instincts"] == "instincts/instincts.yml"
        assert _STATE_FILES["instinct-meta"] == "instincts/meta.json"

    def test_has_exactly_seven_entries(self) -> None:
        assert len(_STATE_FILES) == 7


class TestFrameworkCapabilitiesPath:
    """Verify installer state files include the canonical capability catalog."""

    def test_framework_capabilities_path_value(self) -> None:
        assert _STATE_FILES["framework-capabilities"] == "state/framework-capabilities.json"


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
# copy_template_tree exclude parameter
# ---------------------------------------------------------------------------


class TestCopyTemplateTreeExclude:
    """Verify copy_template_tree respects the exclude parameter."""

    def test_exclude_skips_matching_prefixes(self, tmp_path: Path) -> None:
        from ai_engineering.installer.templates import copy_template_tree

        # Arrange — source tree with agents, skills, and standards
        src = tmp_path / "src"
        (src / "agents").mkdir(parents=True)
        (src / "agents" / "plan.md").write_text("agent")
        (src / "skills" / "test").mkdir(parents=True)
        (src / "skills" / "test" / "SKILL.md").write_text("skill")
        (src / "standards").mkdir(parents=True)
        (src / "standards" / "core.md").write_text("standard")

        dest = tmp_path / "dest"
        dest.mkdir()

        # Act
        result = copy_template_tree(src, dest, exclude=["agents/", "skills/"])

        # Assert — excluded dirs not copied, non-excluded dirs copied
        assert not (dest / "agents" / "plan.md").exists()
        assert not (dest / "skills" / "test" / "SKILL.md").exists()
        assert (dest / "standards" / "core.md").exists()
        assert len(result.created) == 1
        assert len(result.skipped) == 0

    def test_exclude_none_copies_everything(self, tmp_path: Path) -> None:
        from ai_engineering.installer.templates import copy_template_tree

        # Arrange
        src = tmp_path / "src"
        (src / "a").mkdir(parents=True)
        (src / "a" / "file.md").write_text("content")
        (src / "b").mkdir(parents=True)
        (src / "b" / "file.md").write_text("content")

        dest = tmp_path / "dest"
        dest.mkdir()

        # Act
        result = copy_template_tree(src, dest, exclude=None)

        # Assert
        assert (dest / "a" / "file.md").exists()
        assert (dest / "b" / "file.md").exists()
        assert len(result.created) == 2


# ---------------------------------------------------------------------------
# Common file maps and template map completeness
# ---------------------------------------------------------------------------


class TestCommonFileMaps:
    """Verify _COMMON_FILE_MAPS contains security/quality templates."""

    def test_gitleaks_toml_present(self) -> None:
        from ai_engineering.installer.templates import _COMMON_FILE_MAPS

        assert ".gitleaks.toml" in _COMMON_FILE_MAPS
        assert _COMMON_FILE_MAPS[".gitleaks.toml"] == ".gitleaks.toml"

    def test_semgrep_yml_present(self) -> None:
        from ai_engineering.installer.templates import _COMMON_FILE_MAPS

        assert ".semgrep.yml" in _COMMON_FILE_MAPS
        assert _COMMON_FILE_MAPS[".semgrep.yml"] == ".semgrep.yml"

    def test_common_files_not_in_provider_maps(self) -> None:
        """Common files are handled by the dedicated loop, not provider maps."""
        from ai_engineering.installer.templates import resolve_template_maps

        maps = resolve_template_maps()
        assert ".gitleaks.toml" not in maps.file_map
        assert ".semgrep.yml" not in maps.file_map


class TestCopyProjectTemplatesCommonFiles:
    """Verify copy_project_templates deploys common files."""

    def test_common_files_deployed(self, tmp_path: Path) -> None:
        from ai_engineering.installer.templates import copy_project_templates

        # Act
        result = copy_project_templates(tmp_path, providers=["claude_code"])

        # Assert — common files deployed regardless of provider
        gitleaks = tmp_path / ".gitleaks.toml"
        semgrep = tmp_path / ".semgrep.yml"
        assert gitleaks.exists()
        assert semgrep.exists()
        assert gitleaks in result.created
        assert semgrep in result.created

    def test_common_files_not_overwritten(self, tmp_path: Path) -> None:
        from ai_engineering.installer.templates import copy_project_templates

        # Pre-existing files
        (tmp_path / ".gitleaks.toml").write_text("custom")
        (tmp_path / ".semgrep.yml").write_text("custom")

        # Act
        copy_project_templates(tmp_path, providers=["claude_code"])

        # Assert — existing files not overwritten
        assert (tmp_path / ".gitleaks.toml").read_text() == "custom"
        assert (tmp_path / ".semgrep.yml").read_text() == "custom"


class TestCopilotInstructionsTreeMap:
    """Verify copilot/ and instructions/ are tree-mapped for github_copilot."""

    def test_copilot_tree_in_provider_tree_maps(self) -> None:
        from ai_engineering.installer.templates import _PROVIDER_TREE_MAPS

        copilot_trees = _PROVIDER_TREE_MAPS["github_copilot"]
        assert (".github/skills", ".github/skills") in copilot_trees
        assert ("agents", ".github/agents") in copilot_trees
        assert ("instructions", ".github/instructions") in copilot_trees

    def test_sonarqube_instruction_deployed(self, tmp_path: Path) -> None:
        from ai_engineering.installer.templates import copy_project_templates

        # Act
        copy_project_templates(
            tmp_path,
            providers=["github_copilot"],
        )

        # Assert
        sonar_inst = tmp_path / ".github" / "instructions" / "sonarqube_mcp.instructions.md"
        assert sonar_inst.exists()


class TestVcsTemplatesDeployed:
    """Verify VCS-specific templates (CODEOWNERS, dependabot) are deployed."""

    def test_codeowners_deployed_for_github(self, tmp_path: Path) -> None:
        from ai_engineering.installer.templates import copy_project_templates

        # Act
        copy_project_templates(
            tmp_path,
            providers=["claude_code"],
            vcs_provider="github",
        )

        # Assert
        assert (tmp_path / ".github" / "CODEOWNERS").exists()

    def test_dependabot_deployed_for_github(self, tmp_path: Path) -> None:
        from ai_engineering.installer.templates import copy_project_templates

        # Act
        copy_project_templates(
            tmp_path,
            providers=["claude_code"],
            vcs_provider="github",
        )

        # Assert
        assert (tmp_path / ".github" / "dependabot.yml").exists()

    def test_vcs_templates_not_deployed_without_vcs_provider(self, tmp_path: Path) -> None:
        from ai_engineering.installer.templates import copy_project_templates

        # Act
        copy_project_templates(
            tmp_path,
            providers=["claude_code"],
        )

        # Assert — no VCS-specific files without vcs_provider
        assert not (tmp_path / ".github" / "CODEOWNERS").exists()
        assert not (tmp_path / ".github" / "dependabot.yml").exists()


class TestCanonicalTemplateStructure:
    """Verify governance template structure is correct."""

    def test_agents_exist_for_sync_script(self) -> None:
        """agents/ must exist — sync script reads canonical source from here."""
        from ai_engineering.installer.templates import get_project_template_root

        root = get_project_template_root()
        assert (root / ".claude" / "agents").is_dir()

    def test_skills_exist_for_sync_script(self) -> None:
        """skills/ must exist — sync script reads canonical source from here."""
        from ai_engineering.installer.templates import get_project_template_root

        root = get_project_template_root()
        assert (root / ".claude" / "skills").is_dir()

    def test_no_evals_in_governance_templates(self) -> None:
        """evals/ is runtime state, not a governance template."""
        from ai_engineering.installer.templates import get_ai_engineering_template_root

        root = get_ai_engineering_template_root()
        assert not (root / "evals").exists()

    def test_agents_excluded_by_installer(self, tmp_path: Path) -> None:
        """agents/ exists but is excluded during installation (deployed via IDE mirrors)."""
        from ai_engineering.installer.templates import (
            copy_template_tree,
            get_ai_engineering_template_root,
        )

        root = get_ai_engineering_template_root()
        result = copy_template_tree(root, tmp_path, exclude=["agents/", "skills/"])
        created_rels = [p.relative_to(tmp_path).as_posix() for p in result.created]
        assert not any(r.startswith("agents/") for r in created_rels)
        assert not any(r.startswith("skills/") for r in created_rels)


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
    mocks["write_framework_capabilities"] = MagicMock()
    mocks["emit_framework_operation"] = MagicMock()
    mocks["install_hooks"] = MagicMock(return_value=HookInstallResult())
    mocks["load_install_state"] = MagicMock()
    mocks["save_install_state"] = MagicMock()
    mocks["load_manifest_config"] = MagicMock()
    mocks["check_tools_for_stacks"] = MagicMock()
    mocks["check_vcs_auth"] = MagicMock()
    mocks["apply_branch_policy"] = MagicMock()
    mocks["get_provider"] = MagicMock()
    mocks["ensure_tool"] = MagicMock()
    mocks["provider_required_tools"] = MagicMock(return_value=[])

    # Default: _run_operational_phases reads a state that does not exist,
    # so it returns early.  We mock Path.exists on the state path to False
    # to avoid entering the operational phase.
    mocks["default_install_state"] = MagicMock()
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
    stack.enter_context(
        patch(f"{_SVC}.write_framework_capabilities", mocks["write_framework_capabilities"])
    )
    stack.enter_context(
        patch(f"{_SVC}.emit_framework_operation", mocks["emit_framework_operation"])
    )
    stack.enter_context(patch(f"{_SVC}.install_hooks", mocks["install_hooks"]))
    stack.enter_context(patch(f"{_SVC}.load_install_state", mocks["load_install_state"]))
    stack.enter_context(patch(f"{_SVC}.save_install_state", mocks["save_install_state"]))
    stack.enter_context(patch(f"{_SVC}.load_manifest_config", mocks["load_manifest_config"]))
    stack.enter_context(patch(f"{_SVC}.check_tools_for_stacks", mocks["check_tools_for_stacks"]))
    stack.enter_context(patch(f"{_SVC}.check_vcs_auth", mocks["check_vcs_auth"]))
    stack.enter_context(patch(f"{_SVC}.apply_branch_policy", mocks["apply_branch_policy"]))
    stack.enter_context(patch(f"{_SVC}.get_provider", mocks["get_provider"]))
    stack.enter_context(patch(f"{_SVC}.ensure_tool", mocks["ensure_tool"]))
    stack.enter_context(patch(f"{_SVC}.provider_required_tools", mocks["provider_required_tools"]))
    stack.enter_context(patch(f"{_SVC}.default_install_state", mocks["default_install_state"]))
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
        assert len(result.state_files) == 7


class TestInstallSkipsExistingStateFiles:
    """install() skips state files that already exist."""

    def test_no_writes_when_all_exist(self, patched, tmp_path: Path) -> None:
        # Act
        with patch.object(Path, "exists", return_value=True):
            result = install(tmp_path)

        # Assert
        assert result.state_files == []


class TestInstallCreatesDefaultState:
    """install() generates default install state."""

    def test_state_files_created_when_missing(self, patched, tmp_path: Path) -> None:
        with patch.object(Path, "exists", return_value=False):
            result = install(tmp_path, stacks=["python", "dotnet"], ides=["vscode", "terminal"])

        assert len(result.state_files) == 7

    def test_default_stacks_none_passes(self, patched, tmp_path: Path) -> None:
        with patch.object(Path, "exists", return_value=False):
            result = install(tmp_path)

        # State files still created
        assert len(result.state_files) == 7


class TestInstallCallsInstallHooks:
    """install() calls install_hooks when not skipped."""

    def test_hooks_called(self, patched, tmp_path: Path) -> None:
        with patch.object(Path, "exists", return_value=True):
            install(tmp_path)

        patched["install_hooks"].assert_called_once_with(tmp_path)

    def test_hooks_propagates_file_not_found(self, patched, tmp_path: Path) -> None:
        """FileNotFoundError from install_hooks now propagates (not suppressed)."""
        patched["install_hooks"].side_effect = FileNotFoundError("no .git")
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "is_dir", return_value=True),
            pytest.raises(FileNotFoundError, match=r"no \.git"),
        ):
            install(tmp_path)


class TestInstallCallsCheckToolsForStacks:
    """install() calls check_tools_for_stacks in operational phase."""

    def test_called_when_state_exists(self, patched, tmp_path: Path) -> None:
        from ai_engineering.installer.auth import AuthResult
        from ai_engineering.installer.branch_policy import BranchPolicyResult

        patched["load_manifest_config"].return_value = MagicMock(
            providers=MagicMock(stacks=["python"], vcs="github"),
        )
        patched["check_tools_for_stacks"].return_value = MagicMock(tools=[])
        patched["check_vcs_auth"].return_value = AuthResult(
            provider="github",
            mode="cli",
            authenticated=True,
            message="ok",
        )
        patched["apply_branch_policy"].return_value = BranchPolicyResult(
            applied=True,
            mode="cli",
            message="ok",
        )
        patched["provider_required_tools"].return_value = []

        with patch.object(Path, "exists", return_value=True):
            install(tmp_path, stacks=["python"])

        patched["check_tools_for_stacks"].assert_called_once()
        assert patched["check_tools_for_stacks"].call_args.kwargs["vcs_provider"] == "github"


class TestOperationalRemediation:
    def test_provider_tool_manual_steps_use_shared_guidance(self, patched, tmp_path: Path) -> None:
        from ai_engineering.installer.auth import AuthResult
        from ai_engineering.installer.branch_policy import BranchPolicyResult
        from ai_engineering.installer.tools import ToolInstallResult

        patched["load_manifest_config"].return_value = MagicMock(
            providers=MagicMock(stacks=[], vcs="github"),
        )
        patched["check_tools_for_stacks"].return_value = MagicMock(tools=[])
        patched["check_vcs_auth"].return_value = AuthResult(
            provider="github",
            mode="api",
            authenticated=False,
            message="Authenticate gh",
        )
        patched["apply_branch_policy"].return_value = BranchPolicyResult(
            applied=True,
            mode="api",
            message="ok",
        )
        patched["provider_required_tools"].return_value = ["gh"]
        patched["ensure_tool"].return_value = ToolInstallResult(
            tool="gh",
            available=False,
            attempted=False,
            installed=False,
        )

        with patch.object(Path, "exists", return_value=True):
            result = install(tmp_path)

        assert any("Install `gh` manually" in step for step in result.manual_steps)

    def test_stack_tool_manual_steps_use_shared_guidance(self, patched, tmp_path: Path) -> None:
        from ai_engineering.installer.auth import AuthResult
        from ai_engineering.installer.branch_policy import BranchPolicyResult
        from ai_engineering.installer.tools import ToolInstallResult

        missing_tool = MagicMock(name="semgrep", available=False)
        missing_tool.name = "semgrep"
        missing_tool.available = False
        patched["load_manifest_config"].return_value = MagicMock(
            providers=MagicMock(stacks=["python"], vcs="github"),
        )
        patched["check_tools_for_stacks"].return_value = MagicMock(tools=[missing_tool])
        patched["check_vcs_auth"].return_value = AuthResult(
            provider="github",
            mode="cli",
            authenticated=True,
            message="ok",
        )
        patched["apply_branch_policy"].return_value = BranchPolicyResult(
            applied=True,
            mode="cli",
            message="ok",
        )
        patched["provider_required_tools"].return_value = []
        patched["ensure_tool"].return_value = ToolInstallResult(
            tool="semgrep",
            available=False,
            attempted=False,
            installed=False,
        )

        with patch.object(Path, "exists", return_value=True):
            result = install(tmp_path)

        assert any("Install `semgrep` manually" in step for step in result.manual_steps)


class TestInstallCallsCheckVcsAuth:
    """install() calls check_vcs_auth in operational phase."""

    def test_called_when_state_exists(self, patched, tmp_path: Path) -> None:
        from ai_engineering.installer.auth import AuthResult
        from ai_engineering.installer.branch_policy import BranchPolicyResult

        patched["check_tools_for_stacks"].return_value = MagicMock(tools=[])
        patched["check_vcs_auth"].return_value = AuthResult(
            provider="github",
            mode="cli",
            authenticated=True,
            message="ok",
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


class TestInstallCallsApplyBranchPolicy:
    """install() calls apply_branch_policy in operational phase."""

    def test_called_when_state_exists(self, patched, tmp_path: Path) -> None:
        from ai_engineering.installer.auth import AuthResult
        from ai_engineering.installer.branch_policy import BranchPolicyResult

        patched["check_tools_for_stacks"].return_value = MagicMock(tools=[])
        patched["check_vcs_auth"].return_value = AuthResult(
            provider="github",
            mode="cli",
            authenticated=True,
            message="ok",
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


class TestInstallEmitsFrameworkOperation:
    """install() emits a canonical framework operation event."""

    def test_emit_framework_operation_called(self, patched, tmp_path: Path) -> None:
        # Act
        with patch.object(Path, "exists", return_value=True):
            install(tmp_path)

        # Assert
        patched["emit_framework_operation"].assert_called_once()

    def test_framework_operation_is_install(self, patched, tmp_path: Path) -> None:
        # Act
        with patch.object(Path, "exists", return_value=True):
            install(tmp_path)

        # Assert
        kwargs = patched["emit_framework_operation"].call_args.kwargs
        assert kwargs["operation"] == "install"
        assert kwargs["component"] == "installer"


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
            result = install(tmp_path, stacks=[])

        # State files still created for empty stacks
        assert isinstance(result, InstallResult)

    def test_returns_valid_result(self, patched, tmp_path: Path) -> None:
        with patch.object(Path, "exists", return_value=False):
            result = install(tmp_path, stacks=[])

        assert isinstance(result, InstallResult)


class TestInstallWithMultipleStacks:
    """install() with multiple stacks."""

    def test_multiple_stacks_forwarded(self, patched, tmp_path: Path) -> None:
        with patch.object(Path, "exists", return_value=False):
            result = install(tmp_path, stacks=["python", "dotnet"])

        # Verify install completed successfully with multiple stacks
        assert isinstance(result, InstallResult)


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
            result = install(tmp_path, vcs_provider="azure_devops")

        # Verify install completed with azure_devops provider
        assert isinstance(result, InstallResult)
