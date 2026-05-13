"""Test no-orphan-dirs check enforces D-133-13 hard deletions."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.skill_lint.checks.no_orphan_dirs import (
    RubricResult,
    check_no_orphan_dirs,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]


def test_repo_root_has_zero_orphan_dirs() -> None:
    """Real repo passes the rule — D-133-13 deletions persist."""
    results = check_no_orphan_dirs(_REPO_ROOT)
    assert len(results) == 1
    assert results[0].severity == "OK", results[0].reason


def test_detects_resurrected_orphan_dir(tmp_path: Path) -> None:
    """If `.ai-engineering/adapters/` reappears the check flips to MAJOR."""
    (tmp_path / ".ai-engineering" / "adapters").mkdir(parents=True)

    results = check_no_orphan_dirs(tmp_path)
    assert len(results) == 1
    assert results[0].severity == "MAJOR"
    assert ".ai-engineering/adapters" in results[0].reason


def test_detects_resurrected_handlers_dir(tmp_path: Path) -> None:
    """A reappearing ai-debug/handlers/ in any surface mirror flips MAJOR."""
    (tmp_path / ".claude" / "skills" / "ai-debug" / "handlers").mkdir(parents=True)

    results = check_no_orphan_dirs(tmp_path)
    assert len(results) == 1
    assert results[0].severity == "MAJOR"
    assert ".claude/skills/ai-debug/handlers" in results[0].reason


def test_detects_resurrected_contexts_languages(tmp_path: Path) -> None:
    """`.ai-engineering/contexts/languages/` resurrection is caught."""
    (tmp_path / ".ai-engineering" / "contexts" / "languages").mkdir(parents=True)

    results = check_no_orphan_dirs(tmp_path)
    assert results[0].severity == "MAJOR"
    assert ".ai-engineering/contexts/languages" in results[0].reason


def test_missing_repo_root_is_ok(tmp_path: Path) -> None:
    """Pointing at a non-existent root produces OK with a clear reason."""
    ghost = tmp_path / "does" / "not" / "exist"
    results = check_no_orphan_dirs(ghost)
    assert len(results) == 1
    assert results[0].severity == "OK"
    assert "not found" in results[0].reason


def test_rubric_result_rejects_bad_severity() -> None:
    """The dataclass refuses invalid severity values at construction."""
    with pytest.raises(ValueError):
        RubricResult("no_orphan_dirs", "FATAL", "bogus")
