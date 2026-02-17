"""Shared pytest fixtures for the ai-engineering test suite.

Provides reusable fixtures for:
- Fresh project installations (tmp_path-based).
- Git repository setup with feature branches.
- Installed projects with state files.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from ai_engineering.installer.service import install


@pytest.fixture(autouse=True, scope="session")
def _disable_git_commit_signing():
    """Disable git commit signing for all tests.

    Prevents failures in CI/sandbox environments where the signing key
    configured in the global git config is unavailable.
    """
    env_overrides = {
        "GIT_COMMITTER_NAME": "Test User",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "GIT_AUTHOR_NAME": "Test User",
        "GIT_AUTHOR_EMAIL": "test@example.com",
    }
    old_values = {}
    for key, value in env_overrides.items():
        old_values[key] = os.environ.get(key)
        os.environ[key] = value

    # Disable commit signing globally for the test session
    subprocess.run(
        ["git", "config", "--global", "commit.gpgsign", "false"],
        capture_output=True,
    )

    yield

    for key, old in old_values.items():
        if old is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old


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
        ["git", "init", "-b", "main"],
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
        ["git", "init", "-b", "main"],
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
