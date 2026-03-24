"""Unit tests for the autodetect module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.installer.autodetect import (
    DetectionResult,
    detect_ai_providers,
    detect_all,
    detect_ides,
    detect_stacks,
    detect_vcs,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# detect_stacks — individual markers
# ---------------------------------------------------------------------------


class TestDetectStacksSingleMarker:
    """Each marker file resolves to the expected stack."""

    def test_pyproject_toml(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").touch()
        assert detect_stacks(tmp_path) == ["python"]

    def test_setup_py(self, tmp_path: Path) -> None:
        (tmp_path / "setup.py").touch()
        assert detect_stacks(tmp_path) == ["python"]

    def test_setup_cfg(self, tmp_path: Path) -> None:
        (tmp_path / "setup.cfg").touch()
        assert detect_stacks(tmp_path) == ["python"]

    def test_pipfile(self, tmp_path: Path) -> None:
        (tmp_path / "Pipfile").touch()
        assert detect_stacks(tmp_path) == ["python"]

    def test_package_json_alone_is_javascript(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").touch()
        assert detect_stacks(tmp_path) == ["javascript"]

    def test_tsconfig_json_alone_is_typescript(self, tmp_path: Path) -> None:
        (tmp_path / "tsconfig.json").touch()
        assert detect_stacks(tmp_path) == ["typescript"]

    def test_package_json_with_tsconfig_is_typescript_only(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").touch()
        (tmp_path / "tsconfig.json").touch()
        assert detect_stacks(tmp_path) == ["typescript"]

    def test_go_mod(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").touch()
        assert detect_stacks(tmp_path) == ["go"]

    def test_cargo_toml(self, tmp_path: Path) -> None:
        (tmp_path / "Cargo.toml").touch()
        assert detect_stacks(tmp_path) == ["rust"]

    def test_csproj(self, tmp_path: Path) -> None:
        (tmp_path / "MyApp.csproj").touch()
        assert detect_stacks(tmp_path) == ["csharp"]

    def test_sln(self, tmp_path: Path) -> None:
        (tmp_path / "MyApp.sln").touch()
        assert detect_stacks(tmp_path) == ["csharp"]

    def test_pom_xml(self, tmp_path: Path) -> None:
        (tmp_path / "pom.xml").touch()
        assert detect_stacks(tmp_path) == ["java"]

    def test_build_gradle(self, tmp_path: Path) -> None:
        (tmp_path / "build.gradle").touch()
        assert detect_stacks(tmp_path) == ["java"]

    def test_build_gradle_kts_detects_both(self, tmp_path: Path) -> None:
        (tmp_path / "build.gradle.kts").touch()
        assert detect_stacks(tmp_path) == ["java", "kotlin"]

    def test_gemfile(self, tmp_path: Path) -> None:
        (tmp_path / "Gemfile").touch()
        assert detect_stacks(tmp_path) == ["ruby"]

    def test_pubspec_yaml(self, tmp_path: Path) -> None:
        (tmp_path / "pubspec.yaml").touch()
        assert detect_stacks(tmp_path) == ["dart"]

    def test_mix_exs(self, tmp_path: Path) -> None:
        (tmp_path / "mix.exs").touch()
        assert detect_stacks(tmp_path) == ["elixir"]

    def test_package_swift(self, tmp_path: Path) -> None:
        (tmp_path / "Package.swift").touch()
        assert detect_stacks(tmp_path) == ["swift"]

    def test_composer_json(self, tmp_path: Path) -> None:
        (tmp_path / "composer.json").touch()
        assert detect_stacks(tmp_path) == ["php"]


# ---------------------------------------------------------------------------
# detect_stacks — composite & edge cases
# ---------------------------------------------------------------------------


class TestDetectStacksComposite:
    """Multiple markers, empty directory, and sorted output."""

    def test_empty_dir_returns_empty(self, tmp_path: Path) -> None:
        assert detect_stacks(tmp_path) == []

    def test_multi_stack_sorted(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").touch()
        (tmp_path / "Cargo.toml").touch()
        assert detect_stacks(tmp_path) == ["go", "rust"]

    def test_python_and_typescript(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "tsconfig.json").touch()
        assert detect_stacks(tmp_path) == ["python", "typescript"]

    def test_multiple_python_markers_deduplicate(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "setup.py").touch()
        (tmp_path / "Pipfile").touch()
        assert detect_stacks(tmp_path) == ["python"]

    def test_csproj_in_subdirectory_not_detected(self, tmp_path: Path) -> None:
        sub = tmp_path / "src"
        sub.mkdir()
        (sub / "App.csproj").touch()
        assert detect_stacks(tmp_path) == []


# ---------------------------------------------------------------------------
# detect_ai_providers
# ---------------------------------------------------------------------------


class TestDetectAIProviders:
    """AI provider detection from directory markers."""

    def test_claude_dir(self, tmp_path: Path) -> None:
        (tmp_path / ".claude").mkdir()
        assert detect_ai_providers(tmp_path) == ["claude_code"]

    def test_copilot_instructions_file(self, tmp_path: Path) -> None:
        gh = tmp_path / ".github"
        gh.mkdir()
        (gh / "copilot-instructions.md").touch()
        assert detect_ai_providers(tmp_path) == ["github_copilot"]

    def test_copilot_prompts_directory(self, tmp_path: Path) -> None:
        prompts = tmp_path / ".github" / "prompts"
        prompts.mkdir(parents=True)
        assert detect_ai_providers(tmp_path) == ["github_copilot"]

    def test_both_providers(self, tmp_path: Path) -> None:
        (tmp_path / ".claude").mkdir()
        gh = tmp_path / ".github"
        gh.mkdir()
        (gh / "copilot-instructions.md").touch()
        assert detect_ai_providers(tmp_path) == ["claude_code", "github_copilot"]

    def test_agents_dir_not_detected(self, tmp_path: Path) -> None:
        (tmp_path / ".agents").mkdir()
        assert detect_ai_providers(tmp_path) == []

    def test_empty_dir(self, tmp_path: Path) -> None:
        assert detect_ai_providers(tmp_path) == []

    def test_github_dir_without_copilot_markers(self, tmp_path: Path) -> None:
        (tmp_path / ".github").mkdir()
        assert detect_ai_providers(tmp_path) == []


# ---------------------------------------------------------------------------
# detect_ides
# ---------------------------------------------------------------------------


class TestDetectIDEs:
    """IDE detection from directory markers."""

    def test_vscode(self, tmp_path: Path) -> None:
        (tmp_path / ".vscode").mkdir()
        assert detect_ides(tmp_path) == ["vscode"]

    def test_jetbrains(self, tmp_path: Path) -> None:
        (tmp_path / ".idea").mkdir()
        assert detect_ides(tmp_path) == ["jetbrains"]

    def test_both_sorted(self, tmp_path: Path) -> None:
        (tmp_path / ".vscode").mkdir()
        (tmp_path / ".idea").mkdir()
        assert detect_ides(tmp_path) == ["jetbrains", "vscode"]

    def test_empty_dir(self, tmp_path: Path) -> None:
        assert detect_ides(tmp_path) == []


# ---------------------------------------------------------------------------
# detect_vcs
# ---------------------------------------------------------------------------


class TestDetectVCS:
    """VCS detection delegates to vcs.factory.detect_from_remote."""

    def test_returns_github(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.installer.autodetect.detect_from_remote",
            return_value="github",
        ):
            assert detect_vcs(tmp_path) == "github"

    def test_returns_azure_devops(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.installer.autodetect.detect_from_remote",
            return_value="azure_devops",
        ):
            assert detect_vcs(tmp_path) == "azure_devops"

    def test_exception_falls_back_to_github(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.installer.autodetect.detect_from_remote",
            side_effect=RuntimeError("git not available"),
        ):
            assert detect_vcs(tmp_path) == "github"


# ---------------------------------------------------------------------------
# detect_all
# ---------------------------------------------------------------------------


class TestDetectAll:
    """detect_all aggregates all four detection functions."""

    def test_aggregates_results(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".vscode").mkdir()

        with patch(
            "ai_engineering.installer.autodetect.detect_from_remote",
            return_value="github",
        ):
            result = detect_all(tmp_path)

        assert isinstance(result, DetectionResult)
        assert result.stacks == ["python"]
        assert result.providers == ["claude_code"]
        assert result.ides == ["vscode"]
        assert result.vcs == "github"

    def test_empty_project(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.installer.autodetect.detect_from_remote",
            return_value="github",
        ):
            result = detect_all(tmp_path)

        assert result.stacks == []
        assert result.providers == []
        assert result.ides == []
        assert result.vcs == "github"

    def test_multi_stack_multi_provider(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").touch()
        (tmp_path / "Cargo.toml").touch()
        (tmp_path / ".claude").mkdir()
        gh = tmp_path / ".github"
        gh.mkdir()
        (gh / "copilot-instructions.md").touch()
        (tmp_path / ".idea").mkdir()

        with patch(
            "ai_engineering.installer.autodetect.detect_from_remote",
            return_value="azure_devops",
        ):
            result = detect_all(tmp_path)

        assert result.stacks == ["go", "rust"]
        assert result.providers == ["claude_code", "github_copilot"]
        assert result.ides == ["jetbrains"]
        assert result.vcs == "azure_devops"
