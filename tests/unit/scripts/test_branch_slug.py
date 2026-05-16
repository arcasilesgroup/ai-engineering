"""Tests for ``branch_slug.py`` (brief §17)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / ".ai-engineering" / "scripts"

# Importable as a module by adding scripts to sys.path. Prefer module-import
# over subprocess so we can target ``compose_branch`` for golden tests.
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import branch_slug  # noqa: E402


@pytest.mark.unit
def test_compose_with_id_and_title() -> None:
    fm = {"id": "127", "title": "Skill+Agent Excellence Refactor"}
    out = branch_slug.compose_branch("feat", fm)
    assert out == "feat/spec-127-skill-agent-excellence-refactor"


@pytest.mark.unit
def test_compose_caps_at_50_chars_total() -> None:
    fm = {"id": "9999", "title": "a" * 200}
    out = branch_slug.compose_branch("feat", fm)
    assert len(out) <= branch_slug.MAX_SLUG_LEN
    assert out.startswith("feat/")
    assert not out.endswith("-")


@pytest.mark.unit
def test_compose_falls_back_when_no_frontmatter() -> None:
    assert branch_slug.compose_branch("fix", None) == "fix/work"
    assert branch_slug.compose_branch("fix", {}) == "fix/work"


@pytest.mark.unit
def test_compose_handles_spec_prefixed_id() -> None:
    fm = {"id": "spec-126", "title": "Hook NDJSON lock parity"}
    out = branch_slug.compose_branch("feat", fm)
    # Must not double-prefix: ``spec-spec-126`` is a regression marker.
    assert "spec-spec-" not in out
    assert out.startswith("feat/spec-126-")


@pytest.mark.unit
def test_invalid_prefix_raises() -> None:
    with pytest.raises(ValueError):
        branch_slug.compose_branch("invalid", {"id": "1", "title": "x"})
