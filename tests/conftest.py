"""Shared pytest fixtures for the ai-engineering test suite.

Provides reusable fixtures for:
- Fresh project installations (tmp_path-based).
- Git repository setup with feature branches.
- Installed projects with state files.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ai_engineering.installer.service import install


@pytest.fixture()
def installed_project(tmp_path: Path) -> Path:
    """Create a fully installed project in a temporary directory.

    Returns:
        Path to the installed project root.
    """
    install(tmp_path, stacks=["python"], ides=["vscode"])
    return tmp_path


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a bare git repository in a temporary directory.

    Returns:
        Path to the git repository root.
    """
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return tmp_path


@pytest.fixture()
def installed_git_project(installed_project: Path) -> Path:
    """Create a fully installed project with a real git repo on a feature branch.

    Returns:
        Path to the installed git project root.
    """
    subprocess.run(
        ["git", "init"],
        cwd=installed_project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=installed_project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=installed_project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "add", "-A"],
        cwd=installed_project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "initial commit"],
        cwd=installed_project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "checkout", "-b", "feature/test"],
        cwd=installed_project,
        check=True,
        capture_output=True,
    )
    return installed_project
