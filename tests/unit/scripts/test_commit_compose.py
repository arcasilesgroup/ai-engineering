"""Tests for ``commit_compose.py`` (brief §17)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / ".ai-engineering" / "scripts"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import commit_compose  # noqa: E402


@pytest.mark.unit
def test_template_with_spec_and_task_and_desc() -> None:
    out = commit_compose.compose_subject(
        commit_type="feat",
        spec_id="127",
        task="3.4",
        desc="adopt rubric",
    )
    assert out == "feat(spec-127): Task 3.4 -- adopt rubric"


@pytest.mark.unit
def test_template_with_spec_and_no_desc_yields_placeholder() -> None:
    out = commit_compose.compose_subject(
        commit_type="feat",
        spec_id="127",
        task="3.4",
        desc=None,
    )
    assert commit_compose.DESC_PLACEHOLDER in out
    assert out.startswith("feat(spec-127): Task 3.4 -- ")


@pytest.mark.unit
def test_template_without_spec() -> None:
    out = commit_compose.compose_subject(
        commit_type="fix",
        spec_id=None,
        task=None,
        desc="patch upstream regression",
    )
    assert out == "fix: patch upstream regression"


@pytest.mark.unit
def test_template_without_task_drops_task_clause() -> None:
    out = commit_compose.compose_subject(
        commit_type="chore",
        spec_id="42",
        task=None,
        desc="bump deps",
    )
    assert out == "chore(spec-42): bump deps"
    assert "Task" not in out


@pytest.mark.unit
def test_invalid_type_raises() -> None:
    with pytest.raises(ValueError):
        commit_compose.compose_subject(
            commit_type="bogus",
            spec_id=None,
            task=None,
            desc="x",
        )


@pytest.mark.unit
def test_handles_spec_prefixed_id() -> None:
    out = commit_compose.compose_subject(
        commit_type="feat",
        spec_id="spec-127",
        task=None,
        desc="x",
    )
    assert "spec-spec-" not in out
    assert "feat(spec-127):" in out
