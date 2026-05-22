"""Integration tests: provider x VCS install matrix."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer.service import install

# Matrix: (surfaces, vcs, expected_files) — spec-133 D-133-16 canonical surface IDs.
_SINGLE_PROVIDER_CASES = [
    (["claude-code"], "github", ["CLAUDE.md", ".claude"]),
    (["claude-code"], "azure_devops", ["CLAUDE.md", ".claude"]),
    (["github-copilot"], "github", ["AGENTS.md", ".github/copilot-instructions.md"]),
    (
        ["github-copilot"],
        "azure_devops",
        ["AGENTS.md", ".github/copilot-instructions.md"],
    ),
    (["antigravity"], "github", ["AGENTS.md", ".agents"]),
    (["antigravity"], "azure_devops", ["AGENTS.md", ".agents"]),
    (["codex"], "github", ["AGENTS.md", ".codex"]),
    (["codex"], "azure_devops", ["AGENTS.md", ".codex"]),
]

_MULTI_PROVIDER_CASES = [
    (
        ["claude-code", "github-copilot"],
        "github",
        ["CLAUDE.md", "AGENTS.md", ".claude", ".github/copilot-instructions.md"],
    ),
    (
        ["claude-code", "antigravity"],
        "github",
        ["CLAUDE.md", "AGENTS.md", ".claude", ".agents"],
    ),
]


@pytest.fixture()
def clean_target(tmp_path: Path) -> Path:
    """Create a minimal git repo target."""
    import subprocess

    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


class TestInstallMatrix:
    @pytest.mark.parametrize("providers,vcs,expected", _SINGLE_PROVIDER_CASES)
    def test_single_provider(
        self,
        clean_target: Path,
        providers: list[str],
        vcs: str,
        expected: list[str],
    ) -> None:
        """Single provider installs the correct files."""
        install(
            clean_target,
            stacks=["python"],
            vcs_provider=vcs,
            surfaces=providers,
        )
        for expected_path in expected:
            full = clean_target / expected_path
            assert full.exists() or full.is_dir(), f"Missing: {expected_path}"

    @pytest.mark.parametrize("providers,vcs,expected", _MULTI_PROVIDER_CASES)
    def test_multi_provider(
        self,
        clean_target: Path,
        providers: list[str],
        vcs: str,
        expected: list[str],
    ) -> None:
        """Multi-provider installs all provider files."""
        install(
            clean_target,
            stacks=["python"],
            vcs_provider=vcs,
            surfaces=providers,
        )
        for expected_path in expected:
            full = clean_target / expected_path
            assert full.exists() or full.is_dir(), f"Missing: {expected_path}"

    @pytest.mark.parametrize(
        "providers,vcs,_expected", _SINGLE_PROVIDER_CASES + _MULTI_PROVIDER_CASES
    )
    def test_retired_gemini_assets_are_not_installed(
        self,
        clean_target: Path,
        providers: list[str],
        vcs: str,
        _expected: list[str],
    ) -> None:
        """Current installs do not create retired Gemini CLI or legacy Antigravity assets."""
        install(
            clean_target,
            stacks=["python"],
            vcs_provider=vcs,
            surfaces=providers,
        )
        for retired_path in ("GEMINI.md", ".gemini", ".agent"):
            assert not (clean_target / retired_path).exists(), retired_path
