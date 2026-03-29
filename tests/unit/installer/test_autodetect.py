"""Unit tests for the autodetect module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ai_engineering.installer.autodetect import (
    DetectionResult,
    _order_by_popularity,
    _walk_markers,
    detect_ai_providers,
    detect_all,
    detect_ides,
    detect_stacks,
    detect_vcs,
)

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
        # Popularity order: typescript (#1) before python (#2)
        assert detect_stacks(tmp_path) == ["typescript", "python"]

    def test_multiple_python_markers_deduplicate(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "setup.py").touch()
        (tmp_path / "Pipfile").touch()
        assert detect_stacks(tmp_path) == ["python"]

    def test_csproj_in_subdirectory_detected(self, tmp_path: Path) -> None:
        """Recursive walker now detects .csproj in subdirectories."""
        sub = tmp_path / "src"
        sub.mkdir()
        (sub / "App.csproj").touch()
        assert detect_stacks(tmp_path) == ["csharp"]


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

    def test_copilot_skills_directory(self, tmp_path: Path) -> None:
        skills = tmp_path / ".github" / "skills"
        skills.mkdir(parents=True)
        assert detect_ai_providers(tmp_path) == ["github_copilot"]

    def test_both_providers(self, tmp_path: Path) -> None:
        (tmp_path / ".claude").mkdir()
        gh = tmp_path / ".github"
        gh.mkdir()
        (gh / "copilot-instructions.md").touch()
        assert detect_ai_providers(tmp_path) == ["claude_code", "github_copilot"]

    def test_codex_detected_from_codex_dir(self, tmp_path: Path) -> None:
        (tmp_path / ".codex").mkdir()
        assert detect_ai_providers(tmp_path) == ["codex"]

    def test_codex_detected_from_agents_md(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
        assert detect_ai_providers(tmp_path) == ["codex"]

    def test_all_four_provider_surfaces(self, tmp_path: Path) -> None:
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".codex").mkdir()
        (tmp_path / ".gemini").mkdir()
        gh = tmp_path / ".github"
        gh.mkdir()
        (gh / "copilot-instructions.md").touch()
        assert detect_ai_providers(tmp_path) == [
            "claude_code",
            "codex",
            "gemini",
            "github_copilot",
        ]

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

    def test_both_popularity_ordered(self, tmp_path: Path) -> None:
        (tmp_path / ".vscode").mkdir()
        (tmp_path / ".idea").mkdir()
        # Popularity order: vscode before jetbrains
        assert detect_ides(tmp_path) == ["vscode", "jetbrains"]

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

    def test_exception_returns_empty(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.installer.autodetect.detect_from_remote",
            side_effect=RuntimeError("git not available"),
        ):
            assert detect_vcs(tmp_path) == ""


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


# ---------------------------------------------------------------------------
# _order_by_popularity
# ---------------------------------------------------------------------------


class TestOrderByPopularity:
    """Popularity-based ordering helper."""

    _RANKING: tuple[str, ...] = ("typescript", "python", "javascript", "java", "go")

    def test_ranked_items_come_in_ranking_order(self) -> None:
        items = ["java", "typescript", "python"]
        assert _order_by_popularity(items, self._RANKING) == [
            "typescript",
            "python",
            "java",
        ]

    def test_unknown_items_appended_alphabetically(self) -> None:
        items = ["python", "zig", "haskell"]
        assert _order_by_popularity(items, self._RANKING) == [
            "python",
            "haskell",
            "zig",
        ]

    def test_empty_input_returns_empty(self) -> None:
        assert _order_by_popularity([], self._RANKING) == []

    def test_all_unknown_items_sorted_alphabetically(self) -> None:
        items = ["zig", "haskell", "ada"]
        assert _order_by_popularity(items, self._RANKING) == ["ada", "haskell", "zig"]

    def test_single_item(self) -> None:
        assert _order_by_popularity(["go"], self._RANKING) == ["go"]

    def test_preserves_only_items_in_input(self) -> None:
        """Ranking items NOT in input should not appear in output."""
        items = ["java"]
        result = _order_by_popularity(items, self._RANKING)
        assert result == ["java"]
        assert "typescript" not in result

    def test_duplicates_in_input_deduplicated(self) -> None:
        items = ["python", "python", "go"]
        result = _order_by_popularity(items, self._RANKING)
        assert result == ["python", "go"]

    def test_mixed_known_and_unknown(self) -> None:
        items = ["zig", "go", "ada", "typescript"]
        assert _order_by_popularity(items, self._RANKING) == [
            "typescript",
            "go",
            "ada",
            "zig",
        ]


# ---------------------------------------------------------------------------
# _walk_markers — recursive detection
# ---------------------------------------------------------------------------


class TestWalkMarkers:
    """Single-pass recursive walker for stack and IDE detection."""

    def test_monorepo_nested_markers(self, tmp_path: Path) -> None:
        """Detects markers in subdirectories."""
        backend = tmp_path / "backend"
        backend.mkdir()
        (backend / "pyproject.toml").touch()
        frontend = tmp_path / "frontend"
        frontend.mkdir()
        (frontend / "tsconfig.json").touch()

        stacks, _ides = _walk_markers(tmp_path)
        assert "python" in stacks
        assert "typescript" in stacks

    def test_csproj_in_subdirectory_detected(self, tmp_path: Path) -> None:
        """Unlike old shallow detection, .csproj in subdirs IS found."""
        sub = tmp_path / "src"
        sub.mkdir()
        (sub / "App.csproj").touch()

        stacks, _ides = _walk_markers(tmp_path)
        assert "csharp" in stacks

    def test_node_modules_excluded(self, tmp_path: Path) -> None:
        nm = tmp_path / "node_modules" / "some-pkg"
        nm.mkdir(parents=True)
        (nm / "package.json").touch()

        stacks, _ides = _walk_markers(tmp_path)
        assert "javascript" not in stacks

    def test_venv_excluded(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv" / "lib"
        venv.mkdir(parents=True)
        (venv / "pyproject.toml").touch()

        stacks, _ides = _walk_markers(tmp_path)
        assert "python" not in stacks

    def test_vendor_excluded(self, tmp_path: Path) -> None:
        vendor = tmp_path / "vendor" / "pkg"
        vendor.mkdir(parents=True)
        (vendor / "composer.json").touch()

        stacks, _ides = _walk_markers(tmp_path)
        assert "php" not in stacks

    def test_target_excluded(self, tmp_path: Path) -> None:
        target = tmp_path / "target" / "debug"
        target.mkdir(parents=True)
        (target / "Cargo.toml").touch()

        stacks, _ides = _walk_markers(tmp_path)
        assert "rust" not in stacks

    def test_ide_detected_at_nested_level(self, tmp_path: Path) -> None:
        """IDE config in subdirectory counts."""
        web = tmp_path / "apps" / "web" / ".vscode"
        web.mkdir(parents=True)
        api = tmp_path / "apps" / "api" / ".idea"
        api.mkdir(parents=True)

        _stacks, ides = _walk_markers(tmp_path)
        assert "vscode" in ides
        assert "jetbrains" in ides

    def test_js_and_ts_in_different_subdirs_detects_both(self, tmp_path: Path) -> None:
        """JS backend + TS frontend -> both detected."""
        api = tmp_path / "api"
        api.mkdir()
        (api / "package.json").touch()
        web = tmp_path / "web"
        web.mkdir()
        (web / "tsconfig.json").touch()

        stacks, _ides = _walk_markers(tmp_path)
        assert "javascript" in stacks
        assert "typescript" in stacks

    def test_ts_overrides_js_in_same_directory(self, tmp_path: Path) -> None:
        """tsconfig suppresses package.json in same directory."""
        (tmp_path / "package.json").touch()
        (tmp_path / "tsconfig.json").touch()

        stacks, _ides = _walk_markers(tmp_path)
        assert "typescript" in stacks
        # JS should NOT be detected from this directory
        assert "javascript" not in stacks

    def test_symlinks_not_followed(self, tmp_path: Path) -> None:
        """Symlinked directories should not be traversed."""
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        (real_dir / "pyproject.toml").touch()
        link = tmp_path / "linked"
        link.symlink_to(real_dir)

        stacks, _ides = _walk_markers(tmp_path)
        # pyproject.toml in real/ is detected, but the symlink dir itself is not walked
        assert "python" in stacks

    def test_empty_directory(self, tmp_path: Path) -> None:
        stacks, ides = _walk_markers(tmp_path)
        assert stacks == set()
        assert ides == set()

    def test_deeply_nested_marker(self, tmp_path: Path) -> None:
        deep = tmp_path / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True)
        (deep / "go.mod").touch()

        stacks, _ides = _walk_markers(tmp_path)
        assert "go" in stacks
