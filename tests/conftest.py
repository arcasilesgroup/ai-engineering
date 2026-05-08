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
def _ensure_canonical_state_surface():
    """Ensure spec-125 D-125-09 canonical NDJSON files exist before tests run.

    ``framework-events.ndjson`` and ``observation-events.ndjson`` are
    append-only audit logs — gitignored, created by installer / runtime
    on first write. On fresh CI checkouts they don't exist yet, which
    breaks ``tests/unit/specs/test_state_canonical.py::test_required_files_present``
    because the canonical contract asserts the surface, not the content.

    Touching empty files is the cheapest, semantically-correct fix:
    they're append-only, so an empty file is the ground state of "no
    events emitted yet". Production install / runtime appends from
    there. Pre-existing files are preserved as-is.
    """
    state_dir = Path.cwd() / ".ai-engineering" / "state"
    if state_dir.is_dir():
        for required in ("framework-events.ndjson", "observation-events.ndjson"):
            target = state_dir / required
            if not target.exists():
                target.touch()
        # state.db is gitignored too; bootstrap a minimal SQLite DB so
        # the canonical-surface guard passes on fresh CI checkouts.
        # ``state_db.connect`` runs migrations under the hood, producing
        # the canonical schema without a separate install run.
        if not (state_dir / "state.db").exists():
            try:
                from ai_engineering.state.state_db import connect

                conn = connect(Path.cwd(), read_only=False, apply_migrations=None)
                conn.close()
            except Exception:
                # Fail-open: leave the file absent so the canonical-
                # surface assertion fires loudly rather than masking a
                # real environmental problem.
                pass
    yield


@pytest.fixture(autouse=True, scope="session")
def _detect_git_config_contamination():
    """Detect, warn, AND AUTO-RESTORE the real repo's .git/config if tests pollute it.

    Tests that run `git config user.email ...` (or any other config write) without
    `-C tmp_path` write to the real repo's .git/config. Past pollutions observed:
    `[core] bare = true`, `[core] worktree = <sibling-path>`, `[user] email/name`
    overrides — each individually capable of breaking the entire repo for the
    developer (commits fail, work tree mis-resolves, author identity changes).

    This fixture snapshots .git/config at session start and restores it verbatim
    at session end if any difference is detected. The warning is preserved as the
    bisection signal: run with `pytest -W error::UserWarning` to fail loudly on
    the offending test and identify which test needs to be fixed (typically by
    adding `cwd=tmp_path` or `-C tmp_path` to its subprocess calls).
    """
    repo_config = Path.cwd() / ".git" / "config"
    before = repo_config.read_text(encoding="utf-8") if repo_config.exists() else None

    yield

    if before is not None and repo_config.exists():
        after = repo_config.read_text(encoding="utf-8")
        if before != after:
            repo_config.write_text(before, encoding="utf-8")
            warnings.warn(
                "Tests modified the real repo .git/config — AUTO-RESTORED to pre-session state. "
                "Bisect the offending test with: pytest -W error::UserWarning. "
                "The fix is usually adding `cwd=tmp_path` (or `-C tmp_path`) to "
                "subprocess calls that invoke `git config`.",
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
