"""Unit tests for git.context — branch/SHA extraction and caching."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import call, patch

import pytest

from ai_engineering.git.context import GitContext, _reset_cache, get_git_context

FAKE_ROOT = Path("/fake/repo")

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Reset module-level cache before every test."""
    _reset_cache()


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


@patch("ai_engineering.git.context.run_git")
def test_normal_branch(mock_git: object) -> None:
    mock_git.side_effect = [  # type: ignore[attr-defined]
        (True, "feature/cool-thing"),  # branch
        (True, "abc12345"),  # SHA
    ]
    ctx = get_git_context(FAKE_ROOT)
    assert ctx is not None
    assert ctx == GitContext(branch="feature/cool-thing", commit_sha="abc12345")


@patch("ai_engineering.git.context.run_git")
def test_detached_head(mock_git: object) -> None:
    mock_git.side_effect = [  # type: ignore[attr-defined]
        (True, "HEAD"),  # detached HEAD
        (True, "deadbeef"),
    ]
    ctx = get_git_context(FAKE_ROOT)
    assert ctx is not None
    assert ctx.branch == "HEAD"
    assert ctx.commit_sha == "deadbeef"


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


@patch("ai_engineering.git.context.run_git")
def test_branch_failure_returns_none(mock_git: object) -> None:
    mock_git.return_value = (False, "fatal: not a git repository")  # type: ignore[attr-defined]
    assert get_git_context(FAKE_ROOT) is None


@patch("ai_engineering.git.context.run_git")
def test_sha_failure_returns_none(mock_git: object) -> None:
    mock_git.side_effect = [  # type: ignore[attr-defined]
        (True, "main"),
        (False, "fatal: ambiguous argument"),
    ]
    assert get_git_context(FAKE_ROOT) is None


@patch("ai_engineering.git.context.run_git")
def test_exception_returns_none(mock_git: object) -> None:
    mock_git.side_effect = OSError("boom")  # type: ignore[attr-defined]
    assert get_git_context(FAKE_ROOT) is None


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


@patch("ai_engineering.git.context.run_git")
def test_cache_prevents_second_git_call(mock_git: object) -> None:
    mock_git.side_effect = [  # type: ignore[attr-defined]
        (True, "main"),
        (True, "abc12345"),
    ]

    ctx1 = get_git_context(FAKE_ROOT)
    ctx2 = get_git_context(FAKE_ROOT)

    assert ctx1 is ctx2
    # run_git should have been called exactly twice (branch + SHA), not four times.
    assert mock_git.call_count == 2  # type: ignore[attr-defined]
    mock_git.assert_has_calls(
        [  # type: ignore[attr-defined]
            call(["rev-parse", "--abbrev-ref", "HEAD"], FAKE_ROOT),
            call(["rev-parse", "--short=8", "HEAD"], FAKE_ROOT),
        ]
    )
