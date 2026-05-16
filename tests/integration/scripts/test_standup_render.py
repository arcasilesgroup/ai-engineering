"""RED-phase integration tests for ``standup_render.py`` (spec-129 T-7).

These tests intentionally fail with ``ModuleNotFoundError`` until T-8
lands the GREEN implementation at
``.ai-engineering/scripts/skills/skill_scripts/standup_render.py``.

The script under test is expected to expose:

* ``render_standup(since: str = "7d", fmt: str = "md") -> str`` —
  programmatic entry point. ``since`` accepts the ``Nd`` shorthand
  used on the CLI; ``fmt`` is ``"md"`` (default) or ``"json"``.
* ``main(argv: list[str] | None = None) -> int`` — CLI entry point.
  Parses ``--since=<Nd>`` and ``--format=md|json`` and writes the
  rendered standup to stdout.

The fixture pattern matches T-3 (``tests/unit/scripts/_lib/
test_git_activity.py``): a real throwaway repo created via
``git init -b main`` under ``tmp_path``, with commits seeded via
``GIT_AUTHOR_DATE`` / ``GIT_COMMITTER_DATE`` env overrides so time
filtering can be exercised deterministically.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

# RED-phase import: the module does not yet exist. Collection fails
# fast with ``ModuleNotFoundError`` until T-8 lands the GREEN impl.
from skill_scripts.standup_render import (
    main,
    render_standup,
)

# Forbidden placeholder tokens — the standup output must never carry
# untemplated marker strings that would signal an LLM placeholder
# leaked through to the deterministic rendering path.
_FORBIDDEN_PLACEHOLDERS = (
    "TODO",
    "XXX",
    "<insert>",
    "{summary}",
    "<your-narrative>",
)


# ---------------------------------------------------------------------------
# Fixtures — real git repo, no mocks (mirrors T-3 pattern)
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Create a fresh git repo under ``tmp_path`` for fidelity over mocks."""
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


def _commit_at(repo: Path, filename: str, message: str, when: datetime | None = None) -> str:
    """Create a commit and return its sha. ``when`` overrides commit date."""
    (repo / filename).write_text(f"content for {filename}\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", filename],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    env = os.environ.copy()
    if when is not None:
        iso = when.isoformat()
        env["GIT_AUTHOR_DATE"] = iso
        env["GIT_COMMITTER_DATE"] = iso
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo,
        check=True,
        capture_output=True,
        env=env,
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _merge_at(repo: Path, branch: str, message: str, when: datetime | None = None) -> str:
    """Create a non-fast-forward merge commit, optionally with a fixed date."""
    env = os.environ.copy()
    if when is not None:
        iso = when.isoformat()
        env["GIT_AUTHOR_DATE"] = iso
        env["GIT_COMMITTER_DATE"] = iso
    subprocess.run(
        ["git", "merge", "--no-ff", "-m", message, branch],
        cwd=repo,
        check=True,
        capture_output=True,
        env=env,
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
def repo_with_merges(tmp_repo: Path) -> Path:
    """Seed ``tmp_repo`` with two merges in the last 7 days.

    Layout:
        * base commit on main
        * feature/a merged 2 days ago
        * feature/b merged 1 day ago
    """
    now = datetime.now(UTC)
    _commit_at(tmp_repo, "base.txt", "feat: base", when=now - timedelta(days=10))

    # feature/a — merged 2 days ago.
    subprocess.run(
        ["git", "checkout", "-b", "feature/a"],
        cwd=tmp_repo,
        check=True,
        capture_output=True,
    )
    _commit_at(tmp_repo, "a.txt", "feat: a", when=now - timedelta(days=3))
    subprocess.run(
        ["git", "checkout", "main"],
        cwd=tmp_repo,
        check=True,
        capture_output=True,
    )
    _merge_at(tmp_repo, "feature/a", "Merge branch 'feature/a'", when=now - timedelta(days=2))

    # feature/b — merged 1 day ago.
    subprocess.run(
        ["git", "checkout", "-b", "feature/b"],
        cwd=tmp_repo,
        check=True,
        capture_output=True,
    )
    _commit_at(tmp_repo, "b.txt", "feat: b", when=now - timedelta(days=2))
    subprocess.run(
        ["git", "checkout", "main"],
        cwd=tmp_repo,
        check=True,
        capture_output=True,
    )
    _merge_at(tmp_repo, "feature/b", "Merge branch 'feature/b'", when=now - timedelta(days=1))

    return tmp_repo


@pytest.fixture
def chdir_to(monkeypatch: pytest.MonkeyPatch):
    """Chdir to a repo path; restored after the test."""

    def _chdir(path: Path) -> None:
        monkeypatch.chdir(path)

    return _chdir


# ---------------------------------------------------------------------------
# 1. Markdown output structure — required sections
# ---------------------------------------------------------------------------


def test_markdown_output_contains_yesterday_section(repo_with_merges: Path, chdir_to) -> None:
    chdir_to(repo_with_merges)
    output = render_standup(since="7d", fmt="md")
    assert "## Yesterday" in output


def test_markdown_output_contains_today_section(repo_with_merges: Path, chdir_to) -> None:
    chdir_to(repo_with_merges)
    output = render_standup(since="7d", fmt="md")
    assert "## Today" in output


def test_markdown_output_contains_blockers_section(repo_with_merges: Path, chdir_to) -> None:
    chdir_to(repo_with_merges)
    output = render_standup(since="7d", fmt="md")
    assert "## Blockers" in output


# ---------------------------------------------------------------------------
# 2. Yesterday section formatted via render_checklist
# ---------------------------------------------------------------------------


def test_yesterday_section_renders_checklist_of_recent_merges(
    repo_with_merges: Path, chdir_to
) -> None:
    chdir_to(repo_with_merges)
    output = render_standup(since="7d", fmt="md")
    # ``markdown_render.render_checklist`` emits ``- [x] <text>`` or
    # ``- [ ] <text>``. Merged work is "done", so the marker is ``[x]``.
    assert "- [x] " in output
    # Each seeded merge's subject must appear in the checklist.
    assert "feature/a" in output
    assert "feature/b" in output


# ---------------------------------------------------------------------------
# 3. Counts match the seeded fixture exactly
# ---------------------------------------------------------------------------


def test_counts_in_output_match_seeded_commit_fixture(repo_with_merges: Path, chdir_to) -> None:
    chdir_to(repo_with_merges)
    output = render_standup(since="7d", fmt="md")
    # Two seeded merges (feature/a + feature/b) must yield exactly two
    # checklist rows under the Yesterday section.
    checklist_lines = [
        line
        for line in output.splitlines()
        if line.startswith("- [x] ") or line.startswith("- [ ] ")
    ]
    assert len(checklist_lines) == 2, (
        f"expected 2 checklist rows for 2 seeded merges, got {len(checklist_lines)}: "
        f"{checklist_lines}"
    )


# ---------------------------------------------------------------------------
# 4. JSON output shape
# ---------------------------------------------------------------------------


def test_json_format_emits_parseable_dict_with_expected_keys(
    repo_with_merges: Path, chdir_to
) -> None:
    chdir_to(repo_with_merges)
    output = render_standup(since="7d", fmt="json")
    payload = json.loads(output)
    assert isinstance(payload, dict)
    for key in ("yesterday", "today", "blockers", "since", "branch"):
        assert key in payload, f"JSON payload missing key: {key}"


def test_json_yesterday_lists_two_seeded_merges(repo_with_merges: Path, chdir_to) -> None:
    chdir_to(repo_with_merges)
    output = render_standup(since="7d", fmt="json")
    payload = json.loads(output)
    assert isinstance(payload["yesterday"], list)
    assert len(payload["yesterday"]) == 2


# ---------------------------------------------------------------------------
# 5. --since=7d boundary — commit at exactly 7d is INCLUDED
# ---------------------------------------------------------------------------


def test_since_7d_includes_commit_exactly_seven_days_old(tmp_repo: Path, chdir_to) -> None:
    """A merge dated exactly 7 days ago must appear in the standup window."""
    now = datetime.now(UTC)
    _commit_at(tmp_repo, "base.txt", "feat: base", when=now - timedelta(days=20))

    subprocess.run(
        ["git", "checkout", "-b", "feature/boundary"],
        cwd=tmp_repo,
        check=True,
        capture_output=True,
    )
    _commit_at(tmp_repo, "boundary.txt", "feat: boundary", when=now - timedelta(days=8))
    subprocess.run(
        ["git", "checkout", "main"],
        cwd=tmp_repo,
        check=True,
        capture_output=True,
    )
    # Merge stamped exactly 7 days ago.
    _merge_at(
        tmp_repo,
        "feature/boundary",
        "Merge branch 'feature/boundary'",
        when=now - timedelta(days=7),
    )

    chdir_to(tmp_repo)
    output = render_standup(since="7d", fmt="json")
    payload = json.loads(output)
    # The 7-day-old merge must be present (inclusive lower bound).
    assert len(payload["yesterday"]) >= 1, (
        "merge dated exactly 7 days ago must be included in --since=7d window"
    )


def test_since_7d_excludes_commit_older_than_seven_days(tmp_repo: Path, chdir_to) -> None:
    """A merge older than the window must NOT appear."""
    now = datetime.now(UTC)
    _commit_at(tmp_repo, "base.txt", "feat: base", when=now - timedelta(days=30))

    subprocess.run(
        ["git", "checkout", "-b", "feature/old"],
        cwd=tmp_repo,
        check=True,
        capture_output=True,
    )
    _commit_at(tmp_repo, "old.txt", "feat: old", when=now - timedelta(days=20))
    subprocess.run(
        ["git", "checkout", "main"],
        cwd=tmp_repo,
        check=True,
        capture_output=True,
    )
    # Merge stamped 15 days ago — outside the 7d window.
    _merge_at(
        tmp_repo,
        "feature/old",
        "Merge branch 'feature/old'",
        when=now - timedelta(days=15),
    )

    chdir_to(tmp_repo)
    output = render_standup(since="7d", fmt="json")
    payload = json.loads(output)
    assert payload["yesterday"] == [], (
        f"merge 15 days old must be excluded, got: {payload['yesterday']}"
    )


# ---------------------------------------------------------------------------
# 6. No LLM placeholder strings leak through
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("placeholder", _FORBIDDEN_PLACEHOLDERS)
def test_output_contains_no_placeholder_strings(
    repo_with_merges: Path, chdir_to, placeholder: str
) -> None:
    chdir_to(repo_with_merges)
    md_output = render_standup(since="7d", fmt="md")
    json_output = render_standup(since="7d", fmt="json")
    assert placeholder not in md_output, (
        f"markdown output leaked placeholder {placeholder!r}: {md_output!r}"
    )
    assert placeholder not in json_output, (
        f"JSON output leaked placeholder {placeholder!r}: {json_output!r}"
    )


# ---------------------------------------------------------------------------
# 7. Performance smoke — 10 calls under 500 ms p95
# ---------------------------------------------------------------------------


def test_render_standup_p95_under_500ms_over_10_calls(repo_with_merges: Path, chdir_to) -> None:
    chdir_to(repo_with_merges)
    durations: list[float] = []
    for _ in range(10):
        start = time.monotonic()
        render_standup(since="7d", fmt="md")
        durations.append(time.monotonic() - start)
    durations.sort()
    # p95 of 10 samples = the 10th element (index 9 after sort).
    p95 = durations[-1]
    assert p95 < 0.5, (
        f"render_standup p95 over 10 calls was {p95 * 1000:.1f}ms (budget 500ms) — "
        f"regression on the hot path; samples: {durations}"
    )


# ---------------------------------------------------------------------------
# 8. Empty-repo edge case — valid output with empty sections, no crash
# ---------------------------------------------------------------------------


def test_empty_repo_returns_valid_standup_markdown(tmp_repo: Path, chdir_to) -> None:
    chdir_to(tmp_repo)
    output = render_standup(since="7d", fmt="md")
    # Sections still rendered even when there is no activity.
    assert "## Yesterday" in output
    assert "## Today" in output
    assert "## Blockers" in output
    # No checklist rows for an empty repo.
    checklist_lines = [
        line
        for line in output.splitlines()
        if line.startswith("- [x] ") or line.startswith("- [ ] ")
    ]
    assert checklist_lines == [], (
        f"empty repo must produce no checklist rows, got: {checklist_lines}"
    )


def test_empty_repo_returns_valid_standup_json(tmp_repo: Path, chdir_to) -> None:
    chdir_to(tmp_repo)
    output = render_standup(since="7d", fmt="json")
    payload = json.loads(output)
    assert payload["yesterday"] == []
    assert payload["today"] == []
    assert payload["blockers"] == []


# ---------------------------------------------------------------------------
# 9. CLI entry point — argv parsing for --since and --format
# ---------------------------------------------------------------------------


def test_main_accepts_format_json_flag(
    repo_with_merges: Path, chdir_to, capsys: pytest.CaptureFixture[str]
) -> None:
    chdir_to(repo_with_merges)
    exit_code = main(["--since=7d", "--format=json"])
    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert "yesterday" in payload
    assert "today" in payload
    assert "blockers" in payload


def test_main_default_format_is_markdown(
    repo_with_merges: Path, chdir_to, capsys: pytest.CaptureFixture[str]
) -> None:
    chdir_to(repo_with_merges)
    exit_code = main(["--since=7d"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "## Yesterday" in captured.out
    assert "## Today" in captured.out
    assert "## Blockers" in captured.out


# Silence unused-import warnings for ``sys`` (kept available for future
# typing/diagnostic needs without forcing a re-edit during GREEN).
_ = sys
