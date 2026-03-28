"""Integration tests: provider x VCS install matrix."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer.service import install

pytestmark = pytest.mark.integration

# Matrix: (providers, vcs, expected_files)
_SINGLE_PROVIDER_CASES = [
    (["claude_code"], "github", ["CLAUDE.md", ".claude"]),
    (["claude_code"], "azure_devops", ["CLAUDE.md", ".claude"]),
    (["github_copilot"], "github", ["AGENTS.md", ".github/copilot-instructions.md"]),
    (
        ["github_copilot"],
        "azure_devops",
        ["AGENTS.md", ".github/copilot-instructions.md"],
    ),
    (["gemini"], "github", ["GEMINI.md", ".gemini"]),
    (["gemini"], "azure_devops", ["GEMINI.md", ".gemini"]),
    (["codex"], "github", ["AGENTS.md", ".codex"]),
    (["codex"], "azure_devops", ["AGENTS.md", ".codex"]),
]

_MULTI_PROVIDER_CASES = [
    (
        ["claude_code", "github_copilot"],
        "github",
        ["CLAUDE.md", "AGENTS.md", ".claude", ".github/copilot-instructions.md"],
    ),
    (
        ["claude_code", "gemini"],
        "github",
        ["CLAUDE.md", "GEMINI.md", ".claude", ".gemini"],
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
            ides=["terminal"],
            vcs_provider=vcs,
            ai_providers=providers,
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
            ides=["terminal"],
            vcs_provider=vcs,
            ai_providers=providers,
        )
        for expected_path in expected:
            full = clean_target / expected_path
            assert full.exists() or full.is_dir(), f"Missing: {expected_path}"
