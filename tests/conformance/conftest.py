"""Conformance test fixtures for spec-127 M1 (sub-spec sub-002).

Exposes the canonical roots for the live SKILL.md / agent .md surface
so tests can assert the rubric grades the *actual* repository, not a
synthetic fixture. Tests must reproduce brief §2.1 baseline grade
vector (28 A / 14 B / 6 C / 1 D) over the current 50 skills.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Repository root resolved from this conftest's location."""
    # tests/conformance/conftest.py -> repo root is two parents up.
    return Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def skills_root(project_root: Path) -> Path:
    """Path to ``.claude/skills/`` (per Claude Code conventions)."""
    return project_root / ".claude" / "skills"


@pytest.fixture(scope="session")
def agents_root(project_root: Path) -> Path:
    """Path to ``.claude/agents/``."""
    return project_root / ".claude" / "agents"
