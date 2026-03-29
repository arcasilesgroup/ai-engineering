"""Unit tests for vcs.repo_context — remote URL parsing and caching."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.vcs.repo_context import RepoContext, _reset_cache, get_repo_context

FAKE_ROOT = Path("/fake/repo")

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Reset module-level cache before every test."""
    _reset_cache()


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------


@patch("ai_engineering.vcs.repo_context.run_git")
def test_github_https(mock_git: object) -> None:
    mock_git.return_value = (True, "https://github.com/my-org/my-repo.git")  # type: ignore[attr-defined]
    ctx = get_repo_context(FAKE_ROOT)
    assert ctx is not None
    assert ctx == RepoContext(
        provider="github",
        organization="my-org",
        project="my-org",
        repository="my-repo",
    )


@patch("ai_engineering.vcs.repo_context.run_git")
def test_github_https_no_dotgit(mock_git: object) -> None:
    mock_git.return_value = (True, "https://github.com/org/repo")  # type: ignore[attr-defined]
    ctx = get_repo_context(FAKE_ROOT)
    assert ctx is not None
    assert ctx.provider == "github"
    assert ctx.repository == "repo"


@patch("ai_engineering.vcs.repo_context.run_git")
def test_github_ssh(mock_git: object) -> None:
    mock_git.return_value = (True, "git@github.com:my-org/my-repo.git")  # type: ignore[attr-defined]
    ctx = get_repo_context(FAKE_ROOT)
    assert ctx is not None
    assert ctx == RepoContext(
        provider="github",
        organization="my-org",
        project="my-org",
        repository="my-repo",
    )


# ---------------------------------------------------------------------------
# Azure DevOps
# ---------------------------------------------------------------------------


@patch("ai_engineering.vcs.repo_context.run_git")
def test_ado_https_modern(mock_git: object) -> None:
    mock_git.return_value = (True, "https://dev.azure.com/contoso/MyProject/_git/backend")  # type: ignore[attr-defined]
    ctx = get_repo_context(FAKE_ROOT)
    assert ctx is not None
    assert ctx == RepoContext(
        provider="azure-devops",
        organization="contoso",
        project="MyProject",
        repository="backend",
    )


@patch("ai_engineering.vcs.repo_context.run_git")
def test_ado_ssh(mock_git: object) -> None:
    mock_git.return_value = (True, "git@ssh.dev.azure.com:v3/contoso/MyProject/backend")  # type: ignore[attr-defined]
    ctx = get_repo_context(FAKE_ROOT)
    assert ctx is not None
    assert ctx == RepoContext(
        provider="azure-devops",
        organization="contoso",
        project="MyProject",
        repository="backend",
    )


@patch("ai_engineering.vcs.repo_context.run_git")
def test_ado_legacy(mock_git: object) -> None:
    mock_git.return_value = (True, "https://contoso.visualstudio.com/MyProject/_git/backend")  # type: ignore[attr-defined]
    ctx = get_repo_context(FAKE_ROOT)
    assert ctx is not None
    assert ctx == RepoContext(
        provider="azure-devops",
        organization="contoso",
        project="MyProject",
        repository="backend",
    )


@patch("ai_engineering.vcs.repo_context.run_git")
def test_ado_user_prefix(mock_git: object) -> None:
    mock_git.return_value = (True, "https://contoso@dev.azure.com/contoso/MyProject/_git/backend")  # type: ignore[attr-defined]
    ctx = get_repo_context(FAKE_ROOT)
    assert ctx is not None
    assert ctx == RepoContext(
        provider="azure-devops",
        organization="contoso",
        project="MyProject",
        repository="backend",
    )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@patch("ai_engineering.vcs.repo_context.run_git")
def test_unknown_url_returns_none(mock_git: object) -> None:
    mock_git.return_value = (True, "https://gitlab.com/org/repo.git")  # type: ignore[attr-defined]
    assert get_repo_context(FAKE_ROOT) is None


@patch("ai_engineering.vcs.repo_context.run_git")
def test_run_git_failure_returns_none(mock_git: object) -> None:
    mock_git.return_value = (False, "fatal: not a git repository")  # type: ignore[attr-defined]
    assert get_repo_context(FAKE_ROOT) is None


@patch("ai_engineering.vcs.repo_context.run_git")
def test_empty_remote_url_returns_none(mock_git: object) -> None:
    mock_git.return_value = (True, "")  # type: ignore[attr-defined]
    assert get_repo_context(FAKE_ROOT) is None


@patch("ai_engineering.vcs.repo_context.run_git")
def test_exception_returns_none(mock_git: object) -> None:
    mock_git.side_effect = OSError("boom")  # type: ignore[attr-defined]
    assert get_repo_context(FAKE_ROOT) is None


@patch("ai_engineering.vcs.repo_context.run_git")
def test_cache_prevents_second_git_call(mock_git: object) -> None:
    mock_git.return_value = (True, "https://github.com/org/repo.git")  # type: ignore[attr-defined]

    ctx1 = get_repo_context(FAKE_ROOT)
    ctx2 = get_repo_context(FAKE_ROOT)

    assert ctx1 is ctx2
    mock_git.assert_called_once()  # type: ignore[attr-defined]
