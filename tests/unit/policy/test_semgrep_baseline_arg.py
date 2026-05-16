"""spec-141 M1.T5 — `--baseline-commit` argv injection contract.

Verifies that the pre-push semgrep argv built by
:func:`ai_engineering.policy.checks.stack_runner._semgrep_pre_push_cmd`
includes ``--baseline-commit <sha>`` when invoked from a git repository
that has a resolvable merge-base against ``origin/main``.

The hot-path budget (D-141-03) is enforced by the helper itself
(:func:`_semgrep_baseline_ref` caps the ``git merge-base`` subprocess at
1 s). This test asserts the **functional** outcome: the argv carries
the baseline when one is available, and falls back to a non-incremental
invocation when git cannot resolve a merge-base (brand-new repo, no
remote).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ai_engineering.policy.checks.stack_runner import (
    _semgrep_baseline_ref,
    _semgrep_pre_push_cmd,
)


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git command in ``cwd``; surface stderr on failure."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    )


def _init_repo_with_origin_main(repo: Path) -> str:
    """Initialise a repo, seed a commit, and stand up ``origin/main``.

    Returns the SHA of the seeded commit, which is also the merge-base
    against ``origin/main`` for any subsequent HEAD.
    """
    _git(repo, "init", "--initial-branch=main", ".")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "spec-141 test")
    (repo / "README.md").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "seed")
    sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    # Synthesize ``origin/main`` ref by writing into refs/remotes — we
    # don't need a real remote, only a resolvable ref for ``git merge-base``.
    refs_remotes = repo / ".git" / "refs" / "remotes" / "origin"
    refs_remotes.mkdir(parents=True, exist_ok=True)
    (refs_remotes / "main").write_text(f"{sha}\n", encoding="utf-8")
    return sha


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """A throwaway git repo with a seeded ``origin/main`` ref."""
    _init_repo_with_origin_main(tmp_path)
    return tmp_path


def test_baseline_ref_resolves_to_merge_base(git_repo: Path) -> None:
    """The helper returns the merge-base SHA when ``origin/main`` exists."""
    expected = _git(git_repo, "merge-base", "HEAD", "origin/main").stdout.strip()
    assert expected, "fixture must produce a merge-base SHA"

    actual = _semgrep_baseline_ref(cwd=git_repo)

    assert actual == expected


def test_pre_push_cmd_contains_baseline_commit(git_repo: Path) -> None:
    """The constructed argv carries ``--baseline-commit <sha>`` in a real repo."""
    cmd = _semgrep_pre_push_cmd(cwd=git_repo)

    assert "--baseline-commit" in cmd, f"expected --baseline-commit in argv, got: {cmd!r}"
    idx = cmd.index("--baseline-commit")
    # Argv shape: [..., "--baseline-commit", "<sha>", ...]
    assert idx + 1 < len(cmd), f"--baseline-commit must be followed by a SHA argument, got: {cmd!r}"
    sha = cmd[idx + 1]
    # Real SHAs are 40-char lowercase hex; the helper passes through
    # whatever ``git merge-base`` prints. A loose sanity check suffices.
    assert len(sha) == 40 and all(c in "0123456789abcdef" for c in sha), (
        f"baseline arg does not look like a git SHA: {sha!r}"
    )


def test_pre_push_cmd_preserves_canonical_head_and_tail(git_repo: Path) -> None:
    """The head (``semgrep --config .semgrep.yml``) and tail (``--error .``) stay intact."""
    cmd = _semgrep_pre_push_cmd(cwd=git_repo)

    assert cmd[0] == "semgrep"
    assert cmd[1] == "--config"
    assert cmd[2] == ".semgrep.yml"
    # The tail is ``--error .``; baseline pair sits between head and tail.
    assert cmd[-2] == "--error"
    assert cmd[-1] == "."


def test_pre_push_cmd_falls_back_without_merge_base(tmp_path: Path) -> None:
    """When ``origin/main`` cannot resolve, the gate skips ``--baseline-commit``.

    A brand-new repo with no remote MUST keep the gate functional --
    incremental scan is an optimisation, not a precondition.
    """
    # Fresh repo with NO origin/main ref.
    _git(tmp_path, "init", "--initial-branch=main", ".")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "spec-141 test")
    (tmp_path / "README.md").write_text("seed\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-m", "seed")

    cmd = _semgrep_pre_push_cmd(cwd=tmp_path)

    assert "--baseline-commit" not in cmd, (
        f"no remote should mean no --baseline-commit, got: {cmd!r}"
    )
    # Canonical shape preserved end-to-end.
    assert cmd == ["semgrep", "--config", ".semgrep.yml", "--error", "."]
