"""Git activity probe — typed records over `git log` (spec-129 T-4).

This module wraps `git` subprocesses to expose a narrow, typed surface
that skill scripts can use without re-implementing git plumbing.

## Semantics — `commits_since(ref)`

`commits_since(ref)` returns the commits reachable from `HEAD` but **not**
from `ref`. This is the standard `<ref>..HEAD` semantics (exclusive lower
bound): the named ref itself is excluded, only commits introduced
**after** it appear. This matches `git rev-list <ref>..HEAD` and is the
mental model maintainers should preserve — do not switch to inclusive
ranges without updating both the implementation and `tests/unit/scripts/
_lib/test_git_activity.py`.

## Subprocess discipline

Every `git` call uses `check=True, capture_output=True, text=True`,
running with `cwd=Path.cwd()` by default. Callers that need a different
working tree should `os.chdir` (or `monkeypatch.chdir` in tests) before
calling — keeping the parameter list small avoids API churn and matches
how downstream skill scripts are written.

## Performance

`last_commit()` is on the hot path for several skills; its single
`git log -1 --format=...` invocation keeps the per-call cost well under
the 50 ms p95 budget cited in spec-129 (the test enforces a 5 s ceiling
for 100 calls).

## Dependencies

Stdlib + `subprocess` only. No `gitpython`, no third-party clients —
spec-129 prohibits adding dependencies for this layer.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

# Sentinel used in `git log --format` between fields. ASCII unit separator
# (0x1F) never appears in commit subjects or email addresses, so it is a
# safe delimiter even for unusual commit messages.
_FIELD_SEP = "\x1f"

# `%H` full sha, `%s` subject, `%ae` author email, `%aI` ISO-8601 strict
# date (UTC offset, e.g. `2026-05-10T12:34:56+00:00`). The strict form
# avoids locale-dependent parsing and stays stable across git versions.
_FORMAT = _FIELD_SEP.join(["%H", "%s", "%ae", "%aI"])


class NoCommitsError(Exception):
    """Raised when a git operation requires commits but the repo has none."""


@dataclass(frozen=True)
class Commit:
    """Typed record for a single commit."""

    sha: str
    subject: str
    author_email: str
    date: str


@dataclass(frozen=True)
class Merge:
    """Typed record for a merge commit."""

    sha: str
    subject: str
    author_email: str
    date: str


def _run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a `git` subprocess with the project-standard flags.

    Uses `check=False` internally so callers can inspect non-zero exits
    (e.g. empty repo on `git log`) without catching `CalledProcessError`
    everywhere.
    """
    return subprocess.run(
        ["git", *args],
        cwd=cwd if cwd is not None else Path.cwd(),
        check=False,
        capture_output=True,
        text=True,
    )


def _parse_line(line: str) -> tuple[str, str, str, str]:
    """Split a `git log --format=...` line into its four fields."""
    parts = line.split(_FIELD_SEP)
    # `git log` may emit fewer fields if a commit subject is empty —
    # pad to four so callers always get a stable tuple shape.
    while len(parts) < 4:
        parts.append("")
    return parts[0], parts[1], parts[2], parts[3]


def recent_merges(since_iso: str) -> list[Merge]:
    """Return merge commits authored on/after `since_iso`.

    `since_iso` is forwarded to `git log --since=...`, which accepts the
    same ISO-8601 strings produced by `datetime.isoformat()`.
    """
    result = _run_git(
        [
            "log",
            "--merges",
            f"--since={since_iso}",
            f"--format={_FORMAT}",
        ]
    )
    if result.returncode != 0:
        # Empty repo or other benign failure — treat as no merges.
        return []
    merges: list[Merge] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        sha, subject, author_email, date = _parse_line(line)
        merges.append(Merge(sha=sha, subject=subject, author_email=author_email, date=date))
    return merges


def last_commit() -> Commit:
    """Return the HEAD commit as a typed record.

    Raises `NoCommitsError` if the repository has no commits yet.
    """
    result = _run_git(["log", "-1", f"--format={_FORMAT}"])
    if result.returncode != 0 or not result.stdout.strip():
        # `git log` exits non-zero on an empty repo with a message like
        # "fatal: your current branch 'main' does not have any commits yet".
        raise NoCommitsError("Repository has no commits at HEAD")
    sha, subject, author_email, date = _parse_line(result.stdout.splitlines()[0])
    return Commit(sha=sha, subject=subject, author_email=author_email, date=date)


def commits_since(ref: str) -> list[Commit]:
    """Return commits reachable from `HEAD` but not from `ref`.

    Uses `<ref>..HEAD` (exclusive lower bound): `ref` itself is excluded,
    only commits introduced after it appear. Returned in `git log` order
    (newest first).
    """
    result = _run_git(["log", f"{ref}..HEAD", f"--format={_FORMAT}"])
    if result.returncode != 0:
        return []
    commits: list[Commit] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        sha, subject, author_email, date = _parse_line(line)
        commits.append(Commit(sha=sha, subject=subject, author_email=author_email, date=date))
    return commits


def branch_age_days(branch: str) -> int:
    """Return whole days since the branch's most recent commit.

    Uses `git log -1 --format=%ct <branch>` for a Unix timestamp, then
    diffs against the current wall-clock time. Returns `0` for branches
    whose most recent commit is today.
    """
    result = _run_git(["log", "-1", "--format=%ct", branch])
    if result.returncode != 0 or not result.stdout.strip():
        raise NoCommitsError(f"Branch '{branch}' has no commits")
    commit_ts = int(result.stdout.strip())
    # Wall-clock comparison is fine here — we only care about whole-day
    # buckets, and `time.monotonic()` cannot be diffed against an
    # absolute epoch timestamp.
    import time as _time

    now_ts = int(_time.time())
    age_seconds = max(now_ts - commit_ts, 0)
    return age_seconds // 86400
