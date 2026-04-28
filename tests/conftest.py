"""Shared pytest fixtures for the ai-engineering test suite.

Provides reusable fixtures for:
- Git config isolation (prevents test identity leaking into real repo).
- Fresh project installations (tmp_path-based).
- Git repository setup with feature branches.
- Installed projects with state files.
"""

from __future__ import annotations

import os
import subprocess
import warnings
from pathlib import Path

import pytest

from ai_engineering.installer.service import install

TEST_GIT_USER = "Test User"
TEST_GIT_EMAIL = "test@example.com"


@pytest.fixture(autouse=True)
def _stop_orphaned_mocks():
    """Stop any unittest.mock patches that leaked across test boundaries.

    Some legacy tests in the suite create patches via ``mock.patch().start()``
    without a paired ``stop()`` (or fail before the stop runs), leaving the
    patch active for subsequent tests. This causes order-dependent flakes
    where ``subprocess.run`` calls in later tests get intercepted and
    return synthetic results instead of executing real binaries.

    Per-test ``patch.stopall()`` is a belt-and-suspenders cleanup: it stops
    any patch started via ``unittest.mock.patch`` (including those started
    by other tests) at the END of every test, so the next test starts with
    a clean state. Tests that legitimately use ``mock.patch`` as context
    manager or pytest's ``mocker`` fixture are unaffected -- their patches
    are already cleaned up by their own teardown.
    """
    yield
    from unittest.mock import patch as _patch

    _patch.stopall()


@pytest.fixture(autouse=True, scope="session")
def _git_test_isolation():
    """Isolate git config so tests never read or write real global/system config.

    Sets GIT_CONFIG_GLOBAL and GIT_CONFIG_SYSTEM to /dev/null, preventing
    git from touching the user's real config. Identity is provided via
    GIT_AUTHOR_* / GIT_COMMITTER_* env vars instead.
    """
    env_overrides = {
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_COMMITTER_NAME": TEST_GIT_USER,
        "GIT_COMMITTER_EMAIL": TEST_GIT_EMAIL,
        "GIT_AUTHOR_NAME": TEST_GIT_USER,
        "GIT_AUTHOR_EMAIL": TEST_GIT_EMAIL,
    }
    old_values = {}
    for key, value in env_overrides.items():
        old_values[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    for key, old in old_values.items():
        if old is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old


@pytest.fixture(autouse=True, scope="session")
def _detect_git_config_contamination():
    """Warn if tests modify the real repo's .git/config."""
    repo_config = Path.cwd() / ".git" / "config"
    before = repo_config.read_text(encoding="utf-8") if repo_config.exists() else None

    yield

    if before is not None and repo_config.exists():
        after = repo_config.read_text(encoding="utf-8")
        if before != after:
            warnings.warn(
                "Tests modified the real repo .git/config! "
                "Run: git config --local --unset user.name && "
                "git config --local --unset user.email",
                stacklevel=1,
            )


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
    return tmp_path


@pytest.fixture()
def git_repo_with_commit(git_repo: Path) -> Path:
    """Create a git repo with an initial commit on a feature branch.

    Returns:
        Path to the git repository root.
    """
    (git_repo / ".gitkeep").touch()
    subprocess.run(["git", "add", "-A"], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "checkout", "-b", "feature/test"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    return git_repo


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
