"""Tests for ``doc_gate.py`` (brief §17)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".ai-engineering" / "scripts" / "doc_gate.py"
SCRIPT_DIR = SCRIPT.parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import doc_gate  # noqa: E402


@pytest.mark.unit
def test_watched_path_without_doc_fails() -> None:
    ok, reason = doc_gate.evaluate(["src/foo.py"])
    assert ok is False
    assert "without CHANGELOG" in reason or "without" in reason.lower()


@pytest.mark.unit
def test_watched_path_with_changelog_passes() -> None:
    ok, _reason = doc_gate.evaluate(["src/foo.py", "CHANGELOG.md"])
    assert ok is True


@pytest.mark.unit
def test_watched_path_with_readme_passes() -> None:
    ok, _reason = doc_gate.evaluate(["tools/skill_lint/cli.py", "README.md"])
    assert ok is True


@pytest.mark.unit
def test_skill_change_requires_doc() -> None:
    ok, _reason = doc_gate.evaluate([".claude/skills/ai-start/SKILL.md"])
    assert ok is False


@pytest.mark.unit
def test_only_non_watched_paths_passes() -> None:
    ok, reason = doc_gate.evaluate(["docs/notes.md", "tests/unit/foo.py"])
    assert ok is True
    assert "skipped" in reason.lower() or "no watched" in reason.lower()


@pytest.mark.unit
def test_subdirectory_changelog_does_not_satisfy_root_gate() -> None:
    """Per the contract, only repo-root CHANGELOG.md satisfies the gate."""
    ok, _reason = doc_gate.evaluate(["src/foo.py", "packages/foo/CHANGELOG.md"])
    assert ok is False


@pytest.mark.unit
def test_cli_exit_codes() -> None:
    # Failing exit code = 1
    fail = subprocess.run(
        [sys.executable, str(SCRIPT), "--changed-paths", "src/foo.py"],
        capture_output=True,
        text=True,
    )
    assert fail.returncode == 1

    # Passing exit code = 0
    ok = subprocess.run(
        [sys.executable, str(SCRIPT), "--changed-paths", "src/foo.py,CHANGELOG.md"],
        capture_output=True,
        text=True,
    )
    assert ok.returncode == 0
