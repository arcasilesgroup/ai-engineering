"""RED-phase tests for `_lib/git_activity.py` (spec-129 T-3).

These tests intentionally fail with `ImportError` / `ModuleNotFoundError`
until T-4 lands the GREEN implementation under
`.ai-engineering/scripts/skills/_lib/git_activity.py`.

The fixture pattern uses a real throwaway repo via `git init` (preferred
over mocking `subprocess`) so the parser is exercised against authentic
`git log --format=...` output. Per the python override conventions
(`overrides/python/conventions.md`), the module under test is expected to
expose:

  - `recent_merges(since_iso: str) -> list[Merge]`
  - `last_commit() -> Commit`
  - `commits_since(ref: str) -> list[Commit]`
  - `branch_age_days(branch: str) -> int`
  - `NoCommitsError` raised by `last_commit()` on empty repos
  - `Commit`, `Merge` typed records (NamedTuple or @dataclass)

Tests live under `tests/unit/scripts/_lib/` so the `tests/unit/` mirror of
`.ai-engineering/scripts/skills/_lib/` is preserved per the TDD harness
override.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

# RED-phase import: the module does not yet exist. The import below is
# wrapped in the standard `from ... import` form so the module collection
# itself fails fast — every test below will surface as
# ImportError/ModuleNotFoundError until T-4 lands.
from skill_scripts_lib.git_activity import (  # noqa: F401
    Commit,
    Merge,
    NoCommitsError,
    branch_age_days,
    commits_since,
    last_commit,
    recent_merges,
)

# ---------------------------------------------------------------------------
# Fixtures — real git repo, no mocks
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Create a fresh git repo under `tmp_path` for fidelity over mocks."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return repo


def _commit(repo: Path, filename: str, message: str) -> str:
    """Create a commit and return its sha."""
    (repo / filename).write_text(f"content for {filename}\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", filename],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _merge_commit(repo: Path, branch: str, message: str) -> str:
    """Create a non-fast-forward merge commit on the current branch."""
    subprocess.run(
        ["git", "merge", "--no-ff", "-m", message, branch],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@pytest.fixture
def repo_with_history(tmp_repo: Path) -> Path:
    """Seed `tmp_repo` with two regular commits + one feature-branch merge."""
    _commit(tmp_repo, "a.txt", "feat: add a")
    _commit(tmp_repo, "b.txt", "feat: add b")
    subprocess.run(
        ["git", "checkout", "-b", "feature/x"],
        cwd=tmp_repo,
        check=True,
        capture_output=True,
    )
    _commit(tmp_repo, "c.txt", "feat: add c on feature")
    subprocess.run(
        ["git", "checkout", "main"],
        cwd=tmp_repo,
        check=True,
        capture_output=True,
    )
    _merge_commit(tmp_repo, "feature/x", "Merge branch 'feature/x'")
    return tmp_repo


@pytest.fixture
def chdir_to(monkeypatch: pytest.MonkeyPatch):
    """Chdir to a repo path; restored after the test."""

    def _chdir(path: Path) -> None:
        monkeypatch.chdir(path)

    return _chdir


# ---------------------------------------------------------------------------
# 1. recent_merges
# ---------------------------------------------------------------------------


def test_recent_merges_returns_merge_commits_since_iso(repo_with_history: Path, chdir_to) -> None:
    chdir_to(repo_with_history)
    yesterday = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    merges = recent_merges(yesterday)
    assert isinstance(merges, list)
    assert len(merges) == 1
    merge = merges[0]
    # Typed record fields: sha, subject, author_email, date
    assert isinstance(merge.sha, str)
    assert len(merge.sha) >= 7
    assert merge.subject.startswith("Merge branch")
    assert merge.author_email == "test@example.com"
    assert isinstance(merge.date, str)


def test_recent_merges_returns_empty_when_no_merges_in_window(tmp_repo: Path, chdir_to) -> None:
    _commit(tmp_repo, "lonely.txt", "feat: solo")
    chdir_to(tmp_repo)
    yesterday = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    assert recent_merges(yesterday) == []


def test_recent_merges_excludes_commits_before_since_iso(repo_with_history: Path, chdir_to) -> None:
    chdir_to(repo_with_history)
    # A future timestamp must filter out all merges.
    tomorrow = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    assert recent_merges(tomorrow) == []


# ---------------------------------------------------------------------------
# 2. last_commit
# ---------------------------------------------------------------------------


def test_last_commit_returns_head_as_typed_record(tmp_repo: Path, chdir_to) -> None:
    sha = _commit(tmp_repo, "head.txt", "feat: at head")
    chdir_to(tmp_repo)
    commit = last_commit()
    assert isinstance(commit.sha, str)
    assert commit.sha == sha
    assert commit.subject == "feat: at head"
    assert commit.author_email == "test@example.com"
    assert isinstance(commit.date, str)


def test_last_commit_reflects_latest_commit_after_new_commit(tmp_repo: Path, chdir_to) -> None:
    _commit(tmp_repo, "first.txt", "feat: first")
    chdir_to(tmp_repo)
    first = last_commit()
    second_sha = _commit(tmp_repo, "second.txt", "feat: second")
    second = last_commit()
    assert second.sha == second_sha
    assert second.sha != first.sha
    assert second.subject == "feat: second"


# ---------------------------------------------------------------------------
# 3. commits_since
# ---------------------------------------------------------------------------


def test_commits_since_returns_commits_between_ref_and_head(tmp_repo: Path, chdir_to) -> None:
    base_sha = _commit(tmp_repo, "base.txt", "feat: base")
    a_sha = _commit(tmp_repo, "a.txt", "feat: a")
    b_sha = _commit(tmp_repo, "b.txt", "feat: b")
    chdir_to(tmp_repo)
    commits = commits_since(base_sha)
    assert isinstance(commits, list)
    shas = [c.sha for c in commits]
    assert a_sha in shas
    assert b_sha in shas
    # Base ref itself is excluded (exclusive lower bound, standard git semantics).
    assert base_sha not in shas


def test_commits_since_returns_empty_when_ref_is_head(tmp_repo: Path, chdir_to) -> None:
    head_sha = _commit(tmp_repo, "x.txt", "feat: x")
    chdir_to(tmp_repo)
    assert commits_since(head_sha) == []


def test_commits_since_returns_typed_commit_records(tmp_repo: Path, chdir_to) -> None:
    base_sha = _commit(tmp_repo, "base.txt", "feat: base")
    _commit(tmp_repo, "later.txt", "feat: later")
    chdir_to(tmp_repo)
    commits = commits_since(base_sha)
    assert len(commits) == 1
    c = commits[0]
    assert isinstance(c.sha, str)
    assert c.subject == "feat: later"
    assert c.author_email == "test@example.com"
    assert isinstance(c.date, str)


# ---------------------------------------------------------------------------
# 4. branch_age_days
# ---------------------------------------------------------------------------


def test_branch_age_days_returns_zero_for_branch_committed_today(tmp_repo: Path, chdir_to) -> None:
    _commit(tmp_repo, "today.txt", "feat: today")
    subprocess.run(
        ["git", "checkout", "-b", "fresh"],
        cwd=tmp_repo,
        check=True,
        capture_output=True,
    )
    _commit(tmp_repo, "fresh.txt", "feat: fresh on branch")
    chdir_to(tmp_repo)
    assert branch_age_days("fresh") == 0


def test_branch_age_days_returns_integer_for_older_branch(tmp_repo: Path, chdir_to) -> None:
    """Force an older commit date via GIT_*_DATE env vars."""
    (tmp_repo / "old.txt").write_text("old\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "old.txt"],
        cwd=tmp_repo,
        check=True,
        capture_output=True,
    )
    old_date = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = old_date
    env["GIT_COMMITTER_DATE"] = old_date
    subprocess.run(
        ["git", "commit", "-m", "feat: old"],
        cwd=tmp_repo,
        check=True,
        capture_output=True,
        env=env,
    )
    subprocess.run(
        ["git", "checkout", "-b", "stale"],
        cwd=tmp_repo,
        check=True,
        capture_output=True,
    )
    chdir_to(tmp_repo)
    age = branch_age_days("stale")
    assert isinstance(age, int)
    # Allow a one-day tolerance for clock-rounding at the day boundary.
    assert 9 <= age <= 11


# ---------------------------------------------------------------------------
# 5. Empty-repo edge case — typed exception
# ---------------------------------------------------------------------------


def test_last_commit_raises_no_commits_error_on_empty_repo(tmp_repo: Path, chdir_to) -> None:
    chdir_to(tmp_repo)
    with pytest.raises(NoCommitsError):
        last_commit()


def test_no_commits_error_is_a_proper_exception_subclass() -> None:
    assert issubclass(NoCommitsError, Exception)


# ---------------------------------------------------------------------------
# 6. Performance smoke — 100 calls under 5 s
# ---------------------------------------------------------------------------


def test_last_commit_100_calls_under_5_seconds(tmp_repo: Path, chdir_to) -> None:
    _commit(tmp_repo, "perf.txt", "feat: perf")
    chdir_to(tmp_repo)
    start = time.monotonic()
    for _ in range(100):
        commit = last_commit()
        assert commit.sha
    elapsed = time.monotonic() - start
    assert elapsed < 5.0, (
        f"last_commit() x100 took {elapsed:.2f}s (budget 5.0s) — regression on the hot path"
    )


# ---------------------------------------------------------------------------
# 7. Type contracts — Commit and Merge are properly typed records
# ---------------------------------------------------------------------------


def test_commit_record_exposes_required_fields(tmp_repo: Path, chdir_to) -> None:
    _commit(tmp_repo, "shape.txt", "feat: shape")
    chdir_to(tmp_repo)
    commit = last_commit()
    for field in ("sha", "subject", "author_email", "date"):
        assert hasattr(commit, field), f"Commit missing field: {field}"


def test_merge_record_exposes_required_fields(repo_with_history: Path, chdir_to) -> None:
    chdir_to(repo_with_history)
    yesterday = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    merges = recent_merges(yesterday)
    assert merges
    merge = merges[0]
    for field in ("sha", "subject", "author_email", "date"):
        assert hasattr(merge, field), f"Merge missing field: {field}"


# Silence unused-import warnings for `sys` (kept available for future
# typing/diagnostic needs without forcing a re-edit during GREEN).
_ = sys
